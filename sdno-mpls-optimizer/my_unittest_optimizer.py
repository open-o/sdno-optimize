__author__ = 'chenhg'

from tornado.testing import *
from base_handler import *
import time
import os
import subprocess
lsp_serv_cmd = 'coverage run --parallel-mode lsp_serv.py'
test_serv_cmd = 'coverage run --parallel-mode test.py'
fake_openo_serv_cmd = 'coverage run --parallel-mode fake_openo.py'
# tunnel_server_cmd = 'coverage run --parallel-mode tunnel_server.py'
# cus_server_cmd = 'coverage run --parallel-mode customer_server.py'
# ms_controller_cmd = 'coverage run --parallel-mode ms_controller.py'
# os.system(command)

optimizer_prefix_lsp_uri = r'http://127.0.0.1:8620/openoapi/sdnooptimize/v1/lsp'
optimizer_prefix_vsite_lsp_uri = r'http://127.0.0.1:8620/openoapi/sdnooptimize/v1/vsite/lsp'
optimizer_lsp_uri_param = '0'
optimizer_prefix_flow_uri = r'http://127.0.0.1:8620/openoapi/sdnooptimize/v1/flow-policy'
optimizer_prefix_lsp_vsite_uri = r'http://127.0.0.1:8620/openoapi/sdnooptimize/v1/lsp/vsite'
optimizer_vsite_uri_param = '19'

class Test_Optimizer(AsyncTestCase):
    def setUp(self):
        super(Test_Optimizer,self).setUp()
        pass

    def tearDown(self):
        super(Test_Optimizer,self).tearDown()
        
    @tornado.testing.gen_test
    def test_i_delete_lsp(self):
        print('test_delete_lsp:')
        code, resp = yield base_handler.do_json_get(optimizer_prefix_lsp_uri + '/' + optimizer_lsp_uri_param, metd='DELETE')
        self.assertEqual(200, code, 'FAIL:test_delete_lsp, lsp deleted not 200')

    @tornado.testing.gen_test
    def test_h_delete_flow_policy(self):
        print('test_delete_flow_policy:')
        optimizer_del_param = '?lsp_uid=' + optimizer_lsp_uri_param + '&vsite_uid=' + optimizer_vsite_uri_param
        code, resp = yield base_handler.do_json_get(optimizer_prefix_flow_uri + optimizer_del_param, metd='DELETE')
        self.assertEqual(200, code, 'FAIL:test_delete_flow_policy not 200')

    @tornado.testing.gen_test
    def test_g_get_lsp_by_vsite(self):
        code, resp = yield base_handler.do_json_get(optimizer_prefix_lsp_vsite_uri + '/' + optimizer_vsite_uri_param)
        print('test_get_lsp_by_vsite:')
        self.assertEqual(200, code, 'FAIL:test_get_lsp_by_vsite')

    @tornado.testing.gen_test
    def test_f_get_vsite_by_lsp(self):
        code, resp = yield base_handler.do_json_get(optimizer_prefix_vsite_lsp_uri + '/' + optimizer_lsp_uri_param)
        print('test_get_vsite_by_lsp:')
        self.assertEqual(200, code, 'FAIL:test_get_vsite_by_lsp')

    @tornado.testing.gen_test
    def test_e_post_flow_policy(self):
        print('test_post_flow_policy:')
        #req:   {"lsp_uid": "lsp_0", "vsite_uid": "19"}
        req_body = {"lsp_uid": optimizer_lsp_uri_param,"vsite_uid": optimizer_vsite_uri_param}
        code, resp = yield base_handler.do_json_post(optimizer_prefix_flow_uri, req_body)
        self.assertEqual(200, code, 'FAIL:test_post_flow_policy')

    @tornado.testing.gen_test
    def test_d_put_lsp(self):
        print('test_put_lsp:')
        req_body = {"uid":optimizer_lsp_uri_param,"bandwidth": 1000.0}
        code, resp = yield base_handler.do_json_post(optimizer_prefix_lsp_uri, req_body, metd='PUT')
        self.assertEqual(200, code, 'FAIL:test_put_lsp, lsp updated not 200')

    @tornado.testing.gen_test
    def test_c_get_an_lsp(self):
        code, resp = yield base_handler.do_json_get(optimizer_prefix_lsp_uri + '/' + optimizer_lsp_uri_param)
        print('test_get_an_lsp:')
        self.assertIn('lsps', resp, 'FAIL:test_get_an_lsp, key \'lsps\' not found')

    @tornado.testing.gen_test
    def test_b_get_all_lsp(self):
        code, resp = yield base_handler.do_json_get(optimizer_prefix_lsp_uri)
        print('test_get_all_lsp:')
        self.assertIn('lsps', resp, 'FAIL:test_get_all_lsp, key \'lsps\' not found')

    @tornado.testing.gen_test
    def test_a_post_lsp(self):
        print('test_post_lsp:')
        #req:   {"hop_list": ["2", "6"], "ingress_node_uid": "2", "ingress_node_name": "", "lsp_name": "alu_2_6_lsp", "egress_node_uid": "6", "priority": null, "bandwidth": 100.0, "delay": null, "egress_node_name": ""}
        #resp:  {"status": 0, "lsp_uid": "xyz123"}
        req_body = {"hop_list": ["2", "6"], "ingress_node_uid": "2", "ingress_node_name": "", "lsp_name": "alu_2_6_lsp", "egress_node_uid": "6", "priority": 7, "bandwidth": 100.0, "delay": 0, "egress_node_name": ""}
        code, resp = yield base_handler.do_json_post(optimizer_prefix_lsp_uri, req_body)
        if 'lsp_uid' in resp:
            global optimizer_lsp_uri_param
            optimizer_lsp_uri_param = str(resp['lsp_uid'])
        self.assertIn('lsp_uid', resp, 'FAIL:test_post_lsp, key \'lsp_uid\' not found')

if __name__ == '__main__':
    print '---Service Started....'
    # os.system('coverage erase')
    lsp_serv = subprocess.Popen(lsp_serv_cmd, shell=True)
    test_serv = subprocess.Popen(test_serv_cmd, shell=True)
    fake_serv = subprocess.Popen(fake_openo_serv_cmd, shell=True)
    # tunnel_server = subprocess.Popen(tunnel_server_cmd, shell=True)
    # cus_server = subprocess.Popen(cus_server_cmd, shell=True)
    # ms_controller_server = subprocess.Popen(ms_controller_cmd, shell=True)
    time.sleep(3)
    suite = unittest.TestLoader().loadTestsFromTestCase(Test_Optimizer)
    unittest.TextTestRunner(verbosity=2).run(suite)
    try:
        print '---Service Terminated...'
        sig = 2 #signal.SIGINT
        lsp_serv.send_signal(sig)
        test_serv.send_signal(sig)
        fake_serv.send_signal(sig)
        # tunnel_server.send_signal(sig)
        # cus_server.send_signal(sig)
        # ms_controller_server.send_signal(sig)
        print '@@@Service Terminated...'
        pass
    except:
        print '*****Service Terminated...'
        traceback.print_exc()
        pass
    # subprocess.Popen('tskill python & tskill python', shell=True)
    # os.system('coverage combine & coverage html')
    print '+++Service Terminated...'
