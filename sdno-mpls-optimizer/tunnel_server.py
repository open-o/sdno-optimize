#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = 'pzhang'

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options

from tunnel_app import tunnel_app


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = tunnel_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(33770)
    tornado.ioloop.IOLoop.instance().start()