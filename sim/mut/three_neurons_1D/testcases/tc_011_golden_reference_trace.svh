task automatic run_tc_011_golden_reference_trace;
        run_tc_010_c_reference_trace();

        $display("RTL trace ready for golden-reference analysis by the simulation runner");
endtask
