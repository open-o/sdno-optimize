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

from jsonrpc import *
import json
from microsrvurl import *

def openo_register(name, ver, url, ip, port, ttl = 0):

    req = {'serviceName':name, 'version':ver, 'url':url, 'protocol':'REST', 'visualRange':1,
           'nodes':[{'ip':ip, 'port':port, 'ttl':ttl}]}
    rpc = base_rpc(microsrvurl_dict['openo_ms_url'])
    rpc.set_request(req)
    resp = rpc.do_sync_post(0)
    # print('******')
    # print openo_query_service(name, ver)
    pass

def openo_driver_register(name, id, ver, url, ip, port, type):

    req = {"driverInfo":
            {"driverName": name, "instanceID": id, "ip": ip, "port": port, "protocol": "REST",
             "services": [{"service_url":url,
                           "support_sys":[{"type":type,"version":ver}]}]}}

    rpc = base_rpc(microsrvurl_dict['openo_dm_url'])
    rpc.set_request(req)
    resp = rpc.do_sync_post(0)
    # print json.loads(resp)
    # print('******')
    # print openo_query_driver(name, id, ver)
    pass

def openo_esr_controller_info_req(controller_id):
    req = {"ControllerID":controller_id}

    rpc = base_rpc(microsrvurl_dict['openo_esr_url'] + '/' + controller_id)
    resp = rpc.do_sync_get()
    # print json.loads(resp)
    # print('******')
    return resp
    pass

def openo_query_driver(name, id, ver):
    # batch query or exact query, temp batch
    # url = openo_dm_url + '/' + name + '/version/' + ver
    url = microsrvurl_dict['openo_dm_url'] + '/' + name + '/version/' + ver
    rpc = base_rpc(url)
    resp = rpc.do_sync_get()
    if resp is None:
        return None
    try:
        serv = json.loads(resp)
    except:
        return None


    return serv

def openo_query_service(name, ver):
    url = microsrvurl_dict['openo_ms_url'] + '/' + name + '/version/' + ver
    rpc = base_rpc(url)
    resp = rpc.do_sync_get()
    if resp is None:
        return None
    try:
        serv = json.loads(resp)
    except:
        return None


    return serv

