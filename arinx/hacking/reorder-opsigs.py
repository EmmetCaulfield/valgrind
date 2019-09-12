#!/usr/bin/python3

import fileinput
import sys

opsigs=dict()
for line in fileinput.input():
    irop=line.split(',')[0]
    opsigs[irop]=line


irops=list()
with open('irops.lst') as f:
    for line in f:
        irop=line.rstrip().split('=')[0]
        if irop=='Iop_INVALID' or irop=='Iop_LAST':
            continue
        sys.stdout.write(opsigs[irop])

