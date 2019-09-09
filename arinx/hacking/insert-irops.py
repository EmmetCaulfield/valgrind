#!/usr/bin/python3

import sqlite3
from itertools import chain

conn = sqlite3.connect('vexdb.db')
curs = conn.cursor()

ItyToId=dict()

for row in curs.execute('SELECT id, cenum FROM Ity'):
    ItyToId[row[1]]=row[0]

ItyToId['ity_RMode']=ItyToId['Ity_I32']

with open('all-sigs.csv') as f:
    for line in f:
        line=line.rstrip()
        fields=line.split(',')
        mnem=fields[0]          # Mnemonic
        no=int(fields[1])       # Number of args
        qp=tuple(int(ItyToId[x]) for x in fields[3:8]) # Query params

        sql=''
        if no >= 2:
            sql='SELECT id FROM Sig WHERE res=? AND od1=?'
        if no >= 3:
            sql += ' AND od2=?'
        if no >= 4:
            sql += ' AND od3=?'
        if no==5:
            sql += ' AND od4=?'

        try:
            for row in curs.execute(sql, qp):
                print(line + "," + str(row[0]))
        except Exception as e:
            print(e)
            print(line)

        conn.commit()
conn.close()
