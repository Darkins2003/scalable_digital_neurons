import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module compute_current_vector(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input fixed_t current_in,
    input fixed_t neuron_state_variables [0:3],

    output logic valid_out,
    output fixed_t current_vector [0:7] 
);

    // Pipeline
    typedef struct packed {
        fixed_t current_vector_1_data;
        fixed_t current_vector_2_data;
        fixed_t current_vector_3_data;
        fixed_t current_vector_4_data;
        fixed_t current_vector_5_data;
        fixed_t current_vector_6_data;
        fixed_t current_vector_7_data;
        fixed_t phase_2_current_in_d;
        logic valid;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 3;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    // Valids
    logic [9:0] base_two_exponential_pipe_valid_out;

    // Exponential results
    fixed_t result_base_two_exponential_cubic_vmem;
    fixed_t result_base_two_exponential_linear_vmem;
    fixed_t result_base_two_exponential_kp_vna;
    fixed_t result_base_two_exponential_kp_vg;
    fixed_t result_base_two_exponential_vna_offset;
    fixed_t result_base_two_exponential_kp_vk;
    fixed_t result_base_two_exponential_kp_vk_plus_vmem;
    fixed_t result_base_two_exponential_vk;
    fixed_t result_base_two_exponential_vna;
    fixed_t result_base_two_exponential_vg;

    // Delayed results
    fixed_t result_base_two_exponential_kp_vk_plus_vmem_d1;
    fixed_t result_base_two_exponential_kp_vna_d1;
    fixed_t result_base_two_exponential_kp_vna_d2;

    fixed_t phase_1_current_in_d [5:0];

    // current_vector[1]
    base_two_exponential_pipe_cubic base_two_exponential_cubic_vmem(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[0]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[0]),
        .result(result_base_two_exponential_cubic_vmem)
    );

    // current_vector[2]
    base_two_exponential_pipe_linear base_two_exponential_linear_vmem(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[0]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[1]),
        .result(result_base_two_exponential_linear_vmem)
    );

    // current_vector[2]
    base_two_exponential_pipe_linear base_two_exponential_linear_kp_vna(
        .clk(clk),
        .rst(rst),
        .exponent(mul_24_24_24(KP, neuron_state_variables[3])),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[2]),
        .result(result_base_two_exponential_kp_vna)
    );

    // current_vector[3]
    base_two_exponential_pipe_linear base_two_exponential_linear_kp_vg(
        .clk(clk),
        .rst(rst),
        .exponent(mul_24_24_24(KP, neuron_state_variables[2])),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[3]),
        .result(result_base_two_exponential_kp_vg)
    );

    // current_vector[4]
    base_two_exponential_pipe_linear base_two_exponential_linear_vna_offset(
        .clk(clk),
        .rst(rst),
        .exponent(-neuron_state_variables[3] - VNA_OFFSET_Q24),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[4]),
        .result(result_base_two_exponential_vna_offset)
    );

    // current_vector[5]
    base_two_exponential_pipe_linear base_two_exponential_linear_kp_vk(
        .clk(clk),
        .rst(rst),
        .exponent(mul_24_24_24(KP, neuron_state_variables[1])),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[5]),
        .result(result_base_two_exponential_kp_vk)
    );

    // current_vector[5]
    base_two_exponential_pipe_cubic base_two_exponential_cubic_kp_vk_plus_vmem(
        .clk(clk),
        .rst(rst),
        .exponent(mul_24_24_24(KP, neuron_state_variables[1]) + neuron_state_variables[0]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[6]),
        .result(result_base_two_exponential_kp_vk_plus_vmem)
    );

    // current_vector[6]
    base_two_exponential_pipe_linear base_two_exponential_linear_vk(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[1]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[7]),
        .result(result_base_two_exponential_vk)
    );

    // current_vector[7]
    base_two_exponential_pipe_linear base_two_exponential_linear_vna(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[3]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[8]),
        .result(result_base_two_exponential_vna)
    );

    // current_vector[7]
    base_two_exponential_pipe_linear base_two_exponential_linear_vg(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[2]),
        .valid_in(valid_in),

        .valid_out(base_two_exponential_pipe_valid_out[9]),
        .result(result_base_two_exponential_vg)
    );

    always @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            current_vector <= '{default:'0};
            phase_1_current_in_d <= '{default:'0};

            valid_out <= '0;
            result_base_two_exponential_kp_vk_plus_vmem_d1 <= '0;
            result_base_two_exponential_kp_vna_d1 <= '0;
            result_base_two_exponential_kp_vna_d2 <= '0;
        end else begin
            // ------------------------------STAGE 0 (6 clk cycles)-----------------------------
            // Iterations of base_two_exponential_pipe_cubic and base_two_exponential_pipe_linear are processing

            // current_vector[0]
            phase_1_current_in_d[0] <= current_in;

            for (int i = 0; i < 5; i++) begin
                phase_1_current_in_d[i+1] <= phase_1_current_in_d[i];
            end 

            // ------------------------------STAGE 1-----------------------------
            pipe[1].valid <= &base_two_exponential_pipe_valid_out; // Waits for base_two_exponential_pipe_cubic to complete. All should complete simultaneously

            // current_vector[0]
            pipe[1].phase_2_current_in_d <= phase_1_current_in_d[5];

            // current_vector[1]
            pipe[1].current_vector_1_data <= mul_24_8_8(EXPMEL, result_base_two_exponential_cubic_vmem);

            // current_vector[2]
            pipe[1].current_vector_2_data <= mul_24_8_8(EXPVNA, result_base_two_exponential_linear_vmem);
            result_base_two_exponential_kp_vna_d1 <= result_base_two_exponential_kp_vna;

            // current_vector[3]
            pipe[1].current_vector_3_data <= result_base_two_exponential_kp_vg;

            // current_vector[4]
            pipe[1].current_vector_4_data <= mul_24_8_8(EXPVSAT, result_base_two_exponential_vna_offset);

            // current_vector[5]
            pipe[1].current_vector_5_data <= mul_24_8_8(EXPEK, result_base_two_exponential_kp_vk);
            result_base_two_exponential_kp_vk_plus_vmem_d1 <= result_base_two_exponential_kp_vk_plus_vmem;

            // current_vector[6]
            pipe[1].current_vector_6_data <= mul_24_8_8(EXPMVGK, result_base_two_exponential_vk);

            // current_vector[7]
            pipe[1].current_vector_7_data <= result_base_two_exponential_vg - result_base_two_exponential_vna;
            // ------------------------------STAGE 2-----------------------------
            pipe[2].valid <= pipe[1].valid;

            // current_vector[0]
            pipe[2].phase_2_current_in_d <= pipe[1].phase_2_current_in_d;

            // current_vector[1]
            pipe[2].current_vector_1_data <= ONE_Q8 - pipe[1].current_vector_1_data;

            // current_vector[2]
            pipe[2].current_vector_2_data <= ONE_Q8 - pipe[1].current_vector_2_data;
            result_base_two_exponential_kp_vna_d2 <= result_base_two_exponential_kp_vna_d1;

            // current_vector[3]
            pipe[2].current_vector_3_data <= pipe[1].current_vector_3_data;

            // current_vector[4]
            pipe[2].current_vector_4_data <= ONE_Q8 - pipe[1].current_vector_4_data;

            // current_vector[5]
            pipe[2].current_vector_5_data <= result_base_two_exponential_kp_vk_plus_vmem_d1 - pipe[1].current_vector_5_data;

            // current_vector[6]
            pipe[2].current_vector_6_data <= ONE_Q8 - pipe[1].current_vector_6_data;

            // current_vector[6]
            pipe[2].current_vector_7_data <= pipe[1].current_vector_7_data;

            // ------------------------------STAGE 3-----------------------------
            valid_out <= pipe[2].valid;

            // current_vector[0]
            current_vector[0] <= pipe[2].phase_2_current_in_d;

            // current_vector[1]
            current_vector[1] <= pipe[2].current_vector_1_data;

            // current_vector[2]
            current_vector[2] <= mul_8_8_8(pipe[2].current_vector_2_data, result_base_two_exponential_kp_vna_d2); 

            // current_vector[3]
            current_vector[3] <= pipe[2].current_vector_3_data;

            // current_vector[4]
            current_vector[4] <= pipe[2].current_vector_4_data;

            // current_vector[5]
            current_vector[5] <= pipe[2].current_vector_5_data;

            // current_vector[6]
            current_vector[6] <= pipe[2].current_vector_6_data;

            // current_vector[7]
            current_vector[7] <= pipe[2].current_vector_7_data;
        end 
    end 
endmodule
