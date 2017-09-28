#!/usr/bin/expect -f

set totbrds [exec cat /var/lib/misc/dnsmasq.leases | grep roach | wc -l]
send_user "\r\n\r\nFound $totbrds ROACHs\r\n"


set brdcnt 0
send_user "\r\n\r\nSetting pwm1_enable to 0 in hwmon5 for maximum FPGA fan speed...\r\n"

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
    #set rc [eval exec grep 'pwm1_enable' [glob *]]
    set rc ""
    if {$rc == ""} {
        send {sed -i '$a#Set FPGA fan to maximum' rc.local}
        send "\r"
        sleep 1
        expect {*# }
        send {sed -i '$aecho 0 > /sys/class/hwmon/hwmon5/pwm1_enable' rc.local}
        send "\r"
        sleep 1
        expect {*# }
    }
    #send "reboot\r"
    sleep 1
    send_user "\r\n\r\nDONE with $roach!\r\n"
}
send_user "\r\n\r\nProcessed $brdcnt boards. All done!\n\r"


