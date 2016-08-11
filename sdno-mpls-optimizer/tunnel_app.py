#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = 'pzhang'

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options

from tunnel_handler import ms_tunnel_handler

class tunnel_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', ms_tunnel_handler)
        ]
        tornado.web.Application.__init__(self, handlers)
        pass