import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module synapse (
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic [1:0] id_in,
    input fixed_t rx_vmem,
    input fixed_t excitatory_pulse,
    input fixed_t inhibitory_pulse,
    input logic [1:0] source_neuron_idx,
    input logic [1:0] target_neuron_idx,

    output fixed_t excitatory_current_contribution,
    output fixed_t inhibitory_current_contribution,
    output logic valid_out,
    output logic [1:0] id_out
);

    // Pipeline
    typedef struct packed {
        logic valid;
        logic [1:0] id;
        fixed_t excitatory_pulse_d;
        fixed_t inhibitory_pulse_d;
        logic [1:0] source_neuron_idx_d;
        logic [1:0] target_neuron_idx_d;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 5;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

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
        .independent_id_in(3'd0),
        
        .valid_out(),
        .independent_id_out(),
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
            id_out <= '0;
            valid_out <= '0;

        end else begin
            for (int i = 1; i < PIPELINE_STAGES; i++) begin
                pipe[i].valid <= pipe[i-1].valid;
                pipe[i].id <= pipe[i-1].id;
                pipe[i].excitatory_pulse_d <= pipe[i-1].excitatory_pulse_d;
                pipe[i].inhibitory_pulse_d <= pipe[i-1].inhibitory_pulse_d;
                pipe[i].source_neuron_idx_d <= pipe[i-1].source_neuron_idx_d;
                pipe[i].target_neuron_idx_d <= pipe[i-1].target_neuron_idx_d;
            end

            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in;
            pipe[0].id <= id_in;
            pipe[0].excitatory_pulse_d <= excitatory_pulse;
            pipe[0].inhibitory_pulse_d <= inhibitory_pulse;
            pipe[0].source_neuron_idx_d <= source_neuron_idx;
            pipe[0].target_neuron_idx_d <= target_neuron_idx;

            // ------------------------------STAGE 3-----------------------------
            excitatory_scale <= SYNAPSE_EXCITATORY_SCALE_Q8;
            inhibitory_scale <= -inhibitory_scale_neg;

            // ------------------------------STAGE 4-----------------------------
            excitatory_scaled_coefficient <= mul_24_8_24(SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24[pipe[3].target_neuron_idx_d][2*pipe[3].source_neuron_idx_d], excitatory_scale);
            inhibitory_scaled_coefficient <= mul_24_8_24(SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24[pipe[3].target_neuron_idx_d][2*pipe[3].source_neuron_idx_d + 1], inhibitory_scale);

            // ------------------------------STAGE 5-----------------------------
            valid_out <= pipe[PIPELINE_STAGES-1].valid;
            id_out <= pipe[PIPELINE_STAGES-1].id;

            if (pipe[PIPELINE_STAGES-1].valid) begin
                excitatory_current_contribution_reg <= mul_24_8_8(excitatory_scaled_coefficient, pipe[PIPELINE_STAGES-1].excitatory_pulse_d);
                inhibitory_current_contribution_reg <= mul_24_8_8(inhibitory_scaled_coefficient, pipe[PIPELINE_STAGES-1].inhibitory_pulse_d);
            end 
        end 

    end 
endmodule
