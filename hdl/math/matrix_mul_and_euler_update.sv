import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module matrix_mul_and_euler_update(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic [1:0] id_in,
    input fixed_t current_vector [0:7],

    output logic [1:0] id_out,
    output logic valid_out,
    output fixed_t mul_dy_dt_dt [0:3]
);

    logic valid [3:0];

    fixed_t products [0:3][0:7];
    fixed_t layer_one_sums [0:3][0:3];
    fixed_t layer_two_sums [0:3][0:1];

    fixed_t dy_dt [0:3];

    logic [1:0] id [0:3];

    always_ff @(posedge clk) begin
        if (rst) begin
            products <= '{default:'0};
            layer_one_sums <= '{default:'0};
            layer_two_sums <= '{default:'0};
            dy_dt <= '{default:'0};
            mul_dy_dt_dt <= '{default:'0};
            valid <= '{default:'0};
            id <= '{default:'0};
            id_out <= '0;
            valid_out <= '0;

        end else begin
            // ------------------------------STAGE 0-----------------------------
            valid[0] <= valid_in;
            id[0] <= id_in;

            for (int i = 0; i < 4; i++) begin
                for (int j = 0; j < 8; j++) begin
                    products[i][j] <= mul_23_8_8(NEURON_MATRIX[i][j], current_vector[j]);
                end 
            end 

            // ------------------------------STAGE 1-----------------------------
            valid[1] <= valid[0];
            id[1] <= id[0];

            for (int i = 0; i < 4; i++) begin
                for (int j = 0; j < 4; j++) begin
                    layer_one_sums[i][j] <= products[i][2*j] + products[i][2*j+1];
                end 
            end 

            // ------------------------------STAGE 2-----------------------------
            valid[2] <= valid[1];
            id[2] <= id[1];

            for (int i = 0; i < 4; i++) begin
                for (int j = 0; j < 2; j++) begin
                    layer_two_sums[i][j] <= layer_one_sums[i][2*j] + layer_one_sums[i][2*j+1];
                end 
            end 

            // ------------------------------STAGE 3-----------------------------
            valid[3] <= valid[2];
            id[3] <= id[2];

            for (int i = 0; i < 4; i++) begin
                dy_dt[i] <= layer_two_sums[i][0] + layer_two_sums[i][1];
            end 

            // ------------------------------STAGE 4 (Euler update)-----------------------------
            valid_out <= valid[3];
            id_out <= id[3];

            for (int i = 0; i < 4; i++) begin
                mul_dy_dt_dt[i] <= mul_24_8_24(DT, dy_dt[i]);
            end 

        end 
    end 
endmodule
