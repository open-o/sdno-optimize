#!/usr/bin/env python
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

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import json
import re
from db_util import mysql_utils
from common import *
import datetime
from base_handler import base_handler


class ms_handler(base_handler):
    def initialize(self):
        super(ms_handler, self).initialize()
        pass

    #For service register
    def post(self, dummy):
        ctnt = self.request.body
        print 'Fake Open-O: Received post \n'
        print str(ctnt)
        try:
            req = json.loads(str(ctnt))
        except:
            self.write('Invalid Request')
            self.finish()

        sn = req['serviceName']
        if sn not in self.application.service_entry:
            self.application.service_entry[sn] = req
        else:
            added = []
            nodes = req['nodes']
            for n in nodes:
                exists = 0
                for ex in self.application.service_entry[sn]['nodes']:
                    if ex['ip'] == n['ip'] and ex['port'] == n['port']:
                        exists = 1
                        break
                    pass
                if not exists:
                    added.append(n)
                pass
            self.application.service_entry[sn]['nodes'] += added

        self.write('{}')
        self.finish()
        pass

    #For servcie query
    def get(self, input):

        serv = {}

        m = self.application.query_service_pat.match(input)
        if m and m.groups():
            sn = m.groups()[0]
            if sn in self.application.service_entry:
                serv = self.application.service_entry[sn]

        print 'Fake Open-O service: Returned get \n'
        print(json.dumps(serv))

        self.write(json.dumps(serv))
        self.finish()
        pass

class driver_handler(base_handler):
    def initialize(self):
        super(driver_handler, self).initialize()
        pass

    #For driver register
    def post(self, dummy):
        ctnt = self.request.body
        print 'Fake Open-O driver: Received post \n'
        print str(ctnt)
        try:
            req = json.loads(str(ctnt))
        except:
            self.write('Invalid Request')
            self.finish()

        sn = req['driverInfo']['driverName']
        if sn not in self.application.service_entry:
            self.application.service_entry[sn] = req
        else:
            added = []
            services = req['driverInfo']['services']
            for item in services:
                exists = 0
                for ex in self.application.service_entry[sn]['driverInfo']['services']:
                    if ex['service_url'] == item['service_url']:
                        exists = 1
                        break
                    pass
                if not exists:
                    added.append(item)
                pass
            self.application.service_entry[sn]['driverInfo']['services'] += added

        self.write('{}')
        self.finish()
        pass

    #For driver query
    def get(self, input):

        serv = [
          {
            "driverName": "sdno-driver-ct-te",
            "instanceID": "vnfm-0-1",
            "ip": "10.23.63.21",
            "port": "23456",
            "protocol": "http",
            "services": [
                       {
                           "service_url":"/openoapi/sbi-l3vpn/v1",
                       "support_sys":[
                                            {   "type":"Agile Controller-DCN",
                                                "version":"V100R002"
                                            },
                                            {   "type":"Agile Controller-DCN",
                                                "version":"V100R003"
                                            }
                                         ]
                         },
                        {
                           "service_url":"/openoapi/sbi-l2vpn/v1",
                           "support_sys":[
                                            {   "type":"Agile Controller-DCN",
                                                "version":"V100R003"
                                            }
                                         ]
                         }
                       ]
          }]
        print 'Fake Open-O driver: Returned get \n'
        print(json.dumps(serv))
        self.write(json.dumps(serv))
        self.finish()
        pass

class esr_handler(base_handler):
    def initialize(self):
        super(esr_handler, self).initialize()
        pass

    #For ers controller query
    def post(self, dummy):
        ctnt = self.request.body
        print 'Fake Open-O esr: Received post \n'
        print str(ctnt)
        try:
            req = json.loads(str(ctnt))
        except:
            self.write('Invalid Request')
            self.finish()

        resp = {'driver_url':'', 'type':'', 'vendor':'ZTE', 'version':''}

        self.write(json.dumps(resp))
        self.finish()
        pass

    def get(self, input):
        resp = {
       "sdnControllerId":"a6c42529-cd6b-4c01-b149-03eb54b20a03",
       "name":"sdn",
       "url":"http://10.74.151.13:8181",
       "userName":"admin",
       "password":"admin",
       "version":"v1.0",
       "vendor":"ZTE",
       "description":"",
       "protocol":"netconf",
       "productName":"",
       "type":"ODL",
       "createTime":"2016-07-18 12:22:53"
        }
        self.write(json.dumps(resp))
        self.finish()
        pass

class brs_handler(base_handler):
    def initialize(self):
        super(brs_handler, self).initialize()
        pass

    def get(self, input):
        resp = {}
        db = mysql_utils('topology')
        if input.startswith('managed-elements'):
            'Get equipments'
            sql_txt = 'SELECT * FROM t_router'
            res = db.exec_sql(sql_txt)
            num = len(res)
            resp['totalNum'] = num
            eles = []
            for e in res:
                one_me = {'id':str(e[0]), 'name':e[2],'ipAddress':e[4], 'community':e[5],
                          'x':e[7], 'y':e[8], 'manufacturer':e[6]}
                eles.append(one_me)
                pass
            resp['managedElements'] = eles
        elif input.startswith('logical-termination-points'):
            meid = input.split('=')[1]
            sql_txt = 'SELECT * FROM t_port where router_id=%s' % str(meid)
            res = db.exec_sql(sql_txt)
            num = len(res)
            resp['totalNum'] = num
            ports = []
            for p in res:
                one_p = {'id':str(p[0]), 'name':p[4], 'portIndex':p[9], 'phyBW':p[5],
                         'macAddress':p[6], 'ipAddress':p[8], 'type':p[2] }
                ports.append(one_p)
            resp['logicalTerminationPoints'] = ports

        elif input.startswith('topological-links'):
            sql_txt = 'SELECT * FROM t_link'
            res = db.exec_sql(sql_txt)
            num = len(res)
            resp['totalNum'] = num
            lks = []
            for lk in res:
                one_lk = {'id':str(lk[0]), 'aEnd':str(lk[1]), 'zEnd':str(lk[2]), 'phyBW':lk[4]}
                lks.append(one_lk)
            resp['topologicalLinks'] = lks
            pass

        self.write(json.dumps(resp))
        self.finish()
        pass


class openo_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/openoapi/microservices/v1/services(.*)', ms_handler),
            (r'/openoapi/sdno-brs/v1/(.*)', brs_handler),
            (r'/openoapi/extsys/v1/sdncontrollers(.*)', esr_handler),
            (r'/openoapi/drivermgr/v1/drivers(.*)', driver_handler)
        ]

        self.service_entry = {}
        self.query_service_pat = re.compile(r'/(.+?)/version/(.+)')

        tornado.web.Application.__init__(self, handlers)
        pass

if __name__ == '__main__':
    app = openo_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8086)
    tornado.ioloop.IOLoop.instance().start()
