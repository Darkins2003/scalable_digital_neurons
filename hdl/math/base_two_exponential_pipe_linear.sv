import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential_pipe_linear (
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,

    output logic valid_out,
    output fixed_t result
);

    import neuron_params_generated_pkg::*;
    import neuron_params_pkg::*;
    import fixed_point_package::*;

    logic valid [0:4];

    fixed_t frac_exponent;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent;
    fixed_t frac_exponent_plus_one;
    fixed_t two_to_pwr_int_exponent;

    fixed_t result_d [0:2];

    always_ff @(posedge clk) begin
        if (rst) begin
            result_d <= '{default:'0}; 
            valid <= '{default:'0};
            frac_exponent <= '0;
            int_exponent <= '0;
            frac_exponent_plus_one <= '0;
            two_to_pwr_int_exponent <= '0;

            result <= 0; 
            valid_out <= '0;
        end else begin
            // ------------------------------STAGE 0------------------------------
            // Feed the pipeline
            valid[0] <= valid_in;
            frac_exponent <= {8'b0, exponent[STATE_FRAC_BITS-1:0]};
            int_exponent  <= exponent[VALUE_WIDTH-1:STATE_FRAC_BITS];

            // ------------------------------STAGE 1------------------------------
            // Drive the pipeline
            valid[1] <= valid[0];

            // 2 ^ N(int)
            if (int_exponent < -8'sd6) begin
                two_to_pwr_int_exponent <= 32'sb0;
            end else if (int_exponent[7] == 1'b0) begin
                // positive signed
                two_to_pwr_int_exponent <= ONE_Q8 <<< int_exponent;
            end else begin
                // negative signed
                two_to_pwr_int_exponent <= ONE_Q8 >>> (-int_exponent);
            end 

            frac_exponent_plus_one <= frac_exponent + ONE_Q24;

            // ------------------------------STAGE 2------------------------------
            // Drive the pipeline
            valid[2] <= valid[1];
            result_d[0] <= mul_24_8_8(frac_exponent_plus_one, two_to_pwr_int_exponent);

            // ------------------------------STAGE 3------------------------------
            // Drive the pipeline
            valid[3] <= valid[2];
            result_d[1] <= result_d[0]; 

            // ------------------------------STAGE 4------------------------------
            // Drive the pipeline
            valid[4] <= valid[3];
            result_d[2] <= result_d[1];

            // ------------------------------STAGE 5------------------------------
            // Drive the pipeline
            valid_out <= valid[4];
            result <= result_d[2];
            
        end 
    end

endmodule