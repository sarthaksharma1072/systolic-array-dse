set cfg [lindex $argv 0]
set N   [lindex $argv 1]
set W   [lindex $argv 2]
set D   [lindex $argv 3]

create_project $cfg ./runs/$cfg -part xc7s50csga324-1 -force
add_files [glob ./rtl/*.sv]
set_property file_type SystemVerilog [get_files *.sv]
add_files -fileset constrs_1 ./vivado/timing.xdc
set_property top systolic_array [current_fileset]
set_property generic "N=$N WIDTH=$W DATAFLOW=$D" [current_fileset]

set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} \
             -value {-mode out_of_context} -objects [get_runs synth_1]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -jobs 4
wait_on_run impl_1

open_run impl_1
report_utilization    -file ./runs/$cfg/util.rpt
report_timing_summary -file ./runs/$cfg/timing.rpt
report_power          -file ./runs/$cfg/power.rpt
exit