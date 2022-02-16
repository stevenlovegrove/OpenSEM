#!/bin/bash
if [ -z "$1" ]
  then
    exec 3<&0
  else
    exec 3<$1
fi

GREP_COLOR='01;36' egrep --color=always 'INFO:|$' <&3 | GREP_COLOR='01;33' egrep --color=always 'WARNING:|$' | GREP_COLOR='01;31' egrep -i --color=always 'ERROR:|$'