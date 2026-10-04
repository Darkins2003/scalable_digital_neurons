import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module many_neurons_1D (
    input logic clk,
    input logic rst,

    input fixed_t current_in
);

    // Pipeline
    typedef struct packed {
        logic valid;
    } pipeline_t;

    localparam int PIPELINE_STAGES = 1;
    pipeline_t pipe [0:PIPELINE_STAGES-1];

    logic neuron_with_pulse_generator_valid_out[0:2];
    fixed_t excitatory_pulse [0:2];
    fixed_t inhibitory_pulse [0:2];

    logic [2:0] synapse_valid_out;

    fixed_t vmem_out [2:0];

    fixed_t current_in_neuron [0:2] = '{default:'0};

    fixed_t excitatory_current_contribution [0:2];
    fixed_t inhibitory_current_contribution [0:2];

    logic valid_in;
    logic start = 1;

    fixed_t current_in_neuron_0_reg;
    fixed_t current_in_neuron_1_reg;
    fixed_t current_in_neuron_2_reg;

    assign valid_in = pipe[0].valid & !rst;

    neuron_with_pulse_generator neuron_with_pulse_generator_0 (
        .clk(clk),
        .rst(rst),

        .current_in(current_in_neuron[0] + current_in),
        .valid_in(valid_in),
        .start(start),

        .valid_out(neuron_with_pulse_generator_valid_out[0]),
        .vmem_out(vmem_out[0]),
        .excitatory_pulse(excitatory_pulse[0]),
        .inhibitory_pulse(inhibitory_pulse[0])
    );

    synapse #(
        .SOURCE_NEURON_IDX(0),
        .TARGET_NEURON_IDX(1)
    ) synapse_0_1 (
        .clk(clk),
        .rst(rst),

        .valid_in(neuron_with_pulse_generator_valid_out[0]),
        .rx_vmem(vmem_out[1]),
        .excitatory_pulse(excitatory_pulse[0]),
        .inhibitory_pulse(inhibitory_pulse[0]),

        .excitatory_current_contribution(excitatory_current_contribution[0]),
        .inhibitory_current_contribution(inhibitory_current_contribution[0]),
        .valid_out(synapse_valid_out[0])
    );

    neuron_with_pulse_generator neuron_with_pulse_generator_1 (
        .clk(clk),
        .rst(rst),

        .current_in(current_in_neuron[1]),
        .valid_in(valid_in),
        .start(start),

        .valid_out(neuron_with_pulse_generator_valid_out[1]),
        .vmem_out(vmem_out[1]),
        .excitatory_pulse(excitatory_pulse[1]),
        .inhibitory_pulse(inhibitory_pulse[1])
    );

    synapse #(
        .SOURCE_NEURON_IDX(1),
        .TARGET_NEURON_IDX(2)
    ) synapse_1_2 (
        .clk(clk),
        .rst(rst),

        .valid_in(neuron_with_pulse_generator_valid_out[1]),
        .rx_vmem(vmem_out[2]),
        .excitatory_pulse(excitatory_pulse[1]),
        .inhibitory_pulse(inhibitory_pulse[1]),

        .excitatory_current_contribution(excitatory_current_contribution[1]),
        .inhibitory_current_contribution(inhibitory_current_contribution[1]),
        .valid_out(synapse_valid_out[1])
    );

    neuron_with_pulse_generator neuron_with_pulse_generator_2 (
        .clk(clk),
        .rst(rst),

        .current_in(current_in_neuron[2]),
        .valid_in(valid_in),
        .start(start),

        .valid_out(neuron_with_pulse_generator_valid_out[2]),
        .vmem_out(vmem_out[2]),
        .excitatory_pulse(excitatory_pulse[2]),
        .inhibitory_pulse(inhibitory_pulse[2])
    );

    synapse #(
        .SOURCE_NEURON_IDX(2),
        .TARGET_NEURON_IDX(0)
    ) synapse_2_0 (
        .clk(clk),
        .rst(rst),

        .valid_in(neuron_with_pulse_generator_valid_out[2]),
        .rx_vmem(vmem_out[0]),
        .excitatory_pulse(excitatory_pulse[2]),
        .inhibitory_pulse(inhibitory_pulse[2]),

        .excitatory_current_contribution(excitatory_current_contribution[2]),
        .inhibitory_current_contribution(inhibitory_current_contribution[2]),
        .valid_out(synapse_valid_out[2])
    );

    always @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                pipe[i] <= '0;
            end  

            current_in_neuron <= '{default:'0};

            start <= '1;

        end else begin
            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= &synapse_valid_out;
            start <= '0;

            if (&synapse_valid_out) begin
                current_in_neuron[0] <= inhibitory_current_contribution[2] + excitatory_current_contribution[2];
                current_in_neuron[1] <= inhibitory_current_contribution[0] + excitatory_current_contribution[0];
                current_in_neuron[2] <= inhibitory_current_contribution[1] + excitatory_current_contribution[1];
            end 
        end
    end
    
endmodule 