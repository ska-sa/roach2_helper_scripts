#!/usr/bin/expect -f

proc get_temp {sensor roach} {
    set chs [exec kcpcmd -s $roach:7147 sensor-value $sensor]
    set chs_ret [split $chs]
    set idx_nom [expr [lsearch $chs_ret "nominal"]]
    set idx_wrn [expr [lsearch $chs_ret "warn"]]
    set idx [expr {$idx_nom + $idx_wrn} + 2]
    return [lindex $chs_ret $idx]
}

set ignore [lindex $argv]
set totbrds [exec cat /var/lib/misc/dnsmasq.leases | grep roach | wc -l]
send_user "\r\n\r\nFound $totbrds ROACHs\r\n"

set roaches [exec cat /var/lib/misc/dnsmasq.leases | grep roach | cut -d " " -f4]
set roachlist [split $roaches "\n"]

puts "Getting temperatures..."
foreach roach $roachlist {
    set ign_found [string first $roach $ignore]
    if {$ign_found == -1} {
        set amb [get_temp r2hwmond.temp.ambient $roach]
        set ppc [get_temp r2hwmond.temp.ppc $roach]
        set fpga [get_temp r2hwmond.temp.fpga $roach]
        set inlet [get_temp r2hwmond.temp.inlet $roach]
        set outlet [get_temp r2hwmond.temp.outlet $roach]
        puts ""
        puts "Roach $roach ambient temperature = $amb"
        puts "Roach $roach PowerPC temperature = $ppc"
        puts "Roach $roach FPGA temperature    = $fpga"
        puts "Roach $roach inlet temperature   = $inlet"
        puts "Roach $roach outlet temperature  = $outlet"
    } else {
        puts ""
        puts "Skipping $roach"
    }
}
