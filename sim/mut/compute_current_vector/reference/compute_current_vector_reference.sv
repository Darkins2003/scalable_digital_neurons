// Original scalar implementation retained only as a simulation reference.
import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module compute_current_vector_reference(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input fixed_t current_in,
    input fixed_t neuron_state_variables [0:3],

    output logic valid_out,
    output fixed_t current_vector [0:7] 
);

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
    } phase_2_pipeline_t;

    localparam int PHASE_2_PIPELINE_STAGES = 2;
    phase_2_pipeline_t phase_2_pipe [0:PHASE_2_PIPELINE_STAGES-1];

    typedef struct packed {
        fixed_t current_input;
    } phase_1_pipeline_t;

    localparam int PHASE_1_PIPELINE_STAGES = 13;
    phase_1_pipeline_t phase_1_pipe [0:PHASE_1_PIPELINE_STAGES-1];

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

    // Phase 1
    logic [1:0] phase_1_valid_in_d;
    fixed_t neuron_state_snapshot [0:3];

    // Phase 1 linear exponential
    fixed_t linear_exponent;
    fixed_t linear_exponent_tmp;
    logic [7:0] linear_exponent_valid;
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

    base_two_exponential_pipe_linear base_two_exponential_linear_vg(
        .clk(clk),
        .rst(rst),

        .exponent(linear_exponent),
        .valid_in(|linear_exponent_valid),
        .independent_id_in(linear_exponent_independent_id_in),

        .valid_out(linear_exponent_valid_out),
        .independent_id_out(linear_exponent_independent_id_out),
        .result(linear_result_base_two_exponential)
    );

    base_two_exponential_pipe_cubic base_two_exponential_cubic_kp_vk_plus_vmem(
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

            current_vector <= '{default:'0};
            valid_out <= '0;

            phase_1_valid_in_d <= '0;
            neuron_state_snapshot <= '{default:'0};

            linear_exponent <= '0;
            linear_exponent_valid <= '0;
            linear_exponent_independent_id_in <= '0;
            next_linear_exponent_independent_id_in <= '0;
            linear_exponent_done <= '0;

            cubic_exponent <= '0;
            cubic_exponent_valid <= '0;
            cubic_exponent_independent_id_in <= '0;
            mul_kp_vk <= '0;
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

            result_base_two_exponential_kp_vk_plus_vmem_d1 <= '0;
            result_base_two_exponential_kp_vna_d1 <= '0;
            result_base_two_exponential_kp_vna_d2 <= '0;
        end else begin
            // ------------------------------PHASE 1 DRIVE AND SELECT-----------------------------
            for (int i = 1; i < PHASE_1_PIPELINE_STAGES; i++) begin
                phase_1_pipe[i].current_input <= phase_1_pipe[i-1].current_input;
            end

            // Drive the linear_exponent_valid pipeline
            for (int i = 1; i < 8; i ++) begin
                linear_exponent_valid[i] <= linear_exponent_valid[i-1];
            end   

            // Drive the cubic_exponent_valid pipeline
            cubic_exponent_valid[1] <= cubic_exponent_valid[0];

            // Select linear_exponent from the captured neuron state
            if (phase_1_valid_in_d[0] || (|linear_exponent_valid && linear_exponent_independent_id_in != 3'd7)) begin
                case (next_linear_exponent_independent_id_in)
                    3'd0: begin
                        linear_exponent_tmp = neuron_state_snapshot[0];
                    end
                    3'd1: begin
                        linear_exponent_tmp = neuron_state_snapshot[3];
                    end
                    3'd2: begin
                        linear_exponent_tmp = neuron_state_snapshot[2];
                    end
                    3'd3: begin
                        linear_exponent_tmp = -neuron_state_snapshot[3] - VNA_OFFSET_Q24;
                    end
                    3'd4: begin
                        linear_exponent_tmp = neuron_state_snapshot[1];
                    end
                    3'd5: begin
                        linear_exponent_tmp = neuron_state_snapshot[1];
                    end
                    3'd6: begin
                        linear_exponent_tmp = neuron_state_snapshot[3];
                    end
                    3'd7: begin
                        linear_exponent_tmp = neuron_state_snapshot[2];
                    end
                endcase

                if (next_linear_exponent_independent_id_in == 3'd1 || next_linear_exponent_independent_id_in == 3'd2 || next_linear_exponent_independent_id_in == 3'd4) begin
                    linear_exponent <= mul_24_24_24(KP, linear_exponent_tmp);
                end else begin
                    linear_exponent <= linear_exponent_tmp;
                end 
            end

            // Assign linear_exponent_independent_id_in and next_linear_exponent_independent_id_in
            if (phase_1_valid_in_d[0]) begin
                linear_exponent_independent_id_in <= 3'd0;
                next_linear_exponent_independent_id_in <= 3'd1;
            end else if (|linear_exponent_valid && linear_exponent_independent_id_in != 3'd7) begin
                linear_exponent_independent_id_in <= next_linear_exponent_independent_id_in;
                next_linear_exponent_independent_id_in <= next_linear_exponent_independent_id_in + 3'd1;
            end  

            // Select cubic_exponent and cubic_exponent_independent_id_in
            if (phase_1_valid_in_d[1]) begin
                cubic_exponent <= neuron_state_snapshot[0];
                cubic_exponent_independent_id_in <= '0;
            end else if (cubic_exponent_valid[0]) begin
                cubic_exponent <= mul_kp_vk + neuron_state_snapshot[0];
                cubic_exponent_independent_id_in <= '1;
            end

            // ------------------------------PHASE 1 STAGE 0-----------------------------
            phase_1_valid_in_d[0] <= valid_in;
            phase_1_pipe[0].current_input <= current_in;

            if (valid_in) begin
                neuron_state_snapshot <= neuron_state_variables;
            end 

            // ------------------------------PHASE 1 STAGE 1-----------------------------
            phase_1_valid_in_d[1] <= phase_1_valid_in_d[0];

            mul_kp_vk <= mul_24_24_24(KP, neuron_state_snapshot[1]);

            // Feed the linear_exponent_valid pipeline
            linear_exponent_valid[0] <= phase_1_valid_in_d[0];

            // ------------------------------PHASE 1 STAGE 2-----------------------------
            // Feed the cubic_exponent_valid pipeline
            cubic_exponent_valid[0] <= phase_1_valid_in_d[1];

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

            // ------------------------------PHASE 2 STAGE 0-----------------------------
            if (linear_exponent_done && cubic_exponent_done) begin
                phase_2_pipe[0].valid <= '1;
                
                linear_exponent_done <= '0;
                cubic_exponent_done <= '0;
            end else begin
                phase_2_pipe[0].valid <= '0;
            end 

            // current_vector[0]
            phase_2_pipe[0].phase_2_current_in_d <= phase_1_pipe[PHASE_1_PIPELINE_STAGES-1].current_input;

            // current_vector[1]
            phase_2_pipe[0].current_vector_1_data <= mul_24_8_8(EXPMEL, result_base_two_exponential_cubic_vmem);

            // current_vector[2]
            phase_2_pipe[0].current_vector_2_data <= mul_24_8_8(EXPVNA, result_base_two_exponential_linear_vmem);
            result_base_two_exponential_kp_vna_d1 <= result_base_two_exponential_kp_vna;

            // current_vector[3]
            phase_2_pipe[0].current_vector_3_data <= result_base_two_exponential_kp_vg;

            // current_vector[4]
            phase_2_pipe[0].current_vector_4_data <= mul_24_8_8(EXPVSAT, result_base_two_exponential_vna_offset);

            // current_vector[5]
            phase_2_pipe[0].current_vector_5_data <= mul_24_8_8(EXPEK, result_base_two_exponential_kp_vk);
            result_base_two_exponential_kp_vk_plus_vmem_d1 <= result_base_two_exponential_kp_vk_plus_vmem;

            // current_vector[6]
            phase_2_pipe[0].current_vector_6_data <= mul_24_8_8(EXPMVGK, result_base_two_exponential_vk);

            // current_vector[7]
            phase_2_pipe[0].current_vector_7_data <= result_base_two_exponential_vg - result_base_two_exponential_vna;
            // ------------------------------PHASE 2 STAGE 1-----------------------------
            phase_2_pipe[1].valid <= phase_2_pipe[0].valid;

            // current_vector[0]
            phase_2_pipe[1].phase_2_current_in_d <= phase_2_pipe[0].phase_2_current_in_d;

            // current_vector[1]
            phase_2_pipe[1].current_vector_1_data <= ONE_Q8 - phase_2_pipe[0].current_vector_1_data;

            // current_vector[2]
            phase_2_pipe[1].current_vector_2_data <= ONE_Q8 - phase_2_pipe[0].current_vector_2_data;
            result_base_two_exponential_kp_vna_d2 <= result_base_two_exponential_kp_vna_d1;

            // current_vector[3]
            phase_2_pipe[1].current_vector_3_data <= phase_2_pipe[0].current_vector_3_data;

            // current_vector[4]
            phase_2_pipe[1].current_vector_4_data <= ONE_Q8 - phase_2_pipe[0].current_vector_4_data;

            // current_vector[5]
            phase_2_pipe[1].current_vector_5_data <= result_base_two_exponential_kp_vk_plus_vmem_d1 - phase_2_pipe[0].current_vector_5_data;

            // current_vector[6]
            phase_2_pipe[1].current_vector_6_data <= ONE_Q8 - phase_2_pipe[0].current_vector_6_data;

            // current_vector[6]
            phase_2_pipe[1].current_vector_7_data <= phase_2_pipe[0].current_vector_7_data;

            // ------------------------------PHASE 2 OUTPUT-----------------------------
            valid_out <= phase_2_pipe[1].valid;

            // current_vector[0]
            current_vector[0] <= phase_2_pipe[1].phase_2_current_in_d;

            // current_vector[1]
            current_vector[1] <= phase_2_pipe[1].current_vector_1_data;

            // current_vector[2]
            current_vector[2] <= mul_8_8_8(phase_2_pipe[1].current_vector_2_data, result_base_two_exponential_kp_vna_d2);

            // current_vector[3]
            current_vector[3] <= phase_2_pipe[1].current_vector_3_data;

            // current_vector[4]
            current_vector[4] <= phase_2_pipe[1].current_vector_4_data;

            // current_vector[5]
            current_vector[5] <= phase_2_pipe[1].current_vector_5_data;

            // current_vector[6]
            current_vector[6] <= phase_2_pipe[1].current_vector_6_data;

            // current_vector[7]
            current_vector[7] <= phase_2_pipe[1].current_vector_7_data;
        end 
    end 
endmodule
