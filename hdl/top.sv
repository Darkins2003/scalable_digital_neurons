import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module top (
    input logic clk,
    input logic rst,

    input fixed_t current_in,
    output fixed_t out 
);

    fixed_t vmem_out;
    logic step_ready;
    logic step_done;

    assign out = vmem_out; 

    single_neuron single_neuron_i(
        .clk(clk),
        .rst(rst),

        .current_in(current_in),

        .step_ready(step_ready),
        .step_done(step_done),
        .vmem_out(vmem_out)
    );

endmodule 