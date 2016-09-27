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

import time
import urllib2
import json
import zlib
import re

class RedirectHandler(urllib2.HTTPRedirectHandler):

    def process_location(self, req, fp,code,msg, headers, newurl=''):
        pat = re.compile('Location:\s*.+');
        loctxt = pat.findall(str(headers))[0];
        pat = re.compile('http://.+');
        newurl = pat.findall(loctxt)[0];

        reqbody = req.get_data();
        request = urllib2.Request(newurl);
        #request.add_header('Content-Type', 'application/x-www-form-urlencoded');
        opener = urllib2.build_opener(RedirectHandler);
        return opener.open(request, reqbody);

    def http_error_301(self, req, fp, code, msg, headers):
        return self.process_location(req, fp, code, msg, headers);
        pass;
    def http_error_302(self, req, fp, code, msg, headers):
        return self.process_location(req, fp, code, msg, headers);

class base_rpc(object):
    def __init__(self, url='', gz = 0):
        self.target_url = url
        self.request_body = {}
        self.gzip = gz

    def form_request(self, req, arg):
        self.request_body['request'] = req
        self.request_body['args'] = {} if arg is None else arg
        self.request_body['trans_id'] = int(time.time())
        self.request_body['ts'] = time.strftime("%Y%m%d%H%M%S")
        return self.request_body

    def set_request(self, req):
        self.request_body = req
        pass
    def set_url(self,url):
        self.target_url = url

    def do_sync_get(self):
        try:
            opener = urllib2.build_opener(RedirectHandler)
            request = urllib2.Request(self.target_url)
            response = opener.open(request)
            data = response.read()
            return data
        except:
            return None


    def do_sync_post(self, check_resp = 1):
        try:
            json_obj = json.dumps(self.request_body)
            # print 'JSON RPC Request\n' + str(json_obj)
            request = urllib2.Request(self.target_url)
            request.add_header('Content-Type', 'application/json')
            if self.gzip != 0:
                request.add_header('Content-Encoding', 'gzip')
                json_obj = zlib.compress(json_obj)
                request.add_header('Accept-encoding', 'gzip')

            opener = urllib2.build_opener(RedirectHandler)
            response = opener.open(request, json_obj)
            data = response.read()
            hdr = response.headers.get('Content-Encoding')
            if hdr:
                data = zlib.decompress(data)
            # print 'JSON RPC Response:\n' + str(data);
            if check_resp:
                return self.check_response(data)
            else:
                return data

        except Exception, data:
            print 'Exception during post:'
            print str(Exception) + ':' + str(data)
            return None
        pass


    def check_response(self, resp_body):
        # print resp_body;
        try:
            resp = {}
            resp = json.loads(resp_body)
            if resp['response'] != self.request_body['request']:
                print 'Error: Unmatched response, request method is ' + str(self.request_body['request']) + \
                    ' but got the response ' + resp['response']
                return None
            if resp['trans_id'] != self.request_body['trans_id']:
                print 'Error: Unmatched transaction id in response'
                return None

            if int(resp['err_code']) != 0:
                print 'Error: ' + str(self.request_body['request']) + ' got error response: ' + str(resp['err_code'])
                if 'msg' in resp:
                    print 'error message is ' + str(resp['msg'])
                return None

            r = resp['result']
            if r is None:
                r = {}
            return r

        except Exception, data:
            print 'Exception in response of \'' + str(self.request_body['request']) + '\''
            print str(Exception) + ':' + str(data)
        return None





