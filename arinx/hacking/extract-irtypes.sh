#!/bin/bash

src='../../VEX/pub/libvex_ir.h'

sed -n '/Ity_INVALID=/,/^\s*}\s*$/{s/:/\n/g;p}' "$src" \
    | awk -F'[, ]+' '/Ity_/ {print $2}' \
    > irtypes.lst
