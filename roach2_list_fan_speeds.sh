#!/usr/bin/expect -f
if { $argc != 1} {
    puts "Not setting fan driver divisor, reported speeds may be incorrect."
    puts "To set divisors: ./roach2_list_fan_speeds.sh -d"
}

proc set_div {val roach dir} {
    spawn telnet $roach
    expect {*login:}
    send "root\r"
    expect {*# }
    send "cd /sys/class/hwmon/$dir"
    send "\r"
    send "echo $val > fan1_div"
    send "\r"
    expect {*# }
}

proc check_div {curr_val roach dir} {
    if {$curr_val == 7650} {
        set_div 2 $roach $dir
    } elseif {$curr_val < 7650 && $curr_val >= 3825} {
        set_div 4 $roach $dir
    } elseif {$curr_val < 3825} {
	set_div 8 $roach $dir
    }
 }

proc get_fan_speed {sensor roach} {
    set chs [exec kcpcmd -s $roach:7147 sensor-value $sensor]
    set chs_ret [split $chs]
    set idx [expr [lsearch $chs_ret "nominal"] + 1]
    return [lindex $chs_ret $idx]
}

set totbrds [exec cat /var/lib/misc/dnsmasq.leases | grep roach | wc -l]
send_user "\r\n\r\nFound $totbrds ROACHs\r\n"

set roaches [exec cat /var/lib/misc/dnsmasq.leases | grep roach | cut -d " " -f4]
set roachlist [split $roaches "\n"]

#if { [lindex $argv 0] == "-d" } {
    puts "\nChecking divisors on all ROACHs..."
    foreach roach $roachlist {
        set fpga [get_fan_speed r2hwmond.fan.fpga $roach]
	sleep 0.2
        set chs0 [get_fan_speed r2hwmond.fan.chs0 $roach]
	sleep 0.2
        set chs1 [get_fan_speed r2hwmond.fan.chs1 $roach]
	sleep 0.2
        set chs2 [get_fan_speed r2hwmond.fan.chs2 $roach]
	sleep 0.2
	check_div $fpga $roach "hwmon5"
        check_div $chs0 $roach "hwmon6"
        check_div $chs1 $roach "hwmon7"
        check_div $chs2 $roach "hwmon8"
    }
#}

puts "Getting fan speeds..."
foreach roach $roachlist {
    set fpga [get_fan_speed r2hwmond.fan.fpga $roach]
    sleep 0.2
    set chs0 [get_fan_speed r2hwmond.fan.chs0 $roach]
    sleep 0.2
    set chs1 [get_fan_speed r2hwmond.fan.chs1 $roach]
    sleep 0.2
    set chs2 [get_fan_speed r2hwmond.fan.chs2 $roach]
    sleep 0.2
    puts "Roach $roach FPGA    fan   speed = $fpga"
    puts "Roach $roach chassis fan 0 speed = $chs0"
    puts "Roach $roach chassis fan 1 speed = $chs1"
    puts "Roach $roach chassis fan 2 speed = $chs2"
}


