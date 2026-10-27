create_clock -period 10.000 -name clk [get_ports clk]
set_input_delay -clock clk 2.0 [all_inputs -filter {NAME !~ "clk"}]
set_output_delay -clock clk 2.0 [all_outputs]