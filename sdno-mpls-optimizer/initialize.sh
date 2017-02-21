#!/bin/bash
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

BASEDIR=$(dirname $(readlink -f $0))

while [ "$DEBUG" == "1" ]; do
    echo "========================"
    echo "= DEBUG LOOP           ="
    echo "========================"
    if [ -e "/tmp/debug.bye" ]; then
        echo "Exit debug loop"
        break
    fi
    sleep 60
    if [ -e "/tmp/debug.sh" ]; then
        chmod +x /tmp/debug.sh
        sh /tmp/debug.sh
    fi
done

#
# Mysql
#

/sbin/iptables -I INPUT -p tcp --dport 3306 -j ACCEPT

echo "Reset MySql password"
for i in {1..10}; do
    /usr/bin/mysqladmin -uroot -prootpass password 'root' &> /dev/null && break
    sleep $i
done

#
# Python
#
	
#
# Ensure the python-pip can be found and installed
#
yum -y install epel-release
yum install -y python-pip
pip install --upgrade pip

pip install epydoc
pip install tornado
pip install coverage
pip install dotmap
pip install bottle
pip install paste

# Download and install the swagger module
curl https://github.com/SerenaFeng/tornado-swagger/archive/master.zip -L -o /tmp/swagger.zip 
yum install -y unzip
rm -fr /tmp/swagger/
unzip /tmp/swagger.zip -d /tmp/swagger/
cd /tmp/swagger/tornado-swagger-master
python setup.py install
cd ${BASEDIR}

# Python MySQL things
yum install -y gcc.x86_64 
yum install -y python-devel
pip install MySQL-python
pip install DBUtils

. ./db.sh

