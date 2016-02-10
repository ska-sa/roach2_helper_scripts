#!/bin/bash

BRDCNT=0
TOTBRDS=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`

printf "\r\n\r\nUpdating $TOTBRDS ROACHs\r\n"


BRDCNT=0
printf "\r\n\r\nUpdating KERNEL on all boards...\r\n"
for ROACH in `cat /var/lib/misc/dnsmasq.leases | grep roach | cut -f4 -d' '`
do
BRDCNT=$((BRDCNT+1))
printf "\r\n\r\n$BRDCNT $ROACH\r\n"
( exec /usr/local/bin/kcppar -q -i -p -s $ROACH -x update-kernel)
done


BRDCNT=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`
printf "\r\n\r\n"
while [ $BRDCNT -lt $TOTBRDS ]
do
printf "\rProcessed $BRDCNT boards. Now waiting for all boards to restart..."
sleep 10
BRDCNT=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`
done
printf "\r\n\r\nProcessed $BRDCNT boards. All done!\n\r"
