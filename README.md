# roach2_helper_scripts
These scripts are used to configure, program and get status from ROACH2 boards. Generally scripts read the contents of the dnsmasq file (/var/lib/misc/dnsmasq.conf)
to determine which ROACH2s are present.

Use with caution! Many of these scripts will brick a ROACH2 if not used correctly.

clean_all_roaches.sh
deprog_all_roaches.sh  
reboot_all_roaches.sh      
roach2_list_fan_speeds.sh - List the chassis fan speed of all roaches in the dnsmasq file. Note this script will set the driver divisor and may have to be run a number
                            times to obtain accurate fan speeds. 
roach2_reset_fs.sh    
roach2_update_uboot.sh  - Expect a valid u-boot.bin file in /srv/boot with a tftp server running. This script will set the roach to TFTP the u-boot.bin file across and
                          flash it. The flash is erased as part of this process so if the u-boot.bin file is not present the board will be bricked.
update_all_romfs.sh - See roach2_update_uboot.sh
count_all_roaches.sh
roach2_disable_fanctrl.sh - This script removes the fan control process from /etc/tcpborphserver3.ini which, after a reboot, will cause the chassis fans to spin at 
                            maximum RPMs.
roach2_list_uboot_ver.sh
roach2_set_igmpv2.sh
update_all_kernels.sh - See roach2_update_uboot.sh    
update_all_uboot.sh - See roach2_update_uboot.sh

