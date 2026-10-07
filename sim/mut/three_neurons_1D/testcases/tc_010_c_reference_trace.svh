// Match the simulation settings in Synfire_1D_3neur_fixed.c.
localparam int TEST_STEP_COUNT = 190000;
localparam int PULSE_START_STEP = 60000;
localparam int PULSE_END_STEP = 140000;
localparam int PULSE_HEIGHT_Q8 = 20480;

task automatic run_tc_010_c_reference_trace;
        string preparation_command;

        preparation_command = $sformatf("python ../../../../sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --prepare-only --skip-compile --steps %0d --pulse-start %0d --pulse-end %0d --pulse-height-q8 %0d --output-dir .", TEST_STEP_COUNT, PULSE_START_STEP, PULSE_END_STEP, PULSE_HEIGHT_Q8);
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

        items_read = $fscanf(stimulus_file_handle, "%d", current_in);
        if (items_read != 1) begin
            $fatal(1, "Missing input current for step 0");
        end

        $fwrite(trace_file_handle, "step,current,n0_vmem,n0_vk,n0_vg,n0_vna,n1_vmem,n1_vk,n1_vg,n1_vna,n2_vmem,n2_vk,n2_vg,n2_vna,n0_te,n0_ti,n1_te,n1_ti,n2_te,n2_ti\n");

        // The first synapse pass uses the initial states. It is not a completed neuron step.
        repeat (3) @(negedge clk);
        rst = 0;
        ctrl_start = 1;
        @(negedge clk);
        ctrl_start = 0;

        @(posedge dut.synapse_valid_out[0]);
        #1;
        if (dut.synapse_valid_out !== 3'b111) begin
            $fatal(1, "Synapses did not finish the startup pass together");
        end

        if (dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[0] !== INITIAL_STATE[0]) begin
            $fatal(1, "Neuron updated during synapse initialization");
        end

        if (dut.excitatory_current_contribution[0] !== 32'sd1091 || dut.excitatory_current_contribution[1] !== 32'sd1091 || dut.excitatory_current_contribution[2] !== 32'sd1091) begin
            $fatal(1, "Startup synaptic current differs from the C reference (1091 Q8)");
        end

        // Record the four neuron states and two triangle states for each neuron.
        for (int step_index = 0; step_index < total_steps; step_index++) begin
            @(posedge dut.synapse_valid_out[0]);
            #1;
            if (dut.synapse_valid_out !== 3'b111) begin
                $fatal(1, "Synapses did not finish together at step %0d", step_index);
            end

            if ($isunknown({dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[0], dut.neuron_with_pulse_generator_1.single_neuron_i.neuron_state_variables[0], dut.neuron_with_pulse_generator_2.single_neuron_i.neuron_state_variables[0]})) begin
                $fatal(1, "Unknown membrane voltage at step %0d", step_index);
            end

            $fwrite(trace_file_handle, "%0d,%0d", step_index, current_in);
            for (int state_index = 0; state_index < 4; state_index++) begin
                $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[state_index]);
            end

            for (int state_index = 0; state_index < 4; state_index++) begin
                $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_1.single_neuron_i.neuron_state_variables[state_index]);
            end

            for (int state_index = 0; state_index < 4; state_index++) begin
                $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_2.single_neuron_i.neuron_state_variables[state_index]);
            end

            $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_0.synaptic_triangular_generator_i.excitatory_triangular_state_reg);
            $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_0.synaptic_triangular_generator_i.inhibitory_triangular_state_reg);
            $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_1.synaptic_triangular_generator_i.excitatory_triangular_state_reg);
            $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_1.synaptic_triangular_generator_i.inhibitory_triangular_state_reg);
            $fwrite(trace_file_handle, ",%0d", dut.neuron_with_pulse_generator_2.synaptic_triangular_generator_i.excitatory_triangular_state_reg);
            $fwrite(trace_file_handle, ",%0d\n", dut.neuron_with_pulse_generator_2.synaptic_triangular_generator_i.inhibitory_triangular_state_reg);

            if (step_index + 1 < total_steps) begin
                @(negedge clk);
                items_read = $fscanf(stimulus_file_handle, "%d", current_in);
                if (items_read != 1) begin
                    $fatal(1, "Missing input current for step %0d", step_index + 1);
                end
            end
        end

        $fclose(stimulus_file_handle);
        $fclose(trace_file_handle);
        $display("Recorded %0d three-neuron steps", total_steps);

        if ($system("python ../../../../sim/mut/three_neurons_1D/scripts/validate_three_neurons_1D.py --compare-only --output-dir .") != 0) begin
            $fatal(1, "Three-neuron RTL trace differs from the C reference");
        end
endtask
