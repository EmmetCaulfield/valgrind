#!/bin/bash

declare -i first=0
declare -i n
while read ity; do
    if [ $first -eq 0 ]; then
        n=$(echo "$ity" | cut -d= -f2)
        ident=$(echo "$ity" | cut -d= -f1)
        echo "INSERT INTO IRType VALUES($n, 0, 'X');"
        first=1
    else
        b=$(echo $ity | sed 's/[^0-9]//g')
        t=$(echo $ity | sed 's/^Ity_//;s/[0-9]*$//')
        ((n++))
        echo "INSERT INTO IRType VALUES($n, '$t', $b);"
    fi
done

