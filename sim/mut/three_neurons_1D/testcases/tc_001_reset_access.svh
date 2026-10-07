task automatic run_tc_001_reset_access;
        logic [31:0] expected_current;

        reset_register_model();
        expect_register(REG_CONTROL.offset, REG_CONTROL.reset_value);
        expect_register(REG_CURRENT.offset, REG_CURRENT.reset_value);
        expect_register(REG_STATUS.offset, REG_STATUS.reset_value);
        expect_register(REG_STEP_COUNT.offset, REG_STEP_COUNT.reset_value);
        expect_register(REG_VMEM_0.offset, REG_VMEM_0.reset_value);
        expect_register(REG_VMEM_1.offset, REG_VMEM_1.reset_value);
        expect_register(REG_VMEM_2.offset, REG_VMEM_2.reset_value);

        // Set and clear every CURRENT bit independently.
        for (int bit_index = 0; bit_index < 32; bit_index++) begin
            write_register(REG_CURRENT.offset, 32'h1 << bit_index, 4'hf);
            expect_register(REG_CURRENT.offset, 32'h1 << bit_index);
            write_register(REG_CURRENT.offset, 32'd0, 4'hf);
            expect_register(REG_CURRENT.offset, 32'd0);
        end

        // Each byte strobe must change only its selected byte.
        expected_current = 32'hA1B2C3D4;
        write_register(REG_CURRENT.offset, expected_current, 4'hf);
        for (int byte_index = 0; byte_index < 4; byte_index++) begin
            write_register(REG_CURRENT.offset, 32'h5A5A5A5A, 4'b0001 << byte_index);
            expected_current = (expected_current & ~(32'hff << (byte_index * 8))) | (32'h5a << (byte_index * 8));
            expect_register(REG_CURRENT.offset, expected_current);
        end
        write_register(REG_CURRENT.offset, 32'hffffffff, 4'b0000);
        expect_register(REG_CURRENT.offset, expected_current);
        if (register_input_current !== expected_current) begin
            $fatal(1, "CURRENT did not reach the register model output");
        end

        // Software writes cannot change the hardware-owned registers.
        write_register(REG_STATUS.offset, 32'hffffffff, 4'hf);
        write_register(REG_STEP_COUNT.offset, 32'hffffffff, 4'hf);
        write_register(REG_VMEM_0.offset, 32'hffffffff, 4'hf);
        write_register(REG_VMEM_1.offset, 32'hffffffff, 4'hf);
        write_register(REG_VMEM_2.offset, 32'hffffffff, 4'hf);
        expect_register(REG_STATUS.offset, REG_STATUS.reset_value);
        expect_register(REG_STEP_COUNT.offset, REG_STEP_COUNT.reset_value);
        expect_register(REG_VMEM_0.offset, REG_VMEM_0.reset_value);
        expect_register(REG_VMEM_1.offset, REG_VMEM_1.reset_value);
        expect_register(REG_VMEM_2.offset, REG_VMEM_2.reset_value);
endtask
