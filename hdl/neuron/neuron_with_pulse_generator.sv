import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module neuron_with_pulse_generator (
    input logic clk,
    input logic rst,

    input fixed_t current_in,
    input logic valid_in,
    input logic start_pulse,
    input logic [1:0] id_in,

    // Single_neuron
    output logic single_neuron_valid_out,
    output logic [1:0] single_neuron_id_out,
    output fixed_t vmem_out,

    // Pulse/triangular generator
    output logic ready,
    output logic valid_out,
    output logic [1:0] id_out,
    output fixed_t excitatory_pulse,
    output fixed_t inhibitory_pulse
);
    fixed_t vmem_out_reg;

    logic synaptic_triangular_generator_valid_out;
    logic [1:0] synaptic_triangular_generator_id_out;
    logic [1:0] synaptic_pulse_generator_id_in;
    fixed_t excitatory_triangular_state;
    fixed_t inhibitory_triangular_state;

    fixed_t vmem_out_reg_previous;

    assign vmem_out = vmem_out_reg;

    single_neuron single_neuron_i (
        .clk(clk),
        .rst(rst),

        .current_in(current_in),
        .valid_in(valid_in),
        .id_in(id_in),

        .ready(ready),
        .valid_out(single_neuron_valid_out),
        .id_out(single_neuron_id_out),
        .vmem_out(vmem_out_reg),
        .vmem_out_previous(vmem_out_reg_previous)
    );

    synaptic_triangular_generator synaptic_triangular_generator_i (
        .clk(clk),
        .rst(rst),

        .vmem_in(vmem_out_reg_previous),
        .valid_in(single_neuron_valid_out),
        .id_in(single_neuron_id_out),
        
        .valid_out(synaptic_triangular_generator_valid_out),
        .id_out(synaptic_triangular_generator_id_out),
        .excitatory_triangular_state(excitatory_triangular_state), 
        .inhibitory_triangular_state(inhibitory_triangular_state) 
    );

    synaptic_pulse_generator synaptic_pulse_generator_i(
        .clk(clk),
        .rst(rst),

        .valid_in(synaptic_triangular_generator_valid_out),
        .id_in(synaptic_pulse_generator_id_in),
        .start_pulse(start_pulse),
        .excitatory_triangular_state(excitatory_triangular_state), 
        .inhibitory_triangular_state(inhibitory_triangular_state), 

        .valid_out(valid_out),
        .id_out(id_out),
        .excitatory_pulse(excitatory_pulse), 
        .inhibitory_pulse(inhibitory_pulse) 
    );

    always_comb begin
        // If ctrl_start, the sequence begins at synaptic_pulse_generator
        if (start_pulse) begin
            synaptic_pulse_generator_id_in = id_in;
        end else begin
            synaptic_pulse_generator_id_in = synaptic_triangular_generator_id_out;
        end 
    end 

endmodule
