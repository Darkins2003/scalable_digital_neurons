`timescale 1ns/1ps
import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;

module tb_compute_current_vector;
    localparam int TEST_REQUEST_COUNT = 96;
    logic clk = 1'b0;
    always #4 clk = ~clk;
    logic rst = 1'b1;
    logic valid_in = 1'b0;
    logic ready;
    logic [1:0] id_in = '0;
    fixed_t current_in = '0;
    fixed_t neuron_state_variables [0:3] = INITIAL_STATE;
    logic valid_out;
    logic [1:0] id_out;
    fixed_t current_vector [0:7];

    logic reference_valid_in = 1'b0;
    logic reference_valid_out;
    fixed_t reference_current = '0;
    fixed_t reference_states [0:3] = INITIAL_STATE;
    fixed_t reference_vector [0:7];
    fixed_t stimulus_current [0:TEST_REQUEST_COUNT-1];
    fixed_t stimulus_states [0:TEST_REQUEST_COUNT-1][0:3];
    fixed_t expected_vectors [0:TEST_REQUEST_COUNT-1][0:7];
    bit checking_results = 1'b0;
    bit busy_observed = 1'b0;
    int accepted_count = 0;
    int returned_count = 0;
    int cycle_count = 0;

    compute_current_vector dut (
        .clk(clk), .rst(rst),
        .valid_in(valid_in), .ready(ready), .id_in(id_in),
        .current_in(current_in), .neuron_state_variables(neuron_state_variables),
        .valid_out(valid_out), .id_out(id_out), .current_vector(current_vector)
    );

    compute_current_vector_reference reference_engine (
        .clk(clk), .rst(rst),
        .valid_in(reference_valid_in), .current_in(reference_current),
        .neuron_state_variables(reference_states),
        .valid_out(reference_valid_out), .current_vector(reference_vector)
    );

    always @(posedge clk) begin
        cycle_count++;
        if (rst) begin
            accepted_count = 0;
            returned_count = 0;
        end else if (checking_results) begin
            if (valid_in && !ready) begin
                $fatal(1, "Request asserted while shared engine was busy");
            end
            if (valid_in && ready) begin
                accepted_count++;
            end
            #1;
            if (valid_out) begin
                if (returned_count >= accepted_count) begin
                    $fatal(1, "Unexpected or duplicate result");
                end
                if (id_out !== 2'(returned_count % NUM_NEURONS)) begin
                    $fatal(1, "Wrong neuron ID for result %0d: got %0d", returned_count, id_out);
                end
                for (int vector_index = 0; vector_index < 8; vector_index++) begin
                    if (current_vector[vector_index] !== expected_vectors[returned_count][vector_index]) begin
                        $fatal(1, "Result %0d element %0d: expected %0d got %0d", returned_count, vector_index, expected_vectors[returned_count][vector_index], current_vector[vector_index]);
                    end
                end
                returned_count++;
            end
        end
    end

    `include "tc_001_consecutive_requests.svh"

    initial begin
        if (!$test$plusargs("tc_001_consecutive_requests")) begin
            $fatal(1, "Select tc_001_consecutive_requests");
        end
        run_tc_001_consecutive_requests();
        $display("PASS: tc_001_consecutive_requests");
        $finish;
    end

    initial begin
        #200000;
        $fatal(1, "Shared engine testbench timed out");
    end
endmodule
