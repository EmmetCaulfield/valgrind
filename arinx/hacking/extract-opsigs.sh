#!/bin/bash

src='../../VEX/priv/ir_defs.c'

# This code extracts the "operation signatures" from the
# `typeOfPrimop` function in `ir_defs.c`.
#
# It extracts the function itself with `sed`, strips comments with
# `gcc`, gets rid of `#`-lines left behind with `grep`, then extracts
# all the lines with one of `typeOfPrimop()`'s `#define`-d
# constructors (UNARY, BINARY, TERNARY, COMPARISON, and
# UNARY_COMPARISON) or `case` (or both), then strips extraneous
# whitespace with `sed`. It then reverses the file with `tac` so that
# the signature (in the form of one of typeOfPrimop()'s #define-d
# constructors) appears before the IROps that have that signature.
#
# Yes, I know there are better ways of doing this. No, I don't think
# it's worth the effort of doing it those ways.
#
sed -n '/^void typeOfPrimop/,/^}/p' "$src" \
    | gcc -fpreprocessed -dD -E - \
    | grep -v '^#' \
    | grep -E '((UN|BIN|(QUA)?TERN)ARY)|COMPARISON|case' \
    | sed 's/:/\n/g' | sed -n 's/case//;s/^\s*//;s/\s*$//;s/ //g;/^$/!p' \
    | tac \
    | awk -F'[(,) ]+' '
    function n_unique(        ot,opd,i,k) {
        for(i=2; i<=NF; i++) {
            if( $i ~ /^[Ii]ty_/ ) {
                ot[$i]++;
            }
        }
        k=0;
        for(opd in ot) { k++ };
        return k;
    }

    BEGIN {
        OFS=","
        sig="";
    }

    $1=="UNARY" {
        n = n_unique();
        sig = 2 "," n "," $2 "," $3;
    }
    $1=="BINARY" {
        n = n_unique();
        sig = 3 "," n "," $2 "," $3 "," $4;
    }
    $1=="TERNARY" {
        n = n_unique();
        sig = 4 "," n "," $2 "," $3 "," $4 "," $5;
    }
    $1=="QUATERNARY" {
        n = n_unique();
        sig = 5 "," n "," $2 "," $3 "," $4 "," $5 "," $6;
    }
    $1=="COMPARISON" {
        $3  = $2
        $2  = "Ity_I1"
        n   = n_unique();
        sig = 3 "," n "," $2 "," $3 "," $3;
    }
    $1=="UNARY_COMPARISON" {
        $3  = $2
        $2  = "Ity_I1"
        n   = n_unique();
        sig = 2 "," n "," $2 "," $3;
    }
    /^Iop_/ {
        print $1, sig
    }
' | tac > all-opsigs.csv

cut -d, -f2- all-opsigs.csv | sort -u > unique-opsigs.csv
