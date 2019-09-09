#!/bin/bash

src='../../VEX/pub/libvex_ir.h'

sed -n '/Iop_INVALID=/,/^\s*IROp;\s*$/p' "$src" \
    | gcc -fpreprocessed -dD -E - \
    | sed -n '/Iop_/{s/,/\n/g;p}' \
    | sed -n 's/\s*//g;/^$/!p'    \
    > irops.lst
