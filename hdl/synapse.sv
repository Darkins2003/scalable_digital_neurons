import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module synapse #(
    parameter int SOURCE_NEURON_IDX = 0,
    parameter int TARGET_NEURON_IDX = 0
)(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input fixed_t rx_vmem,
    input fixed_t excitatory_pulse,
    input fixed_t inhibitory_pulse,

    output fixed_t excitatory_current_contribution,
    output fixed_t inhibitory_current_contribution,
    output logic valid_out
);

    // Pipeline
    typedef struct packed {
        logic valid;
        fixed_t excitatory_pulse_d;
        fixed_t inhibitory_pulse_d;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 2;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t excitatory_pulse_reg [5:0];
    fixed_t inhibitory_pulse_reg [5:0];

    logic base_two_exponential_pipe_valid_out;
    fixed_t inhibitory_scale_neg;

    fixed_t excitatory_scale;
    fixed_t inhibitory_scale;
    fixed_t excitatory_scaled_coefficient;
    fixed_t inhibitory_scaled_coefficient;

    fixed_t excitatory_current_contribution_reg = '0;
    fixed_t inhibitory_current_contribution_reg = '0;

    assign excitatory_current_contribution = excitatory_current_contribution_reg;
    assign inhibitory_current_contribution = inhibitory_current_contribution_reg;

    base_two_exponential_pipe_linear base_two_exponential_linear_i(
        .clk(clk),
        .rst(rst),
        .exponent(rx_vmem + SYNAPSE_INHIBITORY_VMEM_OFFSET_Q24),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out),
        .result(inhibitory_scale_neg)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

        excitatory_scale <= '0;
        inhibitory_scale <= '0;
        excitatory_scaled_coefficient <= '0;
        inhibitory_scaled_coefficient <= '0;
        excitatory_current_contribution_reg <= '0;
        inhibitory_current_contribution_reg <= '0;
        excitatory_pulse_reg <= '{default:'0};
        inhibitory_pulse_reg <= '{default:'0};
        valid_out <= '0;

        end else begin
            excitatory_pulse_reg[0] <= excitatory_pulse;
            inhibitory_pulse_reg[0] <= inhibitory_pulse;

            for (int i = 0; i < 5; i ++) begin
                excitatory_pulse_reg[i+1] <= excitatory_pulse_reg[i];
                inhibitory_pulse_reg[i+1] <= inhibitory_pulse_reg[i];
            end 

            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= base_two_exponential_pipe_valid_out;
            pipe[0].excitatory_pulse_d <= excitatory_pulse_reg[5];
            pipe[0].inhibitory_pulse_d <= inhibitory_pulse_reg[5];

            excitatory_scale <= SYNAPSE_EXCITATORY_SCALE_Q8;
            inhibitory_scale <= -inhibitory_scale_neg;

            // ------------------------------STAGE 1-----------------------------
            pipe[1].valid <= pipe[0].valid;
            pipe[1].excitatory_pulse_d <= pipe[0].excitatory_pulse_d;
            pipe[1].inhibitory_pulse_d <= pipe[0].inhibitory_pulse_d;

            excitatory_scaled_coefficient <= mul_24_8_24(SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24[TARGET_NEURON_IDX][2*SOURCE_NEURON_IDX], excitatory_scale);
            inhibitory_scaled_coefficient <= mul_24_8_24(SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24[TARGET_NEURON_IDX][2*SOURCE_NEURON_IDX + 1], inhibitory_scale);

            // ------------------------------STAGE 2-----------------------------
            valid_out <= pipe[1].valid;

            if (pipe[1].valid) begin
                excitatory_current_contribution_reg <= mul_24_8_8(excitatory_scaled_coefficient, pipe[1].excitatory_pulse_d);
                inhibitory_current_contribution_reg <= mul_24_8_8(inhibitory_scaled_coefficient, pipe[1].inhibitory_pulse_d);
            end 
        end 

    end 
endmodule 