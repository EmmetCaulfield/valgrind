#!/usr/bin/python3

#---- HEADER FILE --------------------------------------------------------
h_header="""
/* 
 * This file is part of Arinx, an arithmetic intensity estimator for Valgrind
 *
 * Copyright (C) 2017-2019 Emmet Caulfield
 *    emmet@netrogen.com
 *
 */

#ifndef __AI_CLASSES_H
#define __AI_CLASSES_H

#include "libvex_ir.h" /* Needed for IROp */

typedef enum {
    Icls_INVALID=0x00,
"""

h_footer="""    Icls_LAST
} AIClass;

#define AI_N_CLASSES (Icls_LAST-Icls_INVALID+1)

void ppAIClass(AIClass cls);

typedef struct {
    UChar cls;
    UChar nOps;
} AIOpCount;

AIOpCount getOpClassAndCountByIROp(IROp op);

const HChar* aiClassLabel(AIClass cls);
#endif
"""

#---- SOURCE FILE --------------------------------------------------------
c_header="""
/* 
 * This file is part of Arinx, an arithmetic intensity estimator for Valgrind
 *
 * Copyright (C) 2017-2019 Emmet Caulfield
 *    emmet@netrogen.com
 *
 */

#include "ai_classes.h"
#include "pub_tool_basics.h"
#include "pub_tool_libcprint.h"


static const HChar* const _aicls_to_str[Icls_LAST-Icls_INVALID+1] = {
    "Icls_INVALID",
"""

c_middle="""    "Icls_LAST"
};

static const AIOpCount _irop_to_aiopcount[Iop_LAST-Iop_INVALID+1] = {
    { (UChar)Icls_INVALID, (UChar)0 },
"""

c_footer="""    { (UChar)Icls_LAST, (UChar)0 }
};

void ppAIClass(AIClass cls) {
    const HChar* str = _aicls_to_str[cls-Icls_INVALID];
    VG_(printf)("%s", str);
}

AIOpCount getOpClassAndCountByIROp(IROp op) {
    return _irop_to_aiopcount[op-Iop_INVALID];
}

const HChar* aiClassLabel(AIClass cls) {
    return _aicls_to_str[cls-Icls_INVALID];
}

"""


n_classes=0
with open('ai_classes.c', 'w') as cout:
    cout.write(c_header)
    with open('ai_classes.h', 'w') as hout:
        hout.write(h_header)
        with open('unique-opclasses.lst') as infile:
            for line in infile:
                ident=line.rstrip()
                if ident:
                    n_classes += 1
                    hout.write(f'    {ident},\n')
                    cout.write(f'    "{ident}",\n')
        hout.write(h_footer)
    cout.write(c_middle)
    with open('all-opclasses.csv') as infile:
        for line in infile:
            fld=line.rstrip().split(',')
            cls=f'Icls_{fld[6]}{fld[3]}'
            nop=int(fld[7])
            cout.write(f'    {{ (UChar){cls}, (UChar){nop} }},  /* {fld[0]} */ \n')
    cout.write(c_footer)
    
print(n_classes)
