#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2016 China Telecommunication Co., Ltd.
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

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen
import json
import re
from db_util import mysql_utils

class ms_topo_handler(tornado.web.RequestHandler):
    def initialize(self):
        super(ms_topo_handler, self).initialize()
        self.resp_func = {'ms_topo_get_equip': self.get_equips, 'ms_topo_get_ports':self.get_ports, \
                      'ms_topo_get_vlink': self.get_vlinks, 'ms_link_set_links':self.set_vlinks, \
                      'ms_link_get_status':self.get_link_status, 'ms_flow_set_equips': self.set_equips,\
                      'ms_flow_set_topo':self.dummy,
                      'ms_flow_get_flow':self.get_flow, 'ms_cust_get_customer_by_ip': self.get_customer_by_ip,\
                      'ms_tunnel_get_lsp_by_flow': self.get_lsp_by_flow, 'ms_tunnel_get_lsp':self.get_lsp,
                      'ms_tunnel_add_lsp':self.add_lsp, 'ms_tunnel_del_lsp':self.del_lsp,
                      'ms_tunnel_add_flow':self.dummy, 'ms_tunnel_del_flow':self.dummy,
                      'ms_tunnel_update_flow':self.dummy, 'ms_tunnel_get_flows':self.get_flow_lsp,
                      'ms_tunnel_update_lsp':self.update_lsp, 'ms_tunnel_set_lsp':self.dummy,
                      'ms_tunnel_get_cust_by_lsp':self.get_cust_by_lsp,'ms_tunnel_get_lsp_by_cust':self.get_lsp_by_cust,
                      'ms_tunnel_add_customer_to_lsp':self.dummy, 'ms_tunnel_remove_customer_from_lsp':self.dummy,
                      'ms_cust_get_customer':self.get_customer, 'ms_cust_del_customer' : self.del_customer,
                      'ms_cust_add_customer':self.add_customer,'ms_cust_update_customer':self.dummy,
                      'ms_cust_add_flow' : self.cust_add_flow, 'ms_cust_update_flow' : self.cust_add_flow,
                      'ms_cust_del_flow':self.cust_del_flow,
                      'ms_controller_get_lsp':self.get_lsp, 'ms_controller_add_lsp':self.add_lsp,
                      'ms_controller_del_lsp':self.del_lsp, 'ms_controller_update_lsp':self.update_lsp,
                      'ms_controller_add_flow':self.dummy, 'ms_controller_del_flow':self.dummy,
                      'ms_controller_set_equips':self.dummy}
        self.log = 0
        pass

    def dummy(self, args):
        return {}

    def get_cust_by_lsp(self, args):
        return {'lsp_0':['cust_0', 'cust_1']}
    def get_lsp_by_cust(self, args):
        return {'cust_0':['lsp_0', 'lsp_1']}

    def get_flow_lsp(self,args):
        fids = args['flow_uids']
        flows = {}
        for fid in fids:
            lsps = []
            for i in range(0,2):
                p = {'lsp_uid': 'lsp_' + str(i), 'flow_user_data':'xxx'}
                lsps.append(p)

            flows[fid] = lsps
        return flows

    def get_lsp(self, args):
        lsps = []

        if 'lsp_uids' in args:
            ud = {u'lsp_id': 3, u'from_router_uid': u'PE14Z', u'lsp_name': u'ZTE_SAG2'}
            return {'lsps':[{'uid':'xyz123', 'path':['PE14Z', 'PE11A', 'PE24Z'], 'user_data':ud}]}

        for i in range(0,4):
            lsp = {'uid':'lsp_'+str(i), 'name':'Microhard_' + str(i),
                   'from_router_uid':'router'+str(i), 'to_router_uid':'router' + str(4-i),
                   'from_router_name':'', 'to_router_name':'', 'bandwidth': 1000+256*i, 'user_data':'lspdata'+str(i),
                   'status':i}

            lsps.append(lsp)

        return dict(lsps=lsps)

    def add_lsp(self,args):
        return {'uid':'xyz123'}
    def del_lsp(self, args):
        return {}
    def update_lsp(self, args):
        return {}

    def add_customer(self, args):
        return dict(cust_uid='abc')

    def get_customer(self, args):

        custs = []

        nm = 'Goo'
        for i in range(0,3):
            cn = nm + 'gle'
            nm += 'o'
            one_cust = dict(uid = 'cust_'+str(i), name=cn)
            ips = []
            for j in range(0, 2):
                ip = dict(src='123.1'+str(j)+'.88.0/24', dst='10.1'+str(j)+'.20.0/24', uid='ips_'+str(j))
                ips.append(ip)
            one_cust['ips'] = ips
            custs.append(one_cust)
            pass

        return dict(customers=custs)

    def del_customer(self, args):
        return {}

    def cust_add_flow(self, args):

        return dict(flow_uid='flow_abc')

    def cust_del_flow(self, args):
        return {}

    def get_lsp_by_flow(self, ips):
        ' ips should be an array of {uid: xxx, sip_str:xxx, dip_str:xxx} '

        ips = ips['flows']
        for ip in ips:
            if 'sip_str' in ip:
                sip = ip['sip_str']
            if 'sip_str' in ip:
                dip = ip['sip_str']

            if '200' in sip:
                ip['lsp_uid'] = 100
                ip['lsp_name'] = 'Goooooogle  LSP'
        return dict(flows=ips)


    def get_customer_by_ip(self, arg):
        res = {}

        ips = arg['ips']
        c = 'Goo'
        cus = {}
        for ip in ips:
            one_cus = {'cust_uid':'cust_'+str(ip), 'name': c + 'gle'}
            cus[ip] = one_cus
            #c += 'o'
        return cus

    def get_flow(self, arg):
        flow = {}
        fs = []

        if 'equip_uid' in arg:
            for i in range(0, 3):
                f = {}
                f['uid'] =  str(i)
                f['src'] = '10.0.148.1' + str(i)
                f['dst'] = '1.2.3.' + str(i)
                f['bps'] = 2684354560 if i == 0 else 1084354560 + 84354560 * i
                f['next_hop_uid'] = str(10 + i)
                fs.append(f)
            for i in range(0, 3):
                f = {}
                f['uid'] =  str(i)
                f['src'] = '10.0.248.1' + str(i)
                f['dst'] = '111.222.3.' + str(i)
                f['bps'] = 894784853 if i == 0 else 84354560 + 78893002 * i
                f['next_hop_uid'] = str(10 + i)
                fs.append(f)

        flow['flows'] = fs
        return flow

    def set_equips(self, arg):
        return {}


    def get_equips(self, arg):
        vendor_map={'C':'CISCO', 'Z':'ZTE', 'A':'ALU', 'J':'JUNIPER'}
        equips = {}
        rts = []
        router_pat = re.compile(r'(\D{1,2})(\d{1,2})([A-Z])')

        for i in ('PE14Z','PE11A','PE12J','PE13C','R1Z','R3Z','R4Z','R6Z', 'PE21A','PE22J', 'PE23C','PE24Z'):
            m = router_pat.match(i)
            dgt = m.groups()[1]
            vend = vendor_map[m.groups()[2]]

            one_rt = {}
            one_rt['uid'] = i
            one_rt['name'] = i
            one_rt['model'] = 'aladin'
            one_rt['community'] = 'roastedchiken' + str(i)
            one_rt['vendor'] = vend
            one_rt['pos'] = 'Old village of Gao'
            one_rt['x'] = 110.1 + 3.7
            one_rt['y'] = 46.4 + 2.5
            one_rt['ip_str'] = dgt+'.'+dgt+'.'+dgt+'.'+dgt

            rts.append(one_rt)

        equips['routers'] = rts
        return equips

    def get_ports(self, arg):
        uid = arg['uid']
        port = {}

        ps = []
        for i in range(0,4):
            one_port = {}
            one_port['uid'] = str(uid) + '_' + str(i)
            one_port['type'] = 0
            one_port['mac'] = str(i) + '0:01:0E:03:25:2' + str(i)
            one_port['ip_str'] =  '10.9.63.1' + str(i)
            one_port['if_index'] = str(i)

            if i%2 == 1:
                one_port['vport_id'] = str(uid) + '_200'
            ps.append(one_port)
            pass

        #build the vport
        one_port = {}
        one_port['uid'] = str(uid) + '_200'
        one_port['type'] = 1
        one_port['mac'] = str(i) + '0:01:0E:03:25:80'
        one_port['ip_str'] = str(i) + '10.9.63.200'
        one_port['if_index'] = 0
        ps.append(one_port)

        port['ports'] = ps
        return port

    def get_vlinks(self, arg):
        vl = {}
        # FIXME:
        return {'vlinks':[]}
        vls = []

        #ports are 1000_0~1000_3, 1001_0~1001_3, 1002_0~1002_3
        #vports: 1000_200 (contains 1000_1 & 1000_3), 1002_200 (contains 1002_1 & 1002_3),
        #create demo links: 1000_0 <-> 1001_0, 1000_200 <-> 1002_200 (vlink)
        #                   1000_2 <-> 1002_2

        #physical link 1: 1000_0 <-> 1001_0
        v = {}
        v['uid'] = 'v_0'
        v['sport'] = '1000_0'
        v['dport'] = '1001_0'
        v['bandwidth'] = 1000.0
        vls.append(v)

        #physical link 2: 1000_2 <-> 1002_2
        v = {}
        v['uid'] = 'v_1'
        v['sport'] = '1000_2'
        v['dport'] = '1002_2'
        v['bandwidth'] = 1000.0
        vls.append(v)

        #virtual link 3: 1000_200 <-> 1002_200
        v = {}
        v['uid'] = 'v_2'
        v['sport'] = '1000_200'
        v['dport'] = '1002_200'
        v['bandwidth'] = 2000.0
        vls.append(v)

        vl['vlinks'] = vls
        return vl

    def set_vlinks(self, arg):
        return {}

    def get_link_status(self, arg):
        ls = {}
        ps = []
        db = mysql_utils('topology')
        res = db.exec_sql('select flow_add_flag from flag  where id = 1')
        flow_add_tag = res[0][0]
        db.close()

        #link status for 4 ports 1000_0 1001_0 1000_2 1002_2, and 4 ports of vlinks: 1000_1 1000_3 1002_1 1002_3
        s = {}
        s['port_uid'] = '29'
        # s['d_port_uid'] = '1001_0'
        s['utilization'] = 0.58*100 if flow_add_tag == 1 else 0.85*100
        ps.append(s)
        s = {}
        s['port_uid'] = '30'
        # s['d_port_uid'] = '1002_0'
        s['utilization'] = 0.65*100 if flow_add_tag == 1 else 0.38*100
        ps.append(s)
        s = {}

        s['port_uid'] = '43'
        # s['d_port_uid'] = '1000_3'
        s['utilization'] = 0.69*100 if flow_add_tag == 1 else 0.42*100
        ps.append(s)
        s = {}
        s['port_uid'] = '46'
        # s['d_port_uid'] = '1002_3'

        s['utilization'] = 0.59*100 if flow_add_tag == 1 else 0.32*100
        ps.append(s)


        ls['utilization'] = ps

        return ls

    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        resp['ts'] = req['ts']
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        return resp

    def post(self):
        ctnt = self.request.body
        if self.log == 1:
            print 'The request:'
            print  str(ctnt)

        req = json.loads(str(ctnt))
        resp = self.form_response(req)

        result = self.resp_func[req['request']](req['args'])
        resp['result'] = result

        if self.log == 1:
            print 'response:'
            print json.dumps(resp)
        self.write(json.dumps(resp))
        pass

    @tornado.gen.coroutine
    def get(self):
        self.write('xxxx')
        self.finish()

    # def get(self):
    #     resp = self.A()
    #     print resp
    #     # self.write(resp.body)
    #     self.finish()


    pass

class ms_link_handler(ms_topo_handler):

    pass

class ms_controller_handler(ms_topo_handler):

    def initialize(self):
        super(ms_topo_handler, self).initialize()
        self.request_method_map = {'tunnel:query-all-tunnels': self.ms_controller_get_lsp,
                                'tunnel:query-tunnel-by-uuid': self.ms_controller_get_an_lsp,
                                'tunnel:delete-tunnel': self.ms_controller_del_lsp,
                                'tunnel:update-tunnel-bandwidth': self.ms_controller_update_lsp,
                                'tunnel:create-tunnel': self.ms_controller_add_lsp,
                                'traffic-policy:binding-interface': self.ms_controller_del_flow,
                                'traffic-policy:create-traffic-policy-template': self.ms_controller_add_flow,
                                'traffic-policy:binding-interface': self.ms_controller_add_flow_2,
                                'traffic-policy:delete-traffic-policy-template': self.ms_controller_del_flow_2,
                                'traffic-policy:query-traffic-policy-template': self.ms_controller_get_flow}

        self.log = 0
        pass

    def dummy(self, args):
        return {}

    def ms_controller_get_lsp(self, args):
        resp = {   "output": {       "tunnel-uuid": "tunnel1",       "tunnel-id": 1,       "ingress-node-id": "snmp224416250670369",       "tunnel-name": "pce1",       "pce-init": True,       "status": "UP",       "te-argument": {           "preemptPriority": 7,           "holdPriority": 7,           "bandwidth": 120       },       "path": {           "lsp-metric": 0       },       "hsb-path": {           "lsp-metric": 0       }   }}
        return resp
        pass
    def ms_controller_get_an_lsp(self, args):
        resp = {   "output": {       "tunnel-uuid": "tunnel1",       "tunnel-id": 1,       "ingress-node-id": "snmp224416250670369",       "tunnel-name": "pce1",       "pce-init": True,       "status": "UP",       "te-argument": {           "preemptPriority": 7,           "holdPriority": 7,           "bandwidth": 120       },       "path": {           "lsp-metric": 0       },       "hsb-path": {           "lsp-metric": 0       }   }}
        return resp
        pass
    def ms_controller_del_lsp(self, args):
        return {}
        pass
    def ms_controller_update_lsp(self, args):
        return {}
        pass
    def ms_controller_add_lsp(self, args):
        resp = {"output": {"result": True, "info": "success", "tunnel-id-info": [ { "tunnel-uuid": "lsp_zte_14_24", "tunnel-id": 2  } ]  }}
        return resp
        pass
    def ms_controller_del_flow(self, args):
        return  {"output":{"result":True}}
        pass
    def ms_controller_add_flow(self, args):
        resp = {
        "output": {
        "result": True,
        "info": "createTrafficPolicyTemplate success!"
            }
        }
        return resp
        pass
    def ms_controller_add_flow_2(self, args):
        return {"output":{"result":True}}
        pass
    def ms_controller_del_flow_2(self, args):
        return { "output": { "result": True, "info": "deleteTrafficPolicyTemplate success!" } }
        pass
    def ms_controller_get_flow(self, args):
        return {"output":{"result":True}}
        pass

    def post(self, method):
        ctnt = self.request.body
        if self.log == 1:
            print 'The request:' + str(method)
            print  str(ctnt)

        result = self.request_method_map[method](ctnt)

        if self.log == 1:
            print 'response:'
            print json.dumps(result)
        self.write(json.dumps(result))
        pass
    pass

class test_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', ms_topo_handler),
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)
        pass

from jsonrpc import *


import httplib, ssl, urllib2, socket
import types

class HTTPSConnectionV3(httplib.HTTPSConnection):
    def __init__(self,*args,**kwargs):
        httplib.HTTPSConnection.__init__(self,*args,**kwargs)

    def connect(self):
        sock= socket.create_connection((self.host,self.port),self.timeout)
        if self._tunnel_host:
            self.sock= sock
            self._tunnel()
        try:
            self.sock= ssl.wrap_socket(sock,self.key_file,self.cert_file, ssl_version=ssl.PROTOCOL_SSLv3)
        except ssl.SSLError, e:
            print("Trying  SSLv3.")
            self.sock= ssl.wrap_socket(sock,self.key_file,self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)

class HTTPSHandlerV3(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionV3, req)
    pass

class ret(Exception):
    def __init__(self, val):
        super(ret, self).__init__()
        self.value = val
        self.args = (val, )

import functools
import inspect
import sys
def deco(func):
    @functools.wraps(func)
    def _deco(*args,**kwargs):
        try:
            ins = None
            if args and len(args) > 1:
                ins = args[1]
            if ins is None:
                ins = func(*args, **kwargs )
                r = ins
            if isinstance(ins, types.GeneratorType):
                a = ins.next()                    # the next() always return the yielded value.
                r = ins
            else:
                a = ins                         # normal function return value
                r = None
        except (ret) as e:
            return e.value, args[1]
            # if isinstance(func, types.GeneratorType):
            #     func.send(e.value)
            #     return
            # else:
            #     return e.value
        except StopIteration:
            a = ''
            r = None
            pass
        finally:
            pass

        if isinstance(a, tuple):
            a = a[0]
        return a, r
    return _deco

class test_gen(object):
    @deco
    def A(self, *args, **kwargs):
        print 'in func A'
        yield 'A'
        raise ret('A')

    @deco
    def B(self, *args, **kwargs):
        print 'in func B'
        return 'B'

    @deco
    def C(self, *args, **kwargs):
        r = yield self.B()
        print r
        print 'end of C'

    @deco
    def D(self, *args, **kwargs):
        r = yield self.A()
        print 'end of D'

class test_app(tornado.web.Application):
    def __init__(self):

        handlers = [
            (r'/microsrv/topo', ms_topo_handler),
            (r'/microsrv/link_stat', ms_link_handler),
            (r'/microsrv/flow', ms_topo_handler),  # For testing
            (r'/microsrv/customer', ms_topo_handler),
            (r'/microsrv/tunnel', ms_topo_handler),
            (r'/restconf/operations/(.*)', ms_controller_handler),
            (r'/microsrv/controller', ms_topo_handler)
        ]

        settings = {
            'template_path': 'templates',
            'static_path': 'static'
        }

        tornado.web.Application.__init__(self, handlers, **settings)
        pass

if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = test_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(33710)
    tornado.ioloop.IOLoop.instance().start()