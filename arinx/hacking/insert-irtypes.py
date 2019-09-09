#!/usr/bin/python3

import sqlite3
from itertools import chain

conn = sqlite3.connect('vexdb.db')
curs = conn.cursor()

sql = 'INSERT INTO IRType(id, btype, nbits) VALUES (?,?,?)'

first=True
value=0;
with open('irtypes.lst') as f:
    for line in f:
        line = line.rstrip()
        if first:
            # Ity_INVALID=0x1100
            field=line.split('=')
            value=int(field[1],16)
            first=False
            curs.execute(sql, (value, 'X', 0));
        else:
            value += 1;
            btype=line[4];
            nbits=int(line[5:])
            curs.execute(sql, (value, btype, nbits));
            
        conn.commit()
conn.close()
