`timescale 1ns/1ps

import neuron_params_generated_pkg::*;

module tb_base_two_exp;
    logic clk;
    logic rst;
    fixed_t exponent;
    logic valid_in;
    logic valid_out;
    logic [5:0] valid_pipeline;
    fixed_t result;

    real interpreted_result;
    real interpreted_exponent;

    // $itor converts signed number to a real 
    // Divide by 256 to remove 8 fractional bit scaling (right shift by 8)
    assign interpreted_result = $itor(result) / 256.0; 

    // $rtoi converts the real number into an integer by truncating toward zero.
    // Multiply by 2^24 to create 24 fractional bits
    assign exponent = fixed_t'($rtoi(interpreted_exponent * 16777216.0));

    base_two_exponential_pipe_cubic base_two_exponential_pipe_i(
        .clk(clk),
        .rst(rst),

        .exponent(exponent),
        .result(result)
    );

    assign valid_out = valid_pipeline[5];

    always_ff @(posedge clk) begin
        if (rst) begin
            valid_pipeline <= '0;
        end else begin
            valid_pipeline[0] <= valid_in;
            for (int delay_index = 0; delay_index < 5; delay_index++) begin
                valid_pipeline[delay_index+1] <= valid_pipeline[delay_index];
            end
        end
    end

    initial begin
        clk = 1'b0;
        forever begin
            #5 clk = ~clk;
        end 
    end

    `include "tc_001_basic_exponents.svh"

    initial begin
        if (!$test$plusargs("tc_001_basic_exponents"))
            $fatal(1, "Select a base-two testcase with -testplusarg");
        run_tc_001_basic_exponents();
        $display("PASS: tc_001_basic_exponents");
        $finish;
    end
endmodule
