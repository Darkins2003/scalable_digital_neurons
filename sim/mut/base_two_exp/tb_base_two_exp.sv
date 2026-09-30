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

    base_two_exponential_pipe base_two_exponential_pipe_i(
        .clk(clk),
        .rst(rst),

        .exponent(exponent),
        .valid_in(valid_in),

        .valid_out(valid_out),
        .result(result)
    );

    initial begin
        clk = 1'b0;
        forever begin
            #5 clk = ~clk;
        end 
    end

    initial begin
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

        $finish;
    end 

endmodule
