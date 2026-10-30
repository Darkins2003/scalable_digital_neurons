// Reliable results for int_exponent = - 6 to +22 (represented using 6 bits)

import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential_pipe_linear (
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,
    input logic [2:0] independent_id_in,

    output fixed_t result = '0,
    output logic valid_out = '0,
    output logic [2:0] independent_id_out = '0
);

    import neuron_params_generated_pkg::*;
    import neuron_params_pkg::*;
    import fixed_point_package::*;

    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent_reg = '0;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent_reg_d = '0;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] negative_int_exponent = '0;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] negative_int_exponent_delayed = '0;
    fixed_t frac_exponent_plus_one = '0;

    logic result_is_zero = '0;
    logic positive_signed_exponent = '0;

    logic signed [63:0] left_shifted_partial_result = '0;
    logic signed [63:0] right_shifted_partial_result = '0;

    logic signed [63:0] left_shifted_result = '0;
    logic signed [63:0] right_shifted_result = '0;

    logic [2:0] valid_pipeline = '0;
    logic [2:0] independent_id_pipe [0:2] = '{default:'0};

    always_ff @(posedge clk) begin
        if (rst) begin
            int_exponent <= '0;
            int_exponent_reg <= '0;
            int_exponent_reg_d <= '0;
            negative_int_exponent <= '0;
            negative_int_exponent_delayed <= '0;
            frac_exponent_plus_one <= '0;

            result_is_zero <= '0;
            positive_signed_exponent <= '0;

            left_shifted_partial_result <= '0;
            right_shifted_partial_result <= '0;

            left_shifted_result <= '0;
            right_shifted_result <= '0;

            valid_pipeline <= '0;
            independent_id_pipe <= '{default:'0};
            valid_out <= '0;
            independent_id_out <= '0;

            result <= '0;
        end else begin
            // ------------------------------TOTAL STAGES = 4------------------------------
            // ------------------------------STAGE 0------------------------------
            valid_pipeline[0] <= valid_in;
            independent_id_pipe[0] <= independent_id_in;

            int_exponent = exponent[VALUE_WIDTH-1:STATE_FRAC_BITS]; // Bit select is from a constant, therefore this is wiring
            int_exponent_reg <= int_exponent;

            frac_exponent_plus_one <= {7'b0, 1'b1, exponent[STATE_FRAC_BITS-1:0]}; // {8'b0, exponent[STATE_FRAC_BITS-1:0]} + ONE_Q24. Bit selects are from constants, therefore this is wiring

            negative_int_exponent <= -int_exponent;

            // ------------------------------STAGE 1------------------------------
            valid_pipeline[1] <= valid_pipeline[0];
            independent_id_pipe[1] <= independent_id_pipe[0]; 

            int_exponent_reg_d <= int_exponent_reg;
            negative_int_exponent_delayed <= negative_int_exponent;

            // frac_exponent_plus_one x two_to_pwr_int_exponent (for +ve and -ve int_exponent)
            // Performed in 2 stages to reduce levels of logic per stage. Only look at the 6 LSBs when applying shifts as this is our reliable range (int_exponent = -31 to +32)
            // First stage of shift:
            left_shifted_partial_result <= frac_exponent_plus_one <<< int_exponent_reg[2:0];
            right_shifted_partial_result <= frac_exponent_plus_one >>> negative_int_exponent[2:0];

            // ------------------------------STAGE 2------------------------------
            valid_pipeline[2] <= valid_pipeline[1];
            independent_id_pipe[2] <= independent_id_pipe[1];

            // Second stage of shift
            left_shifted_result <= left_shifted_partial_result <<< {int_exponent_reg_d[5:3], 3'b000}; // Only looking at 6 LSBs when shifting (excluding signed bit)
            right_shifted_result <= right_shifted_partial_result >>> {negative_int_exponent_delayed[5:3], 3'b000}; // Only looking at 6 LSBs when shifting (excluding signed bit)

            if ((int_exponent_reg_d < -8'sd6)) begin
                result_is_zero <= '1;
                positive_signed_exponent <= '0;
            end else if (int_exponent_reg_d[7] == 1'b0) begin
                // positive signed
                positive_signed_exponent <= '1; 
                result_is_zero <= '0;
            end else begin
                // negative signed
                positive_signed_exponent <= '0; 
                result_is_zero <= '0;
            end 

            // ------------------------------STAGE 3------------------------------
            valid_out <= valid_pipeline[2];
            independent_id_out <= independent_id_pipe[2];

            // Result (8 frac bits) = frac_exponent_plus_one (24 frac bits) x two_to_pwr_int_exponent(8 frac bits)
            if (result_is_zero) begin
                result <= 32'sd0;
            end else if (positive_signed_exponent) begin
                result <= fixed_t'(left_shifted_result >>> 16); // Convert 64b 24 frac bits to 32b 8 frac bits
            end else begin
                result <= fixed_t'(right_shifted_result >>> 16); // Convert 64b 24 frac bits to 32b 8 frac bits
            end 
            
        end 
    end

endmodule
