import neuron_params_generated_pkg::*;
import neuron_params_pkg::*;
import fixed_point_package::*;

module three_neurons_1D (
    input logic clk,
    input logic rst,

    input logic ctrl_start,
    input fixed_t current_in,

    output logic step_valid,
    output fixed_t vmem_0,
    output fixed_t vmem_1,
    output fixed_t vmem_2
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
    logic running;
    logic startup_complete = 1'b0;
    logic start_pulse = '0;

    fixed_t current_in_neuron_0_reg;
    fixed_t current_in_neuron_1_reg;
    fixed_t current_in_neuron_2_reg;

    assign valid_in = pipe[0].valid & !rst;

    assign step_valid = pipe[0].valid & startup_complete; // Disregard first cycle
    assign vmem_0 = vmem_out[0];
    assign vmem_1 = vmem_out[1];
    assign vmem_2 = vmem_out[2];

    neuron_with_pulse_generator neuron_with_pulse_generator_0 (
        .clk(clk),
        .rst(rst),

        .current_in(current_in_neuron[0] + current_in),
        .valid_in(valid_in),
        .start_pulse(start_pulse),

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
        .start_pulse(start_pulse),

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
        .start_pulse(start_pulse),

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

            running <= '0;
            start_pulse <= '0;
            startup_complete <= 1'b0;

        end else begin
            if (ctrl_start && !running) begin
                running <= '1;
                start_pulse <= '1;
            end else begin
                start_pulse <= '0;
            end

            // ------------------------------STAGE 0-----------------------------
            pipe[0].valid <= &synapse_valid_out;

            if (&synapse_valid_out) begin
                startup_complete <= 1'b1; // Asserts to 1 on the first cycle at stays at 1 until reset. Used to disregard the first cycle

                current_in_neuron[0] <= inhibitory_current_contribution[2] + excitatory_current_contribution[2];
                current_in_neuron[1] <= inhibitory_current_contribution[0] + excitatory_current_contribution[0];
                current_in_neuron[2] <= inhibitory_current_contribution[1] + excitatory_current_contribution[1];
            end 

        end
    end
    
endmodule 
