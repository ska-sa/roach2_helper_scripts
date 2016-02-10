#!/usr/bin/expect
set ROACH [lindex $argv 0]
send_user "Connecting to $ROACH\r"
spawn telnet $ROACH
expect {*login:}
send "root\r"
#expect {*password:}
#send "XXXXXXXX\r"
#expect {*# }
#send "rm /usr/.keep\r"
expect {*# }
send {echo "echo 2 > /proc/sys/net/ipv4/conf/default/force_igmp_version" >> /etc/rc.local}
send "\r"
sleep 1
expect {*# }
send "reboot\r"
sleep 1
send_user "\r\n\r\nDONE with $ROACH!\r\n"
