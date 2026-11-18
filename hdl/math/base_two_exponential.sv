import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module base_two_exponential #(
    parameter bit USE_BRAM_EXPONENTIAL = 1'b1
)(
    input logic clk,
    input logic rst,
    input fixed_t exponent,
    input logic valid_in,
    input logic [2:0] independent_id_in,

    output fixed_t result = '0,
    output logic valid_out = '0,
    output logic [2:0] independent_id_out = '0
);

    localparam int NUM_BRAM_ADDRESSES = 1024;
    localparam EXPONENTIAL_ROM_STYLE = USE_BRAM_EXPONENTIAL ? "block" : "distributed";

    // fractional number is represented by 24 bits. 2^(fractional number) must lie between 1 and 2. Therefore we need to represent 2^(fractional number) with 25 bits
    (* rom_style = EXPONENTIAL_ROM_STYLE *) logic [24:0] fractional_exponent_estimation_table [0:NUM_BRAM_ADDRESSES-1]; 

    logic [24:0] fractional_exponent_estimation; // Number between 1 and 2
    fixed_t exponent_d1;
    logic signed [63:0] intermediate_result;
    logic [7:0] negative_int_exponent; 

    logic [1:0] valid_pipeline = '0;
    logic [2:0] independent_id_pipeline [0:1] = '{default:'0};

    // Fill the BRAM with the read-only estimates of 2^(fractional number)
    initial begin
        $readmemh("fractional_exponent_estimation_table.mem", fractional_exponent_estimation_table);
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            fractional_exponent_estimation <= '0;
            exponent_d1 <= '0;
            intermediate_result <= '0;
            negative_int_exponent <= '0;

            valid_pipeline <= '0;
            independent_id_pipeline <= '{default:'0};
            valid_out <= '0;
            independent_id_out <= '0;
            result <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 3------------------------------
            // ------------------------------STAGE 0------------------------------
            valid_pipeline[0] <= valid_in;
            independent_id_pipeline[0] <= independent_id_in;

            exponent_d1 <= exponent;

            // Read the estimated value of 2^(fractional number) from the BRAM
            fractional_exponent_estimation <= fractional_exponent_estimation_table[exponent[23:14]];

            // If exponent is negative, here we are gathering the postive version
            negative_int_exponent <= -exponent[31:24];

            // ------------------------------STAGE 1------------------------------
            valid_pipeline[1] <= valid_pipeline[0];
            independent_id_pipeline[1] <= independent_id_pipeline[0];

            // Intermediate_result (64 bits, 24 frac bits) = two_to_pwr_frac_exponent (25 bits, 24 frac bits) x two_to_pwr_int_exponent(7 bits, 0 fractional bits)
            if (exponent_d1[31] == 1'b0) begin
                // Positive signed
                intermediate_result <= fractional_exponent_estimation <<< exponent_d1[30:24];
            end else begin
                // Negative signed
                intermediate_result <= fractional_exponent_estimation >>> negative_int_exponent;
            end

            // ------------------------------STAGE 2------------------------------
            valid_out <= valid_pipeline[1];
            independent_id_out <= independent_id_pipeline[1];

            // Result (32 bits, 8 fractional bits) = intermediate_result (64 bits, 24 frac bits) >>> 16
            result <= fixed_t'(intermediate_result >>> 16);

        end 
    end 
endmodule
