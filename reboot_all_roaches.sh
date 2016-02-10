#!/bin/bash

BRDCNT=0
TOTBRDS=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`

printf "\r\n\r\nFound $TOTBRDS ROACHs\r\n"


BRDCNT=0
printf "\r\n\r\nRebooting...\r\n"
for ROACH in `cat /var/lib/misc/dnsmasq.leases | grep roach | cut -f4 -d' '`
do
BRDCNT=$((BRDCNT+1))
printf "\r\n\r\n$BRDCNT $ROACH\r\n"
( exec /usr/local/bin/kcppar -q -i -p -s $ROACH -x restart)
done

printf "\r\n\r\nProcessed $BRDCNT boards. All done!\n\r"
