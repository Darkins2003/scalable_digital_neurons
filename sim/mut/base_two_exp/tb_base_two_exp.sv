`timescale 1ns/1ps

import neuron_params_generated_pkg::*;

module tb_base_two_exp;
    logic clk;
    logic rst;
    fixed_t exponent;
    logic valid_in;
    logic valid_out;
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
        .valid_in(valid_in),
        .independent_id_in(1'b0),
        .result(result),
        .valid_out(valid_out),
        .independent_id_out()
    );

    initial begin
        clk = 1'b0;
        forever begin
            #5 clk = ~clk;
        end 
    end

    `include "tc_001_basic_exponents.svh"

    initial begin
        if (!$test$plusargs("tc_001_basic_exponents")) begin
            $fatal(1, "Select a base-two testcase with -testplusarg");
        end
        run_tc_001_basic_exponents();
        $display("PASS: tc_001_basic_exponents");
        $finish;
    end
endmodule
