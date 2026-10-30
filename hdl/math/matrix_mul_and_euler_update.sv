import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module matrix_mul_and_euler_update(
    input logic clk,
    input logic rst,

    input logic valid_in,
    input logic [1:0] id_in,
    input fixed_t current_vector [0:7],

    output logic [1:0] id_out,
    output logic valid_out,
    output fixed_t mul_dy_dt_dt [0:3]
);

    typedef struct packed {
        logic valid;
        logic [1:0] id;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 17;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t products [0:3][0:7];
    logic products_valid_out [0:3][0:7];
    fixed_t layer_one_sums [0:3][0:3];
    fixed_t layer_two_sums [0:3][0:1];

    fixed_t dy_dt [0:3];

    // ------------------------------STAGE 0 to STAGE 0 (+6)------------------------------
    for (genvar row = 0; row < 4; row++) begin : generate_products
        for (genvar column = 0; column < 8; column++) begin : generate_columns
            signed_32_32_multiplication #(
                .TERM_1_FRACTIONAL_BITS(6'd23),
                .TERM_2_FRACTIONAL_BITS(6'd8),
                .RESULT_FRACTIONAL_BITS(6'd8)
            ) signed_32_32_multiplication_i (
                .clk(clk),
                .rst(rst),

                .term_1(NEURON_MATRIX[row][column]),
                .term_2(current_vector[column]),
                .valid_in(valid_in),

                .result(products[row][column]),
                .valid_out(products_valid_out[row][column])
            );
        end
    end

    // ------------------------------STAGE 4 to STAGE 4 (+6)------------------------------
    signed_32_32_multiplication #(
        .TERM_1_FRACTIONAL_BITS(6'd24),
        .TERM_2_FRACTIONAL_BITS(6'd8),
        .RESULT_FRACTIONAL_BITS(6'd24)
    ) signed_32_32_multiplication_i2 (
        .clk(clk),
        .rst(rst),

        .term_1(DT),
        .term_2(dy_dt[0]),
        .valid_in(pipe[9].valid),

        .result(mul_dy_dt_dt[0]),
        .valid_out(valid_out)
    );

    // ------------------------------STAGE 4 to STAGE 4 (+6)------------------------------
    for (genvar row = 1; row < 4; row++) begin : generate_euler_updates
        signed_32_32_multiplication #(
            .TERM_1_FRACTIONAL_BITS(6'd24),
            .TERM_2_FRACTIONAL_BITS(6'd8),
            .RESULT_FRACTIONAL_BITS(6'd24)
        ) signed_32_32_multiplication_i3 (
            .clk(clk),
            .rst(rst),

            .term_1(DT),
            .term_2(dy_dt[row]),
            .valid_in(pipe[9].valid),

            .result(mul_dy_dt_dt[row]),
            .valid_out()
        );
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end

            layer_one_sums <= '{default:'0};
            layer_two_sums <= '{default:'0};
            dy_dt <= '{default:'0};
            id_out <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 17------------------------------
            // ------------------------------STAGE 0 (FEED signed_32_32_multiplication_i)------------------------------
            pipe[0].id <= id_in;

            // ------------------------------STAGE 0 (+1) to STAGE 0 (+6) (WAIT FOR signed_32_32_multiplication_i)------------------------------
            for (int i = 1; i < 7; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            // ------------------------------STAGE 1-----------------------------
            pipe[7].valid <= products_valid_out[0][0];
            pipe[7].id <= pipe[6].id;

            for (int i = 0; i < 4; i++) begin
                for (int j = 0; j < 4; j++) begin
                    layer_one_sums[i][j] <= products[i][2*j] + products[i][2*j+1];
                end
            end

            // ------------------------------STAGE 2-----------------------------
            pipe[8].valid <= pipe[7].valid;
            pipe[8].id <= pipe[7].id;

            for (int i = 0; i < 4; i++) begin
                for (int j = 0; j < 2; j++) begin
                    layer_two_sums[i][j] <= layer_one_sums[i][2*j] + layer_one_sums[i][2*j+1];
                end
            end

            // ------------------------------STAGE 3-----------------------------
            pipe[9].valid <= pipe[8].valid;
            pipe[9].id <= pipe[8].id;

            for (int i = 0; i < 4; i++) begin
                dy_dt[i] <= layer_two_sums[i][0] + layer_two_sums[i][1];
            end

            // ------------------------------STAGE 4 (FEED signed_32_32_multiplication_i2 AND signed_32_32_multiplication_i3)------------------------------
            pipe[10].id <= pipe[9].id;

            // ------------------------------STAGE 4 (+1) to STAGE 4 (+6) (WAIT FOR signed_32_32_multiplication_i2 AND signed_32_32_multiplication_i3)------------------------------
            for (int i = 11; i < PIPELINE_STAGES-1; i++) begin
                pipe[i].id <= pipe[i-1].id;
            end

            id_out <= pipe[PIPELINE_STAGES-2].id;
        end
    end
endmodule
