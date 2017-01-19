#!/usr/bin/python
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

import MySQLdb
from DBUtils.PooledDB import PooledDB

class mysql_utils(object):
    __pool = {}
    dbhost = 'localhost'
    dbusr = 'root'
    dbpwd = 'root'
    dbport = 3306
    name = ''

    def __init__(self, db):
        self.dbname = db
        self.dbc = mysql_utils.__getConn(self.dbname)
        self.cursor = self.dbc.cursor()

    @staticmethod
    def __getConn(dbname):
        """
        @return MySQLdb.connection
        """
        if dbname not in mysql_utils.__pool:
            mysql_utils.__pool[dbname] = PooledDB(creator=MySQLdb, mincached=1 , maxcached=20 ,
                              host=mysql_utils.dbhost , port=mysql_utils.dbport , user=mysql_utils.dbusr ,
                              passwd=mysql_utils.dbpwd ,
                              db=dbname,use_unicode=False,charset='utf8')
        return mysql_utils.__pool[dbname].connection()


    def close(self):
        if self.dbc is not None:
            self.cursor.close()
            self.dbc.close()

    def commit(self):
        try:
            if self.dbc is not None:
                self.dbc.commit()
            return 0
        except Exception,data:
            self.dbc.rollback()
            print 'DB commit error ' + str(Exception) + str(data)
            return -1

    def exec_sql(self, sqltxt):
        if self.cursor != None:
            try:
                self.cursor.execute(sqltxt)
                result = self.cursor.fetchall()
                return result
            except Exception,data:
                print 'During execute:' + str(sqltxt)
                print 'SQL Exception:' + str(Exception) + str(data)
                return None
        else :
            return None

if __name__ == '__main__':
    db1 = mysql_utils('topology')
    db2 = mysql_utils('customer')

    res1 =  db1.exec_sql('select * from t_router')
    res2 =  db2.exec_sql('select * from t_customer')
    db1.close()
    db2.close()
    print res1
    pass

