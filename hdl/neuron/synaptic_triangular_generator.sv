import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module synaptic_triangular_generator (
    input logic clk,
    input logic rst,

    input fixed_t vmem_in,
    input logic valid_in,
    input logic [1:0] id_in,

    output logic valid_out,
    output logic [1:0] id_out,
    output fixed_t excitatory_triangular_state, // (Te) Q16.16
    output fixed_t inhibitory_triangular_state // (Ti) Q16.16
);

    // Pipeline
    typedef struct packed {
        logic valid;
        logic [1:0] id;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 4;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t excitatory_triangular_state_reg [0:2] = '{default:TRIANGLE_INITIAL_STATE_Q16};
    fixed_t inhibitory_triangular_state_reg [0:2] = '{default:TRIANGLE_INITIAL_STATE_Q16};

    fixed_t excitatory_triangular_state_selected;
    fixed_t inhibitory_triangular_state_selected;

    logic [1:0] triangular_slope_index_selected;
    logic excitatory_triangular_state_at_or_above_upper_bound;
    logic excitatory_triangular_state_at_or_below_zero;
    logic inhibitory_triangular_state_at_or_above_upper_bound;
    logic inhibitory_triangular_state_at_or_below_zero;

    fixed_t membrane_voltage_delayed;

    logic [1:0] excitatory_slope_index;
    logic [1:0] inhibitory_slope_index;

    fixed_t mul_excitatory_dt_slope;
    fixed_t mul_inhibitory_dt_slope;

    assign excitatory_triangular_state = excitatory_triangular_state_reg[id_out];
    assign inhibitory_triangular_state = inhibitory_triangular_state_reg[id_out];

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i].valid <= '0;
                pipe[i].id <= '0;
            end

            excitatory_triangular_state_reg <= '{default:TRIANGLE_INITIAL_STATE_Q16};
            inhibitory_triangular_state_reg <= '{default:TRIANGLE_INITIAL_STATE_Q16};

            excitatory_triangular_state_selected <= TRIANGLE_INITIAL_STATE_Q16;
            inhibitory_triangular_state_selected <= TRIANGLE_INITIAL_STATE_Q16;

            triangular_slope_index_selected <= '0;
            excitatory_triangular_state_at_or_above_upper_bound <= '0;
            excitatory_triangular_state_at_or_below_zero <= '0;
            inhibitory_triangular_state_at_or_above_upper_bound <= '0;
            inhibitory_triangular_state_at_or_below_zero <= '0;

            membrane_voltage_delayed <= '0;

            excitatory_slope_index <= '0;
            inhibitory_slope_index <= '0;
            mul_excitatory_dt_slope <= '0;
            mul_inhibitory_dt_slope <= '0;

            valid_out <= '0;
            id_out <= '0;

        end else begin
            // ------------------------------TOTAL STAGES = 5------------------------------
            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in;
            pipe[0].id <= id_in;
            membrane_voltage_delayed <= vmem_in;

            excitatory_triangular_state_selected <= excitatory_triangular_state_reg[id_in];
            inhibitory_triangular_state_selected <= inhibitory_triangular_state_reg[id_in];

            // ------------------------------STAGE 1-----------------------------
            pipe[1].valid <= pipe[0].valid;
            pipe[1].id <= pipe[0].id;

            // Choose slope
            if (membrane_voltage_delayed >= TRIANGLE_SPIKE_THRESHOLD_Q24) begin
                triangular_slope_index_selected <= 2'd0;
            end else begin
                triangular_slope_index_selected <= 2'd1;
            end

            if (excitatory_triangular_state_selected >= TRIANGLE_UPPER_BOUND_Q16) begin
                excitatory_triangular_state_at_or_above_upper_bound <= '1;
                excitatory_triangular_state_at_or_below_zero <= '0;
            end else if (excitatory_triangular_state_selected <= 32'sd0) begin
                excitatory_triangular_state_at_or_above_upper_bound <= '0;
                excitatory_triangular_state_at_or_below_zero <= '1;
            end else begin
                excitatory_triangular_state_at_or_above_upper_bound <= '0;
                excitatory_triangular_state_at_or_below_zero <= '0;
            end

            if (inhibitory_triangular_state_selected >= TRIANGLE_UPPER_BOUND_Q16) begin
                inhibitory_triangular_state_at_or_above_upper_bound <= '1;
                inhibitory_triangular_state_at_or_below_zero <= '0;
            end else if (inhibitory_triangular_state_selected <= 32'sd0) begin
                inhibitory_triangular_state_at_or_above_upper_bound <= '0;
                inhibitory_triangular_state_at_or_below_zero <= '1;
            end else begin
                inhibitory_triangular_state_at_or_above_upper_bound <= '0;
                inhibitory_triangular_state_at_or_below_zero <= '0;
            end

            // ------------------------------STAGE 2-----------------------------
            pipe[2].valid <= pipe[1].valid;
            pipe[2].id <= pipe[1].id;

            // If a triangle has reached a boundary and its slope would push it farther out, set its slope to zero
            if ((excitatory_triangular_state_at_or_above_upper_bound && TRIANGLE_SLOPE_MATRIX_Q16[0][triangular_slope_index_selected] > 32'sd0) || (excitatory_triangular_state_at_or_below_zero && TRIANGLE_SLOPE_MATRIX_Q16[0][triangular_slope_index_selected] < 32'sd0)) begin
                excitatory_slope_index <= 2'd2;
            end else begin
                excitatory_slope_index <= triangular_slope_index_selected;
            end

            if ((inhibitory_triangular_state_at_or_above_upper_bound && TRIANGLE_SLOPE_MATRIX_Q16[1][triangular_slope_index_selected] > 32'sd0) || (inhibitory_triangular_state_at_or_below_zero && TRIANGLE_SLOPE_MATRIX_Q16[1][triangular_slope_index_selected] < 32'sd0)) begin
                inhibitory_slope_index <= 2'd2;
            end else begin
                inhibitory_slope_index <= triangular_slope_index_selected;
            end

            // ------------------------------STAGE 3-----------------------------
            pipe[3].valid <= pipe[2].valid;
            pipe[3].id <= pipe[2].id;

            mul_excitatory_dt_slope <= TRIANGLE_DT_SLOPE_MATRIX_Q16[0][excitatory_slope_index];
            mul_inhibitory_dt_slope <= TRIANGLE_DT_SLOPE_MATRIX_Q16[1][inhibitory_slope_index];

            // ------------------------------STAGE 4-----------------------------
            valid_out <= pipe[3].valid;
            id_out <= pipe[3].id;

            if (pipe[3].valid) begin
                excitatory_triangular_state_reg[pipe[3].id] <= excitatory_triangular_state_reg[pipe[3].id] + mul_excitatory_dt_slope;
                inhibitory_triangular_state_reg[pipe[3].id] <= inhibitory_triangular_state_reg[pipe[3].id] + mul_inhibitory_dt_slope;
            end
        end

    end
endmodule
