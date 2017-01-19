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

#
# Mysql
#

# Delete mysql replacement
yum erase -y mariadb* 

# Ensure the /root/.mysql_secret file been created
yum install -y perl-Module-Install.noarch

# Add yum repo to system
rpm -ivh http://dev.mysql.com/get/mysql57-community-release-el7-9.noarch.rpm 

# Install mysql stuff
yum install mysql-community-server.x86_64 mysql-community-client.x86_64 mysql-community-devel.x86_64 -y

/sbin/iptables -I INPUT -p tcp --dport 3306 -j ACCEPT

service mysqld start
sleep 10

# Change password of mysql
service mysqld stop
mysqld --user=mysql --skip-grant-tables --skip-networking &
sleep 5
mysql -uroot mysql -e "use mysql; update mysql.user SET authentication_string= PASSWORD ('root') WHERE User='root'; flush privileges;"
pkill mysqld
service mysqld start

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
pip install dotmap
pip install bottle

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

