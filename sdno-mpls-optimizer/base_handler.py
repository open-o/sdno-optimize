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
import traceback
import json
from jsonrpc import base_rpc

import logging

logging.basicConfig(level=logging.DEBUG)

class base_handler(tornado.web.RequestHandler):


    def map_obj_key(self, src, map):
        dst = {}
        for k in src:
            if k in map:
                dst[map[k]] = src[k]
            else:
                dst[k] = src[k]
        return dst

    @tornado.gen.coroutine
    def do_query(self, url, request, args):
        resp = {'err_code':-1}
        try:
            rpc = base_rpc('')
            rpc.form_request(request, args)
            req_body = json.dumps(rpc.request_body)
            logging.debug('Request:\n' + req_body)
            http_req = tornado.httpclient.HTTPRequest(url, method='POST', body=req_body)
            client = tornado.httpclient.AsyncHTTPClient()
            resp = yield tornado.gen.Task(client.fetch, http_req)
            logging.debug('Response:\n' + '' if resp.body is None else resp.body)
            try:
                resp = json.loads(resp.body)
            except:
                traceback.print_exc()
        except (LookupError, TypeError):
            traceback.print_exc()
            pass

        raise tornado.gen.Return(resp)


class base_model(object):
    def __init__(self):
        #self.attr = []
        pass

    def __setattr__(self, name, val):
        object.__setattr__(self, name, val)

    def set_attrib(self, name, val):
        if name in self.__dict__:
            object.__setattr__(self, name, val)
        pass

    def get_attrib(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return None

    def __str__(self):
        return  json.dumps(self.__dict__)