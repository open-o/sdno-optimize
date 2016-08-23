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
from base_handler import base_handler

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
                                  'flow_sched_callback':self.cb_flow_ctrl}
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
            resp = yield self.do_query(microsrv_cust_url, 'ms_cust_get_customer',args)
            flows = resp['result']['customers'][0]['ips']

            #Get current flow's lsp info  from tunnel ms. one flow is allowed to be in more than 1 LSP.
            fs = [f['uid'] for f in flows]
            args = {'flow_uids':fs}
            resp = yield self.do_query(microsrv_tunnel_url, 'ms_tunnel_get_lsp_by_flow', args)
            flow_map = resp['result']

            #Get user_data from tunnel ms
            req_lsp = req['args']['lsp_uid']
            user_data = None
            if op:
                args = {'lsp_uids':[req_lsp]}
                resp = yield self.do_query(microsrv_tunnel_url, 'ms_tunnel_get_lsp', args)
                resp = resp['result']['lsps'][0]    #Here we always query a single lsp.
                if 'user_data' in resp:
                    user_data = resp['user_data']
            else:
                ' Delete flow. we need user_data of flow instead of lsp'
                args = {'lsp_uid': req_lsp, 'flow_uids':[str(x['uid']) for x in flows]}
                resp = yield self.do_query(microsrv_tunnel_url, 'ms_tunnel_get_flow', args)
                user_data = resp['result']

        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return((flows,flow_map,user_data))


    @tornado.gen.coroutine
    def add_flow(self, req):
        ' get customer ips from customer_flow microservice, call controller and then tunnel'
        final_resp = {'err_code':-1, 'result': {}}

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
                resp = yield self.do_query(microsrv_controller_url, self.subreq_ctrler_map[req['request']], args)
                if resp['err_code'] != 0:
                    raise tornado.gen.Return(final_resp)

                #call tunnel to add this flow, with status 0
                status = 0
                args = {'flow_uid':fid, 'lsp_uid':req_lsp, 'status':status}
                if resp['result'] is not None and 'user_data' in resp['result']:
                    ud = resp['result']['user_data']
                    args['user_data'] = ud
                resp = yield self.do_query(microsrv_tunnel_url,  self.subreq_tunnel_map[req['request']], args)
                pass

            #Add/Remove customer to/from to LSP info.
            cust_args = {'lsp_uid':req_lsp, 'cust_uid':req['args']['cust_uid']}
            method = 'ms_tunnel_add_customer_to_lsp'
            resp = yield self.do_query(microsrv_tunnel_url, method, cust_args)
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
                resp = yield self.do_query(microsrv_controller_url, self.subreq_ctrler_map[req['request']], args)
                if resp['err_code'] != 0:
                    raise tornado.gen.Return(final_resp)

                #call tunnel to add this flow, with status 0
                status = 2
                args = {'flow_uid':fid, 'lsp_uid':req_lsp, 'status':status}
                if resp['result'] is not None and 'user_data' in resp['result']:
                    ud = resp['result']['user_data']
                    args['user_data'] = ud
                resp = yield self.do_query(microsrv_tunnel_url,  self.subreq_tunnel_map[req['request']], args)
                pass

            #Add/Remove customer to/from to LSP info.
            cust_args = {'lsp_uid':req_lsp, 'cust_uid':req['args']['cust_uid']}
            method = 'ms_tunnel_del_customer_from_lsp'
            resp = yield self.do_query(microsrv_tunnel_url, method, cust_args)
            final_resp['err_code'] = 0

        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(final_resp)
        pass
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
            resp = yield self.do_query(microsrv_tunnel_url, method, args)
            if resp['err_code'] != 0:
                raise tornado.gen.Return(final_resp)
            else:
                final_resp['err_code'] = 0
        except (LookupError,TypeError):
            traceback.print_exc()
            pass
        raise tornado.gen.Return(final_resp)
        pass

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
        pass


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = flow_sched_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(32773)
    tornado.ioloop.IOLoop.instance().start()