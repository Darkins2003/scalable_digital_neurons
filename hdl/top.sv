import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module top (
    input logic clk,
    input logic rst,

    output fixed_t out //temp
);

    fixed_t current_in;
    fixed_t vmem_out;

    single_neuron single_neuron_i(
        .clk(clk),
        .rst(rst),

        .current_in(current_in),
        .vmem_out(vmem_out)
    );

    assign out = vmem_out; // temp

endmodule 