import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module compute_current_vector(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic [1:0] id_in,
    input fixed_t current_in,
    input fixed_t neuron_state_variables [0:3],

    output logic ready,
    output logic [1:0] id_out,
    output logic valid_out,
    output fixed_t current_vector [0:7] 
);
    // PHASE 1 PIPE
    typedef struct packed {
        fixed_t current_input;
        fixed_t [0:3] neuron_state_reg;
        fixed_t term_i3;
        logic [2:0] linear_exponent_independent_id;
        logic valid;
        logic [1:0] id;
    } phase_1_pipeline_t;

    localparam int PHASE_1_PIPELINE_STAGES = 27;
    phase_1_pipeline_t phase_1_pipe [0:PHASE_1_PIPELINE_STAGES-1];

    // PHASE 2 PIPE
    typedef struct packed {
        fixed_t current_vector_1_data;
        fixed_t current_vector_2_data;
        fixed_t current_vector_3_data;
        fixed_t current_vector_4_data;
        fixed_t current_vector_5_data;
        fixed_t current_vector_6_data;
        fixed_t current_vector_7_data;
        fixed_t phase_2_current_in_d;
        fixed_t result_base_two_exponential_kp_vna;
        fixed_t result_base_two_exponential_kp_vk_plus_vmem;
        logic valid;
        logic [1:0] id;
    } phase_2_pipeline_t;

    localparam int PHASE_2_PIPELINE_STAGES = 15;
    phase_2_pipeline_t phase_2_pipe [0:PHASE_2_PIPELINE_STAGES-1];

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

    fixed_t current_vector_1_product;
    fixed_t current_vector_2_product;
    fixed_t current_vector_4_product;
    fixed_t current_vector_5_product;
    fixed_t current_vector_6_product;
    logic phase_2_multiplication_valid_out;
    logic linear_exponent_multiplication_valid_out;
    logic mul_kp_vk_valid_out;

    // Phase 1 linear exponential
    fixed_t linear_exponent;
    fixed_t linear_exponent_tmp;
    logic [7:0] linear_exponent_valid;
    logic [2:0] linear_exponent_independent_id_in_d1;
    logic [2:0] next_linear_exponent_independent_id_in_d1;
    logic [2:0] linear_exponent_independent_id_in = '0;
    logic [2:0] next_linear_exponent_independent_id_in = '0;
    logic [2:0] linear_exponent_independent_id_out;
    logic linear_exponent_valid_out;
    fixed_t linear_result_base_two_exponential;
    logic linear_exponent_done;

    // Phase 1 cubic exponential
    fixed_t cubic_exponent;
    logic [1:0] cubic_exponent_valid;
    logic cubic_exponent_independent_id_in = '0;
    logic cubic_exponent_independent_id_out;
    logic cubic_exponent_valid_out;
    fixed_t mul_kp_vk;
    fixed_t cubic_result_base_two_exponential;
    logic cubic_exponent_done;

    logic ready_reg = '1;

    assign ready = ready_reg;

    // ------------------------------PHASE 2 STAGE 2 to STAGE 2 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd8),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i (
        .clk(clk),
        .rst(rst),

        .term_1(phase_2_pipe[7].current_vector_2_data),
        .term_2(phase_2_pipe[7].result_base_two_exponential_kp_vna),
        .valid_in(phase_2_pipe[7].valid),

        .result(current_vector[2]),
        .valid_out(valid_out)
    );

    // ------------------------------PHASE 1 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i2 (
        .clk(clk),
        .rst(rst),

        .term_1(KP),
        .term_2(neuron_state_variables[1]),
        .valid_in(valid_in),

        .result(mul_kp_vk),
        .valid_out(mul_kp_vk_valid_out)
    );

    // ------------------------------PHASE 1 STAGE 1 to STAGE 1 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i3 (
        .clk(clk),
        .rst(rst),

        .term_1((next_linear_exponent_independent_id_in_d1 == 3'd1 || next_linear_exponent_independent_id_in_d1 == 3'd2 || next_linear_exponent_independent_id_in_d1 == 3'd4) ? KP : ONE_Q24),
        .term_2(linear_exponent_tmp),
        .valid_in(phase_1_pipe[0].valid || (|linear_exponent_valid && linear_exponent_independent_id_in_d1 != 3'd7)),

        .result(linear_exponent),
        .valid_out(linear_exponent_multiplication_valid_out)
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i4 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPMEL),
        .term_2(result_base_two_exponential_cubic_vmem),
        .valid_in(linear_exponent_done && cubic_exponent_done),

        .result(current_vector_1_product),
        .valid_out(phase_2_multiplication_valid_out)
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i5 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPVNA),
        .term_2(result_base_two_exponential_linear_vmem),
        .valid_in(linear_exponent_done && cubic_exponent_done),

        .result(current_vector_2_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i6 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPVSAT),
        .term_2(result_base_two_exponential_vna_offset),
        .valid_in(linear_exponent_done && cubic_exponent_done),

        .result(current_vector_4_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i7 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPEK),
        .term_2(result_base_two_exponential_kp_vk),
        .valid_in(linear_exponent_done && cubic_exponent_done),

        .result(current_vector_5_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i8 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPMVGK),
        .term_2(result_base_two_exponential_vk),
        .valid_in(linear_exponent_done && cubic_exponent_done),

        .result(current_vector_6_product),
        .valid_out()
    );

    // ------------------------------PHASE 1 STAGE 2 to STAGE 2 (+3)------------------------------
    base_two_exponential_pipe_linear base_two_exponential_pipe_linear_i(
        .clk(clk),
        .rst(rst),

        .exponent(linear_exponent),
        .valid_in(linear_exponent_multiplication_valid_out),
        .independent_id_in(phase_1_pipe[7].linear_exponent_independent_id),

        .valid_out(linear_exponent_valid_out),
        .independent_id_out(linear_exponent_independent_id_out),
        .result(linear_result_base_two_exponential)
    );

    // ------------------------------PHASE 1 STAGE 1 to STAGE 1 (+17)------------------------------
    base_two_exponential_pipe_cubic base_two_exponential_pipe_cubic_i(
        .clk(clk),
        .rst(rst),

        .exponent(cubic_exponent),
        .valid_in(|cubic_exponent_valid),
        .independent_id_in(cubic_exponent_independent_id_in),

        .valid_out(cubic_exponent_valid_out),
        .independent_id_out(cubic_exponent_independent_id_out),
        .result(cubic_result_base_two_exponential)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PHASE_2_PIPELINE_STAGES; i++) begin
                phase_2_pipe[i] <= '0;
            end  

            for (int i = 0; i < PHASE_1_PIPELINE_STAGES; i++) begin
                phase_1_pipe[i] <= '0;
            end

            ready_reg <= '1;

            id_out <= '0;
            current_vector[0] <= '0;
            current_vector[1] <= '0;
            current_vector[3] <= '0;
            current_vector[4] <= '0;
            current_vector[5] <= '0;
            current_vector[6] <= '0;
            current_vector[7] <= '0;

            linear_exponent_tmp <= '0;
            linear_exponent_independent_id_in_d1 <= '0;
            next_linear_exponent_independent_id_in_d1 <= '0;
            linear_exponent_valid <= '0;
            linear_exponent_independent_id_in <= '0;
            next_linear_exponent_independent_id_in <= '0;
            linear_exponent_done <= '0;

            cubic_exponent <= '0;
            cubic_exponent_valid <= '0;
            cubic_exponent_independent_id_in <= '0;
            cubic_exponent_done <= '0;

            result_base_two_exponential_cubic_vmem <= '0;
            result_base_two_exponential_linear_vmem <= '0;
            result_base_two_exponential_kp_vna <= '0;
            result_base_two_exponential_kp_vg <= '0;
            result_base_two_exponential_vna_offset <= '0;
            result_base_two_exponential_kp_vk <= '0;
            result_base_two_exponential_kp_vk_plus_vmem <= '0;
            result_base_two_exponential_vk <= '0;
            result_base_two_exponential_vna <= '0;
            result_base_two_exponential_vg <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 42------------------------------
            // ------------------------------PHASE 1 DRIVE AND SELECT-----------------------------
            // Drive the linear_exponent_valid pipeline
            for (int i = 1; i < 8; i ++) begin
                linear_exponent_valid[i] <= linear_exponent_valid[i-1];
            end   

            // Drive the cubic_exponent_valid pipeline
            cubic_exponent_valid[1] <= mul_kp_vk_valid_out;

            // Select linear_exponent from the captured neuron state
            if (valid_in || (|linear_exponent_valid && linear_exponent_independent_id_in != 3'd7)) begin
                case (next_linear_exponent_independent_id_in)
                    3'd0: begin
                        // STAGE 0
                        linear_exponent_tmp <= neuron_state_variables[0]; // Occurs on first clk cycle so use neuron_state_variables
                    end
                    3'd1: begin
                        // STAGE 1
                        linear_exponent_tmp <= phase_1_pipe[0].neuron_state_reg[3];
                    end
                    3'd2: begin
                        // STAGE 2
                        linear_exponent_tmp <= phase_1_pipe[1].neuron_state_reg[2];
                    end
                    3'd3: begin
                        // STAGE 3
                        linear_exponent_tmp <= phase_1_pipe[2].term_i3;
                    end
                    3'd4: begin
                        // STAGE 4
                        linear_exponent_tmp <= phase_1_pipe[3].neuron_state_reg[1];
                    end
                    3'd5: begin
                        // STAGE 5
                        linear_exponent_tmp <= phase_1_pipe[4].neuron_state_reg[1];
                    end
                    3'd6: begin
                        // STAGE 6
                        linear_exponent_tmp <= phase_1_pipe[5].neuron_state_reg[3];
                    end
                    3'd7: begin
                        // STAGE 7
                        linear_exponent_tmp <= phase_1_pipe[6].neuron_state_reg[2];
                    end
                endcase
            end 

            // Assign linear_exponent_independent_id_in and next_linear_exponent_independent_id_in
            if (valid_in) begin
                // STAGE 0
                linear_exponent_independent_id_in <= 3'd0;
                next_linear_exponent_independent_id_in <= 3'd1;
            end else if (|linear_exponent_valid && linear_exponent_independent_id_in != 3'd7) begin
                // STAGE 1 ONWARDS
                linear_exponent_independent_id_in <= next_linear_exponent_independent_id_in;
                next_linear_exponent_independent_id_in <= next_linear_exponent_independent_id_in + 3'd1;
            end  

            linear_exponent_independent_id_in_d1 <= linear_exponent_independent_id_in;
            next_linear_exponent_independent_id_in_d1 <= next_linear_exponent_independent_id_in;

            // Select cubic_exponent and cubic_exponent_independent_id_in
            if (valid_in) begin
                cubic_exponent <= neuron_state_variables[0];
                cubic_exponent_independent_id_in <= '0;
            end else if (mul_kp_vk_valid_out) begin
                cubic_exponent <= mul_kp_vk + phase_1_pipe[6].neuron_state_reg[0];
                cubic_exponent_independent_id_in <= '1;
            end

            // ------------------------------PHASE 1 STAGE 0 (FEED signed_32_32_multiplication_i2)------------------------------
            phase_1_pipe[0].valid <= valid_in;
            phase_1_pipe[0].current_input <= current_in;
            phase_1_pipe[0].id <= id_in;

            if (valid_in) begin
                ready_reg <= '0;
            end 

            for (int i = 0; i < 4; i++) begin
                phase_1_pipe[0].neuron_state_reg[i] <= neuron_state_variables[i];
            end

            phase_1_pipe[0].term_i3 <= -neuron_state_variables[3] - VNA_OFFSET_Q24;

            // Feed the linear_exponent_valid pipeline
            linear_exponent_valid[0] <= valid_in;

            // Feed the cubic_exponent_valid pipeline
            cubic_exponent_valid[0] <= valid_in;


            // ------------------------------PHASE 1 STAGE 0 (+1) to STAGE 0 (+26) (WAIT FOR signed_32_32_multiplication_i2 AND base_two_exponential_pipe_linear_i AND base_two_exponential_pipe_cubic_i)------------------------------
            for (int i = 1; i < PHASE_1_PIPELINE_STAGES; i++) begin
                phase_1_pipe[i].current_input <= phase_1_pipe[i-1].current_input;
                phase_1_pipe[i].id <= phase_1_pipe[i-1].id;
                phase_1_pipe[i].term_i3 <= phase_1_pipe[i-1].term_i3;

                if (i < 7) begin
                    phase_1_pipe[i].neuron_state_reg <= phase_1_pipe[i-1].neuron_state_reg;
                end
            end

            // ------------------------------PHASE 1 STAGE 1 (FEED signed_32_32_multiplication_i3)------------------------------
            phase_1_pipe[1].linear_exponent_independent_id <= next_linear_exponent_independent_id_in_d1;

            // ------------------------------PHASE 1 STAGE 1 (+1) to STAGE 1 (+6) (WAIT FOR signed_32_32_multiplication_i3)------------------------------
            for (int i = 2; i < 8; i++) begin
                phase_1_pipe[i].linear_exponent_independent_id <= phase_1_pipe[i-1].linear_exponent_independent_id;
            end

            // ------------------------------PHASE 1 RESULTS-----------------------------
            if (linear_exponent_valid_out) begin
                case (linear_exponent_independent_id_out)
                    3'd0: begin
                        result_base_two_exponential_linear_vmem <= linear_result_base_two_exponential;
                    end 
                    3'd1: begin
                        result_base_two_exponential_kp_vna <= linear_result_base_two_exponential;
                    end
                    3'd2: begin
                        result_base_two_exponential_kp_vg <= linear_result_base_two_exponential;
                    end
                    3'd3: begin
                        result_base_two_exponential_vna_offset <= linear_result_base_two_exponential;
                    end
                    3'd4: begin
                        result_base_two_exponential_kp_vk <= linear_result_base_two_exponential;
                    end
                    3'd5: begin
                        result_base_two_exponential_vk <= linear_result_base_two_exponential;
                    end
                    3'd6: begin
                        result_base_two_exponential_vna <= linear_result_base_two_exponential;
                    end
                    3'd7: begin
                        result_base_two_exponential_vg <= linear_result_base_two_exponential;
                    end
                endcase 
            end 

            if (cubic_exponent_valid_out) begin
                case (cubic_exponent_independent_id_out)
                    3'd0: begin
                        result_base_two_exponential_cubic_vmem <= cubic_result_base_two_exponential;
                    end 
                    3'd1: begin
                        result_base_two_exponential_kp_vk_plus_vmem <= cubic_result_base_two_exponential;
                    end
                endcase 
            end 

            if (linear_exponent_valid_out && (linear_exponent_independent_id_out == 3'd7)) begin
                linear_exponent_done <= '1;
            end 

            if (cubic_exponent_valid_out && (cubic_exponent_independent_id_out == 3'd1)) begin
                cubic_exponent_done <= '1;
            end 

            // ------------------------------PHASE 2 STAGE 0 (FEED signed_32_32_multiplication_i4 AND signed_32_32_multiplication_i5 AND signed_32_32_multiplication_i6 AND signed_32_32_multiplication_i7 AND signed_32_32_multiplication_i8)------------------------------
            if (linear_exponent_done && cubic_exponent_done) begin
                ready_reg <= '1;

                linear_exponent_done <= '0;
                cubic_exponent_done <= '0;
            end

            phase_2_pipe[0].id <= phase_1_pipe[PHASE_1_PIPELINE_STAGES-1].id;
            phase_2_pipe[0].phase_2_current_in_d <= phase_1_pipe[PHASE_1_PIPELINE_STAGES-1].current_input;
            phase_2_pipe[0].current_vector_3_data <= result_base_two_exponential_kp_vg;
            phase_2_pipe[0].current_vector_7_data <= result_base_two_exponential_vg - result_base_two_exponential_vna;
            phase_2_pipe[0].result_base_two_exponential_kp_vna <= result_base_two_exponential_kp_vna;
            phase_2_pipe[0].result_base_two_exponential_kp_vk_plus_vmem <= result_base_two_exponential_kp_vk_plus_vmem;

            // ------------------------------PHASE 2 STAGE 0 (+1) to STAGE 0 (+6) (WAIT FOR signed_32_32_multiplication_i4 AND signed_32_32_multiplication_i5 AND signed_32_32_multiplication_i6 AND signed_32_32_multiplication_i7 AND signed_32_32_multiplication_i8)------------------------------
            for (int i = 1; i < 7; i++) begin
                phase_2_pipe[i].id <= phase_2_pipe[i-1].id;
                phase_2_pipe[i].phase_2_current_in_d <= phase_2_pipe[i-1].phase_2_current_in_d;
                phase_2_pipe[i].current_vector_3_data <= phase_2_pipe[i-1].current_vector_3_data;
                phase_2_pipe[i].current_vector_7_data <= phase_2_pipe[i-1].current_vector_7_data;
                phase_2_pipe[i].result_base_two_exponential_kp_vna <= phase_2_pipe[i-1].result_base_two_exponential_kp_vna;
                phase_2_pipe[i].result_base_two_exponential_kp_vk_plus_vmem <= phase_2_pipe[i-1].result_base_two_exponential_kp_vk_plus_vmem;
            end

            // ------------------------------PHASE 2 STAGE 1-----------------------------
            phase_2_pipe[7].valid <= phase_2_multiplication_valid_out;
            phase_2_pipe[7].id <= phase_2_pipe[6].id;

            // current_vector[0]
            phase_2_pipe[7].phase_2_current_in_d <= phase_2_pipe[6].phase_2_current_in_d;

            // current_vector[1]
            phase_2_pipe[7].current_vector_1_data <= ONE_Q8 - current_vector_1_product;

            // current_vector[2]
            phase_2_pipe[7].current_vector_2_data <= ONE_Q8 - current_vector_2_product;
            phase_2_pipe[7].result_base_two_exponential_kp_vna <= phase_2_pipe[6].result_base_two_exponential_kp_vna;

            // current_vector[3]
            phase_2_pipe[7].current_vector_3_data <= phase_2_pipe[6].current_vector_3_data;

            // current_vector[4]
            phase_2_pipe[7].current_vector_4_data <= ONE_Q8 - current_vector_4_product;

            // current_vector[5]
            phase_2_pipe[7].current_vector_5_data <= phase_2_pipe[6].result_base_two_exponential_kp_vk_plus_vmem - current_vector_5_product;

            // current_vector[6]
            phase_2_pipe[7].current_vector_6_data <= ONE_Q8 - current_vector_6_product;

            // current_vector[7]
            phase_2_pipe[7].current_vector_7_data <= phase_2_pipe[6].current_vector_7_data;

            // ------------------------------PHASE 2 STAGE 2 (FEED signed_32_32_multiplication_i)------------------------------
            phase_2_pipe[8].id <= phase_2_pipe[7].id;

            // current_vector[0]
            phase_2_pipe[8].phase_2_current_in_d <= phase_2_pipe[7].phase_2_current_in_d;

            // current_vector[1]
            phase_2_pipe[8].current_vector_1_data <= phase_2_pipe[7].current_vector_1_data;

            // current_vector[3]
            phase_2_pipe[8].current_vector_3_data <= phase_2_pipe[7].current_vector_3_data;

            // current_vector[4]
            phase_2_pipe[8].current_vector_4_data <= phase_2_pipe[7].current_vector_4_data;

            // current_vector[5]
            phase_2_pipe[8].current_vector_5_data <= phase_2_pipe[7].current_vector_5_data;

            // current_vector[6]
            phase_2_pipe[8].current_vector_6_data <= phase_2_pipe[7].current_vector_6_data;

            // current_vector[7]
            phase_2_pipe[8].current_vector_7_data <= phase_2_pipe[7].current_vector_7_data;

            // ------------------------------PHASE 2 STAGE 2 (+1) to STAGE 2 (+6) (WAIT FOR signed_32_32_multiplication_i)------------------------------
            for (int i = 9; i < PHASE_2_PIPELINE_STAGES-1; i++) begin
                phase_2_pipe[i].id <= phase_2_pipe[i-1].id;
                phase_2_pipe[i].phase_2_current_in_d <= phase_2_pipe[i-1].phase_2_current_in_d;
                phase_2_pipe[i].current_vector_1_data <= phase_2_pipe[i-1].current_vector_1_data;
                phase_2_pipe[i].current_vector_3_data <= phase_2_pipe[i-1].current_vector_3_data;
                phase_2_pipe[i].current_vector_4_data <= phase_2_pipe[i-1].current_vector_4_data;
                phase_2_pipe[i].current_vector_5_data <= phase_2_pipe[i-1].current_vector_5_data;
                phase_2_pipe[i].current_vector_6_data <= phase_2_pipe[i-1].current_vector_6_data;
                phase_2_pipe[i].current_vector_7_data <= phase_2_pipe[i-1].current_vector_7_data;
            end

            id_out <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].id;
            current_vector[0] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].phase_2_current_in_d;
            current_vector[1] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_1_data;
            current_vector[3] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_3_data;
            current_vector[4] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_4_data;
            current_vector[5] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_5_data;
            current_vector[6] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_6_data;
            current_vector[7] <= phase_2_pipe[PHASE_2_PIPELINE_STAGES-2].current_vector_7_data;
        end
    end
endmodule
