#!/usr/bin/python3

import sqlite3
from itertools import chain

conn = sqlite3.connect('vexdb.db')
curs = conn.cursor()

ItyToId=dict()

for row in curs.execute('SELECT id, cenum FROM Ity'):
    ItyToId[row[1]]=row[0]

for k,v in ItyToId.items():
    print("{} : {}".format(k,v))

ItyToId['ity_RMode']=ItyToId['Ity_I32']

i_stub='INSERT INTO Sig(n_opds, n_types, r_mode, res,od1'
v_stub=') VALUES (?,?,?,?,?'
with open('unique-sigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        n=int(fields[0])
        u=int(fields[1])
        r=False;
        if fields[2]=='ity_RMode':
            r=True
        values=chain((n, u, r), (int(ItyToId[x]) for x in fields[2:2+n]))
        try:
            if n==2:
                curs.execute(i_stub + v_stub + ')', tuple(values))
            elif n==3:
                curs.execute(i_stub + ',od2' + v_stub + ',?)', tuple(values))
            elif n==4:
                curs.execute(i_stub + ',od2,od3' + v_stub + ',?,?)', tuple(values))
            elif n==5:
                curs.execute(i_stub + ',od2,od3,od4' + v_stub + ',?,?,?)', tuple(values))
            else:
                raise ValueError("Invalid arity ({}) in signature".format(n))
        except Exception as e:
            print(e)
            print(line)

        conn.commit()
conn.close()
