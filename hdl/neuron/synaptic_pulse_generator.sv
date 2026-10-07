import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module synaptic_pulse_generator (
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic start_pulse,
    input fixed_t excitatory_triangular_state, // Te Q16.16
    input fixed_t inhibitory_triangular_state, // Ti Q16.16

    output logic valid_out,
    output fixed_t excitatory_pulse, // Pe
    output fixed_t inhibitory_pulse // Pi
);

    // Pipeline
    typedef struct packed {
        logic valid;
        fixed_t scaled_excitatory_triangular_state; // Ge
        fixed_t scaled_inhibitory_triangular_state; // Gi
    } pipeline_t;

    localparam int PIPELINE_STAGES = 3;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t excitatory_exponent_argument; // Xe
    fixed_t inhibitory_exponent_argument; // Xi

    logic [2:0] exponential_valid;

    assign valid_out = exponential_valid[2];

    base_two_exponential_pipe_linear base_two_exponential_linear_excitatory_exponent(
        .clk(clk),
        .rst(rst),

        .exponent(excitatory_exponent_argument + SYNAPSE_EXP_BIAS_Q24[0]),

        .result(excitatory_pulse)
    );
    
    base_two_exponential_pipe_linear base_two_exponential_linear_inhibitory_exponent(
        .clk(clk),
        .rst(rst),

        .exponent(inhibitory_exponent_argument + SYNAPSE_EXP_BIAS_Q24[1]),
        
        .result(inhibitory_pulse)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            excitatory_exponent_argument <= '0;
            inhibitory_exponent_argument <= '0;
            exponential_valid <= '0;

        end else begin
            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in | start_pulse;

            pipe[0].scaled_excitatory_triangular_state <= mul_24_16_16(SYNAPSE_TRIANGLE_SCALE_Q24, excitatory_triangular_state);
            pipe[0].scaled_inhibitory_triangular_state <= mul_24_16_16(SYNAPSE_TRIANGLE_SCALE_Q24, inhibitory_triangular_state);

            // ------------------------------STAGE 1-----------------------------
            pipe[1].valid <= pipe[0].valid;

            pipe[1].scaled_excitatory_triangular_state <= pipe[0].scaled_excitatory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[0];
            pipe[1].scaled_inhibitory_triangular_state <= pipe[0].scaled_inhibitory_triangular_state + SYNAPSE_GATE_OFFSET_Q16[1];

            // ------------------------------STAGE 2-----------------------------
            pipe[2].valid <= pipe[1].valid;

            excitatory_exponent_argument <= mul_16_24_24(pipe[1].scaled_excitatory_triangular_state, SYNAPSE_EFFECTIVE_COUPLING_Q24);
            inhibitory_exponent_argument <= mul_16_24_24(pipe[1].scaled_inhibitory_triangular_state, SYNAPSE_EFFECTIVE_COUPLING_Q24);

            exponential_valid[0] <= pipe[2].valid;
            exponential_valid[1] <= exponential_valid[0];
            exponential_valid[2] <= exponential_valid[1];
        end 

    end 
endmodule
