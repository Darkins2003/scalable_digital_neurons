import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential_pipe_linear (
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,
    input logic [2:0] id_in,

    output fixed_t result,
    output logic valid_out,
    output logic [2:0] id_out
);

    import neuron_params_generated_pkg::*;
    import neuron_params_pkg::*;
    import fixed_point_package::*;

    fixed_t frac_exponent;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent;
    fixed_t frac_exponent_plus_one;
    fixed_t two_to_pwr_int_exponent;

    logic [1:0] valid_pipeline;
    logic [2:0] id_pipe [0:1];

    always_ff @(posedge clk) begin
        if (rst) begin
            frac_exponent <= '0;
            int_exponent <= '0;
            frac_exponent_plus_one <= '0;
            two_to_pwr_int_exponent <= '0;

            valid_pipeline <= '0;
            id_pipe <= '{default:'0};
            valid_out <= '0;
            id_out <= '0;

            result <= 0;
        end else begin
            // ------------------------------STAGE 0------------------------------
            // Feed the pipeline
            frac_exponent <= {8'b0, exponent[STATE_FRAC_BITS-1:0]};
            int_exponent  <= exponent[VALUE_WIDTH-1:STATE_FRAC_BITS];

            valid_pipeline[0] <= valid_in;
            id_pipe[0] <= id_in;

            // ------------------------------STAGE 1------------------------------
            // Drive the pipeline

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

            valid_pipeline[1] <= valid_pipeline[0];
            id_pipe[1] <= id_pipe[0];

            // ------------------------------STAGE 2------------------------------
            // Drive the pipeline
            result <= mul_24_8_8(frac_exponent_plus_one, two_to_pwr_int_exponent);
            valid_out <= valid_pipeline[1];
            id_out <= id_pipe[1];
            
        end 
    end

endmodule
