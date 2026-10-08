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
    // Shared engine infrastructure
    logic [1:0] id_in = 2'd0;
    logic [1:0] id_out;
    logic [1:0] id_out_d [0:1];
    logic [1:0] neuron_with_pulse_generator_id_out;
    logic [1:0] neuron_with_pulse_generator_1_id_out;
    logic [1:0] neuron_with_pulse_generator_2_id_out;
    logic ready;
    logic cycle_done;
    logic cycle_done_pulse;
    logic valid_in;
    logic [1:0] cycle_count = '0;
    logic [1:0] source_neuron_idx;
    logic [1:0] target_neuron_idx;
    fixed_t rx_vmem;
    logic [2:0] neuron_ready; 
    logic [2:0] synapse_input_done;
    logic [2:0] start_cnt;

    logic neuron_with_pulse_generator_valid_out;
    fixed_t excitatory_pulse;
    fixed_t inhibitory_pulse;
    fixed_t excitatory_pulse_synapse_in;
    fixed_t inhibitory_pulse_synapse_in;
    fixed_t excitatory_pulse_reg [0:2];
    fixed_t inhibitory_pulse_reg [0:2];

    logic synapse_valid_in;
    logic [1:0] synapse_id_in;
    logic synapse_valid_out;
    logic [2:0] synapse_valid_out_d;

    fixed_t vmem_out_reg [2:0] = '{default:INITIAL_STATE[0]};
    fixed_t vmem_out;
    logic [1:0] single_neuron_id_out;
    logic single_neuron_valid_out;

    fixed_t current_in_neuron [0:2] = '{default:'0};

    fixed_t excitatory_current_contribution;
    fixed_t inhibitory_current_contribution;
    fixed_t excitatory_current_contribution_reg [0:2];
    fixed_t inhibitory_current_contribution_reg [0:2];

    logic running;
    logic startup_complete = 1'b0;
    logic start_pulse = '0;

    fixed_t current_in_neuron_0_reg;
    fixed_t current_in_neuron_1_reg;
    fixed_t current_in_neuron_2_reg;

    assign step_valid = cycle_done_pulse & startup_complete; // Disregard first cycle
    assign vmem_0 = vmem_out_reg[0];
    assign vmem_1 = vmem_out_reg[1];
   assign vmem_2 = vmem_out_reg[2];

    neuron_with_pulse_generator neuron_with_pulse_generator_i (
        .clk(clk),
        .rst(rst),

        .current_in(current_in_neuron[id_in]),
        .valid_in(valid_in),
        .start_pulse(start_pulse),
        .id_in(id_in),

        .single_neuron_valid_out(single_neuron_valid_out),
        .single_neuron_id_out(single_neuron_id_out),
        .vmem_out(vmem_out),

        .ready(ready),
        .valid_out(neuron_with_pulse_generator_valid_out),
        .id_out(neuron_with_pulse_generator_id_out),
        .excitatory_pulse(excitatory_pulse),
        .inhibitory_pulse(inhibitory_pulse)
    );

    synapse synapse_i (
        .clk(clk),
        .rst(rst),

        .valid_in(synapse_valid_in),
        .id_in(synapse_id_in),
        .rx_vmem(rx_vmem),
        .excitatory_pulse(excitatory_pulse_synapse_in),
        .inhibitory_pulse(inhibitory_pulse_synapse_in),
        .source_neuron_idx(source_neuron_idx),
        .target_neuron_idx(target_neuron_idx),

        .excitatory_current_contribution(excitatory_current_contribution),
        .inhibitory_current_contribution(inhibitory_current_contribution),
        .valid_out(synapse_valid_out),
        .id_out(id_out)
    );

    always @(posedge clk) begin
        if (rst) begin
            current_in_neuron <= '{default:'0};
            vmem_out_reg <= '{default:INITIAL_STATE[0]};

            id_in <= 2'd0;
            valid_in <= 1'b0;
            synapse_valid_out_d <= 1'b0;
            cycle_count <= 2'd0;

            running <= '0;
            start_pulse <= '0;
            startup_complete <= 1'b0;

            id_out_d <= '{default:2'd0};
            excitatory_current_contribution_reg <= '{default:'0};
            inhibitory_current_contribution_reg <= '{default:'0};

            excitatory_pulse_reg <= '{default:'0};
            inhibitory_pulse_reg <= '{default:'0};
            excitatory_pulse_synapse_in <= '0;
            inhibitory_pulse_synapse_in <= '0;

            synapse_valid_in <= 1'b0;
            synapse_id_in <= 2'd0;
            rx_vmem <= INITIAL_STATE[0];
            source_neuron_idx <= 2'd0;
            target_neuron_idx <= 2'd0;

            cycle_done <= '0;
            neuron_ready <= '0;
            synapse_input_done <= '0;
            start_cnt <= '0;
            cycle_done_pulse <= '0;

        end else begin
            // ------------------------------SEQUENCE-----------------------------
            // Leave one idle clock between inputs so each neuron's excitatory and inhibitory calculations have a 1 clk cycle gap in synaptic_pulse_generator
            if (ctrl_start && !running) begin
                running <= '1;
                start_pulse <= '1;
                start_cnt <= 3'd1;
                id_in <= 2'd0;
            end else if (running && start_cnt < 3'd6 && start_cnt[0]) begin // Odd (idle clk cycle)
                start_pulse <= '0;
                start_cnt <= start_cnt + 3'd1;
            end else if (running && start_cnt < 3'd6 && !start_cnt[0]) begin // Even (active clk cycle)
                start_pulse <= '1;
                id_in <= start_cnt >> 1;
                start_cnt <= start_cnt + 3'd1;
            end else begin
                start_pulse <= '0;
            end 

            
            // Assert valid_in 
            valid_in <= '0;
            if (ready && startup_complete && !valid_in) begin
                if (id_in == 2'd0) begin
                    if (cycle_done) begin
                        valid_in <= '1;
                        cycle_done <= '0;
                    end 
                end else begin
                    valid_in <= '1;
                end 
            end 

            // Increment id_in
            if (valid_in) begin
                if (id_in == 2'd2) begin
                    id_in <= '0;
                end else begin
                    id_in <= id_in + 2'd1;
                end
            end 

            // ------------------------------NEURON_WITH_PULSE_GEN (SINGLE_NEURON) STAGE 0-----------------------------
            if (single_neuron_valid_out) begin
                vmem_out_reg[single_neuron_id_out] <= vmem_out;
            end 

            // ------------------------------NEURON_WITH_PULSE_GEN (PULSE/TRIANGULAR GENERATOR) STAGE 0-----------------------------
            if (neuron_with_pulse_generator_valid_out) begin
                excitatory_pulse_reg[neuron_with_pulse_generator_id_out] <= excitatory_pulse;
                inhibitory_pulse_reg[neuron_with_pulse_generator_id_out] <= inhibitory_pulse;

                // Check to see if the previous neuron's vmem has been caluclated next to see if we can move onto synapse calculations
                case (neuron_with_pulse_generator_id_out)
                    2'd0: neuron_ready[0] <= '1; // Latch high until new cycle starts
                    2'd1: neuron_ready[1] <= '1; // Latch high until new cycle starts
                    2'd2: neuron_ready[2] <= '1; // Latch high until new cycle starts
                endcase
            end 

            // ------------------------------NEURON_WITH_PULSE_GEN (PULSE/TRIANGULAR GENERATOR) WAITING-----------------------------
            if (neuron_ready[0] && neuron_ready[1] && !synapse_input_done[0]) begin
                synapse_valid_in <= '1;
                synapse_id_in <= 2'd0;
                rx_vmem <= vmem_out_reg[1];
                excitatory_pulse_synapse_in <= excitatory_pulse_reg[0];
                inhibitory_pulse_synapse_in <= inhibitory_pulse_reg[0];
                source_neuron_idx <= 2'd0;
                target_neuron_idx <= 2'd1;

                synapse_input_done[0] <= '1;
            end else if (neuron_ready[1] && neuron_ready[2] && !synapse_input_done[1]) begin
                synapse_valid_in <= '1;
                synapse_id_in <= 2'd1;
                rx_vmem <= vmem_out_reg[2];
                excitatory_pulse_synapse_in <= excitatory_pulse_reg[1];
                inhibitory_pulse_synapse_in <= inhibitory_pulse_reg[1];
                source_neuron_idx <= 2'd1;
                target_neuron_idx <= 2'd2;

                synapse_input_done[1] <= '1;
            end else if (neuron_ready[2] && neuron_ready[0] && !synapse_input_done[2]) begin
                synapse_valid_in <= '1;
                synapse_id_in <= 2'd2;
                rx_vmem <= vmem_out_reg[0];
                excitatory_pulse_synapse_in <= excitatory_pulse_reg[2];
                inhibitory_pulse_synapse_in <= inhibitory_pulse_reg[2];
                source_neuron_idx <= 2'd2;
                target_neuron_idx <= 2'd0;

                synapse_input_done[2] <= '1;
            end else begin
                synapse_valid_in <= '0;
            end 

            // ------------------------------POST SYNAPSE STAGE 0-----------------------------
            synapse_valid_out_d[0] <= synapse_valid_out;
            id_out_d[0] <= id_out;

            if (synapse_valid_out) begin
                inhibitory_current_contribution_reg[id_out] <= inhibitory_current_contribution;
                excitatory_current_contribution_reg[id_out] <= excitatory_current_contribution;
            end 

            // ------------------------------POST SYNAPSE STAGE 1-----------------------------
            synapse_valid_out_d[1] <= synapse_valid_out_d[0];
            id_out_d[1] <= id_out_d[0];

            if (synapse_valid_out_d[0]) begin
                case (id_out_d[0])
                    2'd0: begin
                        current_in_neuron[1] <= inhibitory_current_contribution_reg[0] + excitatory_current_contribution_reg[0];
                    end
                    2'd1: begin
                        current_in_neuron[2] <= inhibitory_current_contribution_reg[1] + excitatory_current_contribution_reg[1];
                    end
                    2'd2: begin
                        current_in_neuron[0] <= inhibitory_current_contribution_reg[2] + excitatory_current_contribution_reg[2];
                    end
                endcase
            end

            // ------------------------------POST SYNAPSE STAGE 2-----------------------------
            synapse_valid_out_d[2] <= synapse_valid_out_d[1];

            if (synapse_valid_out_d[1] && id_out_d[1] == 2'd2) begin
                current_in_neuron[0] <= current_in_neuron[0] + current_in;
            end  
            // ------------------------------POST SYNAPSE STAGE 3-----------------------------
            cycle_done_pulse <= '0;
            
            if (synapse_valid_out_d[2]) begin
                if (cycle_count == 2'd2) begin
                    if (startup_complete) begin
                        cycle_done_pulse <= '1;
                    end 

                    cycle_done <= '1;
                    cycle_count <= '0;
                    startup_complete <= 1'b1; // Asserts to 1 on the first cycle at stays at 1 until reset. Used to disregard the first cycle

                    neuron_ready <= '0;
                    synapse_input_done <= '0;

                    // If startup has finished, manually reset id_in
                    if (!startup_complete) begin
                        id_in <= 2'd0;
                    end 
                end else begin
                    cycle_count <= cycle_count + 2'd1;
                end 
            end 
        end
    end
    
endmodule 
