module comparison_testbench;
    logic clock = 0;
    logic reset;
    logic [23:0] fractional_exponent;
    logic input_valid;
    logic [25:0] stimulus [0:19669];
    integer checked_outputs = 0;
    always #2 clock = ~clock;
    logic signed [31:0] result_0;
    logic output_valid_0;
    logic [32:0] expected_0 [0:19669];
    taylor_1_dsp instance_0 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_0), .output_valid(output_valid_0));
    logic signed [31:0] result_1;
    logic output_valid_1;
    logic [32:0] expected_1 [0:19669];
    sollya_1_dsp instance_1 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_1), .output_valid(output_valid_1));
    logic signed [31:0] result_2;
    logic output_valid_2;
    logic [32:0] expected_2 [0:19669];
    taylor_2_dsp instance_2 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_2), .output_valid(output_valid_2));
    logic signed [31:0] result_3;
    logic output_valid_3;
    logic [32:0] expected_3 [0:19669];
    sollya_2_dsp instance_3 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_3), .output_valid(output_valid_3));
    logic signed [31:0] result_4;
    logic output_valid_4;
    logic [32:0] expected_4 [0:19669];
    taylor_3_dsp instance_4 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_4), .output_valid(output_valid_4));
    logic signed [31:0] result_5;
    logic output_valid_5;
    logic [32:0] expected_5 [0:19669];
    sollya_3_dsp instance_5 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_5), .output_valid(output_valid_5));
    logic signed [31:0] result_6;
    logic output_valid_6;
    logic [32:0] expected_6 [0:19669];
    taylor_4_dsp instance_6 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_6), .output_valid(output_valid_6));
    logic signed [31:0] result_7;
    logic output_valid_7;
    logic [32:0] expected_7 [0:19669];
    sollya_4_dsp instance_7 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_7), .output_valid(output_valid_7));
    logic signed [31:0] result_8;
    logic output_valid_8;
    logic [32:0] expected_8 [0:19669];
    research_cubic_dsp instance_8 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_8), .output_valid(output_valid_8));
    initial begin
        $readmemh("validation/stimulus.mem", stimulus);
        $readmemh("validation/taylor_1_dsp.mem", expected_0);
        $readmemh("validation/sollya_1_dsp.mem", expected_1);
        $readmemh("validation/taylor_2_dsp.mem", expected_2);
        $readmemh("validation/sollya_2_dsp.mem", expected_3);
        $readmemh("validation/taylor_3_dsp.mem", expected_4);
        $readmemh("validation/sollya_3_dsp.mem", expected_5);
        $readmemh("validation/taylor_4_dsp.mem", expected_6);
        $readmemh("validation/sollya_4_dsp.mem", expected_7);
        $readmemh("validation/research_cubic_dsp.mem", expected_8);
        for (integer cycle = 0; cycle < 19670; cycle = cycle + 1) begin
            @(negedge clock);
            {reset, input_valid, fractional_exponent} = stimulus[cycle];
            @(posedge clock);
            #0.1;
            if (output_valid_0 !== expected_0[cycle][32]) begin
                $fatal(1, "taylor_1_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_0[cycle][32]) begin
                if (result_0 !== expected_0[cycle][31:0]) begin
                    $fatal(1, "taylor_1_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_1 !== expected_1[cycle][32]) begin
                $fatal(1, "sollya_1_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_1[cycle][32]) begin
                if (result_1 !== expected_1[cycle][31:0]) begin
                    $fatal(1, "sollya_1_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_2 !== expected_2[cycle][32]) begin
                $fatal(1, "taylor_2_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_2[cycle][32]) begin
                if (result_2 !== expected_2[cycle][31:0]) begin
                    $fatal(1, "taylor_2_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_3 !== expected_3[cycle][32]) begin
                $fatal(1, "sollya_2_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_3[cycle][32]) begin
                if (result_3 !== expected_3[cycle][31:0]) begin
                    $fatal(1, "sollya_2_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_4 !== expected_4[cycle][32]) begin
                $fatal(1, "taylor_3_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_4[cycle][32]) begin
                if (result_4 !== expected_4[cycle][31:0]) begin
                    $fatal(1, "taylor_3_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_5 !== expected_5[cycle][32]) begin
                $fatal(1, "sollya_3_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_5[cycle][32]) begin
                if (result_5 !== expected_5[cycle][31:0]) begin
                    $fatal(1, "sollya_3_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_6 !== expected_6[cycle][32]) begin
                $fatal(1, "taylor_4_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_6[cycle][32]) begin
                if (result_6 !== expected_6[cycle][31:0]) begin
                    $fatal(1, "taylor_4_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_7 !== expected_7[cycle][32]) begin
                $fatal(1, "sollya_4_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_7[cycle][32]) begin
                if (result_7 !== expected_7[cycle][31:0]) begin
                    $fatal(1, "sollya_4_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_8 !== expected_8[cycle][32]) begin
                $fatal(1, "research_cubic_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_8[cycle][32]) begin
                if (result_8 !== expected_8[cycle][31:0]) begin
                    $fatal(1, "research_cubic_dsp result mismatch at cycle %0d", cycle);
                end
                checked_outputs = checked_outputs + 1;
            end
        end
        $display("PASS: all models matched Python; checked outputs=%0d", checked_outputs);
        $finish;
    end
endmodule
