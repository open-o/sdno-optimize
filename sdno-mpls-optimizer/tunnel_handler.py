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

import tornado.web
import json
import time
from db_util import mysql_utils

ip2num = lambda x:sum([256**j*int(i) for j,i in enumerate(x.split('.')[::-1])])

num2ip = lambda x: '.'.join([str(x/(256**i)%256) for i in range(3,-1,-1)])

def get_mask_int(mask):
    sum=0
    for i in range(mask):
        sum = sum*2+1
    sum = sum << (32-mask)
    return sum

class ms_tunnel_handler(tornado.web.RequestHandler):
    def initialize(self):
        super(ms_tunnel_handler, self).initialize()
        self.resp_func = {'ms_tunnel_get_lsp_by_flow': self.get_lsp_by_flow, 'ms_tunnel_get_lsp':self.get_lsp, \
                      'ms_tunnel_add_lsp':self.add_lsp, 'ms_tunnel_del_lsp':self.del_lsp, \
                      'ms_tunnel_update_lsp':self.update_lsp, 'ms_tunnel_add_flow':self.add_flow, \
                      'ms_tunnel_del_flow':self.del_flow,  'ms_tunnel_update_flow':self.update_flow,
                      'ms_tunnel_get_flow':self.get_flow,
                      'ms_tunnel_get_customer_by_lsp':self.get_customer_by_lsp, 'ms_tunnel_get_lsp_by_cust':self.get_lsp_by_customer, \
                      'ms_tunnel_add_customer_to_lsp':self.add_customer_to_lsp, 'ms_tunnel_del_customer_from_lsp':self.del_customer_from_lsp,
                      'ms_tunnel_get_cust_by_lsp':self.get_customer_by_lsp,
                      'ms_tunnel_get_lsp_by_uids':self.get_lsp_by_uids
                      }
        self.log = 0
        pass

    def form_response(self, req):
        resp = {}
        resp['response'] = req['request']
        #resp['ts'] = req['ts']
        resp['ts'] = time.strftime("%Y%m%d%H%M%S")
        resp['trans_id'] = req['trans_id']
        resp['err_code'] = 0
        resp['msg'] = ''
        self.set_header('Content-Type', 'application/json')
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

    def get_lsp_by_flow(self,args):
        flow_uids = args['flow_uids']
        flow_lsps = {}

        db = mysql_utils('tunnel')
        for fid in flow_uids:
            sql_str = 'select * from t_assigned_flow inner join t_lsp on t_assigned_flow.lsp_id = t_lsp.id ' + \
                'and t_assigned_flow.flow_id=%s' % fid
            # sql_str = 'select * from t_assigned_flow where t_assigned_flow.flow_id=%s' % fid

            # print sql_str
            results = db.exec_sql(sql_str)
            lsps = []
            if results:
                for res in results:
                    one_lsp = {}
                    one_lsp['lsp_uid'] = str(res[1])
                    one_lsp['flow_user_data'] = str(res[9])
                    # one_lsp['ip'] = results[0][3] + '/' + str(results[0][4])
                    # one_lsp['customer_id'] = str(results[0][6])
                    one_lsp['lsp_name'] = res[12]
                    # one_lsp['bandwidth'] = results[0][18]
                    # one_lsp['delay'] = results[0][19]
                    # one_lsp['priority'] = results[0][20]
                    # one_lsp['status'] = results[0][23]
                    one_lsp['lsp_user_data'] = res[25]
                    one_lsp['hop_list'] = res[26]
                    # one_lsp['path'] = results[0][26]
                    lsps.append(one_lsp)
            else:
                pass
            flow_lsps[fid] = lsps
        db.close()
        return flow_lsps

    def get_lsp(self, args):
        if 'lsp_uids' in args:
            uids = args['lsp_uids']
            p_list = '(' + ','.join(str(uid) for uid in uids) + ')'
            sql_str = 'select * from t_lsp where t_lsp.status < 2 and t_lsp.id in %s' % p_list
        elif 'from_router_uid' in args:
            nid = args['from_router_uid']
            sql_str = 'select * from t_lsp where t_lsp.status < 2 and t_lsp.from_router_id = \'%s\'' % str(nid)
        else:
            sql_str = 'select * from t_lsp where t_lsp.status < 2'

        db = mysql_utils('tunnel')
        results = db.exec_sql(sql_str)
        db.close()
        lsps = {}
        lsp = []

        for result in results:
            one_lsp = {}
            one_lsp['uid'] = str(result[0])
            one_lsp['name'] = result[1]
            one_lsp['from_router_uid'] = result[2]
            one_lsp['to_router_uid'] = result[5]
            one_lsp['bandwidth'] = result[8]
            one_lsp['delay'] = result[9]
            one_lsp['priority'] = result[10]
            one_lsp['control_type'] = result[11]
            one_lsp['path_type'] = result[12]
            one_lsp['status'] = result[13]
            one_lsp['user_data'] = None if result[14] is None or not result[14].startswith('{') else json.loads(result[14])
            one_lsp['hop_list'] = [] if result[15] is None else [x for x in result[15].split(',')]
            one_lsp['path'] = [] if result[16] is None else [x for x in result[16].split(',')]

            lsp.append(one_lsp)

        lsps['lsps'] = lsp
        return lsps


    def add_lsp(self, args):
        lsp = args
        added_lsp = []

        str_keys = ['from_port_uid', 'to_port_uid','from_router_ip', 'to_router_ip','user_data', 'host_list', 'path', 'from_router_name', 'to_router_name']
        num_keys = ['delay', 'priority', 'control_type', 'path_type', 'status']
        for k in str_keys:
            if k not in lsp or lsp[k] is None:
                lsp[k] = ''
        for k in num_keys:
            if k not in lsp or lsp[k] is None:
                lsp[k] = 'null'

        lsp['hop_list'] = ','.join(lsp['hop_list'])
        lsp['path'] = ','.join(lsp['path'])
        #insert into t_lsp values (1, 'lsp-1', 1, '1.1.1.1', 1, 2, '2.2.2.2', 1, 100.0, 20.0, 1, 1, 0);
        sql_str = 'insert into t_lsp(name,from_router_id,from_router_ip,from_port_id,to_router_id,to_router_ip,' \
            + 'to_port_id, bandwidth,delay,priority,control_type,path_type,status,user_data,hop_list,path) values (\'%s\',\'%s\',\'%s\',\'%s\',\'%s\',\'%s\',\'%s\',%s,%s,%s,%s,%s,%s,\'%s\',\'%s\',\'%s\')' \
            % (lsp['name'],lsp['from_router_uid'],lsp['from_router_ip'],lsp['from_port_uid'],lsp['to_router_uid'],lsp['to_router_ip'],lsp['to_port_uid'],\
            lsp['bandwidth'],lsp['delay'],lsp['priority'],lsp['control_type'],lsp['path_type'],lsp['status'],lsp['user_data'],lsp['hop_list'],lsp['path'])
        # print sql_str
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
            db.commit()
        lsp_id = db.exec_sql('SELECT LAST_INSERT_ID()')[0][0]
        db.close()
        return {'uid':str(lsp_id)}

    def del_lsp(self, args):
        if 'uids' in args:
            uids = args['uids']
        elif 'uid' in args:
            uids = [args['uid']]

        sql_str = 'delete from t_lsp where t_lsp.id in (%s)' % (",".join(str(uid) for uid in uids))
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
            db.commit()
        db.close()
        return result

    def update_lsp(self, args):
        lsp = args

        lsp_old = self.get_lsp_by_uid(lsp['uid'])['lsps'][0]

        for k in lsp_old:
            if k not in lsp:
                lsp[k]=lsp_old[k]
                if lsp[k] is None:
                    lsp[k] = ''
        num_keys = ['delay', 'priority', 'control_type', 'path_type', 'status']
        for k in num_keys:
            if k in lsp and lsp[k] == '':
                lsp[k] = 'null'


        sql_str = 'update t_lsp set name=\'%s\',from_router_id=\'%s\',to_router_id=\'%s\',bandwidth=%s,delay=%s,priority=%s,status=%s,user_data=\'%s\',path=\'%s\' where t_lsp.id=%s' \
            % (lsp['name'],lsp['from_router_uid'],lsp['to_router_uid'],lsp['bandwidth'],lsp['delay'],lsp['priority'],lsp['status'],json.dumps(lsp['user_data']),
               ','.join((str(lsp['from_router_uid']), str(lsp['to_router_uid']))) if 'path' not in lsp or len(lsp['path']) == 0 else ','.join(lsp['path']),lsp['uid'])
        # print sql_str
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
            db.commit()
        db.close()
        print result

        pass

    def add_flow(self, args):
        flow_uid = args['flow_uid']
        lsp_uid = args['lsp_uid']
        status = args['status'] if 'status' in args else 0
        user_data = args['user_data'] if 'user_data' in args else {}

        #insert into t_assigned_flow values (1, 1, 16843265, 16843266, '1.1.2.1', '1.1.2.2');
        # ip = customer['ips'].split('/')[0]
        # print ip
        # mask = int(customer['ips'].split('/')[1])
        # print mask
        user_data = json.dumps(user_data)

        sql_str = 'insert into t_assigned_flow(lsp_id,flow_id,status, user_data) values (%s,%s,%s,\'%s\')' \
            % (lsp_uid,flow_uid, status, user_data)
        print sql_str
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
            db.commit()
        db.close()
        return {}

    def del_flow(self, args):
        flow_uid = args['flow_uid']
        lsp_uid = args['lsp_uid']

        sql_str = 'delete from t_assigned_flow where flow_id=%s and lsp_id=%s' % (str(flow_uid), str(lsp_uid))
        db = mysql_utils('tunnel')
        db.exec_sql(sql_str)
        db.commit()
        db.close()
        return {}



    def get_flow(self, args):
        # Get flow details (status, user_data...) of a specific LSP.
        if  'lsp_uid' in args:
            if 'flow_uids' in args :
                flow_uids = args['flow_uids']
            else:
                flow_uids = None
            lsp_uid = args['lsp_uid']
        else:
            print 'Get_flow: lsp_uid must be specified'
            return {}

        flow = {}
        if flow_uids:
            sql_str = 'SELECT * from t_assigned_flow WHERE flow_id in (%s) and lsp_id = %s' % (','.join(flow_uids), lsp_uid)
        else:
            sql_str = 'SELECT * from t_assigned_flow WHERE  lsp_id = %s' % lsp_uid

        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        db.close()

        flows = {}
        for f in result:
            flow = {}
            flow['flow_uid'] = f[10]
            flow['lsp_uid'] = f[1]
            flow['status'] = f[8]
            if f[9] and len(f[9]) > 1:
                flow['user_data'] = json.loads(f[9])
            else:
                flow['user_data'] = None
            flows[f[10]] = flow
        return flows


    def update_flow(self,args):

        if 'flow_uid' in args and 'lsp_uid' in args:
            flow_uid = args['flow_uid']
            lsp_uid = args['lsp_uid']
        else:
            print 'Update_flow: flow_uid and lsp_uid must be specified'
            return {}

        sql_str = 'SELECT * from t_assigned_flow WHERE flow_id = %s and lsp_id = %s' % (flow_uid, lsp_uid)
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)

        if not result:
            print 'Update_flow: Can not find the flow'
            db.close()
            return {}

        flow = result[0]
        status = args['status'] if 'status' in args else flow[8]
        user_data = json.dumps(args['user_data']) if 'user_data' in args else flow[9]

        sql_str = 'UPDATE t_assigned_flow SET status = %s, user_data = \'%s\' WHERE flow_id = %s and lsp_id=%s'\
                  % (status, user_data, flow_uid, lsp_uid)
        db.exec_sql(sql_str)
        db.commit()
        db.close()

        return {}

    def get_lsp_by_uid(self, uid):
        lsps = {}
        lsp = []

        sql_str = 'select * from t_lsp where t_lsp.id = %s' % uid
        print sql_str
        db = mysql_utils('tunnel')
        results = db.exec_sql(sql_str)
        db.close()

        for result in results:
            one_lsp = {}
            one_lsp['uid'] = uid
            one_lsp['name'] = result[1]
            one_lsp['from_router_uid'] = result[2]
            one_lsp['to_router_uid'] = result[5]
            one_lsp['bandwidth'] = result[8]
            one_lsp['delay'] = result[9]
            one_lsp['priority'] = result[10]

            lsp.append(one_lsp)

        lsps['lsps'] = lsp
        return lsps

    def get_lsp_by_customer(self, args):
        customers = args['cust_uids']
        lsps = {}

        sql_str = 'select * from t_assigned_flow inner join t_lsp on t_assigned_flow.lsp_id = t_lsp.id ' + \
            'and t_assigned_flow.customer_id in (%s)' % ','.join(str(c) for c in customers)
        # print sql_str
        db = mysql_utils('tunnel')
        results = db.exec_sql(sql_str)
        db.close()
        # print results
        for result in results:
            cust_uid = str(result[6])
            if cust_uid not in lsps:
                lsps[cust_uid] = []

            one_lsp = {}
            one_lsp['lsp_uid'] = str(result[1])
            one_lsp['customer_id'] = str(result[6])
            one_lsp['lsp_name'] = result[11]
            one_lsp['bandwidth'] = result[18]
            one_lsp['delay'] = result[19]
            one_lsp['priority'] = result[20]
            one_lsp['status'] = result[23]
            one_lsp['user_data'] = result[24]
            one_lsp['hop_list'] = result[25]
            one_lsp['path'] = result[26]
            lsps[cust_uid].append(one_lsp)

        return lsps

    def get_customer_by_lsp(self, args):

        if 'lsp_uids' in args:
            lsps = args['lsp_uids']
            sql_str = 'select * from t_assigned_flow where t_assigned_flow.lsp_id in (%s) and t_assigned_flow.customer_id is not null'\
                      % ','.join(str(p) for p in lsps)
        else:
            sql_str = 'select * from t_assigned_flow  t_assigned_flow.customer_id is not null'

        db = mysql_utils('tunnel')
        results = db.exec_sql(sql_str)
        db.close()
        customers = {}

        for result in results:
            lsp_uid = str(result[1])
            cust_uid = str(result[6])
            if lsp_uid not in customers:
                customers[lsp_uid] = []
            customers[lsp_uid].append(cust_uid)

        return customers

    def add_customer_to_lsp(self, args):
        cust_uid = args['cust_uid']
        lsp_uid = args['lsp_uid']

        sql_str = 'insert into t_assigned_flow (customer_id, lsp_id) VALUES (%s,%s)' % (cust_uid, lsp_uid)
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
                db.commit()
        db.close()
        return {}

    def del_customer_from_lsp(self, args):

        cust_uid = args['cust_uid']
        lsp_uid = args['lsp_uid']

        sql_str = 'delete from t_assigned_flow where t_assigned_flow.customer_id=%s and t_assigned_flow.lsp_id=%s' % (cust_uid, lsp_uid)
        db = mysql_utils('tunnel')
        result = db.exec_sql(sql_str)
        if not result:
                db.commit()
        db.close()
        return {}

    def get_lsp_by_uids(self, args):

        uids = args['lsp_uids']
        lsps = {}

        sql_str = 'select * from t_lsp where t_lsp.id in (%s)' % ','.join(uids)
        db = mysql_utils('tunnel')
        results = db.exec_sql(sql_str)
        db.close()


        for result in results:
            uid = result[0]
            one_lsp = {}
            one_lsp['uid'] = uid
            one_lsp['name'] = result[1]
            one_lsp['from_router_uid'] = result[2]
            one_lsp['to_router_uid'] = result[5]
            one_lsp['bandwidth'] = result[8]
            one_lsp['delay'] = result[9]
            one_lsp['priority'] = result[10]
            one_lsp['status'] = result[13]

            lsps[uid] = one_lsp

        return lsps

