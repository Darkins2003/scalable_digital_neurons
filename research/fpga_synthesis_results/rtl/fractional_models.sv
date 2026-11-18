module fractional_input_register (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] registered_exponent,
    output logic registered_valid
);

    always_ff @(posedge clock) begin
        if (reset) begin
            registered_exponent <= '0;
            registered_valid <= 1'b0;
        end else begin
            registered_exponent <= $signed({8'b0, fractional_exponent});
            registered_valid <= input_valid;
        end
    end

endmodule

module fractional_delay #(
    parameter integer CYCLES = 8
)(
    input logic clock,
    input logic reset,
    input logic signed [31:0] input_value,
    output logic signed [31:0] output_value
);

    logic signed [31:0] values [0:CYCLES-1];

    assign output_value = values[CYCLES-1];

    always_ff @(posedge clock) begin
        if (reset) begin
            for (integer position = 0; position < CYCLES; position = position + 1) begin
                values[position] <= '0;
            end
        end else begin
            values[0] <= input_value;
            for (integer position = 1; position < CYCLES; position = position + 1) begin
                values[position] <= values[position-1];
            end
        end
    end

endmodule

module fractional_polynomial #(
    parameter integer DEGREE = 3,
    parameter logic signed [31:0] COEFFICIENT_0 = 32'sd16775420,
    parameter logic signed [31:0] COEFFICIENT_1 = 32'sd11684617,
    parameter logic signed [31:0] COEFFICIENT_2 = 32'sd3763773,
    parameter logic signed [31:0] COEFFICIENT_3 = 32'sd1328826,
    parameter logic signed [31:0] COEFFICIENT_4 = 32'sd0
)(
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    localparam logic signed [31:0] COEFFICIENTS [0:4] = '{COEFFICIENT_0, COEFFICIENT_1, COEFFICIENT_2, COEFFICIENT_3, COEFFICIENT_4};
    wire signed [31:0] exponents [0:DEGREE];
    wire signed [31:0] partial_results [0:DEGREE];
    wire validity [0:DEGREE];

    fractional_input_register input_register (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .registered_exponent(exponents[0]), .registered_valid(validity[0]));

    assign partial_results[0] = COEFFICIENTS[DEGREE];

    for (genvar stage = 0; stage < DEGREE; stage = stage + 1) begin : polynomial_stage
        wire signed [31:0] product;
        wire product_valid;
        logic signed [31:0] accumulated_result;
        logic accumulated_valid;

        signed_32_32_multiplication multiplication (.clk(clock), .rst(reset), .term_1(partial_results[stage]), .term_2(exponents[stage]), .valid_in(validity[stage]), .result(product), .valid_out(product_valid));
        fractional_delay #(.CYCLES(8)) exponent_delay (.clock(clock), .reset(reset), .input_value(exponents[stage]), .output_value(exponents[stage+1]));

        assign partial_results[stage+1] = accumulated_result;
        assign validity[stage+1] = accumulated_valid;

        always_ff @(posedge clock) begin
            if (reset) begin
                accumulated_result <= '0;
                accumulated_valid <= 1'b0;
            end else begin
                accumulated_result <= product + COEFFICIENTS[DEGREE-stage-1];
                accumulated_valid <= product_valid;
            end
        end
    end

    always_ff @(posedge clock) begin
        if (reset) begin
            result <= '0;
            output_valid <= 1'b0;
        end else begin
            result <= partial_results[DEGREE];
            output_valid <= validity[DEGREE];
        end
    end

endmodule

module fractional_research_linear (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    wire signed [31:0] registered_exponent;
    wire registered_valid;

    fractional_input_register input_register (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .registered_exponent(registered_exponent), .registered_valid(registered_valid));

    always_ff @(posedge clock) begin
        if (reset) begin
            result <= '0;
            output_valid <= 1'b0;
        end else begin
            result <= 32'sd16777216 + registered_exponent;
            output_valid <= registered_valid;
        end
    end

endmodule

module fractional_research_cubic (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    wire signed [31:0] registered_exponent;
    wire registered_valid;
    wire signed [31:0] squared_exponent;
    wire squared_valid;
    wire signed [31:0] square_aligned_exponent;
    wire signed [31:0] correction_aligned_linear;
    logic signed [31:0] divided_difference;
    logic divided_difference_valid;
    logic signed [31:0] correction;
    logic correction_valid;
    wire signed [31:0] final_product;
    wire final_valid;

    fractional_input_register input_register (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .registered_exponent(registered_exponent), .registered_valid(registered_valid));
    signed_32_32_multiplication square_multiplication (.clk(clock), .rst(reset), .term_1(registered_exponent), .term_2(registered_exponent), .valid_in(registered_valid), .result(squared_exponent), .valid_out(squared_valid));
    fractional_delay #(.CYCLES(7)) square_exponent_delay (.clock(clock), .reset(reset), .input_value(registered_exponent), .output_value(square_aligned_exponent));
    fractional_delay #(.CYCLES(9)) linear_delay (.clock(clock), .reset(reset), .input_value(32'sd16777216 + registered_exponent), .output_value(correction_aligned_linear));
    signed_32_32_multiplication #(.TERM_1_FRACTIONAL_BITS(6'd24), .TERM_2_FRACTIONAL_BITS(6'd24), .RESULT_FRACTIONAL_BITS(6'd24)) correction_multiplication (.clk(clock), .rst(reset), .term_1(correction), .term_2(correction_aligned_linear), .valid_in(correction_valid), .result(final_product), .valid_out(final_valid));

    always_ff @(posedge clock) begin
        if (reset) begin
            divided_difference <= '0;
            divided_difference_valid <= 1'b0;
            correction <= '0;
            correction_valid <= 1'b0;
            result <= '0;
            output_valid <= 1'b0;
        end else begin
            divided_difference <= (squared_exponent - square_aligned_exponent) >>> 2;
            divided_difference_valid <= squared_valid;
            correction <= 32'sd16777216 + divided_difference;
            correction_valid <= divided_difference_valid;
            result <= final_product;
            output_valid <= final_valid;
        end
    end

endmodule

module fractional_rom #(
    parameter integer ADDRESS_BITS = 10,
    parameter MEMORY_STYLE = "block",
    parameter MEMORY_FILE = "memory/rom_1024.mem"
)(
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    (* rom_style = MEMORY_STYLE *) logic [24:0] memory [0:(1 << ADDRESS_BITS)-1];
    wire signed [31:0] registered_exponent;
    wire registered_valid;
    logic [24:0] stored_value;
    logic stored_valid;

    initial begin
        $readmemh(MEMORY_FILE, memory);
    end

    fractional_input_register input_register (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .registered_exponent(registered_exponent), .registered_valid(registered_valid));

    always_ff @(posedge clock) begin
        stored_value <= memory[registered_exponent[23 -: ADDRESS_BITS]];
        if (reset) begin
            stored_valid <= 1'b0;
            result <= '0;
            output_valid <= 1'b0;
        end else begin
            stored_valid <= registered_valid;
            result <= $signed({7'b0, stored_value});
            output_valid <= stored_valid;
        end
    end

endmodule
