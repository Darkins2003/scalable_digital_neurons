import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module signed_32_32_multiplication #(
    parameter logic [5:0] TERM_1_FRACTIONAL_BITS = 6'd24,
    parameter logic [5:0] TERM_2_FRACTIONAL_BITS = 6'd24,
    parameter logic [5:0] RESULT_FRACTIONAL_BITS = 6'd24
)(
    input logic clk,
    input logic rst,

    input fixed_t term_1,
    input fixed_t term_2,
    input logic valid_in,

    output fixed_t result,
    output logic valid_out
);
    typedef struct packed {
        logic valid;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 6;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    logic signed [63:0] product;

    // ------------------------------STAGE 0 to STAGE 0 (+5)------------------------------
    // Latency = 6 clk cycles
    signed_multiplier signed_multiplier_i (
        .CLK(clk),
        .A(term_1),
        .B(term_2),
        .SCLR(rst),
        .P(product)
    );

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end

            valid_out <= '0;
            result <= '0;
        end else begin
            // ------------------------------TOTAL STAGES = 7------------------------------
            // ------------------------------STAGE 0 (FEED signed_multiplier_i)------------------------------
            pipe[0].valid <= valid_in;

            // ------------------------------STAGE 0 (+1) to STAGE 0 (+5) (WAIT FOR signed_multiplier_i)------------------------------
            for (int i = 1; i < PIPELINE_STAGES; i++) begin
                pipe[i].valid <= pipe[i-1].valid;
            end

            // ------------------------------STAGE 1------------------------------
            valid_out <= pipe[PIPELINE_STAGES-1].valid;
            
            case({TERM_1_FRACTIONAL_BITS, TERM_2_FRACTIONAL_BITS, RESULT_FRACTIONAL_BITS})
                {6'd24, 6'd24, 6'd24}: begin
                    result <= fixed_t'(product >>> 24); // Shift right by 24 bits and truncate to 32 bits
                end 
                {6'd24, 6'd16, 6'd16}: begin
                    result <= fixed_t'(product >>> 24); // Shift right by 24 bits and truncate to 32 bits
                end
                {6'd24, 6'd8, 6'd8}: begin
                    result <= fixed_t'(product >>> 24); // Shift right by 24 bits and truncate to 32 bits
                end
                {6'd23, 6'd8, 6'd8}: begin
                    result <= fixed_t'(product >>> 23); // Shift right by 23 bits and truncate to 32 bits
                end
                {6'd16, 6'd24, 6'd24}: begin
                    result <= fixed_t'(product >>> 16); // Shift right by 16 bits and truncate to 32 bits
                end
                {6'd24, 6'd8, 6'd24}: begin
                    result <= fixed_t'(product >>> 8); // Shift right by 8 bits and truncate to 32 bits
                end
                {6'd8, 6'd8, 6'd8}: begin
                    result <= fixed_t'(product >>> 8); // Shift right by 8 bits and truncate to 32 bits
                end
            endcase
        end 
    end 

endmodule
