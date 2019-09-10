#!/usr/bin/python3

import re
from operator import itemgetter

regex=re.compile(r'Iop_[A-Za-z]+([0-9]+)([A-Z])?x([0-9]+)')

vtypes=dict()

of=open('vtypes.csv', 'w')

with open('all-opsigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        code=fields[0]
        tent=fields[3][4]
        m = regex.match(code)
        if m:
            nlanes=int(m.group(3))
            btype=m.group(2)
            if btype is None or btype != 'F':
                btype = 'I';
            nbits=int(m.group(1))
            vtstr='Aty_V{}x{}{}'.format(nlanes,btype,nbits)
            vtypes[vtstr] = (nlanes,btype,nbits)
            of.write("{},{}\n".format(m.group(0),vtstr))

of.close()
            
vlist=list(vtypes.values())
vlist.sort(key=itemgetter(2,0,1))

of=open('unique-vtypes.lst', 'w')
for t in vlist:
    of.write('Aty_V{}x{}{}\n'.format(*t))
of.close()
