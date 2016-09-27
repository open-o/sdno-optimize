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

    rpc = base_rpc(openo_ms_url)
    rpc.set_request(req)
    resp = rpc.do_sync_post(0)

    # openo_query_service(name, ver)
    pass


def openo_query_service(name, ver):
    url = openo_ms_url + '/' + name + '/version/' + ver
    rpc = base_rpc(url)
    resp = rpc.do_sync_get()
    if resp is None:
        return None
    try:
        serv = json.loads(resp)
    except:
        return None


    return serv

