proc grab {f pat} {
    if {![file exists $f]} { return "" }
    set fh [open $f r]; set txt [read $fh]; close $fh
    if {[regexp $pat $txt -> v]} { return $v }
    return ""
}

proc get_wns {f} {
    if {![file exists $f]} { return "" }
    set fh [open $f r]; set lines [split [read $fh] "\n"]; close $fh
    set n [llength $lines]
    for {set i 0} {$i < $n} {incr i} {
        if {[string match "*WNS(ns)*" [lindex $lines $i]]} {
            for {set j 1} {$j <= 3} {incr j} {
                set l [lindex $lines [expr {$i + $j}]]
                if {[regexp {^\s*(-?[0-9]+\.[0-9]+)} $l -> v]} { return $v }
            }
        }
    }
    return ""
}

proc run_one {cfg N W D} {
    if {[file exists ./runs/$cfg/power.rpt]} {
        puts "  $cfg already done, skipping"
        return
    }
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
    close_project
}

set todo {}
foreach N {2 4 8 16} {
    foreach W {4 8 12 16} {
        foreach D {0 1} {
            lappend todo [list $N $W $D]
        }
    }
}

set fh [open runs.csv w]
puts $fh "cfg,N,WIDTH,DATAFLOW,lut,ff,dsp,bram,wns_ns,fmax_mhz,power_mw"
close $fh

set i 0
set total [llength $todo]
foreach c $todo {
    incr i
    lassign $c N W D
    set cfg "N${N}_W${W}_D${D}"
    puts "\[$i/$total\] $cfg"
    run_one $cfg $N $W $D

    set u ./runs/$cfg/util.rpt
    set lut  [grab $u {Slice LUTs\s*\|\s*([0-9]+)}]
    set ff   [grab $u {Slice Registers\s*\|\s*([0-9]+)}]
    set dsp  [grab $u {DSPs\s*\|\s*([0-9]+)}]
    set bram [grab $u {Block RAM Tile\s*\|\s*([0-9.]+)}]
    set wns  [get_wns ./runs/$cfg/timing.rpt]
    set dyn  [grab ./runs/$cfg/power.rpt {Dynamic \(W\)\s*\|\s*([0-9.]+)}]

    set fmax ""
    if {$wns ne ""} { set fmax [format %.1f [expr {1000.0/(10.0-$wns)}]] }
    set pmw ""
    if {$dyn ne ""} { set pmw [format %.1f [expr {$dyn*1000.0}]] }

    set fh [open runs.csv a]
    puts $fh "$cfg,$N,$W,$D,$lut,$ff,$dsp,$bram,$wns,$fmax,$pmw"
    close $fh
    puts "      lut=$lut ff=$ff dsp=$dsp fmax=$fmax power=$pmw mW"
}
puts "\nDONE - runs.csv ready"