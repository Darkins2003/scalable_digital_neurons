set directory [file normalize [file dirname [info script]]]
set project_directory [file normalize [file join $directory .. ..]]
set implementation [lindex $argv 0]
set part [lindex $argv 1]
set cache_directory [file join $directory results _work multiplier_ip $implementation]
file mkdir $cache_directory
set_param general.maxThreads 2
create_project multiplier_project $cache_directory -part $part -force
create_ip -name mult_gen -vendor xilinx.com -library ip -version 12.0 -module_name signed_multiplier
source [file join $directory multiplier_configuration.tcl]
if {$implementation eq "lut"} {
    set_property CONFIG.Multiplier_Construction Use_LUTs [get_ips signed_multiplier]
} elseif {$implementation eq "dsp"} {
    set_property CONFIG.Multiplier_Construction Use_Mults [get_ips signed_multiplier]
}
generate_target all [get_ips signed_multiplier]
synth_ip [get_ips signed_multiplier]
set output [open [file join $cache_directory ip_path.txt] w]
puts $output [get_property IP_FILE [get_ips signed_multiplier]]
close $output
close_project
