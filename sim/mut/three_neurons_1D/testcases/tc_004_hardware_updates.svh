task automatic run_tc_004_hardware_updates;
        reset_register_model();
        expect_register(REG_STEP_COUNT.offset, 32'd0);
        expect_register(REG_STATUS.offset, 32'd0);

        drive_register_step(32'sd100, -32'sd200, 32'sd300);
        expect_register(REG_STEP_COUNT.offset, 32'd1);
        expect_register(REG_STATUS.offset, 32'd2);
        expect_register(REG_VMEM_0.offset, 32'sd100);
        expect_register(REG_VMEM_1.offset, -32'sd200);
        expect_register(REG_VMEM_2.offset, 32'sd300);

        register_network_voltage_0 = 32'sd999;
        register_network_voltage_1 = 32'sd999;
        register_network_voltage_2 = 32'sd999;
        repeat (2) begin
            @(negedge clk);
        end
        expect_register(REG_STEP_COUNT.offset, 32'd1);
        expect_register(REG_VMEM_0.offset, 32'sd100);
        expect_register(REG_VMEM_1.offset, -32'sd200);
        expect_register(REG_VMEM_2.offset, 32'sd300);

        drive_register_step(-32'sd400, 32'sd500, -32'sd600);
        expect_register(REG_STEP_COUNT.offset, 32'd2);
        expect_register(REG_VMEM_0.offset, -32'sd400);
        expect_register(REG_VMEM_1.offset, 32'sd500);
        expect_register(REG_VMEM_2.offset, -32'sd600);

        write_register(REG_CURRENT.offset, 32'h12345678, 4'hf);
        reset_register_model();
        expect_register(REG_CONTROL.offset, REG_CONTROL.reset_value);
        expect_register(REG_CURRENT.offset, REG_CURRENT.reset_value);
        expect_register(REG_STATUS.offset, REG_STATUS.reset_value);
        expect_register(REG_STEP_COUNT.offset, REG_STEP_COUNT.reset_value);
        expect_register(REG_VMEM_0.offset, REG_VMEM_0.reset_value);
        expect_register(REG_VMEM_1.offset, REG_VMEM_1.reset_value);
        expect_register(REG_VMEM_2.offset, REG_VMEM_2.reset_value);
endtask
