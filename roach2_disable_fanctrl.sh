#!/usr/bin/expect -f

set totbrds [exec cat /var/lib/misc/dnsmasq.leases | grep roach | wc -l]
send_user "\r\n\r\nFound $totbrds ROACHs\r\n"


set brdcnt 0
send_user "\r\n\r\nCommenting out fancontol in tcpborphserver3.ini and rebooting...\r\n"

set roaches [exec cat /var/lib/misc/dnsmasq.leases | grep roach | cut -d " " -f4]
set roachlist [split $roaches "\n"]
foreach roach $roachlist {
    incr brdcnt
    send_user "\r\n\r\n$brdcnt $roach\r\n"
    send_user "Connecting to $roach\r\n"
    spawn telnet $roach
    expect {*login:}
    send "root\r"
    expect {*# }
    send {cd /etc}
    send "\r"
    expect {/usr/etc #}
    send {sed -i 's/?job process r2fanctrl/#?job process r2fanctrl/' tcpborphserver3.init}
    send "\r"
    sleep 1
    expect {*# }
    send "reboot\r"
    sleep 1
    send_user "\r\n\r\nDONE with $roach!\r\n"
}
send_user "\r\n\r\nProcessed $brdcnt boards. All done!\n\r"


