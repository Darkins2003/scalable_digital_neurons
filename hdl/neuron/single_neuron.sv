import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module single_neuron (
    input logic clk,
    input logic rst,

    input fixed_t current_in,
    input logic valid_in,
    input logic [1:0] id_in,

    output logic ready,
    output logic valid_out,
    output logic [1:0] id_out,
    output fixed_t vmem_out,
    output fixed_t vmem_out_previous
);

    fixed_t neuron_state_variables [0:3][0:2] = '{
        '{default:INITIAL_STATE[0]},
        '{default:INITIAL_STATE[1]},
        '{default:INITIAL_STATE[2]},
        '{default:INITIAL_STATE[3]}
    };

    fixed_t current_vector [0:7];
    fixed_t mul_dy_dt_dt [0:3];

    fixed_t vmem_out_previous_reg [0:2] = '{default:INITIAL_STATE[0]};

    logic compute_current_vector_valid_out;
    logic matrix_mul_and_euler_update_valid_out;

    logic [1:0] matrix_mul_and_euler_update_id_out;
    logic [1:0] compute_current_vector_id_out;

    assign vmem_out = neuron_state_variables[0][id_out];
    assign vmem_out_previous = vmem_out_previous_reg[id_out];

    compute_current_vector compute_current_vector_i(
        .clk(clk),
        .rst(rst),

        .valid_in(valid_in),
        .id_in(id_in),
        .current_in(current_in),
        .neuron_state_variables('{neuron_state_variables[0][id_in], neuron_state_variables[1][id_in], neuron_state_variables[2][id_in], neuron_state_variables[3][id_in]}),

        .ready(ready),
        .id_out(compute_current_vector_id_out),
        .valid_out(compute_current_vector_valid_out),
        .current_vector(current_vector)
    );

    matrix_mul_and_euler_update matrix_mul_and_euler_update_i(
        .clk(clk),
        .rst(rst),

        .valid_in(compute_current_vector_valid_out),
        .id_in(compute_current_vector_id_out),
        .current_vector(current_vector),

        .id_out(matrix_mul_and_euler_update_id_out),
        .valid_out(matrix_mul_and_euler_update_valid_out),
        .mul_dy_dt_dt(mul_dy_dt_dt)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            neuron_state_variables <= '{
                '{default:INITIAL_STATE[0]},
                '{default:INITIAL_STATE[1]},
                '{default:INITIAL_STATE[2]},
                '{default:INITIAL_STATE[3]}
            };

            vmem_out_previous_reg <= '{default:INITIAL_STATE[0]};
            id_out <= '0;
            valid_out <= '0;

        end else begin
            // ------------------------------EULER UPDATE-----------------------------
            valid_out <= matrix_mul_and_euler_update_valid_out;
            id_out <= matrix_mul_and_euler_update_id_out;

            if (matrix_mul_and_euler_update_valid_out) begin
                vmem_out_previous_reg[matrix_mul_and_euler_update_id_out] <= neuron_state_variables[0][matrix_mul_and_euler_update_id_out]; // Store the previous vmem for the triangular generator input

                for (int i = 0; i < 4; i++) begin
                    neuron_state_variables[i][matrix_mul_and_euler_update_id_out] <= neuron_state_variables[i][matrix_mul_and_euler_update_id_out] + mul_dy_dt_dt[i];
                end 
            end 
        end 
    end

endmodule
