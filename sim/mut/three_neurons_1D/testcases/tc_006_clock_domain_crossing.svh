int crossing_error_count = 0;
int live_snapshot_check_count = 0;
int received_start_count = 0;
int produced_step_count = 0;
logic previous_neuron_start = 1'b0;
fixed_t crossing_voltage_history_0 [0:63];
fixed_t crossing_voltage_history_1 [0:63];
fixed_t crossing_voltage_history_2 [0:63];

initial begin
    if ($test$plusargs("tc_006_clock_domain_crossing")) begin
        forever begin
            wait (asynchronous_neuron_clock_enabled);
            #(neuron_clock_phase_offset);
            while (asynchronous_neuron_clock_enabled) begin
                #(neuron_clock_half_period);
                if (asynchronous_neuron_clock_enabled) begin
                    asynchronous_neuron_clock = ~asynchronous_neuron_clock;
                end
            end
            asynchronous_neuron_clock = 1'b0;
        end
    end
end

always @(posedge asynchronous_neuron_clock) begin
    if ($test$plusargs("tc_006_clock_domain_crossing")) begin
        if (!asynchronous_neuron_reset_n) begin
            received_start_count = 0;
            produced_step_count = 0;
            previous_neuron_start = 1'b0;
            crossing_voltage_history_0 = '{default:'0};
            crossing_voltage_history_1 = '{default:'0};
            crossing_voltage_history_2 = '{default:'0};
        end else begin
            if (axil_dut.network.ctrl_start && !previous_neuron_start) begin
                received_start_count++;
            end
            previous_neuron_start = axil_dut.network.ctrl_start;

            if (axil_dut.network_step_valid) begin
                produced_step_count++;
                if (produced_step_count > 63) begin
                    $fatal(1, "CDC voltage history overflow");
                end
                crossing_voltage_history_0[produced_step_count] = axil_dut.network_vmem_0;
                crossing_voltage_history_1[produced_step_count] = axil_dut.network_vmem_1;
                crossing_voltage_history_2[produced_step_count] = axil_dut.network_vmem_2;
            end
            #1;
            if (asynchronous_neuron_reset_n) begin
                if (axil_dut.registers.completed_steps !== produced_step_count) begin
                    record_crossing_failure(-1, "Accelerator register step count does not match completed neuron updates");
                end
                if (produced_step_count > 0) begin
                    if (axil_dut.registers.vmem_snapshot_0 !== crossing_voltage_history_0[produced_step_count] || axil_dut.registers.vmem_snapshot_1 !== crossing_voltage_history_1[produced_step_count] || axil_dut.registers.vmem_snapshot_2 !== crossing_voltage_history_2[produced_step_count]) begin
                        record_crossing_failure(-1, "Accelerator registers captured an inconsistent neuron snapshot");
                    end
                end
            end
        end
    end
end

initial begin
    if ($test$plusargs("tc_006_clock_domain_crossing")) begin
        #1000000;
        $fatal(1, "CDC testcase exceeded its simulation timeout");
    end
end

task automatic record_crossing_failure(input int scenario_index, input string message);
        crossing_error_count++;
        $display("CDC FAILURE: scenario=%0d accelerator_period_ns=%0.3f phase_ns=%0.3f %s", scenario_index, 2.0 * neuron_clock_half_period, neuron_clock_phase_offset, message);
endtask

task automatic reset_crossing_scenario(input int scenario_index, input int neuron_period_ns, input int phase_offset_ns);
        @(negedge clk);
        rst_n = 1'b0;
        asynchronous_neuron_reset_n = 1'b0;
        asynchronous_neuron_clock_enabled = 1'b0;
        #(neuron_clock_half_period + neuron_clock_phase_offset + 1.0);
        neuron_clock_half_period = real'(neuron_period_ns) / 2.0;
        neuron_clock_phase_offset = real'(phase_offset_ns);
        asynchronous_neuron_clock_enabled = 1'b1;

        repeat (5) begin
            @(negedge asynchronous_neuron_clock);
        end
        if (scenario_index % 2 == 0) begin
            @(negedge clk);
            rst_n = 1'b1;
            #2;
            asynchronous_neuron_reset_n = 1'b1;
        end else begin
            @(negedge asynchronous_neuron_clock);
            asynchronous_neuron_reset_n = 1'b1;
            repeat (3) begin
                @(negedge clk);
            end
            rst_n = 1'b1;
        end

        repeat (8) begin
            @(negedge asynchronous_neuron_clock);
        end
        axi_read(REG_STEP_COUNT.offset, count_read);
        if (count_read !== 0 || axil_dut.network.running !== 1'b0 || received_start_count != 0 || produced_step_count != 0) begin
            record_crossing_failure(scenario_index, "Network did not remain idle after reset without START");
        end
endtask

task automatic check_live_crossing_snapshot(input int scenario_index);
        logic [31:0] steps_before;
        logic [31:0] steps_after;
        logic [31:0] snapshot_0;
        logic [31:0] snapshot_1;
        logic [31:0] snapshot_2;

        axi_read(REG_STEP_COUNT.offset, steps_before);
        axi_read(REG_VMEM_0.offset, snapshot_0);
        axi_read(REG_VMEM_1.offset, snapshot_1);
        axi_read(REG_VMEM_2.offset, snapshot_2);
        axi_read(REG_STEP_COUNT.offset, steps_after);
        if ($isunknown({steps_before, steps_after, snapshot_0, snapshot_1, snapshot_2})) begin
            record_crossing_failure(scenario_index, "Unknown AXI count or voltage snapshot while neuron clock is running");
        end else if (steps_before == steps_after && steps_before > 0) begin
            if (steps_before > produced_step_count || steps_before > 63) begin
                record_crossing_failure(scenario_index, "AXI step count is ahead of the produced neuron updates");
            end else begin
                live_snapshot_check_count++;
                if (snapshot_0 !== crossing_voltage_history_0[steps_before] || snapshot_1 !== crossing_voltage_history_1[steps_before] || snapshot_2 !== crossing_voltage_history_2[steps_before]) begin
                    record_crossing_failure(scenario_index, "Stable AXI step count identifies an incoherent or incorrect live voltage snapshot");
                end
            end
        end
endtask

task automatic run_crossing_scenario(input int scenario_index, input int neuron_period_ns, input int phase_offset_ns);
        int scenario_errors_before;
        int neuron_cycles;
        fixed_t programmed_current;
        logic [31:0] reported_steps;

        scenario_errors_before = crossing_error_count;
        reset_crossing_scenario(scenario_index, neuron_period_ns, phase_offset_ns);

        for (int current_index = 0; current_index < 2; current_index++) begin
            if (current_index == 0) begin
                programmed_current = 32'sh0003e800;
            end else begin
                programmed_current = 32'shffffb000;
            end
            axi_write(REG_CURRENT.offset, programmed_current, 4'hf, scenario_index % 3, (scenario_index + 1) % 3);
            repeat (8) begin
                @(negedge asynchronous_neuron_clock);
            end
            axi_read(REG_CURRENT.offset, count_read);
            if (count_read !== programmed_current) begin
                record_crossing_failure(scenario_index, "Current register readback differs from the value written through the clock converter");
            end
            if (axil_dut.network.current_in !== programmed_current) begin
                record_crossing_failure(scenario_index, $sformatf("Current transfer mismatch: expected %0d received %0d", programmed_current, axil_dut.network.current_in));
            end
        end

        axi_write(REG_CONTROL.offset, 32'h1, 4'h1, scenario_index % 2, 0);
        repeat (16) begin
            @(negedge asynchronous_neuron_clock);
        end
        if (received_start_count != 1 || axil_dut.network.running !== 1'b1) begin
            record_crossing_failure(scenario_index, $sformatf("START lost or duplicated: one command, %0d received events, running=%b", received_start_count, axil_dut.network.running));
        end else begin
            neuron_cycles = 0;
            while (produced_step_count < 1 && neuron_cycles < 2048) begin
                @(negedge asynchronous_neuron_clock);
                neuron_cycles++;
            end
            if (produced_step_count > 0) begin
                for (int snapshot_index = 0; snapshot_index < 8; snapshot_index++) begin
                    check_live_crossing_snapshot(scenario_index);
                end
            end
            while (produced_step_count < 4 && neuron_cycles < 2048) begin
                @(negedge asynchronous_neuron_clock);
                neuron_cycles++;
            end
            if (produced_step_count < 4) begin
                record_crossing_failure(scenario_index, "Network did not produce four updates within 2048 neuron clocks");
            end

            axi_read(REG_STEP_COUNT.offset, reported_steps);
            if ($isunknown(reported_steps) || reported_steps < 4 || reported_steps > produced_step_count) begin
                record_crossing_failure(scenario_index, $sformatf("Invalid step count read through converter: neuron produced %0d, AXI read %0d", produced_step_count, reported_steps));
            end
            check_live_crossing_snapshot(scenario_index);
            if (received_start_count != 1) begin
                record_crossing_failure(scenario_index, "Additional START event appeared without an AXI command");
            end
        end

        if (crossing_error_count == scenario_errors_before) begin
            $display("CDC SCENARIO PASS: scenario=%0d accelerator_period_ns=%0d phase_ns=%0d", scenario_index, neuron_period_ns, phase_offset_ns);
        end
endtask

task automatic run_tc_006_clock_domain_crossing;
        if (!CLOCK_CONVERTER_ENABLED) begin
            $fatal(1, "Run this testcase using run_testcase.ps1 so the generated AXI Clock Converter is enabled");
        end
        crossing_error_count = 0;
        live_snapshot_check_count = 0;
        run_crossing_scenario(0, 6, 1);
        run_crossing_scenario(1, 6, 4);
        run_crossing_scenario(2, 14, 1);
        run_crossing_scenario(3, 14, 4);
        run_crossing_scenario(4, 10, 2);
        run_crossing_scenario(5, 10, 7);
        run_crossing_scenario(6, 38, 1);
        run_crossing_scenario(7, 38, 11);
        reset_crossing_scenario(8, 14, 3);
        if (crossing_error_count != 0) begin
            $fatal(1, "CDC verification failed: %0d errors across eight clock scenarios and reset/restart checks", crossing_error_count);
        end
        if (live_snapshot_check_count == 0) begin
            $fatal(1, "CDC testcase did not verify any stable live voltage snapshots");
        end
        $display("Verified %0d live voltage snapshots", live_snapshot_check_count);
        $display("Verified generated AXI Clock Converter across independent source and accelerator clocks, phase offsets, current transfers, START delivery, step accounting, coherent snapshots and reset/restart");
endtask
