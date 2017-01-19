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
from jsonrpc import *
import time
from microsrvurl import *
from common import  *
import copy

class topo_fetcher(object):
    def __init__(self):
        self.equips = []
        self.equip_map = {}
        self.port_map = {}
        self.vlink_map = {}
        self.vlinks = []
        self.simple_vlinks = []

        #timestamp for last fetch.
        self.last_equip_ts = 0
        self.last_port_ts = 0
        self.last_vlink_ts = 0
        self.vlink_modified = 0

        self.brs = None

        self.brs_equip_key_map = {'id':'uid', 'name':'name', 'ipAddress':'ip_str', 'manufacturer':'vendor'}
        self.brs_port_key_map = {'id':'uid', 'ipAddress':'ip_str', 'macAddress':'mac',
                                 'phyBW':'capacity','portIndex':'if_index', 'name':'if_name'}
        self.brs_link_key_map = {'id':'uid', 'aEnd':'sport', 'zEnd':'dport','phyBW':'bandwidth'}

        pass

    def prepare(self):
        # self.brs = openo_query_service('sdno-brs', 'v1')
        self.brs = microsrvurl_dict['openo_brs_url']
        pass

    def fetch_equip(self):

        fetched = 0
        # if self.brs and 'nodes' in self.brs and len(self.brs['nodes']) > 0:
        if self.brs:
            # n = self.brs['nodes'][0]
            url = self.brs + '/managed-elements'
            rpc = base_rpc(url)
            resp = rpc.do_sync_get()
            try:
                brs_me = json.loads(resp)
                mes = brs_me['managedElements']
                equip = []
                for me in mes:
                    e = {}
                    for k in me:
                        if k in self.brs_equip_key_map:
                            e[self.brs_equip_key_map[k]] = me[k]
                        else:
                            e[k] = me[k]
                    equip.append(e)
                    pass
                fetched = 1
            except:
                pass

        if fetched == 0:
            rpc = base_rpc(microsrvurl_dict['microsrv_topo_url'])
            args = {}
            args['last_fetch'] = self.last_equip_ts
            rpc.form_request('ms_topo_get_equip', args)
            equip = rpc.do_sync_post()
            if equip is None:
                return
            self.last_equip_ts = time.strftime("%Y%m%d%H%M%S")

            # the return result should be an array of equipment object
            equip = equip['routers']
            pass

        self.equips = equip
        self.equip_map = {}
        for e in equip:
            self.equip_map[e['uid']] = e


        #equipment data modified, force port and link re-fetch
        self.last_port_ts = 0
        self.last_vlink_ts = 0
        pass

    def fetch_port(self):

        rpc_brs = None
        url = ''
        # if self.brs and 'nodes' in self.brs and len(self.brs['nodes']) > 0:
        if self.brs :
            # n = self.brs['nodes'][0]
            url = self.brs + '/logical-termination-points/meID='
            rpc_brs = base_rpc()


        pmap = {}
        for e in self.equips:
            fetched = 0
            if rpc_brs:
                try:
                    url_o = url + str(e['uid'])
                    rpc_brs.set_url(url_o)
                    resp = rpc_brs.do_sync_get()
                    resp = json.loads(resp)
                    brs_ports = resp['logicalTerminationPoints']
                    ports = []
                    for brs_p in brs_ports:
                        p = {}
                        for k in brs_p:
                            if k in self.brs_port_key_map:
                                p[self.brs_port_key_map[k]] = brs_p[k]
                            else:
                                p[k] = brs_p[k]
                        ports.append(p)
                    fetched = 1
                except:
                    pass

            if fetched == 0:
                arg = {}
                arg['last_fetch'] = self.last_port_ts
                arg['uid'] = e['uid']
                rpc = base_rpc(microsrvurl_dict['microsrv_topo_url'])
                rpc.form_request('ms_topo_get_ports', arg)
                ports = rpc.do_sync_post()
                if ports is None:
                    continue
                ports = ports['ports']


            e['ports'] = ports

            # save the mapping of portid to router
            for p in ports:
                pmap[p['uid']] = dict(equip=e, port=p)

            pass
        self.last_port_ts = time.strftime("%Y%m%d%H%M%S")
        if len(pmap) > 0:
            self.port_map = pmap
        pass


    def fetch_vlink(self):

        fetched = 0
        # if self.brs and 'nodes' in self.brs and len(self.brs['nodes']) > 0:
        if self.brs :
            # n = self.brs['nodes'][0]
            # url = 'http://' + n['ip'] + ':' + str(n['port']) + self.brs['url'] + '/topological-links'
            url = self.brs + '/topological-links'
            rpc = base_rpc(url)
            resp = rpc.do_sync_get()
            try:
                resp = json.loads(resp)
                brs_links = resp['topologicalLinks']
                vlinks = []
                for bl in brs_links:
                    v = {}
                    for k in bl:
                        if k in self.brs_link_key_map:
                            v[self.brs_link_key_map[k]] = bl[k]
                        else:
                            v[k] = bl[k]
                        pass
                    vlinks.append(v)
                    pass
                fetched = 1
                self.vlink_modified = 1
            except:
                pass

        if fetched == 0:
            rpc = base_rpc(microsrvurl_dict['microsrv_topo_url'])
            args = {}
            args['last_fetch'] = self.last_vlink_ts
            rpc.form_request('ms_topo_get_vlink', args)
            vlinks = rpc.do_sync_post()
            if vlinks is None:
                return

            self.vlink_modified = 1
            self.last_vlink_ts = time.strftime("%Y%m%d%H%M%S")

            # the return result should be an array of links
            vlinks = vlinks['vlinks']
            pass


        self.vlinks = vlinks
        for v in vlinks:
            cv = copy.copy(v)
            self.simple_vlinks.append(cv)

        # fill the vlink with its equipment and physical port info. Will be used for link utilization fetch.
        lmap = {}
        for v in self.vlinks:
            portid = v['sport']
            dport = v['dport']
            if portid not in self.port_map:
                continue
            e = self.port_map[portid]['equip']
            de = self.port_map[dport]['equip']
            p = self.port_map[portid]['port']

            v['ports'] = []
            type = p['type'] if 'type' in p else 0
            if type == 1:
                ' vitual ports '
                vid = p['uid']
                for pp in e['ports']:
                    if 'vport_id' in pp and pp['vport_id'] == vid:
                        v['ports'].append(pp)
                        lmap[pp['uid']] = v
                    pass
            else:
                v['ports'].append(p)
                lmap[p['uid']] = v
            v['sequip'] = e
            v['dequip'] = de

        if len(lmap) > 0:
            self.vlink_map = lmap

        pass


class customer_fetcher(object):

    def __init__(self):
        self.last_fetch_ts = 0
        self.cus_map = {}
        self.customers = {}
        pass

    def fetch_customer(self):
        rpc = base_rpc(microsrvurl_dict['microsrv_cust_url'])
        args = {}
        args['last_fetch'] = self.last_fetch_ts

        rpc.form_request('ms_cust_get_all', args)
        cust = rpc.do_sync_post()
        if cust is None or 'customers' not in cust:
            return

        self.last_fetch_ts = time.strftime('%Y%m%d%H%M%S')
        cust = cust['customers']

        self.customers = cust

        for one_cust in cust:
            if 'uid' in one_cust:
                self.cus_map[one_cust['uid']] = cust
        pass

    pass
