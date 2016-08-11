#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'liyiqun'

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen
import traceback
import json
from jsonrpc import base_rpc


class base_handler(tornado.web.RequestHandler):

    @tornado.gen.coroutine
    def do_query(self, url, request, args):
        resp = {'err_code':-1}
        try:
            rpc = base_rpc('')
            rpc.form_request(request, args)
            req_body = json.dumps(rpc.request_body)
            print 'Request:\n' + req_body
            http_req = tornado.httpclient.HTTPRequest(url, method='POST', body=req_body)
            client = tornado.httpclient.AsyncHTTPClient()
            resp = yield tornado.gen.Task(client.fetch, http_req)
            print 'Response:\n' + resp.body
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