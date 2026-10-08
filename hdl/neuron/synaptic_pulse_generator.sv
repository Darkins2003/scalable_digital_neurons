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

    localparam int PIPELINE_STAGES = 8;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t excitatory_exponent_argument; // Xe
    fixed_t inhibitory_exponent_argument; // Xi

    fixed_t inhibitory_exponent_argument_d1;
    fixed_t linear_exponent;
    logic [2:0] linear_exponent_independent_id_in;
    logic [2:0] linear_exponent_independent_id_out;
    fixed_t linear_result_base_two_exponential;

    base_two_exponential_pipe_linear base_two_exponential_linear_pulse(
        .clk(clk),
        .rst(rst),

        .exponent(linear_exponent),
        .valid_in(pipe[3].valid | pipe[4].valid),
        .independent_id_in(linear_exponent_independent_id_in),

        .valid_out(),
        .independent_id_out(linear_exponent_independent_id_out),
        .result(linear_result_base_two_exponential)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            excitatory_exponent_argument <= '0;
            inhibitory_exponent_argument <= '0;
            inhibitory_exponent_argument_d1 <= '0;
            linear_exponent <= '0;
            linear_exponent_independent_id_in <= '0;
            excitatory_pulse <= '0;
            inhibitory_pulse <= '0;
            valid_out <= '0;
            id_out <= '0;

        end else begin
            for (int i = 1; i < PIPELINE_STAGES; i++) begin
                pipe[i].valid <= pipe[i-1].valid;
                pipe[i].id <= pipe[i-1].id;
            end

            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in | start_pulse;
            pipe[0].id <= id_in;

            pipe[0].scaled_excitatory_triangular_state <= mul_24_16_16(SYNAPSE_TRIANGLE_SCALE_Q24, excitatory_triangular_state);
            pipe[0].scaled_inhibitory_triangular_state <= mul_24_16_16(SYNAPSE_TRIANGLE_SCALE_Q24, inhibitory_triangular_state);

            // ------------------------------STAGE 1-----------------------------
            pipe[1].scaled_excitatory_triangular_state <= pipe[0].scaled_excitatory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[0];
            pipe[1].scaled_inhibitory_triangular_state <= pipe[0].scaled_inhibitory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[1];

            // ------------------------------STAGE 2-----------------------------
            excitatory_exponent_argument <= mul_16_24_24(pipe[1].scaled_excitatory_triangular_state, SYNAPSE_EFFECTIVE_COUPLING_Q24);
            inhibitory_exponent_argument <= mul_16_24_24(pipe[1].scaled_inhibitory_triangular_state, SYNAPSE_EFFECTIVE_COUPLING_Q24);

            // ------------------------------STAGE 3-----------------------------
            if (pipe[2].valid) begin
                linear_exponent <= excitatory_exponent_argument + SYNAPSE_EXP_BIAS_Q24[0];
                linear_exponent_independent_id_in <= 3'd0;

                inhibitory_exponent_argument_d1 <= inhibitory_exponent_argument;
            end 
            
            // ------------------------------STAGE 4-----------------------------
            if (pipe[3].valid) begin
                linear_exponent <= inhibitory_exponent_argument_d1 + SYNAPSE_EXP_BIAS_Q24[1];
                linear_exponent_independent_id_in <= 3'd1;
            end

            // ------------------------------RESULTS STAGE 1-----------------------------
            if (pipe[6].valid) begin
                excitatory_pulse <= linear_result_base_two_exponential;
            end 

            // ------------------------------RESULTS STAGE 2-----------------------------
            valid_out <= pipe[PIPELINE_STAGES-1].valid;;

            if (pipe[7].valid) begin
                inhibitory_pulse <= linear_result_base_two_exponential;
                id_out <= pipe[PIPELINE_STAGES-1].id;
            end 

            
        end 

    end 
endmodule
