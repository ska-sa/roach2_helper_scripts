#!/bin/bash

DEST=10.103.254.2

for name in $(kcpcmd -s ${DEST}:7147 client-list | grep proxy | cut -f2 -d  ' ' ) ; do kcpcmd -rs ${DEST}:72${name:2:2} sensor-value l-band.time.synchronisation-epoch  | grep --label=$name -H  synchronisation ; done

