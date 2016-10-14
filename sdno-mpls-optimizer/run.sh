#!/bin/bash
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

PROC_UNIQ_KEY=e152313f-284e-4059-b7c4-f76260606dc0

BASEDIR=$(dirname $(readlink -f $0))
nohup python ${BASEDIR}/lsp_serv.py --uniq=${PROC_UNIQ_KEY} &> /dev/null &
nohup python ${BASEDIR}/flow_sche_serv.py --uniq=${PROC_UNIQ_KEY} &> /dev/null &
nohup python ${BASEDIR}/tunnel_server.py --uniq=${PROC_UNIQ_KEY} &> /dev/null &
