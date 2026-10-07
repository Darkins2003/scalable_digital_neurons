task automatic run_tc_001_c_reference_trace;
        if (!$test$plusargs("external_reference") &&
            $system("python ../../../../sim/mut/single_neuron/scripts/validate_single_neuron.py --prepare-only --skip-compile --steps 3 --pulse-start 1 --wide-reference --output-dir .") != 0)
            $fatal(1, "Could not prepare single-neuron C reference");
        stimulus_file = $fopen("stimulus.txt", "r");
        if (stimulus_file == 0)
            $fatal(1, "Cannot open stimulus.txt");

        trace_file = $fopen("hdl_trace.csv", "w");
        if (trace_file == 0)
            $fatal(1, "Cannot create hdl_trace.csv");

        read_count = $fscanf(stimulus_file, "%d", number_of_steps);
        if (read_count != 1 || number_of_steps <= 0)
            $fatal(1, "First line of stimulus.txt must be a positive step count");

        $fwrite(trace_file, "step,current,vmem,vk,vg,vna\n");

        repeat (3) @(negedge clk);
        for (int state_index = 0; state_index < 4; state_index++) begin
            if (dut.neuron_state_variables[state_index] !== INITIAL_STATE[state_index])
                $fatal(1, "Initial state[%0d] differs from INITIAL_STATE", state_index);
        end
        expected_previous_vmem = INITIAL_STATE[0];
        rst = 1'b0;

        // Submit one valid transaction at a time. Waiting for valid_out before
        // submitting the next current keeps each Euler update dependent on the
        // state produced by the preceding step.
        for (int step = 0; step < number_of_steps; step++) begin
            @(negedge clk);
            read_count = $fscanf(stimulus_file, "%d", current_in);
            if (read_count != 1)
                $fatal(1, "Missing current for step %0d", step);
            valid_in = 1'b1;

            @(negedge clk);
            valid_in = 1'b0;

            @(posedge valid_out);
            #1; // Let the state register updates settle.

            if ($isunknown({vmem_out, vmem_out_previous,
                            dut.neuron_state_variables[1],
                            dut.neuron_state_variables[2],
                            dut.neuron_state_variables[3]}))
                $fatal(1, "Unknown result at step %0d", step);

            if (vmem_out !== dut.neuron_state_variables[0])
                $fatal(1, "vmem_out does not match state[0] at step %0d", step);

            if (vmem_out_previous !== expected_previous_vmem)
                $fatal(1, "vmem_out_previous mismatch at step %0d", step);

            $fwrite(trace_file, "%0d,%0d,%0d,%0d,%0d,%0d\n",
                    step, current_in, vmem_out,
                    dut.neuron_state_variables[1],
                    dut.neuron_state_variables[2],
                    dut.neuron_state_variables[3]);

            expected_previous_vmem = vmem_out;
        end

        $fclose(trace_file);
        $fclose(stimulus_file);
        $display("Recorded %0d completed neuron steps", number_of_steps);
        if (!$test$plusargs("external_reference") &&
            $system("python ../../../../sim/mut/single_neuron/scripts/validate_single_neuron.py --compare-only --output-dir .") != 0)
            $fatal(1, "Single-neuron C comparison failed");
endtask
