#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2016-2017 China Telecommunication Co., Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

__author__ = 'liyiqun'

import sys

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen
import json
import threading
import traceback

from topofetch import *
from jsonrpc import *
from microsrvurl import *
from test import *
from base_handler import base_handler
import datetime
import copy
from db_util import mysql_utils

class flow_sched_handler(base_handler):
    '''
    Flow schedule also need asynchronous callbacks because it is a time consuming action.
    Flow status: Not Scheduled(-1), scheduling(0), scheduled(1), De-scheduling(2)
     A successful de-scheduling of a flow will change the status to -1.
     If callback of scheduling reports a status 0, that means scheduling is time out. Keep the original status.
     If callback of de-scheduling reports a status 2, that means de-scheduling is time out.  Keep the original status.
    '''
    def initialize(self):
        super(flow_sched_handler, self).initialize()
        self.subreq_tunnel_map = {'flow_sched_add_flow': 'ms_tunnel_add_flow',
                                  'flow_sched_del_flow': 'ms_tunnel_update_flow',

                                  }
        self.subreq_ctrler_map = {'flow_sched_add_flow': 'ms_controller_add_flow',
                                  'flow_sched_del_flow': 'ms_controller_del_flow'}

        self.flow_sched_req_map = {'flow_sched_add_flow': self.add_flow,
                                  'flow_sched_del_flow': self.del_flow,
                                  'flow_sched_callback':self.cb_flow_ctrl,
                                  'flow_sched_get_flow_by_equip':self.get_cur_flow,
                                  'flow_sched_simulate':self.flow_simu,
                                  'flow_sched_del_lsp_flow':self.del_all_flow}
        self.flow_op_map = {'flow_sched_add_flow': 1,
                                  'flow_sched_del_flow': 0}

        self.log = 0
        pass

    def form_response(self, req):
        resp = {'response':req['request'], 'ts':req['ts'], 'trans_id':req['trans_id'], 'err_code':0, 'msg':''}
        return resp


    @tornado.gen.coroutine
    def get_base_info(self, req, op):
        flows = None
        flow_map = {}
        user_data = None
        try:
            # call customer service to get ips
            args = {'uids':[req['args']['cust_uid']]}
            resp = yield self.do_query(microsrvurl_dict['microsrv_cust_url'], 'ms_cust_get_customer',args)
            flows = resp['result']['customers'][0]['ips']

            #Get current flow's lsp info  from tunnel ms. one flow is allowed to be in more than 1 LSP.
            fs = [f['uid'] for f in flows]
            args = {'flow_uids':fs}
            resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], 'ms_tunnel_get_lsp_by_flow', args)
            flow_map = resp['result']

            #Get user_data from tunnel ms
            req_lsp = req['args']['lsp_uid']
            user_data = None
            if op:
                args = {'lsp_uids':[req_lsp]}
                resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], 'ms_tunnel_get_lsp', args)
                resp = resp['result']['lsps'][0]    #Here we always query a single lsp.
                if 'user_data' in resp:
                    user_data = resp['user_data']
            else:
                ' Delete flow. we need user_data of flow instead of lsp'
                args = {'lsp_uid': req_lsp, 'flow_uids':[str(x['uid']) for x in flows]}
                resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], 'ms_tunnel_get_flow', args)
                user_data = resp['result']

        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return((flows,flow_map,user_data))


    @tornado.gen.coroutine
    def add_flow(self, req):
        ' get customer ips from customer_flow microservice, call controller and then tunnel'
        final_resp = {'err_code':-1, 'result': {}}
        # flow_add_tag = True
        # db = mysql_utils('topology')
        # db.exec_sql('Update flag set flow_add_flag = 1 where id = 1')
        # db.commit()
        # db.close()
        try:
            req_lsp = req['args']['lsp_uid']
            flows, flow_map, user_data = yield self.get_base_info(req, 1)
            for f in flows:
                fid = f['uid']

                #check if the necessary operation on this flow.
                if fid in flow_map:
                    'The flow is in LSP'
                    lsp_list = [p['lsp_uid'] for p in flow_map[fid]]
                    if req_lsp in lsp_list:
                        continue

                # call controller service to control the flow

                args = {'lsp_uid':req_lsp, 'flow':f, 'user_data':user_data, 'callback':'flow_sched_callback'}
                resp = yield self.do_query(microsrvurl_dict['microsrv_controller_url'], self.subreq_ctrler_map[req['request']], args)
                if resp['err_code'] != 0:
                    raise tornado.gen.Return(final_resp)

                #call tunnel to add this flow, with status 0
                status = 0
                args = {'flow_uid':fid, 'lsp_uid':req_lsp, 'status':status}
                if resp['result'] is not None and 'user_data' in resp['result']:
                    ud = resp['result']['user_data']
                    args['user_data'] = ud
                resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'],  self.subreq_tunnel_map[req['request']], args)
                pass

            #Add/Remove customer to/from to LSP info.
            cust_args = {'lsp_uid':req_lsp, 'cust_uid':req['args']['cust_uid']}
            method = 'ms_tunnel_add_customer_to_lsp'
            resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], method, cust_args)
            final_resp['err_code'] = 0

        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)
        pass


    @tornado.gen.coroutine
    def del_flow(self, req):
        ' get customer ips from customer_flow microservice, call controller and then tunnel'
        final_resp = {'err_code':-1, 'result': {}}
        # flow_add_tag = False
        db = mysql_utils('topology')
        db.exec_sql('Update flag set flow_add_flag = 0 where id = 1')
        db.commit()
        db.close()
        try:
            req_lsp = req['args']['lsp_uid']
            flows, flow_map, user_data = yield self.get_base_info(req, 0)
            for f in flows:
                fid = f['uid']

                #check if the necessary operation on this flow.
                if fid in flow_map:
                    'The flow is in LSP'
                    lsp_list = [p['lsp_uid'] for p in flow_map[fid]]
                    if req_lsp not in lsp_list:
                        continue
                else:
                    ' flow is not in any LSP'
                    continue

                # call controller service to control the flow
                args = {'lsp_uid':req_lsp, 'flow':f, 'user_data':user_data[fid]['user_data'] if fid in user_data else None, 'callback':'flow_sched_callback'}
                resp = yield self.do_query(microsrvurl_dict['microsrv_controller_url'], self.subreq_ctrler_map[req['request']], args)
                if resp['err_code'] != 0:
                    raise tornado.gen.Return(final_resp)

                #call tunnel to add this flow, with status 0
                status = 2
                args = {'flow_uid':fid, 'lsp_uid':req_lsp, 'status':status}
                if resp['result'] is not None and 'user_data' in resp['result']:
                    ud = resp['result']['user_data']
                    args['user_data'] = ud
                resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'],  self.subreq_tunnel_map[req['request']], args)
                pass

            #Add/Remove customer to/from to LSP info.
            cust_args = {'lsp_uid':req_lsp, 'cust_uid':req['args']['cust_uid']}
            method = 'ms_tunnel_del_customer_from_lsp'
            resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], method, cust_args)
            final_resp['err_code'] = 0

        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)
        pass

    @tornado.gen.coroutine
    def del_all_flow(self, req):

        final_resp = {'err_code':-1, 'result':{}}
        try:
            lsp = req['args']['lsp_uid']
            flows = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], 'ms_tunnel_get_flow', {'lsp_uid': lsp})
            for f in flows:
                # call controller service to control the flow
                if 'user_data' not in f or len(f['user_data']) < 1:
                    continue
                args = {'lsp_uid':lsp, 'flow':f['flow_uid'], 'user_data':f['user_data'], 'callback':'flow_sched_callback'}
                resp = yield self.do_query(microsrvurl_dict['microsrv_controller_url'], self.subreq_ctrler_map[req['request']], args)
                pass

            final_resp['err_code'] = 0
            pass
        except:
            traceback.print_exc()
            pass
        raise tornado.gen.Return(final_resp)

    @tornado.gen.coroutine
    def cb_flow_ctrl(self, req):
        ' get customer ips from customer_flow microservice, call controller and then tunnel'
        final_resp = {'err_code':-1, 'result':{}}
        try:
            status = int(req['args']['status'])
            if status == 0 or status == 2:
                final_resp['err_code'] = 0
                raise tornado.gen.Return(final_resp)

            method = 'ms_tunnel_update_flow' if status == 1 else 'ms_tunnel_del_flow'
            args = {'flow_uid':req['args']['flow_uid'], 'status':status, 'lsp_uid':req['args']['lsp_uid']}
            if 'user_data' in req['args']:
                args['user_data'] = req['args']['user_data']
            resp = yield self.do_query(microsrvurl_dict['microsrv_tunnel_url'], method, args)
            if resp['err_code'] != 0:
                raise tornado.gen.Return(final_resp)
            else:
                final_resp['err_code'] = 0
        except (LookupError,TypeError):
            traceback.print_exc()
            pass
        raise tornado.gen.Return(final_resp)
        pass

    @tornado.gen.coroutine
    def get_cur_flow(self, req):
        '''
            1. The req contains 'equip_uid' argument.  This func call ms_flow to get current flows in this equip.
            2. Current flows is a list of {src, dst, vlink_uid, bps}
            3. Aggregate all flows into {cust_uid, cust_name, bps, next_hop_uid, next_hop_name} and return the result
        '''
        final_resp = {'err_code':-1, 'result':{}}
        try:
            req = req['args']
            equip, vlink = None, None
            sub_arg = {}
            if 'equip_uid' in req:
                equip = str(req['equip_uid'])
                sub_arg = {'equip_uid':equip}
            elif 'vlink_uid' in req:
                vlink = str(req['vlink_uid'])
                sub_arg = {'vlink_uid':vlink}

            #Call ms_flow to get flow
            resp = yield self.do_query(microsrvurl_dict['microsrv_flow_url'], 'ms_flow_get_flow', sub_arg)
            flows = resp['result']['flows']

            # Form dest ip list and get customer of all flow.
            ips = {}
            for f in flows:
                ips[f['dst']] = 0
            ip_list = [x for x in ips]

            resp = yield self.do_query(microsrvurl_dict['microsrv_cust_url'], 'ms_cust_get_customer_by_ip', {'ips':ip_list})
            custs = resp['result']

            #Aggregate data.  cust_flows is {cust_uid: {cust_name, hops:{next_hop_uid:{next_hop_name, bps} } }}
            cust_flows = {}
            for f in flows:
                c = custs[f['dst']] if f['dst'] in custs else {'name':'Unknown', 'cust_uid':'-1'}
                cid = c['cust_uid']
                try:
                    next = str(f['next_hop_uid'])
                    if cid in cust_flows:
                        fs = cust_flows[cid]['hops']
                        if next in fs:
                            link = fs[next]
                            link['bps'] += f['bps']
                        else:
                            fs[next] =  {'next_hop_name':self.application.equips[next]['name'], 'bps': f['bps']}
                    else:
                        hops = {next:{'next_hop_name':self.application.equips[next]['name'], 'bps': f['bps']}}
                        cust_flows[cid] = {'cust_name':c['name'], 'hops':hops}
                except (KeyError,LookupError):
                    traceback.print_exc()
                    pass
                pass

            #form output flow list
            flow_list = []
            for c in cust_flows:
                f = {'cust_uid':c, 'cust_name':cust_flows[c]['cust_name']}
                hops = cust_flows[c]['hops']
                for h in hops:
                    fc = copy.copy(f)
                    fc['next_hop_name'] = hops[h]['next_hop_name']
                    fc['next_hop_uid'] = h
                    fc['bps'] =  hops[h]['bps']
                    flow_list.append(fc)
                    pass
                pass

            total = sum([float(x['bps'] )for x in flow_list])
            for f in flow_list:
                f['percentage'] = float(f['bps'])*100.0 / total if total > 0 else 0

            # Sort the list.
            flow_list.sort(reverse=True, key=lambda x:x['bps'])

            final_resp['err_code'] = 0
            final_resp['result'] = {'flows':flow_list}

        except (LookupError, KeyError):
            traceback.print_exc()

        raise tornado.gen.Return(final_resp)

    @tornado.gen.coroutine
    def flow_simu(self, req):
        '''
            Simulate a flow schedule and show the status of concerned links before/after the flow schedule.
             Input: {"args": {"lsp_path": ["9", "11","12","10"], "bps":91.45, "next_hop_uid":"10"}, "request": "flow_sched_simulate", "ts": "20160602112215", "trans_id": 1464837735}
             Output: {"orig_path":[{"from_router_name":"a", "to_router_name":"b", "ratio_before": 34, "ratio_after":47}], "lsp_path":[{"from_router_name":"x", "to_router_name":"y", "ratio_before": 25, "ratio_after":45}, {"from_router_name":"s", "to_router_name":"t", "ratio_before": 13, "ratio_after":34}]}

             1. Fetch link status from topo_man. Get list of [{dequip,sequip,dport,sport,bandwidth, percentage}]
             2. Find the current link util ratio of orignal path. from first node of LSP, to next_hop_uid, (xxx, zzz)
             3. Find current link util ratio of LSP path.
             4. Update the new util ratio according to the speed of the flow to be scheduled.

        '''
        final_resp = {'err_code':-1, 'result':{}}

        try:
            # Fetch link status
            resp = yield self.do_query(microsrvurl_dict['te_topo_man_url'],'topo_man_get_vlinks', {} )
            vlinks = resp['result']['vlinks']
            ls_map = self.form_link_status_map(vlinks)

            args = req['args']
            result = {}
            cur_speed = float(args['bps'])
            equips = self.application.equips


            # Original flow path
            lsp_path = args['lsp_path']
            orig_s = lsp_path[0]
            orig_e = args['next_hop_uid']
            k = str(orig_s) + str(orig_e)
            orig_util = ls_map[k]
            percent = orig_util['percentage']
            bw = orig_util['bandwidth']
            occu = (float(percent)/100.0 * float(bw))
            free = float(bw) * 0.92 - occu

            overlap = 0
            if orig_e == lsp_path[1]:
                'LSP overlaps with current hop.'
                new_perc = percent
                new_occu = occu
                new_free = free
                overlap = 1
            else:
                new_perc = (occu - cur_speed) * 100.0 / float(bw)
                new_occu = occu - cur_speed
                new_free = free + cur_speed

            result['orig_path'] = [{'from_router_name':equips[orig_s]['name'], 'to_router_name':equips[orig_e]['name'],
                                    'ratio_before':percent, 'ratio_after':new_perc,
                                    'occup_before':occu, 'occup_after':new_occu,
                                    'free_before':free, 'free_after':new_free}]


            #LSP path
            path = []
            for i in range(0, len(lsp_path)-1):
                orig_s = lsp_path[i]
                orig_e = lsp_path[i+1]
                k = str(orig_s) + str(orig_e)
                orig_util = ls_map[k]
                percent = orig_util['percentage']
                bw = orig_util['bandwidth']
                occu = (float(percent)/100.0 * float(bw))
                free = float(bw) * 0.92 - occu

                if i == 0 and overlap == 1:
                    new_perc = percent
                    new_occu = occu
                    new_free = free
                else:
                    new_perc = (occu + cur_speed) * 100.0 / float(bw)
                    new_occu = occu + cur_speed
                    new_free = free - cur_speed

                path.append({'from_router_name':equips[orig_s]['name'], 'to_router_name':equips[orig_e]['name'],
                                    'ratio_before':percent, 'ratio_after':new_perc,
                                    'occup_before':occu, 'occup_after':new_occu,
                                    'free_before':free, 'free_after':new_free})

                pass

            result['lsp_path'] = path

            final_resp['err_code'] = 0
            final_resp['result'] = result

        except (KeyError, LookupError):
            traceback.print_exc()

        raise tornado.gen.Return(final_resp)



    def form_link_status_map(self, utils):
        ' Genrate a map of from_to:utils map'
        ls_map = {}
        e_map = self.application.equips
        for u in utils:
            se = u['sequip']
            de = u['dequip']
            if se not in e_map or de not in e_map:
                continue
            key = str(se) + str(de)
            ls_map[key] = {'bandwidth':u['bandwidth'], 'percentage':u['percentage']}
            pass
        return ls_map



    def get(self):
        self.write('Not allowed')
        return

    @tornado.gen.coroutine
    def post(self):
        try:
            ctnt = self.request.body
            req = json.loads(str(ctnt))
            self.req = req
            resp = self.form_response(req)
            res = None
            if 'request' not in req or req['request'] not in self.flow_sched_req_map:
                resp['err_code'] = -1
                resp['msg'] = 'Unrecognised method'
                self.write(json.dumps(resp))
                self.finish()
                return

            res = yield self.flow_sched_req_map[req['request']](req)
            resp['result'] = res['result']
            resp['err_code'] = res['err_code']
            self.write(resp)
            self.finish()

        except Exception, data:
            print str(Exception) + str(data)
            self.write('Internal Server Error')
            self.finish()
            traceback.print_exc()

    pass

class flow_sched_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', flow_sched_handler),
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)
        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=5000),
                        self.get_topo )
        self.equips = None
        pass

    def get_topo(self):
        'Get topo data from topo service'
        rpc = base_rpc(microsrvurl_dict['microsrv_topo_url'])
        rpc.form_request('ms_topo_get_equip', {})
        resp = rpc.do_sync_post()
        try:
            equips = resp['routers']
            e_map = {}
            for e in equips:
                e_map[e['uid']] = e

            if len(e_map) == 0:
                tornado.ioloop.IOLoop.instance().add_timeout(
                                datetime.timedelta(milliseconds=5000),
                                self.get_topo)
            else:
                self.equips = e_map

                # #Generate a port-equip map
                # pe_map = {}
                # for e in equips:
                #     for p in e['ports']:
                #         pe_map[p['uid']] = e['uid']
                #
                # self.port_map = pe_map

        except:
            traceback.print_exc()
            pass

if __name__ == '__main__':
    app = flow_sched_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(32773)
    tornado.ioloop.IOLoop.instance().start()
