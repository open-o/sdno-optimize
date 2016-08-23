#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'liyiqun'

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
import datetime
from base_handler import base_handler
from err import *
from tornado_swagger import swagger
import os
import os.path
from flow_sche_serv import *

swagger.docs()

class lsp_handler(base_handler):
    '''
    LSP CRUD operations:
    - LSP status:   creating(0), up(1), down(-1), missing(-2), deleting(2), deleted(3)
    - On LSP creation request:
      1. Create LSP in tunnel ms, with status 0.
      2. Call controller ms to create LSP with callback.
         - Fail: Call tunnel ms to delete the LSP and return error to the caller
         - OK: save the user_data into tunnel ms and then return status to caller
      3. On callback from controller:
         - up: call tunnel ms to update the status to 1 and add 'path' data
         - down: call tunnel ms to update the status to -1
         - creating: call controller ms to delete the LSP without callback (to avoid the zombie LSP occupies resources)
           and call tunnel ms to update the status to -1.
    - On LSP delete request:
      1. Call controller ms to delete the LSP with callbacks.
         - OK: call tunnel ms to update the LSP status to 2 and return response to the caller.
         - Fail: Do nothing and return fault response to the caller.
      2. On callback from controller:
         - OK: call tunnel ms to change the status to 3
         - Fail: update the tunnel status to 1 to allow callers to delete it again.
    '''
    def initialize(self):
        super(lsp_handler, self).initialize()
        self.subreq_tunnel_map = {'lsp_man_get_lsp': 'ms_tunnel_get_lsp',
                           'lsp_man_del_lsp': 'ms_tunnel_del_lsp',
                           'lsp_man_delete_lsp': 'ms_tunnel_del_lsp',
                           'lsp_man_update_lsp': 'ms_tunnel_update_lsp',
                           'lsp_man_add_lsp' : 'ms_tunnel_add_lsp',
                           'lsp_man_get_cust_by_lsp':'ms_tunnel_get_cust_by_lsp',
                           'lsp_man_get_lsp_by_cust':'ms_tunnel_get_lsp_by_cust'
                           }

        self.subreq_ctrler_map = {'lsp_man_get_lsp': 'ms_controller_get_lsp',
                           'lsp_man_del_lsp': 'ms_controller_del_lsp',
                           'lsp_man_delete_lsp': 'ms_controller_del_lsp',
                           'lsp_man_update_lsp': 'ms_controller_update_lsp',
                           'lsp_man_add_lsp' : 'ms_controller_add_lsp'}

        self.lsp_req_map = {'lsp_man_get_lsp' : self.get_lsp,
                            'lsp_man_del_lsp': self.update_or_delete_lsp,
                            'lsp_man_delete_lsp': self.update_or_delete_lsp,
                           'lsp_man_update_lsp': self.update_or_delete_lsp ,
                           'lsp_man_add_lsp' : self.add_lsp,
                            'lsp_man_cb_lsp' : self.cb_lsp,
                            'lsp_man_get_cust_by_lsp':self.get_cust_by_lsp,
                            'lsp_man_get_lsp_by_cust':self.get_lsp_by_cust}

        self.log = 0
        pass

    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        resp['ts'] = req['ts']
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        return resp

    @tornado.gen.coroutine
    def get_lsp_by_cust(self, req):
        final_resp = {'err_code':-1, 'result':{}}
        try:
            # Get lsp uids of each customer
            custs = req['args']['cust_uids']
            resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map[req['request']], req['args'])
            lsp_uids = {}
            if resp is not None and 'result' in resp:
                lsp_uids = resp['result']
            lsp_dict = {}
            for c in lsp_uids:
                for lsp in lsp_uids[c]:
                    lsp_dict[lsp['lsp_uid']] = None

            #get lsp details
            resp2 = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map['lsp_man_get_lsp'],
                                        {'lsp_uids':lsp_dict.keys()})
            lsps = resp2['result']['lsps']
            lsp_map = {}
            for p in lsps:
                lsp_map[p['uid']] = p

            #Aggregate data
            res = {}
            for cust_uid in custs:
                lsp_list = []
                if cust_uid in lsp_uids:
                    for p in lsp_uids[cust_uid]:
                        lsp_list.append(lsp_map[p['lsp_uid']])
                    res[cust_uid] = lsp_list
            final_resp['err_code'] = 0
            final_resp['result'] = res


        except (TypeError,LookupError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)


    @tornado.gen.coroutine
    def get_cust_by_lsp(self,req):
        final_resp = {'err_code':-1, 'result':{}}
        try:
            lsps = req['args']['lsps']
            if 'from_router_uid' not in lsps[0]:
                'ingress node is missing in request.'
                resp = yield self.do_query(microsrv_tunnel_url,'ms_tunnel_get_lsp_by_uids',
                                           {'lsp_uids':[x['uid'] for x in lsps]})
                # A map of {uid: {lsp obj}}
                lsp_detail = resp['result']
                for p in lsps:
                    if p['uid'] in lsp_detail:
                        p['from_router_uid'] = lsp_detail[p['uid']]['from_router_uid']
                    pass

            lsp_uids = [p['uid'] for p in lsps]

            # Get customer uids with input lsp_uids
            args = {'lsp_uids':lsp_uids}
            resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map[req['request']], args)
            if resp['err_code'] != MS_OK:
                raise tornado.gen.Return(final_resp)

            # form a customer list.
            custs = resp['result']
            cust_dict = {}
            for lsp in lsp_uids:
                if lsp in custs:
                    for c in custs[lsp]:
                        cust_dict[c] = None

            # Call customer ms to get detail info.
            if len(cust_dict) == 0:
                final_resp['err_code'] = 0
                raise tornado.gen.Return(final_resp)
            resp = yield self.do_query(microsrv_cust_url, 'ms_cust_get_customer', {'uids':cust_dict.keys()})
            res = resp['result']['customers']
            for c in res:
                cust_dict[c['uid']] = c

            # Get current bitrates of each ingress nodes
            #----------------------------------------------------------------------------------
            ingress_uids = [p['from_router_uid'] for p in lsps]
            flow_resp = yield self.do_query(microsrv_flow_url, 'ms_flow_get_flow', {'ingress_uids':[ingress_uids]})
            flow_resp = flow_resp['result']
            #resp is a map of ingress_uid:flows
            # Form the IP list to match customer.
            ips = {}
            for p in flow_resp:
                for f in flow_resp[p]:
                    ips[f['src']] = None
            # call customer ms to convert ips to customers
            cust_match = yield self.do_query(microsrv_cust_url, 'ms_cust_get_customer_by_ip', {"ips":ips.keys()})
            ip_custs = cust_match['result']
            #Sum up the flow bps by customers
            cust_bps={}
            for p in flow_resp:
                for f in flow_resp[p]:
                    ip = f['src']
                    if ip in ip_custs:
                        cust = ip_custs[ip]['cust_uid']
                        bps = f['bps']
                        if cust in cust_bps:
                            cust_bps[cust] = int(cust_bps[cust]) + int(bps)
                        else:
                            cust_bps[cust] = int(bps)
            # Set bps to customers
            for cust in cust_bps:
                if cust in cust_dict:
                    c = cust_dict[cust]
                    c['bps'] = cust_bps[cust]
            #------------------------------------------------------------------------------------

            # Aggregate the info.
            for lsp in lsp_uids:
                if lsp in custs:
                    cs = [cust_dict[c] for c in custs[lsp]]
                    custs[lsp] = cs

            final_resp['err_code'] = 0
            final_resp['result'] = custs
        except (TypeError,LookupError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)

    @tornado.gen.coroutine
    def get_lsp(self, req):
        ' Get all lsps from tunnel micro service. No interface with controller '
        resp = {'err_code':-1, 'result':{}}
        try:
            resp = yield self.do_query(microsrv_tunnel_url,self.subreq_tunnel_map[req['request']], req['args'] )

            # Change path into detail information for convenience of view
            equips = self.application.equips
            lsps = resp['result']['lsps']
            for p in lsps:
                uid = p['uid']
                if 'from_router_uid' in p:
                    eid = p['from_router_uid']
                    if eid in equips:
                        e = equips[eid]
                        p['from_router_name'] = '' if 'name' not in e else e['name']
                if 'to_router_uid' in p:
                    eid = p['to_router_uid']
                    if eid in equips:
                        e = equips[eid]
                        p['to_router_name'] = '' if 'name' not in e else e['name']

                if 'path' not in p:
                    continue
                path = p['path']
                detail_path = []
                for e_uid in path:
                    if e_uid in equips:
                        detail_path.append(equips[e_uid])
                    else:
                        detail_path.append({})
                p['path'] = detail_path


        except (LookupError, TypeError):
            traceback.print_exc()
            pass
        raise tornado.gen.Return(resp)

        pass

    @tornado.gen.coroutine
    def add_lsp(self, req):
        ' add a lsp '

        final_resp = {'err_code':-1, 'result':{}}
        try:
            # call tunnel service to add a temporary lsp with status 0
            resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map[req['request']], req['args'])
            res = resp['result']
            if 'uid' not in res:
                resp['err_code'] = -1
                raise tornado.gen.Return(resp)

            uid = res['uid']
            # call controller service to add tunnel
            rpc = base_rpc('')
            req['args']['uid'] = uid
            req['args']['callback'] = 'lsp_man_cb_lsp'
            resp = yield self.do_query(microsrv_controller_url, self.subreq_ctrler_map[req['request']], req['args'])
            if resp['err_code'] != MS_OK:
                ' Error occurs, Delete the LSP from tunnel ms '
                args = {}
                stat = 1
                args['uid'] = uid
                resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map['lsp_man_delete_lsp'], args)
                resp['err_code'] = -1
                raise tornado.gen.Return(resp)

            # The LSP setup is in progress. Save the possible user_data(cookie) from controller.
            if 'user_data' in resp:
                rpc = base_rpc('')
                args = {'uid':uid, 'user_data':resp['user_data']}
                resp = yield self.do_query(microsrv_tunnel_url, self.subreq_ctrler_map['lsp_man_update_lsp'], args)

            final_resp = {'err_code':0}
            result = {'uid':uid, 'status':0}
            final_resp['result'] = result

        except (LookupError, TypeError):
            traceback.print_exc()
            pass
        raise tornado.gen.Return(final_resp)
        pass

    @tornado.gen.coroutine
    def update_or_delete_lsp(self,req):
        final_resp = {'err_code':-1, 'result':{}}
        try:
            #Get user_data from tunnel ms
            rpc = base_rpc('')
            args = {'lsp_uids':[req['args']['uid']]}
            resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map['lsp_man_get_lsp'], args)
            res = resp['result']['lsps'][0]
            user_data = None
            if 'user_data' in res:
                user_data = res['user_data']

            # call controller service to update tunnel
            rpc = base_rpc('')
            if user_data:
                req['args']['user_data'] = user_data
            req['args']['callback'] = 'lsp_man_cb_lsp'
            resp = yield self.do_query(microsrv_controller_url, self.subreq_ctrler_map[req['request']], req['args'])
            if 'user_data' in resp:
                user_data = resp['user_data']

            if resp['err_code'] == MS_OK:
                rpc = base_rpc('')
                err = 0
                req['args']['user_data'] = user_data
                up_args = req['args']
                if 'lsp_man_update_lsp' == req['request']:
                    pass
                else:
                    'LSP delete'
                    up_args['status'] = 2       #Deleting
                    final_resp['result'] = {'uid':req['args']['uid'], 'status':2}

                resp = yield self.do_query(microsrv_tunnel_url,self.subreq_tunnel_map['lsp_man_update_lsp'], req['args'] )
            elif resp['err_code'] == MS_DELETE_NON_EXISTING:
                resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map['lsp_man_del_lsp'],
                    {'uid':req['args']['uid']})
            else:
                raise tornado.gen.Return(final_resp)

            final_resp['err_code'] = 0
        except (LookupError,TypeError):
            traceback.print_exc()
            pass
        raise tornado.gen.Return(final_resp)


    @tornado.gen.coroutine
    def cb_lsp(self,req):
        final_resp = {'err_code':-1, 'result':{}}

        # The map for transiting status.
        # 1. if controller callback with status creating(0), means the unsuccessful setup of LSP (timeout), should
        #    change the status to down(-1) to allow user process it.
        # 2. if controller callback with status deleting(2), means the unsuccessful deletion of LSP(timeout),also
        #    change the status to down(-1).
        # 3. Other values (Up, deleted or a real down, these are stable status), keep the original value.
        status_map = {0:-1, 2:-1}
        try:
            args = req['args']
            if 'name' in args:
                args.pop('name')        #Don't let controller update the LSP name in Tunnel ms.
            print 'Callback:\n' + str(args)
            status = args['status']
            if status in status_map:
                status = status_map[status]
            up_args = {'uid':args['uid'], 'status':status}
            if 'user_data' in args:
                up_args['user_data'] = args['user_data']
            if 'path' in args:
                up_args['path'] = args['path']

            resp = yield self.do_query(microsrv_tunnel_url, self.subreq_tunnel_map['lsp_man_update_lsp'], up_args)
            if resp['err_code'] != 0:
                raise tornado.gen.Return(final_resp)
            final_resp['err_code'] = 0
        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)


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
            if 'request' not in req or req['request'] not in self.lsp_req_map:
                resp['err_code'] = -1
                resp['msg'] = 'Unrecognised method'
                self.write(json.dumps(resp))
                self.finish()
                return

            #resp = yield tornado.gen.Task(self.lsp_req_map[req['request']], req)
            lsp_resp = yield self.lsp_req_map[req['request']](req)
            resp['result'] = lsp_resp['result']
            resp['err_code'] = lsp_resp['err_code']
            self.write(json.dumps(resp))
            self.finish()

        except Exception, data:
            print str(Exception) + str(data)
            self.write('Internal Server Error')
            self.finish()
            traceback.print_exc()

    pass


def remove_lsp(id):

    rpc = base_rpc(microsrv_tunnel_url)
    rpc.form_request('ms_tunnel_del_lsp', dict(uid=id))
    rpc.do_sync_post()
    pass

def sync_lsp(*args, **kwargs):
    ''

    app = args[0]

    #Get equips data from topo ms
    rpc = base_rpc(microsrv_topo_url)
    req = rpc.form_request('ms_topo_get_equip',{})
    r = rpc.do_sync_post()
    es = r['routers']        #an array of equip
    em = {}
    for e in es:
        if 'ports' in e:
            e.pop('ports')
        em[e['uid']] = e

    app.set_attrib('equips', em)

    rpc = base_rpc(microsrv_controller_url)
    args = {}
    args['equips'] = es
    rpc.form_request('ms_controller_set_equips', args)
    r = rpc.do_sync_post()

    return
    #Get current LSPs from tunnel ms
    rpc = base_rpc(microsrv_tunnel_url)
    req = rpc.form_request('ms_tunnel_get_lsp', {})
    r = rpc.do_sync_post()
    t_lsps = r['lsps'] if 'lsps' in r else {}
    t_map = {}
    for lp in t_lsps:
        t_map[str(lp['user_data'])] = lp

    #Get LSPs from controller ms
    rpc = base_rpc(microsrv_controller_url)
    req = rpc.form_request('ms_controller_get_lsp', {})
    r = rpc.do_sync_post()
    c_lsps = r['lsps'] if 'lsps' in r else {}
    c_map = {}
    for cl in c_lsps:
        c_map[str(cl['user_data'])] = cl


    #Compare result and update lsps in tunnel ms
    for tl in t_lsps:
        if str(tl['user_data']) not in c_map:
            'delete the lsp'
            remove_lsp(tl['uid'])
        else:
            'Update the status if not the same'
            c_lsp = c_map[str(tl['user_data'])]
            if tl['status'] != c_lsp['status']:
                rpc = base_rpc(microsrv_tunnel_url)
                tl['status'] = c_lsp['status']
                rpc.form_request('ms_tunnel_update_lsp', tl)
                r = rpc.do_sync_post()

    for clsp in c_lsps:
        if str(clsp['user_data']) not in t_map:
            rpc = base_rpc(microsrv_tunnel_url)
            rpc.form_request('ms_tunnel_add_lsp', clsp)
            r = rpc.do_sync_post()
        pass

    tornado.ioloop.IOLoop.instance().add_timeout(
            datetime.timedelta(milliseconds=60*1000),
            sync_lsp, app)

    pass



class lsp_app(tornado.web.Application):
    def __init__(self, other_app):

        self.other_app = other_app
        handlers = [
            (r'/', lsp_handler),
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)

        self.equips = {}
        tornado.ioloop.IOLoop.instance().add_timeout(
                datetime.timedelta(milliseconds=1000),
                sync_lsp, self)
        pass

    def set_attrib(self, name, val):
        if name in self.__dict__:
            object.__setattr__(self, name, val)
            if self.other_app:
                object.__setattr__(self.other_app, name, val)

        pass

@swagger.model()
class lsp(object):
    """
        @description:
            LSP model
        @property hop_list: Desired hop list of the LSP. Each item of the list is the node uid.
        @ptype hop_list: C{list} of L{String}
    """
    def __init__(self, ingress_node_id, egress_node_id, ingress_node_name, egress_node_name, bandwidth, hop_list, uid = None, path=None):
        self.ingress_node_id = ingress_node_id
        self.egress_node_id = egress_node_id
        self.ingress_node_name = ingress_node_name
        self.egress_node_name = egress_node_name
        self.bandwidth = bandwidth
        self.hop_list = hop_list
        self.uid = uid
        self.path = path

class lsp_post_handler(lsp_handler):
    @tornado.gen.coroutine
    @swagger.operation(nickname='add_lsp')
    def post(self):
        """
            @param body: create an LSP
            @type body: L{lsp}
            @in body: body

            @return 200: flow was created.
            @raise 500: invalid input

            @description: Add a new LSP
            @notes: POST lsp/
            <br /> request body sample <br />
            {"hop_list": ["2", "6"], "ingress_node_uid": "2", "ingress_node_name": "", "lsp_name": "alu_2_6_lsp", "egress_node_uid": "6", "priority": null, "bandwidth": 100.0, "delay": null, "egress_node_name": ""}
        """
        p = json.loads(self.request.body)
        np = {}
        rev_map = {}
        for k in self.application.lsp_attrib_map:
            rev_map[self.application.lsp_attrib_map[k]] = k

        for k in p:
            if k in rev_map:
                np[rev_map[k]] = p[k]
            else:
                np[k] = p[k]

        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_add_lsp', np)
        resp = yield self.add_lsp(req)
        result = resp['result']
        rest_resp = {'lsp_uid':result['uid'], 'status':result['status']}
        self.write(json.dumps(rest_resp))
        self.finish()
        pass

    @tornado.gen.coroutine
    @swagger.operation(nickname='update_lsp')
    def put(self):
        """
            @param body: update an LSP
            @type body: L{lsp}
            @in body: body

            @rtype: {}

            @description: Update LSP. Only LSP bandwidth is allowed to be updated in current version.
            @notes: PUT lsp/
        """
        p = json.loads(self.request.body)
        id = p['uid']
        bw = p['bandwidth']
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_update_lsp', {'uid':id, 'bandwidth':bw})
        resp = yield self.update_or_delete_lsp(req)
        self.write('')
        self.finish()
        pass

    @tornado.gen.coroutine
    @swagger.operation(nickname='get_all_lsp')
    def get(self):
        """
            @rtype: list of lsp
            Example:<br />
            {"lsps": [{"uid": "lsp_0", "ingress_node_name": "", "egress_node_name": "", "bandwidth": 1000, "ingress_node_uid": "100", "egress_node_uid": "102", "lsp_name": "vip_lsp1", "path":["100","101", "102"] , "user_data":"xxx"}]}
            <br /> <br />
            lsp_name: The name of an LSP <br />
            ingress_node_name: name of the ingress node (Get from BRS).  <br />
            ingress_node_uid: unique id of ingress node.<br />
            egress_node_name: name of the egress node <br />
            egress_node_uid: unique id of egress node. <br />
            uid: unique id of the LSP <br />
            path: A list of node uids that the LSP traverses in sequence. <br />
            user_data: opaque context data of the LSP. It will be used at manipulation of the LSP. <br />
            bandwidth: Configured LSP capacity in Mbps


            @description: Get LSP information.  return all available LSPs
            @notes:  GET lsp/
        """
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_get_lsp', {})
        resp = yield self.get_lsp(req)

        lsps = resp['result']['lsps']
        val = []
        for p in lsps:
            np = self.map_obj_key(p, self.application.lsp_attrib_map)
            val.append(np)

        rest_resp = {'lsps':val}
        self.write(json.dumps(rest_resp))
        self.finish()


class lsp_get_handler(lsp_handler):
    @tornado.gen.coroutine
    @swagger.operation(nickname='delete_lsp')
    def delete(self, lsp_uid):
        """
            @param lsp_uid:
            @type lsp_uid: L{string}
            @in lsp_uid: path
            @required lsp_uid: True

            @rtype: list of lsp
            @description: Delete an LSP
            @notes: DELETE lsp/uid
        """
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_del_lsp', {'uid':lsp_uid})
        resp = yield self.update_or_delete_lsp(req)

        if resp['err_code'] == 0:
            self.write('')
        else:
            raise tornado.web.HTTPError(500)

        pass

    @tornado.gen.coroutine
    @swagger.operation(nickname='get_lsp')
    def get(self, ingress_uid):
        """
            @param ingress_uid:
            @type ingress_uid: L{string}
            @in ingress_uid: path
            @required ingress_uid: True

            @rtype: list of lsp
            Example:<br />
            {"lsps": [{"uid": "lsp_0", "ingress_node_name": "", "egress_node_name": "", "bandwidth": 1000, "ingress_node_uid": "100", "egress_node_uid": "102", "lsp_name": "vip_lsp1", "path":["100","101", "102"] , "user_data":"xxx"}]}
            <br /> <br />
            lsp_name: The name of an LSP <br />
            ingress_node_name: name of the ingress node (Get from BRS).  <br />
            ingress_node_uid: unique id of ingress node.<br />
            egress_node_name: name of the egress node <br />
            egress_node_uid: unique id of egress node. <br />
            uid: unique id of the LSP <br />
            path: A list of node uids that the LSP traverses in sequence. <br />
            user_data: opaque context data of the LSP. It will be used at manipulation of the LSP. <br />
            bandwidth: Configured LSP capacity in Mbps


            @description: Get LSP information. If the ingress_node_uid presents, return the LSP starts from the desired node.
            otherwise, return all available LSPs
            @notes: GET lsp/uid or  GET lsp/
        """
        args = {} if not ingress_uid else {'from_router_uid':str(ingress_uid)}
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_get_lsp', args)
        resp = yield self.get_lsp(req)

        if 'result' not in resp:
            self.write('{}')
            self.finish()

        # Field name conversion.
        lsps = resp['result']['lsps']
        val = []
        for p in lsps:
            np = self.map_obj_key(p, self.application.lsp_attrib_map)
            val.append(np)

        rest_resp = {'lsps':val}
        self.write(json.dumps(rest_resp))
        self.finish()
        pass

class lsp_vsite_handler(lsp_handler):

    @tornado.gen.coroutine
    @swagger.operation(nickname='get_lsp_by_vsite')
    def get(self, vsite_uid):
        """
            @param vsite_uid:
            @type vsite_uid: L{string}
            @in vsite_uid: path
            @required vsite_uid: True

            @rtype: map of {vsite_uid:[L{lsp}]}
            @description: Get the LSPs of  the flow specs of vsite

            @notes: GET lsp/visite/{uid}
        """
        vsites = vsite_uid.split(',')
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_get_lsp_by_cust', {'cust_uids':vsites})
        resp = yield self.get_lsp_by_cust(req)
        cust_lsps = resp['result']

        vsite_lsp = {}
        for c in cust_lsps:
            r_lsps = []
            for p in cust_lsps[c]:
                r_p = self.map_obj_key(p, self.application.lsp_attrib_map)
                r_lsps.append(r_p)
            vsite_lsp[c] = r_lsps

        self.write(json.dumps(vsite_lsp))
        self.finish()
        pass

class vsite_lsp_handler(lsp_handler):
    @tornado.gen.coroutine
    @swagger.operation(nickname='get_vsite_by_lsp')
    def get(self, lsp_uid):
        """
            @param lsp_uid:
            @type lsp_uid: L{string}
            @in lsp_uid: path
            @required lsp_uid: True

            @rtype: map of {lsp_uid:[list of vsite]}
            @description: Get the vsite flow specs in the LSP.

            @notes: GET /visite/lsp/{lsp_uids}
        """
        rpc = base_rpc('')
        req = rpc.form_request('lsp_man_get_cust_by_lsp', {'lsps':[{'uid':x} for x in lsp_uid.split(',')]})
        resp = yield self.get_cust_by_lsp(req)
        self.write(resp['result'])
        self.finish()
        pass

class vsite_flow_policy_handler(flow_sched_handler):
    @tornado.gen.coroutine
    @swagger.operation(nickname='create_flow_policy')
    def post(self):
        """
            @param body: body
            @type body: Json
            @in body: body

            @return 200: flow policy was created.
            @raise 500: invalid input

            @description: Create new flow policy to scheduling the flow spec of a vsite to a specific LSP.
            @notes: POST flow-policy
            <br /> Request body sample <br />
            {"lsp_uid": "xxx", "vsite_uid": "yyy"}

        """
        rpc = base_rpc('')
        rest_req = json.loads(self.request.body)
        req = rpc.form_request('flow_sched_add_flow', {'lsp_uid': rest_req['lsp_uid'], 'cust_uid':rest_req['vsite_uid']})
        resp = yield self.add_flow(req)
        self.write('')
        self.finish()
        pass

    @tornado.gen.coroutine
    @swagger.operation(nickname='delete_flow_policy')
    def delete(self):
        """
            @param lsp_uid:
            @type lsp_uid: L{string}
            @in lsp_uid: query
            @required lsp_uid: True

            @param vsite_uid:
            @type vsite_uid: L{string}
            @in lsp_uid: query
            @required vsite_uid: True

            @return 200: flow policy was deleted.
            @raise 500: invalid input
            @description: Delete a flow policy.

            @notes: DELETE flow-policy?lsp_uid=xxx&vsite_uid=yyy
        """

        rpc = base_rpc('')
        lsp = self.get_argument('lsp_uid')
        vsite = self.get_argument('vsite_uid')
        req = rpc.form_request('flow_sched_del_flow', {'lsp_uid': lsp, 'cust_uid':vsite})
        resp = yield self.del_flow(req)
        self.write('')
        self.finish()
        pass



class swagger_app(swagger.Application):
    def __init__(self):

        settings = {
            'static_path': os.path.join(os.path.dirname(__file__), 'sdno-mpls-optimizer.swagger')
        }

        handlers = [(r'/openoapi/sdno-mpls-optimizer/v1/lsp/([^/]+)', lsp_get_handler),
                    (r'/openoapi/sdno-mpls-optimizer/v1/lsp', lsp_post_handler),
                    (r'/openoapi/sdno-mpls-optimizer/v1/lsp/vsite/([^/]+)', lsp_vsite_handler),
                    (r'/openoapi/sdno-mpls-optimizer/v1/vsite/lsp/([^/]+)', vsite_lsp_handler),
                    (r'/openoapi/sdno-mpls-optimizer/v1/flow-policy', vsite_flow_policy_handler),
                    (r'/openoapi/sdno-mpls-optimizer/v1/(swagger.json)', tornado.web.StaticFileHandler, dict(path=settings['static_path']))
                    ]

        super(swagger_app, self).__init__(handlers, **settings)

        self.equips = {}
        self.lsp_attrib_map = {'from_router_uid':'ingress_node_uid', 'to_router_uid':'egress_node_uid',
                                 'bandwidth':'bandwidth', 'from_router_name':'ingress_node_name',
                                 'to_router_name':'egress_node_name', 'name':'lsp_name'
                                 }

        tornado.ioloop.IOLoop.instance().add_timeout(
                        datetime.timedelta(milliseconds=500),
                        openo_register, 'mpls-optimizer', 'v1', '/openoapi/sdno-mpls-optimizer/v1',
                        '127.0.0.1', te_lsp_rest_port )


if __name__ == '__main__':
    tornado.options.parse_command_line()
    swag = swagger_app()    # For REST interface
    app = lsp_app(swag)
    server = tornado.httpserver.HTTPServer(app)
    server.listen(32772)
    server_swag = tornado.httpserver.HTTPServer(swag)
    server_swag.listen(te_lsp_rest_port)

    tornado.ioloop.IOLoop.instance().start()