set worker_script_directory [file normalize [file dirname [info script]]]
set worker_directory [file normalize [lindex $argv 0]]
file mkdir $worker_directory
set comparison_keep_project 1
while {1} {
    if {[file exists [file join $worker_directory stop.txt]]} {
        break
    }
    set worker_task [file join $worker_directory task.tcl]
    if {![file exists $worker_task]} {
        after 100
        continue
    }
    source $worker_task
    file delete $worker_task
    puts "Starting implementation: $worker_task_log"
    set worker_error [catch {source [file join $worker_script_directory implement_design.tcl]} worker_message]
    if {$worker_error} {
        catch {close_project}
    }
    flush stdout
    set worker_status [open [file join $worker_directory pending_status.txt] w]
    puts $worker_status [expr {$worker_error ? "FAIL" : "PASS"}]
    puts $worker_status $worker_message
    close $worker_status
    file rename -force [file join $worker_directory pending_status.txt] [file join $worker_directory status.txt]
}
catch {close_project}
