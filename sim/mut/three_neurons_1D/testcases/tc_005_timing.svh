typedef struct packed {
    int sample_count;
    int minimum_cycles;
    int maximum_cycles;
    longint total_cycles;
} timing_statistics_t;

task automatic record_timing_sample(input int cycle_count, inout timing_statistics_t statistics);
        if (cycle_count < 0) begin
            $fatal(1, "Timing sample has negative latency");
        end
        if (statistics.sample_count == 0 || cycle_count < statistics.minimum_cycles) begin
            statistics.minimum_cycles = cycle_count;
        end
        if (statistics.sample_count == 0 || cycle_count > statistics.maximum_cycles) begin
            statistics.maximum_cycles = cycle_count;
        end
        statistics.sample_count++;
        statistics.total_cycles += cycle_count;
endtask

task automatic display_timing_statistics(input string metric_name, input timing_statistics_t statistics, input real clock_period_ns);
        real mean_cycles;

        if (statistics.sample_count == 0) begin
            $fatal(1, "No samples recorded for %s", metric_name);
        end
        mean_cycles = real'(statistics.total_cycles) / statistics.sample_count;
        $display("TIMING: %s samples=%0d cycles min/mean/max=%0d/%0.3f/%0d mean_ns=%0.3f", metric_name, statistics.sample_count, statistics.minimum_cycles, mean_cycles, statistics.maximum_cycles, mean_cycles * clock_period_ns);
endtask

task automatic run_tc_005_timing;
        int clock_count;
        int startup_pulse_count;
        int previous_startup_clock;
        int completed_steps;
        int previous_step_clock;
        int neuron_request_clocks [0:2];
        int network_request_clock;
        timing_statistics_t neuron_latency [0:2];
        timing_statistics_t network_update_latency;
        timing_statistics_t network_update_interval;
        timing_statistics_t startup_to_first_update;
        timing_statistics_t startup_synapse_pass;
        realtime startup_request_time;
        real clock_period_ns;
        logic [2:0] neuron_request_ids;
        logic [2:0] neuron_result_ids;
        logic [2:0] pulse_result_ids;
        logic [2:0] synapse_result_ids;
        bit startup_finished;

        clock_count = 0;
        startup_pulse_count = 0;
        previous_startup_clock = -1;
        completed_steps = 0;
        previous_step_clock = -1;
        network_request_clock = -1;
        neuron_request_clocks = '{default:-1};
        neuron_latency = '{default:'0};
        network_update_latency = '0;
        network_update_interval = '0;
        startup_to_first_update = '0;
        startup_synapse_pass = '0;
        neuron_request_ids = '0;
        neuron_result_ids = '0;
        pulse_result_ids = '0;
        synapse_result_ids = '0;
        startup_finished = 1'b0;
        rst = 1'b1;
        ctrl_start = 1'b0;
        current_in = 32'sd20480;

        repeat (3) begin
            @(negedge clk);
        end
        rst = 1'b0;
        ctrl_start = 1'b1;
        @(posedge clk);
        startup_request_time = $realtime;
        @(negedge clk);
        ctrl_start = 1'b0;

        while (completed_steps < 128 && clock_count < 128 * 512) begin
            @(posedge clk);
            clock_count++;
            if (clock_count == 1) begin
                clock_period_ns = $realtime - startup_request_time;
            end
            if (dut.start_pulse) begin
                if (startup_finished || startup_pulse_count >= 3 || dut.id_in !== 2'(startup_pulse_count)) begin
                    $fatal(1, "Unexpected startup pulse or ID at clock %0d", clock_count);
                end
                if (startup_pulse_count > 0 && clock_count != previous_startup_clock + 2) begin
                    $fatal(1, "Startup pulses did not have exactly one idle clock between them");
                end
                previous_startup_clock = clock_count;
                startup_pulse_count++;
            end

            if (dut.valid_in) begin
                if (!startup_finished || !dut.ready || $isunknown(dut.id_in) || dut.id_in > 2 || neuron_request_ids[dut.id_in]) begin
                    $fatal(1, "Invalid neuron request at clock %0d, ID %0d", clock_count, dut.id_in);
                end
                neuron_request_ids[dut.id_in] = 1'b1;
                neuron_request_clocks[dut.id_in] = clock_count;
                if (network_request_clock < 0) begin
                    network_request_clock = clock_count;
                end
            end
            #1;
            if (dut.single_neuron_valid_out) begin
                if ($isunknown(dut.single_neuron_id_out) || dut.single_neuron_id_out > 2 || neuron_result_ids[dut.single_neuron_id_out]) begin
                    $fatal(1, "Invalid or duplicate neuron result at clock %0d", clock_count);
                end
                if (!neuron_request_ids[dut.single_neuron_id_out]) begin
                    $fatal(1, "Neuron result arrived without a matching request");
                end
                neuron_result_ids[dut.single_neuron_id_out] = 1'b1;
                record_timing_sample(clock_count - neuron_request_clocks[dut.single_neuron_id_out], neuron_latency[dut.single_neuron_id_out]);
            end
            if (dut.neuron_with_pulse_generator_valid_out) begin
                if ($isunknown(dut.neuron_with_pulse_generator_id_out) || dut.neuron_with_pulse_generator_id_out > 2 || pulse_result_ids[dut.neuron_with_pulse_generator_id_out]) begin
                    $fatal(1, "Invalid or duplicate pulse result at clock %0d", clock_count);
                end
                pulse_result_ids[dut.neuron_with_pulse_generator_id_out] = 1'b1;
            end
            if (dut.synapse_valid_out) begin
                if ($isunknown(dut.id_out) || dut.id_out > 2 || synapse_result_ids[dut.id_out]) begin
                    $fatal(1, "Invalid or duplicate synapse result at clock %0d", clock_count);
                end
                synapse_result_ids[dut.id_out] = 1'b1;
            end

            if (!startup_finished && dut.startup_complete) begin
                if (startup_pulse_count != 3 || pulse_result_ids !== 3'b111 || synapse_result_ids !== 3'b111 || neuron_request_ids !== 3'b000 || neuron_result_ids !== 3'b000 || network_step_valid) begin
                    $fatal(1, "Startup completed with missing results or an unexpected neuron update");
                end
                startup_finished = 1'b1;
                record_timing_sample(clock_count, startup_synapse_pass);
                pulse_result_ids = '0;
                synapse_result_ids = '0;
            end
            if (network_step_valid) begin
                if (!startup_finished || neuron_request_ids !== 3'b111 || neuron_result_ids !== 3'b111 || pulse_result_ids !== 3'b111 || synapse_result_ids !== 3'b111) begin
                    $fatal(1, "Step %0d completed before all three neurons and synapses finished", completed_steps);
                end
                record_timing_sample(clock_count - network_request_clock, network_update_latency);
                if (previous_step_clock >= 0) begin
                    record_timing_sample(clock_count - previous_step_clock, network_update_interval);
                end else begin
                    record_timing_sample(clock_count, startup_to_first_update);
                end
                network_request_clock = -1;
                previous_step_clock = clock_count;
                completed_steps++;
                neuron_request_ids = '0;
                neuron_result_ids = '0;
                pulse_result_ids = '0;
                synapse_result_ids = '0;
            end
        end
        if (completed_steps != 128) begin
            $fatal(1, "Timing test timed out after %0d clocks with %0d completed steps", clock_count, completed_steps);
        end
        for (int neuron_index = 0; neuron_index < 3; neuron_index++) begin
            if (neuron_latency[neuron_index].sample_count != 128) begin
                $fatal(1, "Wrong timing sample count for neuron %0d", neuron_index);
            end
            display_timing_statistics($sformatf("neuron_%0d_latency", neuron_index), neuron_latency[neuron_index], clock_period_ns);
        end
        display_timing_statistics("network_update_latency", network_update_latency, clock_period_ns);
        display_timing_statistics("network_update_interval", network_update_interval, clock_period_ns);
        display_timing_statistics("startup_to_first_update", startup_to_first_update, clock_period_ns);
        display_timing_statistics("startup_synapse_pass", startup_synapse_pass, clock_period_ns);
endtask
