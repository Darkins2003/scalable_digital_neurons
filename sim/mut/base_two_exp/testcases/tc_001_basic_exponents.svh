task automatic run_tc_001_basic_exponents;
        valid_in = '0;
        interpreted_exponent = '0;
        rst = '0;

        // ------------------------------RESET SEQUENCE------------------------------
        for (int i = 0; i < 2; i++) begin
            @(negedge clk);
        end 

        rst = '1;

        for (int i = 0; i < 2; i++) begin
            @(negedge clk);
        end 

        rst = '0;

        // ------------------------------SEQUENCE 1------------------------------
        @(negedge clk);
        valid_in = '1;
        interpreted_exponent = 2;

        @(negedge clk);
        valid_in = '0;

        for (int i = 1; i < 6; i++) begin
            @(negedge clk);
            $display("iteration: %0d exponent: %0.6f valid_out: %0b result: %0.6f", i, interpreted_exponent, valid_out, interpreted_result);
        end 

        // ------------------------------SEQUENCE 2------------------------------
        @(negedge clk);
        valid_in = '1;
        interpreted_exponent = -3.5;

        @(negedge clk);
        valid_in = '0;

        for (int i = 1; i < 6; i++) begin
            @(negedge clk);
            $display("iteration: %0d exponent: %0.6f valid_out: %0b result: %0.6f", i, interpreted_exponent, valid_out, interpreted_result);
        end 

        // ------------------------------SEQUENCE 3------------------------------
        @(negedge clk);
        valid_in = '1;
        interpreted_exponent = 1;
        @(negedge clk);
        interpreted_exponent = 2;
        @(negedge clk);
        interpreted_exponent = 3;
        @(negedge clk);
        interpreted_exponent = 4;
        @(negedge clk);
        interpreted_exponent = 5;

        @(negedge clk);
        valid_in = '0;

        for (int i = 1; i < 6; i++) begin
            @(negedge clk);
            $display("iteration: %0d valid_out: %0b result: %0.6f", i, valid_out, interpreted_result);
        end 

endtask
