import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential_pipe_cubic (
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,
    input logic id_in,

    output fixed_t result,
    output logic valid_out,
    output logic id_out
);

    import neuron_params_generated_pkg::*;
    import neuron_params_pkg::*;
    import fixed_point_package::*;

    typedef struct packed {
        logic valid;
        logic id;
        fixed_t frac_exponent;
        logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent;
        fixed_t two_to_pwr_int_exponent;
        fixed_t frac_exponent_plus_one; 
    } pipeline_t;

    localparam int PIPELINE_STAGES = 5;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t frac_exponent_squared;
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four; 
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four_plus_one; 
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d1; 
    fixed_t mult_term; 

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i=0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end 

            frac_exponent_squared <= 0;
            frac_exponent_squared_minus_frac_exponent_div_four <= 0; 
            frac_exponent_squared_minus_frac_exponent_div_four_plus_one <= 0; 
            frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d1 <= 0; 
            mult_term <= 0; 
            result <= 0; 
            valid_out <= '0;
            id_out <= '0;

        end else begin
            // ------------------------------STAGE 0------------------------------
            // Feed the pipeline
            pipe[0].frac_exponent <= {8'b0, exponent[STATE_FRAC_BITS-1:0]};
            pipe[0].int_exponent  <= exponent[VALUE_WIDTH-1:STATE_FRAC_BITS];

            pipe[0].valid <= valid_in;
            pipe[0].id <= id_in;

            // ------------------------------STAGE 1------------------------------
            // Drive the pipeline
            pipe[1].frac_exponent <= pipe[0].frac_exponent;

            pipe[1].valid <= pipe[0].valid;
            pipe[1].id <= pipe[0].id;

            // 2 ^ N(int)
            if (pipe[0].int_exponent < -8'sd6) begin
                pipe[1].two_to_pwr_int_exponent <= 32'sb0;
            end else if (pipe[0].int_exponent[7] == 1'b0) begin
                // positive signed
                pipe[1].two_to_pwr_int_exponent <= ONE_Q8 <<< pipe[0].int_exponent;
            end else begin
                // negative signed
                pipe[1].two_to_pwr_int_exponent <= ONE_Q8 >>> (-pipe[0].int_exponent);
            end 

            frac_exponent_squared <= mul_24_24_24(pipe[0].frac_exponent, pipe[0].frac_exponent);

            pipe[1].frac_exponent_plus_one <= pipe[0].frac_exponent + ONE_Q24;

            // ------------------------------STAGE 2------------------------------
            // Drive the pipeline
            pipe[2].two_to_pwr_int_exponent <= pipe[1].two_to_pwr_int_exponent;
            pipe[2].frac_exponent_plus_one <= pipe[1].frac_exponent_plus_one;

            pipe[2].valid <= pipe[1].valid;
            pipe[2].id <= pipe[1].id;

            frac_exponent_squared_minus_frac_exponent_div_four <= (frac_exponent_squared - pipe[1].frac_exponent) >>> 2;

            // ------------------------------STAGE 3------------------------------
            // Drive the pipeline
            pipe[3].two_to_pwr_int_exponent <= pipe[2].two_to_pwr_int_exponent;
            pipe[3].frac_exponent_plus_one <= pipe[2].frac_exponent_plus_one;

            pipe[3].valid <= pipe[2].valid;
            pipe[3].id <= pipe[2].id;

            frac_exponent_squared_minus_frac_exponent_div_four_plus_one <= frac_exponent_squared_minus_frac_exponent_div_four + ONE_Q24;

            // ------------------------------STAGE 4------------------------------
            // Drive the pipeline
            frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d1 <= frac_exponent_squared_minus_frac_exponent_div_four_plus_one;

            mult_term <= mul_24_8_8(pipe[3].frac_exponent_plus_one, pipe[3].two_to_pwr_int_exponent);

            pipe[4].valid <= pipe[3].valid;
            pipe[4].id <= pipe[3].id;

            // ------------------------------STAGE 5------------------------------
            // Drive the pipeline

            result <= mul_24_8_8(mult_term, frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d1);
            valid_out <= pipe[4].valid;
            id_out <= pipe[4].id;
        end 
    end

endmodule
