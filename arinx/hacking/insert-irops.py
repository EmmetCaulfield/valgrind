#!/usr/bin/python3

import sqlite3
from itertools import chain

conn = sqlite3.connect('vexdb.db')
curs = conn.cursor()
curs.execute('DELETE FROM IROp')
conn.commit()

sql = 'INSERT INTO IROp(id, mnem) VALUES (?,?)'

# Might as well cache the IROps: there's not many of them (~1100)
IopToId=dict()

first=True
value=0;
with open('irops.lst') as f:
    for line in f:
        line = line.rstrip()
        if first:
            # Iop_INVALID=0x1100
            field = line.split('=')
            value = int(field[1],16)
            IopToId['INVALID']=value
            first = False
            curs.execute(sql, (value, 'INVALID'));
        else:
            value += 1;
            IopToId[line]=value
            mnem   = line[4:]
            curs.execute(sql, (value, mnem));
            
conn.commit()

# Lookup IDs from IRTypes in a dict
ItyToId=dict()
for row in curs.execute('SELECT id, "Ity_" || btype || nbits AS cenum FROM IRType'):
    ItyToId[row[1]]=row[0]
ItyToId['ity_RMode']=ItyToId['Ity_I32']


with open('all-opsigs.csv') as f:
    for line in f:
        line=line.rstrip()
        fields=line.split(',')
        rmode=False
        mnem=fields[0]          # Mnemonic
        if fields[3]=='ity_RMode':
            rmode=True
        no=int(fields[1])       # Number of args
        qp=chain((int(rmode),),(int(ItyToId[x]) for x in fields[3:8])) # Query params
        
        sql=''
        if no >= 2:
            sql='SELECT id FROM AiOpSig WHERE rmode=? AND res=? AND opd1=?'
        if no >= 3:
            sql += ' AND opd2=?'
        if no >= 4:
            sql += ' AND opd3=?'
        if no==5:
            sql += ' AND opd4=?'

        try:
            upd='UPDATE IROp SET aiopsig=? WHERE id=?'
            foo=tuple(qp)
            curs.execute(sql, foo)
            row=curs.fetchone()    
            aiopsig=int(row[0])
            curs.execute(upd, (aiopsig, IopToId[mnem]))
        except Exception as e:
            print(str(e), line)

conn.commit()
conn.close()
