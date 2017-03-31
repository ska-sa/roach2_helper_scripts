#!/bin/bash

BRDCNT=0
TOTBRDS=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`

printf "\r\n\r\nGetting all boards' statuses...\r\n"
for ROACH in `cat /var/lib/misc/dnsmasq.leases | grep roach | cut -f4 -d' '`
do
BRDCNT=$((BRDCNT+1))
printf "\r\n\r\n$BRDCNT $ROACH\r\n"
( exec /usr/local/bin/kcppar -p -s $ROACH:7147 -x status |grep 'raw fpga\|roach' |grep -v connect )
#( exec /usr/local/bin/kcppar -n -q -i -p -s $ROACH:7147 -x status )
done
