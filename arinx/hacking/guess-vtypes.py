#!/usr/bin/python3

import re
from operator import itemgetter

opembeds=re.compile(r'Iop_[A-Za-z]+([0-9]+)([A-Z])?x([0-9]+)')

# In this classification "arithmetic" is any type-neutral
# operation. So, while HAdd, MAdd, MSub, Sad, etc. might only be
# available for one of FP or integer, there's no intrinsic reason why
# they shouldn't exist for the other. Other operations have no meaning
# for one type or the other (what does it mean to "round" an integer?).

classifiers = {
    # Standard arithmetic operations
    'StdArith'   : re.compile('Add|Sub|Mul|Div'),
    # Extended/extra arithmetic operations
    'ExtArith'    : re.compile('Abs|Neg'),
    # Horizontal SIMD add and subtract
    'HozArith' : re.compile('HAdd|HSub'),
    # Arithmetic that implies more than one arithmetic operation 
    'PlurArith' : re.compile('MAdd|MSub|Sad|Avg'), # Sum of Absolute Differences
    # FP rounding and alike operations:
    'FpRound'  : re.compile('Round|Trunc|Rnd|Quantize'),
    # FP functions
    'FpFunc'   : re.compile('Recip|Sqrt|Log|Exp|Atan|Yl2x|Scale|PRem|Sin|Cos|Tan|2xm1'),
    'Shuffle'  : re.compile('Interleave|Cat|Perm|Reverse|Left|Get|Set|Dup|Pack|Slice|Extract|Inject'),
    'Bitwise'  : re.compile('And|Xor|Or|Not'),
    'Compar'   : re.compile('Cmp|Max|Min'),
    'Count'    : re.compile('Cnt|Clz|Ctz|Cls|PopCount'),      # non-zeros, leading zeros, sign bits
    'Twiddle'  : re.compile('Shl|Shr|Sar|Sal|Rsh|Sh|Rot|Rol|Qsh'),
    'Convert'  : re.compile('Narrow|Widen|Fixed|BCD|ZeroHI|(?:[IFVD]?(?:1|8|16|32|64|128|256)([US]|(?:[HL][IOL]))?to[IFVD]?(?:1|8|16|32|64|128|256))'),
    'Impotent' : re.compile('Reinterp'),   # Really unsure about this. Could be a NOP.
    'Crypt'    : re.compile('Cipher|SHA')
}

classiforder=(
    'FpRound',
    'ExtArith',
    'HozArith',
    'StdArith',
    'PlurArith',
    'FpFunc',
    'Shuffle',
    'Bitwise',
    'Compar',
    'Count',
    'Twiddle',
    'Convert',
    'Impotent',
    'Crypt'
)


# This is what's left as unclassified after the above regexes have had
# their go:
manual = {
    'Iop_64x4toV256': 'Convert',
    'Iop_PwBitMtxXpose64x2' : 'Shuffle',   # Matrix transpose?
    'Iop_F64x2_2toQ32x4' : 'Convert',
    'Iop_F32x4_2toQ16x8' : 'Convert'
}





vtypes=dict()
vclasses=dict()

of=open('vtypes.csv', 'w')

with open('all-opsigs.csv') as f:
    for line in f:
        fields=line.rstrip().split(',')
        mnem=fields[0]

        classes=[]
        for cls in classiforder:
            m = classifiers[cls].search(mnem)
            if m:
                classes.append(cls)

        if not classes:
            # Failed to classify by regex
            if mnem in manual:
                classes.append(manual[mnem])
            else:
                classes.append('<<< UNCLASSIFIED >>>')
            
        # Classify by first match:
        opclass = classes[0]

        # Tentatively assume the type is the fourth letter of the
        # result
        tent=fields[3][4]

        # We're going to be Converting the numbers after "Ity_[FI]"
        # and "Mode" isn't a numbers but ity_RMode is really Ity_I32
        # and implies that the type is 'F' (floating-point)
        if fields[3]=='ity_RMode':
            fields[3]='Ity_I32'
            tent='F'

        opdsz=[int(x[5:]) for x in fields[3:]]
        maxos=max(opdsz)
        parent=f'Ity_{tent}{maxos}'
        vtstr=None
        btype=None
        nlanes=None
        nbits=None

        
        m = opembeds.match(mnem)
        if m:
            nlanes=int(m.group(3))
            btype=m.group(2)
            if btype is None or btype != 'F':
                btype = 'I';
            nbits=int(m.group(1))
            vtstr=f'Aty_{btype}{nbits}x{nlanes}'
        else:
            vtstr=parent
            btype=tent
            nlanes=1
            nbits=maxos

        nops = nlanes
        if opclass=='HozArith':
            nops = nlanes - 1
        elif opclass=='PlurArith':
            if re.search('Sad', mnem):
                # Sum of absolute differences: how many we count this as is open to debate
                nops = 2*nlanes-1
            elif re.search('Avg', mnem):
                nops = nlanes
            else:
                nops = 2*nlanes # MAdd/MSub
#        elif opclass=='Convert':
#            nops = 1
        elif opclass=='Shuffle':
            nops = 1

        cls=f'Icls_{opclass}_{btype}'
        vclasses[cls] = 1
            
        sig=f'{vtstr},{parent},{btype},{nbits},{nlanes},{opclass},{nops}'
        vtypes[sig] = 1
        row=f'{mnem},{sig}'
        of.write(row+'\n')
        print(row)
    of.close()
            
vlist=list(vtypes.keys())

of=open('unique-vtypes.lst', 'w')
for t in vlist:
    of.write(t+'\n')
of.close()


of=open('unique-vtypes.lst', 'w')
for t in vlist:
    of.write(t+'\n')
of.close()

of=open('vclasses.lst', 'w')
for c in list(vclasses.keys()):
    of.write(c+'\n')
of.close()


