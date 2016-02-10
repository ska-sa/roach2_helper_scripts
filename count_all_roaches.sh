#!/bin/bash

TOTBRDS=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`
BRDCNT=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`
printf "\rProcessed $BRDCNT boards."
printf "\r\n\r\n"
while [ 1 ]
do
BRDCNT=`cat /var/lib/misc/dnsmasq.leases |grep roach |wc -l`
printf "\rProcessed $BRDCNT boards."
sleep 1
done
