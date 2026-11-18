module sollya_2_dsp (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    fractional_polynomial #(
        .DEGREE(2),
        .COEFFICIENT_0(32'sd16818757),
        .COEFFICIENT_1(32'sd10922753),
        .COEFFICIENT_2(32'sd5771381),
        .COEFFICIENT_3(32'sd0),
        .COEFFICIENT_4(32'sd0)
    ) design_instance (
        .clock(clock),
        .reset(reset),
        .fractional_exponent(fractional_exponent),
        .input_valid(input_valid),
        .result(result),
        .output_valid(output_valid)
    );

endmodule
