#!/usr/bin/python3

import sqlite3
from itertools import chain

conn = sqlite3.connect('vexdb.db')
curs = conn.cursor()

ItyToId=dict()

for row in curs.execute('SELECT id, "Ity_" || btype || nbits AS cenum FROM IRType'):
    ItyToId[row[1]]=row[0]
curs.execute('DELETE FROM AiOpSig')
conn.commit()
    
ItyToId['ity_RMode']=ItyToId['Ity_I32']



with open('unique-opsigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        n=int(fields[0])
        if n<2 or n>5:
            raise Exception("Invalid operand count.")
        u=int(fields[1])
        r=False;
        if fields[2]=='ity_RMode':
            r=True
        values=chain((n, u, r), (int(ItyToId[x]) for x in fields[2:2+n]))

        i_stub='INSERT INTO AiOpSig(nopds, ntypes, rmode, res,opd1'
        v_stub=') VALUES (?,?,?,?,?'
        if n>=3:
            i_stub += ',opd2'
            v_stub += ',?'
        if n>=4:
            i_stub += ',opd3'
            v_stub += ',?'
        if n==5:
            i_stub += ',opd4'
            v_stub += ',?'
            
        try:
            curs.execute(i_stub + v_stub + ')', tuple(values))
        except Exception as e:
            print(e)
            print(line)

conn.commit()
conn.close()
