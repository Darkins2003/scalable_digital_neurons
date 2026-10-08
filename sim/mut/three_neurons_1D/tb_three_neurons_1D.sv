`timescale 1ns/1ps
import neuron_params_generated_pkg::*;
import three_neuron_regs_pkg::*;

module tb_three_neurons_1D;
    logic clk = 1'b0;
    always #5 clk = ~clk;
    logic rst = 1;
    logic ctrl_start = 0;
    fixed_t current_in = 0;
    integer stimulus_file_handle, trace_file_handle, items_read;
    integer total_steps = 0;
    integer elapsed_cycles = 0;
    logic network_step_valid;
    logic [2:0] completed_synapse_ids = '0;
    logic startup_observed = 1'b0;
    logic previous_step_valid = 1'b0;


    three_neurons_1D dut (
        .clk(clk), .rst(rst),
        .ctrl_start(ctrl_start),
        .current_in(current_in),
        .step_valid(network_step_valid),
        .vmem_0(), .vmem_1(), .vmem_2()
    );

    always @(negedge clk) begin
        if (rst) begin
            elapsed_cycles = 0;
            completed_synapse_ids = '0;
            startup_observed = 1'b0;
            previous_step_valid = 1'b0;
        end else if (dut.running) begin
            elapsed_cycles++;
            if (elapsed_cycles > 512) begin
                $fatal(1, "Network made no progress for 512 clocks");
            end
            if (dut.synapse_valid_out) begin
                if ($isunknown(dut.id_out) || dut.id_out > 2 || completed_synapse_ids[dut.id_out]) begin
                    $fatal(1, "Invalid or duplicate synapse result ID %0d", dut.id_out);
                end
                completed_synapse_ids[dut.id_out] = 1'b1;
            end
            if ((!startup_observed && dut.startup_complete) || network_step_valid) begin
                if (completed_synapse_ids !== 3'b111) begin
                    $fatal(1, "Network completed without results for all three synapses");
                end
                completed_synapse_ids = '0;
                elapsed_cycles = 0;
            end
            if (network_step_valid && previous_step_valid) begin
                $fatal(1, "step_valid lasted more than one clock");
            end
            startup_observed = dut.startup_complete;
            previous_step_valid = network_step_valid;
        end
    end

    logic rst_n = 1'b0;
    logic [4:0] awaddr = '0;
    logic [2:0] awprot = '0;
    logic awvalid = 1'b0;
    logic awready;
    logic [31:0] wdata = '0;
    logic [3:0] wstrb = '0;
    logic wvalid = 1'b0;
    logic wready;
    logic [1:0] bresp;
    logic bvalid;
    logic bready = 1'b0;
    logic [4:0] araddr = '0;
    logic [2:0] arprot = '0;
    logic arvalid = 1'b0;
    logic arready;
    logic [31:0] rdata;
    logic [1:0] rresp;
    logic rvalid;
    logic rready = 1'b0;

    logic ref_step_valid;
    fixed_t ref_vmem_0, ref_vmem_1, ref_vmem_2;
    fixed_t ref_history_0 [0:63];
    fixed_t ref_history_1 [0:63];
    fixed_t ref_history_2 [0:63];
    int ref_count = 0;
    logic [31:0] count_read;
    logic [31:0] count_after;
    logic [31:0] vmem_read_0, vmem_read_1, vmem_read_2;
    bit stable_snapshot;
    int start_pulse_count = 0;
    logic start_previous = 1'b0;

    three_neuron_control_top axil_dut (
        .s00_axi_aclk(clk), .s00_axi_aresetn(rst_n),
        .s00_axi_awaddr(awaddr), .s00_axi_awprot(awprot),
        .s00_axi_awvalid(awvalid), .s00_axi_awready(awready),
        .s00_axi_wdata(wdata), .s00_axi_wstrb(wstrb),
        .s00_axi_wvalid(wvalid), .s00_axi_wready(wready),
        .s00_axi_bresp(bresp), .s00_axi_bvalid(bvalid), .s00_axi_bready(bready),
        .s00_axi_araddr(araddr), .s00_axi_arprot(arprot),
        .s00_axi_arvalid(arvalid), .s00_axi_arready(arready),
        .s00_axi_rdata(rdata), .s00_axi_rresp(rresp),
        .s00_axi_rvalid(rvalid), .s00_axi_rready(rready)
    );

    three_neurons_1D reference_network (
        .clk(clk), .rst(!rst_n),
        .ctrl_start(axil_dut.ctrl_start),
        .current_in(axil_dut.input_current),
        .step_valid(ref_step_valid),
        .vmem_0(ref_vmem_0), .vmem_1(ref_vmem_1), .vmem_2(ref_vmem_2)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            ref_count <= 0;
        end else if (ref_step_valid) begin
            if (ref_count >= 63) begin
                $fatal(1, "Reference history overflow");
            end
            ref_history_0[ref_count+1] <= ref_vmem_0;
            ref_history_1[ref_count+1] <= ref_vmem_1;
            ref_history_2[ref_count+1] <= ref_vmem_2;
            ref_count <= ref_count + 1;
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            start_pulse_count <= 0;
            start_previous <= 1'b0;
        end else begin
            if (axil_dut.network.ctrl_start) begin
                if (start_previous) begin
                    $fatal(1, "ctrl_start lasted more than one clock");
                end
                start_pulse_count <= start_pulse_count + 1;
            end
            start_previous <= axil_dut.network.ctrl_start;
        end
    end

    `include "axi_lite_manager.svh"
    `include "axi_lite_register_methods.svh"
    `include "register_model_fixture.svh"

    `include "tc_001_reset_access.svh"
    `include "tc_002_axil_integration.svh"
    `include "tc_003_commands.svh"
    `include "tc_004_hardware_updates.svh"
    `include "tc_010_c_reference_trace.svh"

    initial begin
        if ($test$plusargs("tc_001_reset_access")) begin
            run_tc_001_reset_access();
            $display("PASS: tc_001_reset_access");
        end else if ($test$plusargs("tc_002_axil_integration")) begin
            run_tc_002_axil_integration();
            $display("PASS: tc_002_axil_integration");
        end else if ($test$plusargs("tc_003_commands")) begin
            run_tc_003_commands();
            $display("PASS: tc_003_commands");
        end else if ($test$plusargs("tc_004_hardware_updates")) begin
            run_tc_004_hardware_updates();
            $display("PASS: tc_004_hardware_updates");
        end else if ($test$plusargs("tc_010_c_reference_trace")) begin
            run_tc_010_c_reference_trace();
            $display("PASS: tc_010_c_reference_trace");
        end else begin
            $fatal(1, "Select a three-neuron testcase with -testplusarg");
        end
        $finish;
    end
endmodule
