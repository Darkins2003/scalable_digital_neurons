import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential_pipe_cubic (
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,
    input logic independent_id_in,

    output fixed_t result,
    output logic valid_out,
    output logic independent_id_out
);

    import neuron_params_generated_pkg::*;
    import neuron_params_pkg::*;
    import fixed_point_package::*;

    typedef struct packed {
        logic valid;
        logic independent_id;
        fixed_t frac_exponent;
        logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent;
        fixed_t frac_exponent_plus_one;
        fixed_t shifted_result; 
    } pipeline_t;

    localparam int PIPELINE_STAGES = 18;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t frac_exponent_squared;
    logic squared_exponent_valid_out;
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four; 
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four_plus_one; 
    fixed_t frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d;
    fixed_t mult_term; 

    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] int_exponent_reg_d = '0;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] negative_int_exponent = '0;
    logic signed [VALUE_WIDTH-STATE_FRAC_BITS-1:0] negative_int_exponent_delayed = '0;

    logic result_is_zero = '0;
    logic positive_signed_exponent = '0;

    logic signed [63:0] left_shifted_partial_result = '0;
    logic signed [63:0] right_shifted_partial_result = '0;

    logic signed [63:0] left_shifted_result = '0;
    logic signed [63:0] right_shifted_result = '0;

    // ------------------------------STAGE 1 to STAGE 1 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd24),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i3 (
        .clk(clk),
        .rst(rst),

        .term_1(pipe[0].frac_exponent),
        .term_2(pipe[0].frac_exponent),
        .valid_in(pipe[0].valid),

        .result(frac_exponent_squared),
        .valid_out(squared_exponent_valid_out)
    );

    // ------------------------------STAGE 5 to STAGE 5 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd8)
    ) signed_32_32_multiplication_i2 (
        .clk(clk),
        .rst(rst),

        .term_1(frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d),
        .term_2(mult_term),
        .valid_in(pipe[10].valid),

        .result(result),
        .valid_out(valid_out)  
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i=0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end 

            independent_id_out <= '0;

            frac_exponent_squared_minus_frac_exponent_div_four <= 0; 
            frac_exponent_squared_minus_frac_exponent_div_four_plus_one <= 0; 

            frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d <= '0;
            mult_term <= '0;

            int_exponent_reg_d <= '0;
            negative_int_exponent <= '0;
            negative_int_exponent_delayed <= '0;

            result_is_zero <= '0;
            positive_signed_exponent <= '0;

            left_shifted_partial_result <= '0;
            right_shifted_partial_result <= '0;

            left_shifted_result <= '0;
            right_shifted_result <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 18------------------------------
            // ------------------------------STAGE 0------------------------------
            // Feed the pipeline
            pipe[0].frac_exponent <= {8'b0, exponent[STATE_FRAC_BITS-1:0]};
            pipe[0].int_exponent  <= exponent[VALUE_WIDTH-1:STATE_FRAC_BITS];
            pipe[0].frac_exponent_plus_one <= {7'b0, 1'b1, exponent[STATE_FRAC_BITS-1:0]};

            negative_int_exponent <= -$signed(exponent[VALUE_WIDTH-1:STATE_FRAC_BITS]);

            pipe[0].valid <= valid_in;
            pipe[0].independent_id <= independent_id_in;

            // ------------------------------STAGE 1 (FEED signed_32_32_multiplication_i3)------------------------------
            pipe[1].frac_exponent <= pipe[0].frac_exponent;

            pipe[1].independent_id <= pipe[0].independent_id;

            pipe[1].int_exponent <= pipe[0].int_exponent;

            pipe[1].frac_exponent_plus_one <= pipe[0].frac_exponent_plus_one;

            int_exponent_reg_d <= pipe[0].int_exponent;
            negative_int_exponent_delayed <= negative_int_exponent;

            left_shifted_partial_result <= pipe[0].frac_exponent_plus_one <<< pipe[0].int_exponent[2:0];
            right_shifted_partial_result <= pipe[0].frac_exponent_plus_one >>> negative_int_exponent[2:0];

            // ------------------------------STAGE 1 (+1) to STAGE 1 (+6) (WAIT FOR signed_32_32_multiplication_i3)------------------------------
            for (int i = 2; i < 8; i++) begin
                pipe[i].frac_exponent <= pipe[i-1].frac_exponent;
                pipe[i].independent_id <= pipe[i-1].independent_id;
                pipe[i].int_exponent <= pipe[i-1].int_exponent;
                pipe[i].frac_exponent_plus_one <= pipe[i-1].frac_exponent_plus_one;
            end

            // ------------------------------STAGE 1 (+1)------------------------------
            left_shifted_result <= left_shifted_partial_result <<< {int_exponent_reg_d[5:3], 3'b000};
            right_shifted_result <= right_shifted_partial_result >>> {negative_int_exponent_delayed[5:3], 3'b000};

            if ((int_exponent_reg_d < -8'sd6) || (int_exponent_reg_d >= 8'sd64)) begin
                result_is_zero <= '1;
                positive_signed_exponent <= '0;
            end else if (int_exponent_reg_d[7] == 1'b0) begin
                positive_signed_exponent <= '1;
                result_is_zero <= '0;
            end else begin
                positive_signed_exponent <= '0;
                result_is_zero <= '0;
            end

            // ------------------------------STAGE 1 (+2)------------------------------
            if (result_is_zero) begin
                pipe[3].shifted_result <= 32'sd0;
            end else if (positive_signed_exponent) begin
                pipe[3].shifted_result <= fixed_t'(left_shifted_result >>> 16);
            end else begin
                pipe[3].shifted_result <= fixed_t'(right_shifted_result >>> 16);
            end

            // ------------------------------STAGE 1 (+3) to STAGE 1 (+6)------------------------------
            for (int i = 4; i < 8; i++) begin
                pipe[i].shifted_result <= pipe[i-1].shifted_result;
            end

            // ------------------------------STAGE 2------------------------------
            pipe[8].int_exponent <= pipe[7].int_exponent;
            pipe[8].shifted_result <= pipe[7].shifted_result;
            pipe[8].frac_exponent_plus_one <= pipe[7].frac_exponent_plus_one;

            pipe[8].valid <= squared_exponent_valid_out;
            pipe[8].independent_id <= pipe[7].independent_id;

            frac_exponent_squared_minus_frac_exponent_div_four <= (frac_exponent_squared - pipe[7].frac_exponent) >>> 2;

            // ------------------------------STAGE 3------------------------------
            pipe[9].int_exponent <= pipe[8].int_exponent;
            pipe[9].shifted_result <= pipe[8].shifted_result;
            pipe[9].frac_exponent_plus_one <= pipe[8].frac_exponent_plus_one;

            pipe[9].valid <= pipe[8].valid;
            pipe[9].independent_id <= pipe[8].independent_id;

            frac_exponent_squared_minus_frac_exponent_div_four_plus_one <= frac_exponent_squared_minus_frac_exponent_div_four + ONE_Q24;

            // ------------------------------STAGE 4------------------------------
            frac_exponent_squared_minus_frac_exponent_div_four_plus_one_d <= frac_exponent_squared_minus_frac_exponent_div_four_plus_one;

            pipe[10].valid <= pipe[9].valid;
            pipe[10].independent_id <= pipe[9].independent_id;

            mult_term <= pipe[9].shifted_result;

            // ------------------------------STAGE 5 (FEED signed_32_32_multiplication_i2)------------------------------
            pipe[11].independent_id <= pipe[10].independent_id;

            // ------------------------------STAGE 5 (+1) to STAGE 5 (+6) (WAIT FOR signed_32_32_multiplication_i2)------------------------------
            for (int i = 12; i < PIPELINE_STAGES-1; i++) begin
                pipe[i].independent_id <= pipe[i-1].independent_id;
            end 

            independent_id_out <= pipe[PIPELINE_STAGES-2].independent_id;
        end 
    end

endmodule
