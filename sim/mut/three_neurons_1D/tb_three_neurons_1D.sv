`timescale 1ns/1ps
import neuron_params_generated_pkg::*;
import three_neuron_regs_pkg::*;

module tb_three_neurons_1D;
    parameter bit CLOCK_CONVERTER_ENABLED = 1'b0;
    // ------------------------------TOTAL STAGES = N/A------------------------------
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
    logic asynchronous_neuron_clock = 1'b0;
    logic asynchronous_neuron_reset_n = 1'b0;
    logic asynchronous_neuron_clock_enabled = 1'b0;
    realtime neuron_clock_half_period = 7.0;
    realtime neuron_clock_phase_offset = 1.0;
    wire selected_neuron_clock = $test$plusargs("tc_006_clock_domain_crossing") ? asynchronous_neuron_clock : clk;
    wire selected_neuron_reset_n = $test$plusargs("tc_006_clock_domain_crossing") ? asynchronous_neuron_reset_n : rst_n;
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

    wire [4:0] accelerator_write_address;
    wire [2:0] accelerator_write_protection;
    wire accelerator_write_address_valid;
    wire accelerator_write_address_ready;
    wire [31:0] accelerator_write_data;
    wire [3:0] accelerator_write_strobes;
    wire accelerator_write_data_valid;
    wire accelerator_write_data_ready;
    wire [1:0] accelerator_write_response;
    wire accelerator_write_response_valid;
    wire accelerator_write_response_ready;
    wire [4:0] accelerator_read_address;
    wire [2:0] accelerator_read_protection;
    wire accelerator_read_address_valid;
    wire accelerator_read_address_ready;
    wire [31:0] accelerator_read_data;
    wire [1:0] accelerator_read_response;
    wire accelerator_read_data_valid;
    wire accelerator_read_data_ready;

    generate
        if (CLOCK_CONVERTER_ENABLED) begin : clock_converter_enabled
            design_1_axi_clock_converter_0_0 clock_converter (
                .s_axi_aclk(clk), .s_axi_aresetn(rst_n),
                .m_axi_aclk(selected_neuron_clock), .m_axi_aresetn(selected_neuron_reset_n),
                .s_axi_awaddr(awaddr),
                .s_axi_awprot(awprot),
                .s_axi_awvalid(awvalid),
                .s_axi_awready(awready),
                .s_axi_wdata(wdata),
                .s_axi_wstrb(wstrb),
                .s_axi_wvalid(wvalid),
                .s_axi_wready(wready),
                .s_axi_bresp(bresp),
                .s_axi_bvalid(bvalid),
                .s_axi_bready(bready),
                .s_axi_araddr(araddr),
                .s_axi_arprot(arprot),
                .s_axi_arvalid(arvalid),
                .s_axi_arready(arready),
                .s_axi_rdata(rdata),
                .s_axi_rresp(rresp),
                .s_axi_rvalid(rvalid),
                .s_axi_rready(rready),
                .m_axi_awaddr(accelerator_write_address),
                .m_axi_awprot(accelerator_write_protection),
                .m_axi_awvalid(accelerator_write_address_valid),
                .m_axi_awready(accelerator_write_address_ready),
                .m_axi_wdata(accelerator_write_data),
                .m_axi_wstrb(accelerator_write_strobes),
                .m_axi_wvalid(accelerator_write_data_valid),
                .m_axi_wready(accelerator_write_data_ready),
                .m_axi_bresp(accelerator_write_response),
                .m_axi_bvalid(accelerator_write_response_valid),
                .m_axi_bready(accelerator_write_response_ready),
                .m_axi_araddr(accelerator_read_address),
                .m_axi_arprot(accelerator_read_protection),
                .m_axi_arvalid(accelerator_read_address_valid),
                .m_axi_arready(accelerator_read_address_ready),
                .m_axi_rdata(accelerator_read_data),
                .m_axi_rresp(accelerator_read_response),
                .m_axi_rvalid(accelerator_read_data_valid),
                .m_axi_rready(accelerator_read_data_ready)
            );
        end else begin : clock_converter_disabled
            assign accelerator_write_address = awaddr;
            assign accelerator_write_protection = awprot;
            assign accelerator_write_address_valid = awvalid;
            assign awready = accelerator_write_address_ready;
            assign accelerator_write_data = wdata;
            assign accelerator_write_strobes = wstrb;
            assign accelerator_write_data_valid = wvalid;
            assign wready = accelerator_write_data_ready;
            assign bresp = accelerator_write_response;
            assign bvalid = accelerator_write_response_valid;
            assign accelerator_write_response_ready = bready;
            assign accelerator_read_address = araddr;
            assign accelerator_read_protection = arprot;
            assign accelerator_read_address_valid = arvalid;
            assign arready = accelerator_read_address_ready;
            assign rdata = accelerator_read_data;
            assign rresp = accelerator_read_response;
            assign rvalid = accelerator_read_data_valid;
            assign accelerator_read_data_ready = rready;
        end
    endgenerate

    three_neuron_control_top axil_dut (
        .s00_axi_aclk(selected_neuron_clock), .s00_axi_aresetn(selected_neuron_reset_n),
        .neuron_clk(selected_neuron_clock), .neuron_aresetn(selected_neuron_reset_n),
        .s00_axi_awaddr(accelerator_write_address), .s00_axi_awprot(accelerator_write_protection),
        .s00_axi_awvalid(accelerator_write_address_valid), .s00_axi_awready(accelerator_write_address_ready),
        .s00_axi_wdata(accelerator_write_data), .s00_axi_wstrb(accelerator_write_strobes),
        .s00_axi_wvalid(accelerator_write_data_valid), .s00_axi_wready(accelerator_write_data_ready),
        .s00_axi_bresp(accelerator_write_response), .s00_axi_bvalid(accelerator_write_response_valid), .s00_axi_bready(accelerator_write_response_ready),
        .s00_axi_araddr(accelerator_read_address), .s00_axi_arprot(accelerator_read_protection),
        .s00_axi_arvalid(accelerator_read_address_valid), .s00_axi_arready(accelerator_read_address_ready),
        .s00_axi_rdata(accelerator_read_data), .s00_axi_rresp(accelerator_read_response),
        .s00_axi_rvalid(accelerator_read_data_valid), .s00_axi_rready(accelerator_read_data_ready)
    );

    three_neurons_1D reference_network (
        .clk(selected_neuron_clock), .rst(!selected_neuron_reset_n),
        .ctrl_start(axil_dut.ctrl_start),
        .current_in(axil_dut.input_current),
        .step_valid(ref_step_valid),
        .vmem_0(ref_vmem_0), .vmem_1(ref_vmem_1), .vmem_2(ref_vmem_2)
    );

    always @(posedge selected_neuron_clock) begin
        if (!selected_neuron_reset_n) begin
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
        end else if (!$test$plusargs("tc_006_clock_domain_crossing")) begin
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
    `include "tc_005_timing.svh"
    `include "tc_006_clock_domain_crossing.svh"
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
        end else if ($test$plusargs("tc_005_timing")) begin
            run_tc_005_timing();
            $display("PASS: tc_005_timing");
        end else if ($test$plusargs("tc_006_clock_domain_crossing")) begin
            run_tc_006_clock_domain_crossing();
            $display("PASS: tc_006_clock_domain_crossing");
        end else if ($test$plusargs("tc_010_c_reference_trace")) begin
            run_tc_010_c_reference_trace();
            $display("PASS: tc_010_c_reference_trace");
        end else begin
            $fatal(1, "Select a three-neuron testcase with -testplusarg");
        end
        $finish;
    end
endmodule
