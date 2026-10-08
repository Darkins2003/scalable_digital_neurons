localparam int TEST_STEP_COUNT = 190000;
localparam int PULSE_START_STEP = 60000;
localparam int PULSE_END_STEP = 140000;
localparam int PULSE_HEIGHT_Q8 = 20480;

task automatic run_tc_010_c_reference_trace;
        string preparation_command;
        int requested_steps;
        int requested_pulse_start;
        int requested_pulse_end;
        int requested_pulse_height;
        fixed_t stimulus_currents [];

        requested_steps = TEST_STEP_COUNT;
        requested_pulse_start = PULSE_START_STEP;
        requested_pulse_end = PULSE_END_STEP;
        requested_pulse_height = PULSE_HEIGHT_Q8;
        items_read = $value$plusargs("steps=%d", requested_steps);
        items_read = $value$plusargs("pulse_start=%d", requested_pulse_start);
        items_read = $value$plusargs("pulse_end=%d", requested_pulse_end);
        items_read = $value$plusargs("pulse_height_q8=%d", requested_pulse_height);
        preparation_command = $sformatf("python ../../../../sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --prepare-only --skip-compile --steps %0d --pulse-start %0d --pulse-end %0d --pulse-height-q8 %0d --output-dir .", requested_steps, requested_pulse_start, requested_pulse_end, requested_pulse_height);
        if ($system(preparation_command) != 0) begin
            $fatal(1, "Could not prepare the three-neuron C reference");
        end

        stimulus_file_handle = $fopen("stimulus.txt", "r");
        trace_file_handle = $fopen("hdl_trace.csv", "w");
        if (!stimulus_file_handle || !trace_file_handle) begin
            $fatal(1, "Could not open stimulus.txt or hdl_trace.csv");
        end
        items_read = $fscanf(stimulus_file_handle, "%d", total_steps);
        if (items_read != 1 || total_steps < 1) begin
            $fatal(1, "Invalid number of stimulus steps");
        end
        stimulus_currents = new[total_steps];
        for (int step_index = 0; step_index < total_steps; step_index++) begin
            items_read = $fscanf(stimulus_file_handle, "%d", stimulus_currents[step_index]);
            if (items_read != 1) begin
                $fatal(1, "Missing input current for step %0d", step_index);
            end
        end
        current_in = stimulus_currents[0];
        $fclose(stimulus_file_handle);
        $fwrite(trace_file_handle, "step,current,n0_vmem,n0_vk,n0_vg,n0_vna,n1_vmem,n1_vk,n1_vg,n1_vna,n2_vmem,n2_vk,n2_vg,n2_vna,n0_te,n0_ti,n1_te,n1_ti,n2_te,n2_ti\n");

        repeat (3) begin
            @(negedge clk);
        end
        rst = 1'b0;
        ctrl_start = 1'b1;
        @(negedge clk);
        ctrl_start = 1'b0;
        @(posedge dut.startup_complete);
        #1;
        if (network_step_valid) begin
            $fatal(1, "Startup incorrectly reported a completed neuron step");
        end
        for (int neuron_index = 0; neuron_index < 3; neuron_index++) begin
            for (int state_index = 0; state_index < 4; state_index++) begin
                if (dut.neuron_with_pulse_generator_i.single_neuron_i.neuron_state_variables[state_index][neuron_index] !== INITIAL_STATE[state_index]) begin
                    $fatal(1, "Neuron %0d state %0d updated during startup", neuron_index, state_index);
                end
            end
            if (dut.excitatory_current_contribution_reg[neuron_index] !== 32'sd1091) begin
                $fatal(1, "Startup synaptic current for source %0d differs from C (1091 Q8)", neuron_index);
            end
        end
        @(negedge clk);
        if (total_steps > 1) begin
            current_in = stimulus_currents[1];
        end

        for (int step_index = 0; step_index < total_steps; step_index++) begin
            @(posedge network_step_valid);
            #1;
            $fwrite(trace_file_handle, "%0d,%0d", step_index, stimulus_currents[step_index]);
            for (int neuron_index = 0; neuron_index < 3; neuron_index++) begin
                for (int state_index = 0; state_index < 4; state_index++) begin
                    if ($isunknown(dut.neuron_with_pulse_generator_i.single_neuron_i.neuron_state_variables[state_index][neuron_index])) begin
                        $fatal(1, "Unknown state %0d for neuron %0d at step %0d", state_index, neuron_index, step_index);
                    end
                    $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_i.single_neuron_i.neuron_state_variables[state_index][neuron_index]);
                end
            end
            for (int neuron_index = 0; neuron_index < 3; neuron_index++) begin
                $fwrite(trace_file_handle, ",%0d,%0d", dut.neuron_with_pulse_generator_i.synaptic_triangular_generator_i.excitatory_triangular_state_reg[neuron_index], dut.neuron_with_pulse_generator_i.synaptic_triangular_generator_i.inhibitory_triangular_state_reg[neuron_index]);
            end
            $fwrite(trace_file_handle, "\n");
            @(negedge clk);
            if (step_index + 2 < total_steps) begin
                current_in = stimulus_currents[step_index + 2];
            end
        end
        $fclose(trace_file_handle);
        $display("Recorded %0d three-neuron steps", total_steps);
        if ($system("python ../../../../sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --compare-only --output-dir .") != 0) begin
            $fatal(1, "Three-neuron RTL trace differs from the C reference");
        end
endtask
