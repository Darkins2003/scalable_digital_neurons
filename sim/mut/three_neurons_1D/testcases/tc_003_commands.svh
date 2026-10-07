task automatic run_tc_003_commands;
        reset_register_model();
        if (register_start !== 1'b0) begin
            $fatal(1, "START was set after reset");
        end
        expect_register(REG_STATUS.offset, REG_STATUS.reset_value);

        write_register(REG_CONTROL.offset, 32'h1, 4'h1);
        if (register_start !== 1'b1) begin
            $fatal(1, "START did not produce a pulse");
        end
        expect_register(REG_CONTROL.offset, REG_CONTROL.reset_value);
        expect_register(REG_STATUS.offset, 32'd1);
        @(negedge clk);
        if (register_start !== 1'b0) begin
            $fatal(1, "START pulse lasted more than one clock");
        end

        write_register(REG_CONTROL.offset, 32'd0, 4'h1);
        if (register_start !== 1'b0) begin
            $fatal(1, "Writing zero triggered START");
        end
        expect_register(REG_STATUS.offset, 32'd1);

        write_register(REG_CONTROL.offset, 32'h1, 4'h0);
        if (register_start !== 1'b0) begin
            $fatal(1, "A write without byte strobes triggered START");
        end

        write_register(REG_CONTROL.offset, 32'h1, 4'b0010);
        if (register_start !== 1'b0) begin
            $fatal(1, "A write to an unrelated byte triggered START");
        end

        write_register(REG_CONTROL.offset, 32'h2, 4'h1);
        if (register_start !== 1'b0) begin
            $fatal(1, "Reserved CONTROL bit 1 triggered START");
        end
        expect_register(REG_CONTROL.offset, REG_CONTROL.reset_value);
        expect_register(REG_STATUS.offset, 32'd1);
endtask
