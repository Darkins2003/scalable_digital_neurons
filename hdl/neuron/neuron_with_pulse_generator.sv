import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module neuron_with_pulse_generator (
    input logic clk,
    input logic rst,

    input fixed_t current_in,
    input logic valid_in,
    input logic start_pulse,

    output logic valid_out,
    output fixed_t vmem_out,
    output fixed_t excitatory_pulse,
    output fixed_t inhibitory_pulse
);

    logic single_neuron_valid_out;
    fixed_t vmem_out_reg;

    logic synaptic_triangular_generator_valid_out;
    fixed_t excitatory_triangular_state;
    fixed_t inhibitory_triangular_state;

    fixed_t vmem_out_reg_previous;

    assign vmem_out = vmem_out_reg;

    single_neuron single_neuron_i (
        .clk(clk),
        .rst(rst),

        .current_in(current_in),
        .valid_in(valid_in),

        .valid_out(single_neuron_valid_out),
        .vmem_out(vmem_out_reg),
        .vmem_out_previous(vmem_out_reg_previous)
    );

    synaptic_triangular_generator synaptic_triangular_generator_i (
        .clk(clk),
        .rst(rst),

        .vmem_in(vmem_out_reg_previous),
        .valid_in(single_neuron_valid_out),
        
        .valid_out(synaptic_triangular_generator_valid_out),
        .excitatory_triangular_state(excitatory_triangular_state), 
        .inhibitory_triangular_state(inhibitory_triangular_state) 
    );

    synaptic_pulse_generator synaptic_pulse_generator_i(
        .clk(clk),
        .rst(rst),

        .valid_in(synaptic_triangular_generator_valid_out),
        .start_pulse(start_pulse),
        .excitatory_triangular_state(excitatory_triangular_state), 
        .inhibitory_triangular_state(inhibitory_triangular_state), 

        .valid_out(valid_out),
        .excitatory_pulse(excitatory_pulse), 
        .inhibitory_pulse(inhibitory_pulse) 
    );

endmodule
