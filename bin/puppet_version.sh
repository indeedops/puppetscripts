#!/bin/bash
ENVIRONMENT=$1
WORKING_COPY=$2

cd $WORKING_COPY 2>/dev/null
TIMESTAMP=`date +'%F %H:%M:%S (%z)'`
if [ -e ".git" ]; then
    CMD="git rev-parse --short HEAD"
    REVISION=`$CMD 2>/dev/null`
else
    CMD="svn info"
    REVISION=`$CMD 2>/dev/null | grep Revision: | cut -f 2 -d' ' | sed -r "s/^/r/"`
fi

if [ -n "$REVISION" ]; then
    echo "master=$HOSTNAME environment=$ENVIRONMENT $REVISION @ $TIMESTAMP"
else
    echo "master=$HOSTNAME environment=$ENVIRONMENT unknown revision @ $TIMESTAMP"
fi
