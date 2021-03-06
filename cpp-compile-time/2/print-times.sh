#!/bin/bash

logdir=$1

function die() {
    echo "Usage: ./print-times.sh [logs-dir]"
    echo "Outputs columns: <cpp-utime> <includes-utime> <header-utime> <includes-ratio> <header-ratio> <filename>"
    exit 1
}

[ "$#" -eq 1 ] && [ ! -d $logdir ] && die
[ "$#" -ge 2 ] && die
[ -z $logdir ] && logdir='.'

function record() {
    basef=$(echo $1 | sed 's@\.cpp\.o\.time@@g')
    srcfa=$(readlink -f ${basef}.cpp)
    srcfr=$(realpath --relative-to=$(pwd) $srcfa)
    timef="${basef}.cpp.o.time"
    htimef="${basef}.includes.cpp.o.time"
    hhtimef="${basef}.header.cpp.o.time"

    time=$(cat $timef)
    htime=$(cat $htimef)
    hhtime=$(cat $hhtimef)

    rhtime=$(echo "100 * ${htime} / (${time} + 0.000001)" | bc)
    rhhtime=$(echo "100 * ${hhtime} / (${time} + 0.000001)" | bc)

    echo "$time $htime $hhtime $rhtime $rhhtime $srcfr"

    # echo $basef
    # echo $timef
    # echo $htimef
    # echo $hhtimef
    # echo $srcfa
    # echo $srcfr
}

export -f record

modules=$(find $logdir -name '*cpp.o.time' -not -name '*includes.cpp.o.time' -not -name '*header.cpp.o.time')
echo "$modules" | xargs -P0 -i bash -c "record {}" | sort -rnk1 | column -t -s' '
