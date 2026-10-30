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
        fixed_t excitatory_scaled_coefficient;
        logic [1:0] source_neuron_idx_d;
        logic [1:0] target_neuron_idx_d;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 20;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t linear_exponent = '0;
    fixed_t inhibitory_scale_neg;
    fixed_t inhibitory_scale = '0;
    logic linear_exponent_valid_out_d = '0;
    logic linear_exponent_valid_out;

    fixed_t inhibitory_scaled_coefficient;
    logic inhibitory_scaled_coefficient_valid_out;

    fixed_t excitatory_current_contribution_reg;
    fixed_t inhibitory_current_contribution_reg;

    assign excitatory_current_contribution = excitatory_current_contribution_reg;
    assign inhibitory_current_contribution = inhibitory_current_contribution_reg;

    // ------------------------------STAGE 3 to STAGE 3 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i3 (
        .clk(clk),
        .rst(rst),

        .term_1(SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24[pipe[5].target_neuron_idx_d][2*pipe[5].source_neuron_idx_d + 1]),
        .term_2(inhibitory_scale),
        .valid_in(linear_exponent_valid_out_d),

        .result(inhibitory_scaled_coefficient),
        .valid_out(inhibitory_scaled_coefficient_valid_out)
    );

    // ------------------------------STAGE 4 to STAGE 4 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i (
        .clk(clk),
        .rst(rst),

        .term_1(pipe[12].excitatory_scaled_coefficient),
        .term_2(pipe[12].excitatory_pulse_d),
        .valid_in(inhibitory_scaled_coefficient_valid_out),

        .result(excitatory_current_contribution_reg),
        .valid_out(valid_out)
    );

    // ------------------------------STAGE 4 to STAGE 4 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i2 (
        .clk(clk),
        .rst(rst),

        .term_1(inhibitory_scaled_coefficient),
        .term_2(pipe[12].inhibitory_pulse_d),
        .valid_in(inhibitory_scaled_coefficient_valid_out),

        .result(inhibitory_current_contribution_reg),
        .valid_out()
    );

    // ------------------------------STAGE 1 to STAGE 1 (+3)------------------------------
    base_two_exponential_pipe_linear base_two_exponential_linear_i(
        .clk(clk),
        .rst(rst),

        .exponent(linear_exponent),
        .valid_in(pipe[0].valid),
        .independent_id_in(3'd0),
        
        .valid_out(linear_exponent_valid_out),
        .independent_id_out(),
        .result(inhibitory_scale_neg)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            id_out <= '0;
            linear_exponent <= '0;
            inhibitory_scale <= '0;
            linear_exponent_valid_out_d <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 20------------------------------
            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in;
            pipe[0].id <= id_in;
            pipe[0].excitatory_pulse_d <= excitatory_pulse;
            pipe[0].inhibitory_pulse_d <= inhibitory_pulse;
            pipe[0].source_neuron_idx_d <= source_neuron_idx;
            pipe[0].target_neuron_idx_d <= target_neuron_idx;

            linear_exponent <= rx_vmem + SYNAPSE_INHIBITORY_VMEM_OFFSET_Q24;

            // ------------------------------STAGE 1 to STAGE 1 (+3) (WAIT FOR base_two_exponential_linear_i)------------------------------
            for (int i = 1; i < 5; i++) begin
                pipe[i].id <= pipe[i-1].id;
                pipe[i].excitatory_pulse_d <= pipe[i-1].excitatory_pulse_d;
                pipe[i].inhibitory_pulse_d <= pipe[i-1].inhibitory_pulse_d;
                pipe[i].source_neuron_idx_d <= pipe[i-1].source_neuron_idx_d;
                pipe[i].target_neuron_idx_d <= pipe[i-1].target_neuron_idx_d;
            end

            // ------------------------------STAGE 2------------------------------
            pipe[5].id <= pipe[4].id;
            pipe[5].excitatory_pulse_d <= pipe[4].excitatory_pulse_d;
            pipe[5].inhibitory_pulse_d <= pipe[4].inhibitory_pulse_d;

            pipe[5].source_neuron_idx_d <= pipe[4].source_neuron_idx_d;
            pipe[5].target_neuron_idx_d <= pipe[4].target_neuron_idx_d;

            inhibitory_scale <= -inhibitory_scale_neg;
            linear_exponent_valid_out_d <= linear_exponent_valid_out;

            // ------------------------------STAGE 3 (FEED signed_32_32_multiplication_i3)------------------------------
            pipe[6].id <= pipe[5].id;
            pipe[6].excitatory_pulse_d <= pipe[5].excitatory_pulse_d;
            pipe[6].inhibitory_pulse_d <= pipe[5].inhibitory_pulse_d;

            // inhibitory_scaled_coefficient is not a multiplication by 2 constants, therefore feed signed_32_32_multiplication_i3
            // excitatory_scaled_coefficient is multiplication by 2 constants, therefore use precomputed products
            pipe[6].excitatory_scaled_coefficient <= SYNFIRE_1D_3_SCALED_EXCITATORY_COEFFICIENT_Q24[pipe[5].target_neuron_idx_d][pipe[5].source_neuron_idx_d];

            // ------------------------------STAGE 3 (+1) to STAGE 3 (+6) (WAIT FOR signed_32_32_multiplication_i3)------------------------------
            for (int i = 7; i < 13; i++) begin
                pipe[i].id <= pipe[i-1].id;
                pipe[i].excitatory_pulse_d <= pipe[i-1].excitatory_pulse_d;
                pipe[i].inhibitory_pulse_d <= pipe[i-1].inhibitory_pulse_d;
                pipe[i].excitatory_scaled_coefficient <= pipe[i-1].excitatory_scaled_coefficient;
            end

            // ------------------------------STAGE 4 (FEED signed_32_32_multiplication_i AND signed_32_32_multiplication_i2)------------------------------
            pipe[13].id <= pipe[12].id;

            // ------------------------------STAGE 4 (+1) to STAGE 4 (+6) (WAIT FOR signed_32_32_multiplication_i AND signed_32_32_multiplication_i2)------------------------------
            for (int i = 14; i < PIPELINE_STAGES-1; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            id_out <= pipe[PIPELINE_STAGES-2].id;
        end 

    end 
endmodule
