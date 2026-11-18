module signed_multiplier (
    input logic CLK,
    input logic signed [31:0] A,
    input logic signed [31:0] B,
    input logic SCLR,
    output wire signed [63:0] P
);

    logic [5:0][63:0] product_pipeline;
    logic signed [63:0] current_product;

    assign P = product_pipeline[5];
    assign current_product = A * B;

    always_ff @(posedge CLK) begin
        if (SCLR) begin
            product_pipeline <= '0;
        end else begin
            product_pipeline <= {product_pipeline[4:0], current_product};
        end
    end

endmodule
