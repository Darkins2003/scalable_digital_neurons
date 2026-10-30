import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module synaptic_pulse_generator (
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic [1:0] id_in,
    input logic start_pulse,
    input fixed_t excitatory_triangular_state, // Te Q16.16
    input fixed_t inhibitory_triangular_state, // Ti Q16.16

    output logic valid_out,
    output logic [1:0] id_out,
    output fixed_t excitatory_pulse, // Pe
    output fixed_t inhibitory_pulse // Pi
);

    // Pipeline
    typedef struct packed {
        logic valid;
        logic [1:0] id;
        fixed_t scaled_excitatory_triangular_state; // Ge
        fixed_t scaled_inhibitory_triangular_state; // Gi
    } pipeline_t;

    localparam int PIPELINE_STAGES = 21;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t scaled_excitatory_triangular_state;
    fixed_t scaled_inhibitory_triangular_state;
    logic scaled_triangular_state_valid_out;
    logic exponent_argument_valid_out;

    fixed_t excitatory_exponent_argument; // Xe
    fixed_t inhibitory_exponent_argument; // Xi

    fixed_t inhibitory_exponent_argument_d1;
    fixed_t linear_exponent;
    logic [2:0] linear_exponent_independent_id_in;
    logic [2:0] linear_exponent_independent_id_out;
    logic linear_exponent_valid_out;
    fixed_t linear_result_base_two_exponential;

    // ------------------------------STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd16),
        .RESULT_FRACTIONAL_BITS(6'd16)
    ) signed_32_32_multiplication_i (
        .clk(clk),
        .rst(rst),

        .term_1(SYNAPSE_TRIANGLE_SCALE_Q24),
        .term_2(excitatory_triangular_state),
        .valid_in(valid_in | start_pulse),

        .result(scaled_excitatory_triangular_state),
        .valid_out(scaled_triangular_state_valid_out)
    );

    // ------------------------------STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd16),
        .RESULT_FRACTIONAL_BITS(6'd16)
    ) signed_32_32_multiplication_i2 (
        .clk(clk),
        .rst(rst),

        .term_1(SYNAPSE_TRIANGLE_SCALE_Q24),
        .term_2(inhibitory_triangular_state),
        .valid_in(valid_in | start_pulse),

        .result(scaled_inhibitory_triangular_state),
        .valid_out()
    );

    // ------------------------------STAGE 2 to STAGE 2 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd16),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i3 (
        .clk(clk),
        .rst(rst),

        .term_1(pipe[7].scaled_excitatory_triangular_state),
        .term_2(SYNAPSE_EFFECTIVE_COUPLING_Q24),
        .valid_in(pipe[7].valid),

        .result(excitatory_exponent_argument),
        .valid_out(exponent_argument_valid_out)
    );

    // ------------------------------STAGE 2 to STAGE 2 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd16),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i4 (
        .clk(clk),
        .rst(rst),

        .term_1(pipe[7].scaled_inhibitory_triangular_state),
        .term_2(SYNAPSE_EFFECTIVE_COUPLING_Q24),
        .valid_in(pipe[7].valid),

        .result(inhibitory_exponent_argument),
        .valid_out()
    );

    // ------------------------------STAGE 4 to STAGE 4 (+3)------------------------------
    // ------------------------------STAGE 5 to STAGE 5 (+3)------------------------------
    base_two_exponential_pipe_linear base_two_exponential_pipe_linear_i(
        .clk(clk),
        .rst(rst),

        .exponent(linear_exponent),
        .valid_in(pipe[15].valid | pipe[16].valid),
        .independent_id_in(linear_exponent_independent_id_in),

        .valid_out(linear_exponent_valid_out),
        .independent_id_out(linear_exponent_independent_id_out),
        .result(linear_result_base_two_exponential)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            inhibitory_exponent_argument_d1 <= '0;
            linear_exponent <= '0;
            linear_exponent_independent_id_in <= '0;
            excitatory_pulse <= '0;
            inhibitory_pulse <= '0;
            valid_out <= '0;
            id_out <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 22------------------------------
            // ------------------------------STAGE 0 (FEED signed_32_32_multiplication_i AND signed_32_32_multiplication_i2)------------------------------
            pipe[0].id <= id_in;

            // ------------------------------STAGE 0 (+1) to STAGE 0 (+6) (WAIT FOR signed_32_32_multiplication_i AND signed_32_32_multiplication_i2)------------------------------
            for (int i = 1; i < 7; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            // ------------------------------STAGE 1-----------------------------
            pipe[7].valid <= scaled_triangular_state_valid_out;
            pipe[7].id <= pipe[6].id;

            pipe[7].scaled_excitatory_triangular_state <= scaled_excitatory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[0];
            pipe[7].scaled_inhibitory_triangular_state <= scaled_inhibitory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[1];

            // ------------------------------STAGE 2 (FEED signed_32_32_multiplication_i3 AND signed_32_32_multiplication_i4)------------------------------
            pipe[8].id <= pipe[7].id;

            // ------------------------------STAGE 2 (+1) to STAGE 2 (+6) (WAIT FOR signed_32_32_multiplication_i3 AND signed_32_32_multiplication_i4)------------------------------
            for (int i = 9; i < 15; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            // ------------------------------STAGE 3-----------------------------
            pipe[15].valid <= exponent_argument_valid_out;
            pipe[15].id <= pipe[14].id;

            if (exponent_argument_valid_out) begin
                linear_exponent <= excitatory_exponent_argument + SYNAPSE_EXP_BIAS_Q24[0];
                linear_exponent_independent_id_in <= 3'd0;

                inhibitory_exponent_argument_d1 <= inhibitory_exponent_argument;
            end

            // ------------------------------STAGE 4 (FEED base_two_exponential_pipe_linear_i)------------------------------
            pipe[16].valid <= pipe[15].valid;
            pipe[16].id <= pipe[15].id;

            if (pipe[15].valid) begin
                linear_exponent <= inhibitory_exponent_argument_d1 + SYNAPSE_EXP_BIAS_Q24[1];
                linear_exponent_independent_id_in <= 3'd1;
            end

            // ------------------------------STAGE 5 (FEED base_two_exponential_pipe_linear_i)------------------------------
            pipe[17].id <= pipe[16].id;

            // ------------------------------STAGE 5 (+1) to STAGE 5 (+3) (WAIT FOR base_two_exponential_pipe_linear_i)------------------------------
            for (int i = 18; i < PIPELINE_STAGES; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            // ------------------------------RESULTS STAGE 1-----------------------------
            if (linear_exponent_valid_out && linear_exponent_independent_id_out == 3'd0) begin
                excitatory_pulse <= linear_result_base_two_exponential;
            end 

            // ------------------------------RESULTS STAGE 2-----------------------------
            valid_out <= linear_exponent_valid_out && linear_exponent_independent_id_out == 3'd1;

            if (linear_exponent_valid_out && linear_exponent_independent_id_out == 3'd1) begin
                inhibitory_pulse <= linear_result_base_two_exponential;
                id_out <= pipe[PIPELINE_STAGES-1].id;
            end 

            
        end 

    end 
endmodule
