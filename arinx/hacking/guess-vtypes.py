#!/usr/bin/python3

import re
from operator import itemgetter

opembeds=re.compile(r'Iop_[A-Za-z]+([0-9]+)([A-Z])?x([0-9]+)')

# In this classification "arithmetic" is any type-neutral
# operation. So, while HAdd, MAdd, MSub, Sad, etc. might only be
# available for one of FP or integer, there's no intrinsic reason why
# they shouldn't exist for the other. Other operations have no meaning
# for one type or the other (what does it mean to "round" an integer?).
#
# As a general rule, an op is 'F' (floating point) if any of its
# arguments are 'F' or its mnemonic implies 'F', otherwise 'I'.
#
# This means that any conversion to or from 'F' is 'F'. Only 'I' to
# 'I' conversions are 'I'. Unspecified shuffles or bit-twiddling is
# assumed 'I'. We end up with 27 classes.
#

# I've tried to handle the IBM 'D' thing but I've no way of testing.

classifiers = {
    # Standard arithmetic operations
    'StdArOp'   : re.compile('Add|Sub|Mul|Div'),
    # Extended/extra arithmetic operations
    'ExtArOp'   : re.compile('Abs|Neg'),
    # Horizontal SIMD add and subtract
    'HozArOp'   : re.compile('HAdd|HSub'),
    # Arithmetic that implies more than one arithmetic operation 
    'MultiArOp' : re.compile('MAdd|MSub|Sad|Avg'), # Sum of Absolute Differences
    # FP rounding and alike operations:
    'Round'     : re.compile('Round|Trunc|Rnd|Quantize'),
    # FP functions
    'MathFunc'  : re.compile('Recip|Sqrt|Log|Exp|Atan|Yl2x|Scale|PRem|Sin|Cos|Tan|2xm1'),
    'Shuffle'   : re.compile('Interleave|Cat|Perm|Reverse|Left|Get|Set|Dup|Pack|Slice|Extract|Inject'),
    'Bitwise'   : re.compile('And|Xor|Or|Not'),
    'Compare'   : re.compile('Cmp|Max|Min'),
    'Count'     : re.compile('Cnt|Clz|Ctz|Cls|PopCount'),      # non-zeros, leading zeros, sign bits
    'Twiddle'   : re.compile('Shl|Shr|Sar|Sal|Rsh|Sh|Rot|Rol|Qsh'),
    'Convert'   : re.compile('Narrow|Widen|Fixed|BCD|ZeroHI|(?:([IFVD])?(?:1|8|16|32|64|128|256)([US]|(?:[HL][IOL]))?to([IFVD])?(?:1|8|16|32|64|128|256))'),
    'Impotent'  : re.compile('Reinterp'),   # Really unsure about this. Could be a NOP.
    'Crypt'     : re.compile('Cipher|SHA')
}

simdsig=re.compile('([USF])?(?:0|1|2|4|8|16|32|64|128|256)([USF])?x([USF])?(?:1|2|4|8|16|32|64|128|256)([USF])?')

classiforder=(
    'Round',
    'ExtArOp',
    'HozArOp',
    'StdArOp',
    'MultiArOp',
    'MathFunc',
    'Shuffle',
    'Bitwise',
    'Compare',
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
        mnem = fields[0]        # Mnemonic
        res  = fields[3]        # Result operand
        
        # Tentatively assume the type is the fourth letter of the
        # result operand:
        if res=='ity_Rmode':
            tent=fields[4][4]
        else:
            tent=res[4]
            
        classes=[]
        for cls in classiforder:
            m = classifiers[cls].search(mnem)
            if m:
                classes.append(cls)
                if cls=='Convert':
                    # Conversion operations often have semantically
                    # vacuous operands (e.g. "V128"), so we try to
                    # infer the likely type from the mnemonic:
                    fromType=m.group(1)
                    sign=m.group(2)
                    toType=m.group(3)
#                    print(mnem, fromType, sign, toType)
                    if fromType is not None:
                        if toType is not None:
                            if fromType=='F' or toType=='F':
                                tent='F'
                            elif fromType=='D' or toType=='D':
                                tent='D'
                            elif fromType=='I' or toType=='I':
                                tent='I'
                        elif fromType=='V':
                            tent='I'
                        else:
                            tent=fromType
                    else:
                        if toType is not None:
                            if toType=='V':
                                tent='I'
                            else:
                                tent=toType
                        elif sign is not None:
                            if sign=='U' or sign=='S':
                                tent='I'
                if cls=='Twiddle':
                    if tent=='V':
                        tent='I'

        if tent=='V':
            m=simdsig.search(mnem)
            if m:
                types = m.group(1,2,3,4)
                if not all(types):
                    tent='I'
                elif 'F' in types:
                    tent='F'
                elif 'U' in types or 'S' in types:
                    tent='I'

        if not classes:
            # Failed to classify by regex
            if mnem in manual:
                classes.append(manual[mnem])
            else:
                classes.append('<<< UNCLASSIFIED >>>')
            
        # Classify by first match:
        opclass = classes[0]

        # We've (hopefully) detected the non-integer ones of these (if any):
        if tent=='V' and opclass in ('Shuffle', 'Bitwise', 'Crypt', 'Convert'):
            tent = 'I'

        # This one deserves to be out on its own so we can disable it
        # and see if we're catching any FP stuff we shouldn't be. At
        # the time of writing, we caught 3 "MulI128..." and two
        # "BCD<op>", which are integer:
        if tent=='V' and opclass=='StdArOp':
            tent = 'I'

        # We're going to be Converting the numbers after "Ity_[FI]"
        # and "Mode" isn't a numbers but ity_RMode is really Ity_I32
        # and implies that the type is 'F' (floating-point)
        if fields[3]=='ity_RMode':
            fields[3]='Ity_I32'
            tent='F'

        # We don't care about sign:
        if tent=='U' or tent=='S':
            tent='I'
            
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
            if btype is None:
                btype = tent;
            elif btype in ('U','S'):
                btype = 'I'
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

        cls=f'Icls_{btype}{opclass}'
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


