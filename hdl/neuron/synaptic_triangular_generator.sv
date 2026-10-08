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

    localparam int PIPELINE_STAGES = 2;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    fixed_t excitatory_triangular_state_reg [0:2] = '{default:TRIANGLE_INITIAL_STATE_Q16};
    fixed_t inhibitory_triangular_state_reg [0:2] = '{default:TRIANGLE_INITIAL_STATE_Q16};

    fixed_t excitatory_triangular_slope; // (dTe) Q16.16
    fixed_t excitatory_triangular_slope_reg; // (dTe) Q16.16
    fixed_t inhibitory_triangular_slope; // (dTi) Q16.16
    fixed_t inhibitory_triangular_slope_reg; // (dTi) Q16.16

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

            excitatory_triangular_slope = '0; // Blocking
            excitatory_triangular_slope_reg <= '0; 
            inhibitory_triangular_slope = '0; // Blocking
            inhibitory_triangular_slope_reg <= '0; 
            mul_excitatory_dt_slope <= '0;
            mul_inhibitory_dt_slope <= '0;

            valid_out <= '0;
            id_out <= '0;

        end else begin
            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= valid_in;
            pipe[0].id <= id_in;
            
            // Choose slope
            if (vmem_in >= TRIANGLE_SPIKE_THRESHOLD_Q24) begin
                excitatory_triangular_slope = TRIANGLE_SLOPE_MATRIX_Q16[0][0];
                inhibitory_triangular_slope = TRIANGLE_SLOPE_MATRIX_Q16[1][0];
            end else begin
                excitatory_triangular_slope = TRIANGLE_SLOPE_MATRIX_Q16[0][1];
                inhibitory_triangular_slope = TRIANGLE_SLOPE_MATRIX_Q16[1][1];
            end 

            // If a triangle has reached a boundary and its slope would push it farther out, set its slope to zero
            if ( (excitatory_triangular_state_reg[id_in] >= TRIANGLE_UPPER_BOUND_Q16) && (excitatory_triangular_slope > 32'sd0) ) begin
                excitatory_triangular_slope = 32'sd0;
            end 

            if ( (inhibitory_triangular_state_reg[id_in] >= TRIANGLE_UPPER_BOUND_Q16) && (inhibitory_triangular_slope > 32'sd0) ) begin
                inhibitory_triangular_slope = 32'sd0;
            end 

            if ( (excitatory_triangular_state_reg[id_in] <= 32'sd0) && (excitatory_triangular_slope < 32'sd0) ) begin
                excitatory_triangular_slope = 32'sd0;
            end 

            if ( (inhibitory_triangular_state_reg[id_in] <= 32'sd0) && (inhibitory_triangular_slope < 32'sd0) ) begin
                inhibitory_triangular_slope = 32'sd0;
            end 

            excitatory_triangular_slope_reg <= excitatory_triangular_slope;
            inhibitory_triangular_slope_reg <= inhibitory_triangular_slope;

            // ------------------------------STAGE 1-----------------------------
            pipe[1].valid <= pipe[0].valid;
            pipe[1].id <= pipe[0].id;
            
            mul_excitatory_dt_slope <= mul_24_16_16(DT ,excitatory_triangular_slope_reg);
            mul_inhibitory_dt_slope <= mul_24_16_16(DT ,inhibitory_triangular_slope_reg);

            // ------------------------------STAGE 2-----------------------------
            valid_out <= pipe[1].valid;
            id_out <= pipe[1].id;
            
            if (pipe[1].valid) begin
                excitatory_triangular_state_reg[pipe[1].id] <= excitatory_triangular_state_reg[pipe[1].id] + mul_excitatory_dt_slope;
                inhibitory_triangular_state_reg[pipe[1].id] <= inhibitory_triangular_state_reg[pipe[1].id] + mul_inhibitory_dt_slope;
            end 
        end 

    end 
endmodule 
