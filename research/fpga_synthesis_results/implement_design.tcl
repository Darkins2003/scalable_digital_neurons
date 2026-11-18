set directory [file normalize [file dirname [info script]]]
set project_directory [file normalize [file join $directory .. ..]]
set top [lindex $argv 0]
set implementation [lindex $argv 1]
set period [lindex $argv 2]
set part [lindex $argv 3]
set output_directory [file normalize [lindex $argv 4]]
file mkdir $output_directory
cd $directory
set_param general.maxThreads 2
if {[info exists worker_directory]} {
    set comparison_keep_project 1
}
if {![info exists comparison_loaded_backend]} {
    set comparison_loaded_backend ""
}
if {![info exists comparison_keep_project] || [current_project -quiet] eq ""} {
    create_project -in_memory -part $part
    set comparison_loaded_backend ""
} elseif {($implementation eq "lut" || $implementation eq "dsp") && $comparison_loaded_backend ne "" && $comparison_loaded_backend ne $implementation} {
    close_project
    create_project -in_memory -part $part
    set comparison_loaded_backend ""
}
set packages [file join $project_directory ip scalable_digital_neurons hdl packages]
foreach source_file [list [file join $packages neuron_params_generated_pkg.sv] [file join $packages neuron_params_pkg.sv] [file join $packages fixed_point_package.sv] [file join $project_directory ip scalable_digital_neurons hdl math signed_32_32_multiplication.sv] [file join $directory rtl fractional_models.sv] [file join $directory rtl ${top}.sv]] {
    if {![llength [get_files -quiet $source_file]]} {
        read_verilog -sv $source_file
    }
}
if {($implementation eq "lut" || $implementation eq "dsp") && $comparison_loaded_backend eq ""} {
    set input [open [file join $directory results _work multiplier_ip $implementation ip_path.txt] r]
    set ip_path [string trim [read $input]]
    close $input
    read_ip $ip_path
    set comparison_loaded_backend $implementation
}
set constraints [file join $output_directory clock.xdc]
set output [open $constraints w]
puts $output "create_clock -name comparison_clock -period $period \[get_ports clock\]"
puts $output {set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports clock]}
puts $output {set_false_path -from [get_ports {reset input_valid fractional_exponent[*]}]}
puts $output {set_false_path -to [all_outputs]}
puts $output {set_clock_uncertainty 0.100 [get_clocks comparison_clock]}
close $output
read_xdc $constraints
synth_design -top $top -part $part -mode out_of_context -flatten_hierarchy rebuilt
report_utilization -file [file join $output_directory synthesis_utilization.rpt]
opt_design
place_design
phys_opt_design
route_design
report_utilization -file [file join $output_directory routed_utilization.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $output_directory routed_timing.rpt]
report_timing -delay_type max -max_paths 10 -file [file join $output_directory critical_paths.rpt]
check_timing -verbose -file [file join $output_directory timing_checks.rpt]
write_checkpoint -force [file join $output_directory routed.dcp]
set paths [get_timing_paths -delay_type max -max_paths 1]
set hold_paths [get_timing_paths -delay_type min -max_paths 1]
set output [open [file join $output_directory timing_metrics.csv] w]
puts $output "setup_slack_ns,hold_slack_ns,data_path_delay_ns,dsp_cells,ram18_cells,ram36_cells"
set slack ""
set hold_slack ""
set delay ""
if {[llength $paths]} {
    set slack [get_property SLACK [lindex $paths 0]]
    set delay [get_property DATAPATH_DELAY [lindex $paths 0]]
}
if {[llength $hold_paths]} {
    set hold_slack [get_property SLACK [lindex $hold_paths 0]]
}
set dsp_count [llength [get_cells -hierarchical -filter {REF_NAME =~ DSP48*}]]
set ram18_count [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB18*}]]
set ram36_count [llength [get_cells -hierarchical -filter {REF_NAME =~ RAMB36*}]]
puts $output "$slack,$hold_slack,$delay,$dsp_count,$ram18_count,$ram36_count"
close $output
if {[info exists comparison_keep_project] && $comparison_keep_project} {
    close_design
} else {
    close_project
}
