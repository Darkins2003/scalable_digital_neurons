module rom_32768_distributed (
    input logic clock,
    input logic reset,
    input logic [23:0] fractional_exponent,
    input logic input_valid,
    output logic signed [31:0] result,
    output logic output_valid
);

    fractional_rom #(.ADDRESS_BITS(15), .MEMORY_STYLE("distributed"), .MEMORY_FILE("memory/rom_32768.mem")) design_instance (
        .clock(clock),
        .reset(reset),
        .fractional_exponent(fractional_exponent),
        .input_valid(input_valid),
        .result(result),
        .output_valid(output_valid)
    );

endmodule
