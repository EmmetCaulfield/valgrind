#!/usr/bin/python3

import re
from operator import itemgetter

opembeds=re.compile(r'Iop_[A-Za-z]+([0-9]+)([A-Z])?x([0-9]+)')

classifiers = {
    'horiz'    : re.compile('HAdd|HSub'),
    'armulti'  : re.compile('MAdd|MSub|Sad'), # Sum of Absolute Differences
    'arith'    : re.compile('Add|Sub|Mul|Div'),
    'arext'    : re.compile('Abs|Neg|Avg'),
    'round'    : re.compile('Round|Trunc|Rnd|Quantize'),       # Are these "arithmetic" or "math"?
    'func'     : re.compile('Recip|Sqrt|Log|Exp|Atan|Yl2x|Scale|PRem|Sin|Cos|Tan|2xm1'),
    'shuffle'  : re.compile('Interleave|Cat|Perm|Reverse|Left|Get|Set|Dup|Pack|Slice|Extract|Inject'),
    'bitwise'  : re.compile('And|Xor|Or|Not'),
    'compar'   : re.compile('Cmp|Max|Min'),
    'count'    : re.compile('Cnt|Clz|Ctz|Cls|PopCount'),      # non-zeros, leading zeros, sign bits
    'twiddle'  : re.compile('Shl|Shr|Sar|Sal|Rsh|Sh|Rot|Rol|Qsh'),
    'convert'  : re.compile('Narrow|Widen|Fixed|BCD|ZeroHI|(?:[IFVD]?(?:1|8|16|32|64|128|256)([US]|(?:[HL][IOL]))?to[IFVD]?(?:1|8|16|32|64|128|256))'),
    'nop'      : re.compile('Reinterp'),   # Really unsure about this. Could be a NOP.
    'crypt'    : re.compile('Cipher|SHA')
}

# This is what's left as unclassified after the above regexes have had
# their go:
manual = {
    'Iop_64x4toV256': 'convert',
    'Iop_PwBitMtxXpose64x2' : 'shuffle',   # Matrix transpose?
    'Iop_F64x2_2toQ32x4' : 'convert',
    'Iop_F32x4_2toQ16x8' : 'convert'
}



vtypes=dict()

of=open('vtypes.csv', 'w')

with open('all-opsigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        mnem=fields[0]

        classes=[]
        for tag,regex in classifiers.items():
            m = regex.search(mnem)
            if m:
                classes.append(tag)
                
        if not classes:
            if mnem in manual:
                classes.append(manual[mnem])
            else:
                classes.append('<<< UNCLASSIFIED >>>')
            
        # Tentatively assume the type is the fourth letter of the
        # result
        tent=fields[3][4]

        # We're going to be converting the numbers after "Ity_[FI]"
        # and "Mode" isn't a numbers but ity_RMode is really Ity_I32
        # and implies that the type is 'F' (floating-point)
        if fields[3]=='ity_RMode':
            fields[3]='Ity_I32'
            tent='F'

        opdsz=[int(x[5:]) for x in fields[3:]]
        maxos=max(opdsz)
        parent=f'Ity_{tent}{maxos}'
        
        m = opembeds.match(mnem)
        if m:
            nlanes=int(m.group(3))
            btype=m.group(2)
            if btype is None or btype != 'F':
                btype = 'I';
            nbits=int(m.group(1))
            vtstr='Aty_{}{}x{}'.format(btype,nbits,nlanes)
            vtypes[vtstr] = (nlanes,btype,nbits)
            of.write(f"{m.group(0)},{vtstr}\n")
            print(f'{mnem} {vtstr} <- {parent} ', classes)
        else:
            print(f'{mnem} {parent} ', classes)
            
of.close()
            
vlist=list(vtypes.values())
vlist.sort(key=itemgetter(2,0,1))

of=open('unique-vtypes.lst', 'w')
for t in vlist:
    of.write('Aty_V{}x{}{}\n'.format(*t))
of.close()
