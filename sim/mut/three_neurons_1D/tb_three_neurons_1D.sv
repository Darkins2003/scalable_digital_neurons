`timescale 1ns/1ps
import neuron_params_generated_pkg::*;

module tb_three_neurons_1D;
    logic clk = 0;
    logic rst = 1;
    fixed_t current_in = 0;
    integer stimulus_file, trace_file, read_count, steps, cycles = 0;

    three_neurons_1D dut (.clk(clk), .rst(rst), .current_in(current_in));
    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!rst) begin
            cycles <= cycles + 1;
            if (cycles > (steps + 1) * 100)
                $fatal(1, "Timed out waiting for network step completion");
        end
    end

    initial begin
        stimulus_file = $fopen("stimulus.txt", "r");
        trace_file = $fopen("hdl_trace.csv", "w");
        if (!stimulus_file || !trace_file)
            $fatal(1, "Cannot open stimulus.txt or hdl_trace.csv");
        read_count = $fscanf(stimulus_file, "%d", steps);
        if (read_count != 1 || steps < 1)
            $fatal(1, "Invalid stimulus step count");
        read_count = $fscanf(stimulus_file, "%d", current_in);
        if (read_count != 1)
            $fatal(1, "Missing stimulus for step 0");
        $fwrite(trace_file, "step,current,n0_vmem,n0_vk,n0_vg,n0_vna,n1_vmem,n1_vk,n1_vg,n1_vna,n2_vmem,n2_vk,n2_vg,n2_vna,n0_te,n0_ti,n1_te,n1_ti,n2_te,n2_ti\n");
        repeat (3) @(negedge clk);
        rst = 0;
        // The startup pulse/synapse pass computes current from the initial
        // states. It is preparation for C step 0, not a completed Euler step.
        @(posedge dut.synapse_valid_out[0]);
        #1;
        if (dut.synapse_valid_out !== 3'b111)
            $fatal(1, "Startup synapse completion signals differ");
        if (dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[0] !== INITIAL_STATE[0])
            $fatal(1, "Neuron updated during synapse initialization");
        if (dut.excitatory_current_contribution[0] !== 32'sd1091 ||
            dut.excitatory_current_contribution[1] !== 32'sd1091 ||
            dut.excitatory_current_contribution[2] !== 32'sd1091)
            $fatal(1, "Initial synaptic current does not match C (1091 Q8)");
        for (int step = 0; step < steps; step++) begin
            @(posedge dut.synapse_valid_out[0]);
            #1;
            if (dut.synapse_valid_out !== 3'b111)
                $fatal(1, "Synapse completion signals differ at step %0d", step);
            if ($isunknown({dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[0],
                            dut.neuron_with_pulse_generator_1.single_neuron_i.neuron_state_variables[0],
                            dut.neuron_with_pulse_generator_2.single_neuron_i.neuron_state_variables[0]}))
                $fatal(1, "Unknown neuron state at step %0d", step);
            $fwrite(trace_file, "%0d,%0d", step, current_in);
            for (int j = 0; j < 4; j++)
                $fwrite(trace_file, ",%0d", dut.neuron_with_pulse_generator_0.single_neuron_i.neuron_state_variables[j]);
            for (int j = 0; j < 4; j++)
                $fwrite(trace_file, ",%0d", dut.neuron_with_pulse_generator_1.single_neuron_i.neuron_state_variables[j]);
            for (int j = 0; j < 4; j++)
                $fwrite(trace_file, ",%0d", dut.neuron_with_pulse_generator_2.single_neuron_i.neuron_state_variables[j]);
            $fwrite(trace_file, ",%0d,%0d,%0d,%0d,%0d,%0d\n",
                dut.neuron_with_pulse_generator_0.synaptic_triangular_generator_i.excitatory_triangular_state_reg,
                dut.neuron_with_pulse_generator_0.synaptic_triangular_generator_i.inhibitory_triangular_state_reg,
                dut.neuron_with_pulse_generator_1.synaptic_triangular_generator_i.excitatory_triangular_state_reg,
                dut.neuron_with_pulse_generator_1.synaptic_triangular_generator_i.inhibitory_triangular_state_reg,
                dut.neuron_with_pulse_generator_2.synaptic_triangular_generator_i.excitatory_triangular_state_reg,
                dut.neuron_with_pulse_generator_2.synaptic_triangular_generator_i.inhibitory_triangular_state_reg);
            if (step + 1 < steps) begin
                @(negedge clk);
                read_count = $fscanf(stimulus_file, "%d", current_in);
                if (read_count != 1)
                    $fatal(1, "Missing stimulus for step %0d", step + 1);
            end
        end
        $fclose(stimulus_file);
        $fclose(trace_file);
        $display("Recorded %0d network steps", steps);
        $finish;
    end
endmodule
