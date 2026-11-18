module sollya_4_dsp (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    fractional_polynomial #(
        .DEGREE(4),
        .COEFFICIENT_0(32'sd16777278),
        .COEFFICIENT_1(32'sd11626044),
        .COEFFICIENT_2(32'sd4054016),
        .COEFFICIENT_3(32'sd867224),
        .COEFFICIENT_4(32'sd229808)
    ) design_instance (
        .clock(clock),
        .reset(reset),
        .fractional_exponent(fractional_exponent),
        .input_valid(input_valid),
        .result(result),
        .output_valid(output_valid)
    );

endmodule
