import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module single_neuron (
    input logic clk,
    input logic rst,

    input fixed_t current_in,
    output fixed_t vmem_out
);

    fixed_t neuron_state_variables [0:3] = INITIAL_STATE;
    fixed_t current_vector [0:7];
    fixed_t transformation_matrix [0:3][0:7];

    typedef struct packed {
        fixed_t current_vector_1;
        logic valid;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 3;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    logic valid_in;
    logic valid_out;

    assign valid_in = 1'b1; //TEMPORARY

    base_two_exponential_pipe i_one(
        .clk(clk),
        .rst(rst),
        .exponent(neuron_state_variables[0]),
        .valid_in(valid_in),

        .valid_out(valid_out),
        .result(pipe[0].current_vector_1)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            neuron_state_variables <= INITIAL_STATE;

            for (int i=0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end 

            current_vector[1] <= '{default:'0};

        end else begin
            // ------------------------------STAGE 0-----------------------------
            pipe[1].valid <= valid_out;

            if (valid_out) begin
                pipe[1].current_vector_1 <= mul_24_8_8(EXPMEL, pipe[0].current_vector_1);
            end 

            // ------------------------------STAGE 1-----------------------------
            if (pipe[1].valid) begin
                pipe[2].valid <= pipe[1].valid;
                current_vector[1] <= ONE_Q8 - pipe[1].current_vector_1;
            end 
        end 
    end

    assign vmem_out = current_vector[1]; // temp

endmodule