import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module compute_current_vector #(
    parameter bit USE_DSP_MULTIPLIERS = 1'b1,
    parameter bit USE_BRAM_EXPONENTIAL = 1'b1
)(
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
        logic [2:0] exponent_independent_id;
        logic valid;
        logic [1:0] id;
    } phase_1_pipeline_t;

    localparam int PHASE_1_PIPELINE_STAGES = 19;
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
    fixed_t result_base_two_exponential_vmem;
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
    logic exponent_multiplication_valid_out;
    logic mul_kp_vk_valid_out;

    // Phase 1 exponential
    fixed_t exponent;
    fixed_t selected_exponent;
    fixed_t exponent_temporary;
    logic [7:0] exponent_valid;
    logic [2:0] exponent_independent_id_in_d1;
    logic [2:0] next_exponent_independent_id_in_d1;
    logic [2:0] exponent_independent_id_in = '0;
    logic [2:0] next_exponent_independent_id_in = '0;
    logic [2:0] exponent_independent_id_out;
    logic exponent_valid_out;
    fixed_t result_base_two_exponential;
    logic exponent_done;

    fixed_t combined_exponent;
    logic [2:0] membrane_exponent_valid;
    fixed_t mul_kp_vk;

    logic ready_reg = '1;

    assign ready = ready_reg;

    function automatic fixed_t select_exponent(input logic membrane_request_valid, input fixed_t membrane_exponent, input logic [2:0] exponent_identifier, input fixed_t combined_exponent_value, input fixed_t multiplied_exponent);
        if (membrane_request_valid) begin
            select_exponent = membrane_exponent;
        end else if (exponent_identifier == 3'd0) begin
            select_exponent = combined_exponent_value;
        end else begin
            select_exponent = multiplied_exponent;
        end
    endfunction

    assign selected_exponent = select_exponent(phase_1_pipe[0].valid, phase_1_pipe[0].neuron_state_reg[0], phase_1_pipe[7].exponent_independent_id, combined_exponent, exponent);

    // ------------------------------PHASE 2 STAGE 2 to STAGE 2 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
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
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
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
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i3 (
        .clk(clk),
        .rst(rst),

        .term_1((next_exponent_independent_id_in_d1 == 3'd1 || next_exponent_independent_id_in_d1 == 3'd2 || next_exponent_independent_id_in_d1 == 3'd4) ? KP : ONE_Q24),
        .term_2(exponent_temporary),
        .valid_in(phase_1_pipe[0].valid || (|exponent_valid && exponent_independent_id_in_d1 != 3'd7)),

        .result(exponent),
        .valid_out(exponent_multiplication_valid_out)
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i4 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPMEL),
        .term_2(result_base_two_exponential_vmem),
        .valid_in(exponent_done),

        .result(current_vector_1_product),
        .valid_out(phase_2_multiplication_valid_out)
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i5 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPVNA),
        .term_2(result_base_two_exponential_vmem),
        .valid_in(exponent_done),

        .result(current_vector_2_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i6 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPVSAT),
        .term_2(result_base_two_exponential_vna_offset),
        .valid_in(exponent_done),

        .result(current_vector_4_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i7 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPEK),
        .term_2(result_base_two_exponential_kp_vk),
        .valid_in(exponent_done),

        .result(current_vector_5_product),
        .valid_out()
    );

    // ------------------------------PHASE 2 STAGE 0 to STAGE 0 (+6)------------------------------
    signed_32_32_multiplication #(
        .USE_DSP_MULTIPLIERS(USE_DSP_MULTIPLIERS),
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i8 (
        .clk(clk),
        .rst(rst),

        .term_1(EXPMVGK),
        .term_2(result_base_two_exponential_vk),
        .valid_in(exponent_done),

        .result(current_vector_6_product),
        .valid_out()
    );

    // ------------------------------PHASE 1 STAGE 2 to STAGE 2 (+2)------------------------------
    base_two_exponential #(
        .USE_BRAM_EXPONENTIAL(USE_BRAM_EXPONENTIAL)
    ) base_two_exponential_i(
        .clk(clk),
        .rst(rst),

        .exponent(selected_exponent),
        .valid_in(phase_1_pipe[0].valid || exponent_multiplication_valid_out),
        .independent_id_in(phase_1_pipe[7].exponent_independent_id),

        .valid_out(exponent_valid_out),
        .independent_id_out(exponent_independent_id_out),
        .result(result_base_two_exponential)
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

            exponent_temporary <= '0;
            exponent_independent_id_in_d1 <= '0;
            next_exponent_independent_id_in_d1 <= '0;
            exponent_valid <= '0;
            exponent_independent_id_in <= '0;
            next_exponent_independent_id_in <= '0;
            exponent_done <= '0;

            combined_exponent <= '0;
            membrane_exponent_valid <= '0;

            result_base_two_exponential_vmem <= '0;
            result_base_two_exponential_kp_vna <= '0;
            result_base_two_exponential_kp_vg <= '0;
            result_base_two_exponential_vna_offset <= '0;
            result_base_two_exponential_kp_vk <= '0;
            result_base_two_exponential_kp_vk_plus_vmem <= '0;
            result_base_two_exponential_vk <= '0;
            result_base_two_exponential_vna <= '0;
            result_base_two_exponential_vg <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 34------------------------------
            // ------------------------------PHASE 1 DRIVE AND SELECT-----------------------------
            // Drive the exponent_valid pipeline
            for (int i = 1; i < 8; i ++) begin
                exponent_valid[i] <= exponent_valid[i-1];
            end   

            // Drive the membrane_exponent_valid pipeline
            for (int i = 1; i < 3; i++) begin
                membrane_exponent_valid[i] <= membrane_exponent_valid[i-1];
            end

            // Select exponent from the captured neuron state
            if (valid_in || (|exponent_valid && exponent_independent_id_in != 3'd7)) begin
                case (next_exponent_independent_id_in)
                    3'd0: begin
                        // STAGE 0
                        exponent_temporary <= neuron_state_variables[0]; // Occurs on first clk cycle so use neuron_state_variables
                    end
                    3'd1: begin
                        // STAGE 1
                        exponent_temporary <= phase_1_pipe[0].neuron_state_reg[3];
                    end
                    3'd2: begin
                        // STAGE 2
                        exponent_temporary <= phase_1_pipe[1].neuron_state_reg[2];
                    end
                    3'd3: begin
                        // STAGE 3
                        exponent_temporary <= phase_1_pipe[2].term_i3;
                    end
                    3'd4: begin
                        // STAGE 4
                        exponent_temporary <= phase_1_pipe[3].neuron_state_reg[1];
                    end
                    3'd5: begin
                        // STAGE 5
                        exponent_temporary <= phase_1_pipe[4].neuron_state_reg[1];
                    end
                    3'd6: begin
                        // STAGE 6
                        exponent_temporary <= phase_1_pipe[5].neuron_state_reg[3];
                    end
                    3'd7: begin
                        // STAGE 7
                        exponent_temporary <= phase_1_pipe[6].neuron_state_reg[2];
                    end
                endcase
            end 

            // Assign exponent_independent_id_in and next_exponent_independent_id_in
            if (valid_in) begin
                // STAGE 0
                exponent_independent_id_in <= 3'd0;
                next_exponent_independent_id_in <= 3'd1;
            end else if (|exponent_valid && exponent_independent_id_in != 3'd7) begin
                // STAGE 1 ONWARDS
                exponent_independent_id_in <= next_exponent_independent_id_in;
                next_exponent_independent_id_in <= next_exponent_independent_id_in + 3'd1;
            end  

            exponent_independent_id_in_d1 <= exponent_independent_id_in;
            next_exponent_independent_id_in_d1 <= next_exponent_independent_id_in;

            // Select combined_exponent
            if (mul_kp_vk_valid_out) begin
                combined_exponent <= mul_kp_vk + phase_1_pipe[6].neuron_state_reg[0];
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

            // Feed the exponent_valid pipeline
            exponent_valid[0] <= valid_in;

            // Feed the membrane_exponent_valid pipeline
            membrane_exponent_valid[0] <= phase_1_pipe[0].valid;


            // ------------------------------PHASE 1 STAGE 0 (+1) to STAGE 0 (+18) (WAIT FOR signed_32_32_multiplication_i2 AND base_two_exponential_i)------------------------------
            for (int i = 1; i < PHASE_1_PIPELINE_STAGES; i++) begin
                phase_1_pipe[i].current_input <= phase_1_pipe[i-1].current_input;
                phase_1_pipe[i].id <= phase_1_pipe[i-1].id;
                phase_1_pipe[i].term_i3 <= phase_1_pipe[i-1].term_i3;

                if (i < 7) begin
                    phase_1_pipe[i].neuron_state_reg <= phase_1_pipe[i-1].neuron_state_reg;
                end
            end

            // ------------------------------PHASE 1 STAGE 1 (FEED signed_32_32_multiplication_i3)------------------------------
            phase_1_pipe[1].exponent_independent_id <= next_exponent_independent_id_in_d1;

            // ------------------------------PHASE 1 STAGE 1 (+1) to STAGE 1 (+6) (WAIT FOR signed_32_32_multiplication_i3)------------------------------
            for (int i = 2; i < 8; i++) begin
                phase_1_pipe[i].exponent_independent_id <= phase_1_pipe[i-1].exponent_independent_id;
            end

            // ------------------------------PHASE 1 RESULTS-----------------------------
            if (exponent_valid_out && membrane_exponent_valid[2]) begin
                result_base_two_exponential_vmem <= result_base_two_exponential;
            end else if (exponent_valid_out) begin
                case (exponent_independent_id_out)
                    3'd0: begin
                        result_base_two_exponential_kp_vk_plus_vmem <= result_base_two_exponential;
                    end 
                    3'd1: begin
                        result_base_two_exponential_kp_vna <= result_base_two_exponential;
                    end
                    3'd2: begin
                        result_base_two_exponential_kp_vg <= result_base_two_exponential;
                    end
                    3'd3: begin
                        result_base_two_exponential_vna_offset <= result_base_two_exponential;
                    end
                    3'd4: begin
                        result_base_two_exponential_kp_vk <= result_base_two_exponential;
                    end
                    3'd5: begin
                        result_base_two_exponential_vk <= result_base_two_exponential;
                    end
                    3'd6: begin
                        result_base_two_exponential_vna <= result_base_two_exponential;
                    end
                    3'd7: begin
                        result_base_two_exponential_vg <= result_base_two_exponential;
                    end
                endcase 
            end 

            if (exponent_valid_out && !membrane_exponent_valid[2] && (exponent_independent_id_out == 3'd7)) begin
                exponent_done <= '1;
            end 

            // ------------------------------PHASE 2 STAGE 0 (FEED signed_32_32_multiplication_i4 AND signed_32_32_multiplication_i5 AND signed_32_32_multiplication_i6 AND signed_32_32_multiplication_i7 AND signed_32_32_multiplication_i8)------------------------------
            if (exponent_done) begin
                ready_reg <= '1;

                exponent_done <= '0;
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
