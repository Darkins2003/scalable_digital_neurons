task automatic run_tc_002_axil_integration;
        repeat (5) begin
            @(negedge clk);
        end
        rst_n = 1'b1;

        // Program the network through AXI-Lite and check its input pins.
        axi_write(REG_CURRENT.offset, 32'd256000, 4'hf, 2, 0);
        if (axil_dut.network.current_in !== 32'd256000) begin
            $fatal(1, "Programmed current did not reach the network");
        end

        repeat (100) begin
            @(negedge clk);
        end
        axi_read(REG_STEP_COUNT.offset, count_read);
        if (count_read !== 0 || axil_dut.network.running !== 1'b0) begin
            $fatal(1, "Network ran before START");
        end

        axi_write(REG_CONTROL.offset, 32'h1, 4'h1, 0, 0);
        if (start_pulse_count !== 1) begin
            $fatal(1, "START did not reach the network once");
        end

        count_read = 0;
        for (int poll_index = 0; poll_index < 100 && count_read < 3; poll_index++) begin
            axi_read(REG_STEP_COUNT.offset, count_read);
        end
        if (count_read < 3) begin
            $fatal(1, "Three-neuron network did not complete three steps");
        end

        // Compare a snapshot taken between two reads of the same step count.
        stable_snapshot = 1'b0;
        for (int attempt_index = 0; attempt_index < 20 && !stable_snapshot; attempt_index++) begin
            axi_read(REG_STEP_COUNT.offset, count_read);
            axi_read(REG_VMEM_0.offset, vmem_read_0);
            axi_read(REG_VMEM_1.offset, vmem_read_1);
            axi_read(REG_VMEM_2.offset, vmem_read_2);
            axi_read(REG_STEP_COUNT.offset, count_after);
            stable_snapshot = (count_after == count_read);
        end
        if (!stable_snapshot || count_read < 3 || count_read > 63) begin
            $fatal(1, "Could not capture a stable network snapshot");
        end
        if (ref_count < count_read) begin
            $fatal(1, "Reference step count trails AXI count");
        end
        if (vmem_read_0 !== ref_history_0[count_read] || vmem_read_1 !== ref_history_1[count_read] || vmem_read_2 !== ref_history_2[count_read]) begin
            $fatal(1, "Three-neuron VMEM snapshots differ from the reference at step %0d", count_read);
        end
        if (vmem_read_0 === INITIAL_STATE[0]) begin
            $fatal(1, "Neuron 0 did not respond to the programmed input current");
        end

        // Reset must stop the network and require another START write.
        @(negedge clk);
        rst_n = 1'b0;
        repeat (3) begin
            @(negedge clk);
        end
        rst_n = 1'b1;

        repeat (100) begin
            @(negedge clk);
        end
        axi_read(REG_STEP_COUNT.offset, count_read);
        if (count_read !== 0 || axil_dut.network.running !== 1'b0) begin
            $fatal(1, "Network restarted without START after reset");
        end
        axi_read(REG_STATUS.offset, count_read);
        if (count_read !== REG_STATUS.reset_value) begin
            $fatal(1, "STATUS did not reset");
        end

        axi_write(REG_CONTROL.offset, 32'h1, 4'h1, 0, 0);
        count_read = 0;
        for (int poll_index = 0; poll_index < 100 && count_read < 1; poll_index++) begin
            axi_read(REG_STEP_COUNT.offset, count_read);
        end
        if (count_read < 1 || axil_dut.network.running !== 1'b1) begin
            $fatal(1, "Network did not restart after the second START");
        end
endtask
