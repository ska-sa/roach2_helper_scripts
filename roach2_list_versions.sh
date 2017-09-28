#!/usr/bin/expect -f

set ignore [lindex $argv]
set totbrds [exec cat /var/lib/misc/dnsmasq.leases | grep roach | wc -l]
send_user "\r\n\r\nFound $totbrds ROACHs\r\n"


set brdcnt 0
send_user "\r\n\r\nListing all U-BOOT versions...\r\n"

set roaches [exec cat /var/lib/misc/dnsmasq.leases | grep roach | cut -d " " -f4]
set roachlist [split $roaches "\n"]
set versions ""
foreach roach $roachlist {
    set ign_found [string first $roach $ignore]
    if {$ign_found == -1} {
	    incr brdcnt
	    send_user "\r\n\r\n$brdcnt $roach\r\n"
	    spawn telnet $roach
	    expect {*login:}
	    send "root\r"
	    expect {*# }
	    send {cat /dev/mtd5 | head -c 100}
	    send "\r"
	    expect {*# }
	    set output $expect_out(buffer)
            set start [string first U-Boot $output]
            set end [string first ) $output]
	    set ver [string range $output $start $end]
        set detail [exec kcpcmd -s $roach:7147 system-detail] 
        set start [string first label $detail]
        set end [string first \n $detail $start]
	    set romfs [string range $detail $start+6 $end]
        set start [string first "kernel version" $detail]
        set end [string first \n $detail $start]
	    set kernel [string range $detail $start+29 $end]
	    append versions "$brdcnt $roach:\n\tU-Boot Version: $ver\n\tKernel Version: $kernel\tRootFS Version: $romfs"

    }
}
puts "\n\n$versions"

