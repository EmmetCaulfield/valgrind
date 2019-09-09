#!/usr/bin/python3

import re

regex=re.compile(r'Iop_[A-Za-z]+([0-9]+)([A-Z])?x([0-9]+)')

with open('all-opsigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        code=fields[0]
        tent=fields[3][4]
        m = regex.match(code)
        if m:
            nlanes=m.group(3)
            btype=m.group(2)
            if btype is None or btype != 'F':
                btype = 'I';
            nbits=m.group(1)
            print(m.group(0), "Aty_V{}x{}{}".format(nlanes,btype,nbits))
        
