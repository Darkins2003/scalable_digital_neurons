import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module single_neuron (
    input logic clk,
    input logic rst,

    input fixed_t current_in,

    output logic step_ready,
    output logic step_done,
    output fixed_t vmem_out
);

    fixed_t neuron_state_variables [0:3] = INITIAL_STATE;
    fixed_t current_vector [0:7];
    fixed_t mul_dy_dt_dt [0:3];

    logic valid_in;
    logic compute_current_vector_valid_out;
    logic matrix_mul_and_euler_update_valid_out;

    assign valid_in = step_ready & !rst; 
    assign vmem_out = neuron_state_variables[0];

    compute_current_vector compute_current_vector_i(
        .clk(clk),
        .rst(rst),

        .valid_in(valid_in),
        .current_in(current_in),
        .neuron_state_variables(neuron_state_variables),

        .valid_out(compute_current_vector_valid_out),
        .current_vector(current_vector)
    );

    matrix_mul_and_euler_update matrix_mul_and_euler_update_i(
        .clk(clk),
        .rst(rst),

        .valid_in(compute_current_vector_valid_out),
        .current_vector(current_vector),

        .valid_out(matrix_mul_and_euler_update_valid_out),
        .mul_dy_dt_dt(mul_dy_dt_dt)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            neuron_state_variables <= INITIAL_STATE;
            step_ready <= '1;
            step_done <= '0;

        end else begin
            // ------------------------------EULER UPDATE-----------------------------
            if (matrix_mul_and_euler_update_valid_out) begin
                step_ready <= '1;
                step_done <= '1;

                for (int i = 0; i < 4; i++) begin
                    neuron_state_variables[i] <= neuron_state_variables[i] + mul_dy_dt_dt[i];
                end 
            end else begin
                step_ready <= '0;
                step_done <= '0;
            end 

        end 
    end

endmodule
