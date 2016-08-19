#coding:utf-8
'''
version:1.0
date:2016-08-13
starting:
        修复doctor/master大小写相关漏洞
result:
       已提取到相关结果，并且已经生成相关txt文件
tips：
    需要根据不同数据表的记录属性结构，进行相应的提取结果的列表索引的修改
'''

import pymysql
import re

database = 'ustcbbs'
table = 'csjobsv2'
conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='0551', db=database, charset='utf8')
cur = conn.cursor()

Result = {}
fobj = open('Result.txt', 'w')

def analysisData():
    cur.execute('select * from %s' % (table,))
    datas = cur.fetchall()
    print('len(datas):', len(datas))

    for data in datas:
        date = data[0]
        content = data[2]

        # print("type(date):", type(date))
        # print("type(content):", type(content))
        datestr = str(date)
        # print("type(datestr):", type(datestr))
        # print('datestr:', datestr)
        year = re.findall(re.compile('\d+'), datestr)[0]
        #print(year)
        if year not in Result.keys():
            #      统计数据：总数，硕士，博士
            Result[year] = {}
            Result[year]['all'] = 0
            Result[year]['master'] = 0
            Result[year]['doctor'] = 0

        Result[year]['all'] += 1
        master = re.search("硕士|master", content.lower())
        if master:
            Result[year]['master'] += 1
        doctor = re.search("博士|doctor", content.lower())
        if doctor:
            Result[year]['doctor'] += 1

    print("year  all  master  doctor")
    fobj.write("year\tall\tmaster\tdoctor\n")

    for key in Result.keys():
        print('%s  %3d %5d %6d' %(key, Result[key]['all'], Result[key]['master'], Result[key]['doctor']))
        fobj.write('%s\t%d\t%d\t%d\n'%(key, Result[key]['all'], Result[key]['master'], Result[key]['doctor']))

analysisData()
cur.close()
conn.close()
fobj.close()

