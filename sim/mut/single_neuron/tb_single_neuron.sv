`timescale 1ns/1ps

import neuron_params_generated_pkg::*;

module tb_single_neuron;
    logic clk = 1'b0;
    logic rst = 1'b1;
    logic valid_in = 1'b0;
    logic valid_out;
    logic ready;
    logic [1:0] id_out;
    fixed_t current_in = '0;
    fixed_t vmem_out;
    fixed_t vmem_out_previous;
    fixed_t expected_previous_vmem;

    integer stimulus_file;
    integer trace_file;
    integer read_count;
    integer number_of_steps = 0;
    integer cycles_after_reset = 0;

    single_neuron dut (
        .clk(clk),
        .rst(rst),
        .current_in(current_in),
        .valid_in(valid_in),
        .ready(ready),
        .id_in(2'd0),
        .id_out(id_out),
        .valid_out(valid_out),
        .vmem_out(vmem_out),
        .vmem_out_previous(vmem_out_previous)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!rst) begin
            cycles_after_reset <= cycles_after_reset + 1;
            if (cycles_after_reset > number_of_steps * 256 + 256) begin
                $fatal(1, "Timed out waiting for valid_out");
            end
        end
    end

    `include "tc_001_c_reference_trace.svh"

    initial begin
        if (!$test$plusargs("tc_001_c_reference_trace")) begin
            $fatal(1, "Select a single-neuron testcase with -testplusarg");
        end
        run_tc_001_c_reference_trace();
        $display("PASS: tc_001_c_reference_trace");
        $finish;
    end
endmodule
