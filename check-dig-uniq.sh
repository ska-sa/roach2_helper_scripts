#!/bin/bash

DEST=10.103.254.2

(for name in $(kcpcmd -s ${DEST}:7147 client-list | grep proxy | cut -f2 -d  ' ' ) ; do for value in $(kcpcmd -rs ${DEST}:72${name:2:2} capture-list  | grep capture-list | cut -f 2,3 -d ' '  | tr -s ' ' '-') ; do echo ${value} ; done ; done) | sort | uniq -d
