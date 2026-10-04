`timescale 1ns/1ps

import neuron_params_generated_pkg::*;

module tb_three_neurons_1D_axil;
    logic clk = 1'b0;
    always #5 clk = ~clk;

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
    logic [31:0] vmem_read_0, vmem_read_1, vmem_read_2;

    three_neuron_control_top dut (
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

    // Reference network sees the intended current, rather than the AXI register
    // output. Matching snapshots demonstrate that the register reaches all
    // three neurons through the existing 1D network RTL.
    three_neurons_1D reference_network (
        .clk(clk), .rst(!rst_n || !dut.run_enable),
        .current_in(32'sd256000),
        .step_valid(ref_step_valid),
        .vmem_0(ref_vmem_0), .vmem_1(ref_vmem_1), .vmem_2(ref_vmem_2)
    );

    always @(posedge clk) begin
        if (!rst_n) begin
            ref_count <= 0;
        end else if (ref_step_valid && dut.run_enable) begin
            if (ref_count >= 63) $fatal(1, "Reference history overflow");
            ref_history_0[ref_count+1] <= ref_vmem_0;
            ref_history_1[ref_count+1] <= ref_vmem_1;
            ref_history_2[ref_count+1] <= ref_vmem_2;
            ref_count <= ref_count + 1;
        end
    end

    task automatic send_aw(input logic [4:0] addr, input int delay_cycles);
        repeat (delay_cycles) @(negedge clk);
        @(negedge clk);
        awaddr = addr;
        awvalid = 1'b1;
        do @(posedge clk); while (!awready);
        @(negedge clk);
        awvalid = 1'b0;
    endtask

    task automatic send_w(input logic [31:0] data, input logic [3:0] strb,
                          input int delay_cycles);
        repeat (delay_cycles) @(negedge clk);
        @(negedge clk);
        wdata = data;
        wstrb = strb;
        wvalid = 1'b1;
        do @(posedge clk); while (!wready);
        @(negedge clk);
        wvalid = 1'b0;
    endtask

    task automatic axi_write(input logic [4:0] addr, input logic [31:0] data,
                             input logic [3:0] strb,
                             input int aw_delay, input int w_delay);
        fork
            send_aw(addr, aw_delay);
            send_w(data, strb, w_delay);
        join
        @(negedge clk);
        bready = 1'b1;
        do @(posedge clk); while (!bvalid);
        if (bresp !== 2'b00) $fatal(1, "AXI write error at %h", addr);
        @(negedge clk);
        bready = 1'b0;
    endtask

    task automatic axi_read(input logic [4:0] addr, output logic [31:0] data);
        @(negedge clk);
        araddr = addr;
        arvalid = 1'b1;
        do @(posedge clk); while (!arready);
        @(negedge clk);
        arvalid = 1'b0;
        rready = 1'b1;
        do @(posedge clk); while (!rvalid);
        if (rresp !== 2'b00) $fatal(1, "AXI read error at %h", addr);
        data = rdata;
        @(negedge clk);
        rready = 1'b0;
    endtask

    task automatic expect_read(input logic [4:0] addr, input logic [31:0] expected);
        logic [31:0] actual;
        axi_read(addr, actual);
        if (actual !== expected)
            $fatal(1, "Register %h: expected %h, got %h", addr, expected, actual);
    endtask

    initial begin
        #1000000;
        $fatal(1, "AXI/three-neuron integration timed out");
    end

    initial begin
        repeat (5) @(negedge clk);
        rst_n = 1'b1;

        expect_read(5'h00, 32'h0);
        expect_read(5'h04, 32'h0);
        expect_read(5'h08, 32'h0);
        expect_read(5'h0c, 32'h0);
        expect_read(5'h10, INITIAL_STATE[0]);
        expect_read(5'h14, INITIAL_STATE[0]);
        expect_read(5'h18, INITIAL_STATE[0]);

        // Exercise independent address/data arrival and byte strobes.
        axi_write(5'h04, 32'h12345678, 4'b0001, 2, 0);
        expect_read(5'h04, 32'h00000078);
        axi_write(5'h04, 32'd256000, 4'hf, 0, 3);
        expect_read(5'h04, 32'd256000);

        axi_write(5'h00, 32'h1, 4'hf, 0, 0);
        expect_read(5'h00, 32'h1);

        count_read = 0;
        for (int poll = 0; poll < 100 && count_read < 3; poll++)
            axi_read(5'h0c, count_read);
        if (count_read < 3) $fatal(1, "Three-neuron network did not complete three steps");

        // Hold the network in reset while preserving the captured register
        // values, so all three AXI reads refer to the same completed step.
        axi_write(5'h00, 32'h0, 4'hf, 0, 0);
        expect_read(5'h00, 32'h0);
        axi_read(5'h0c, count_read);
        if (count_read < 3 || count_read > 63)
            $fatal(1, "Unexpected completed-step count %0d", count_read);
        expect_read(5'h08, 32'h2);
        axi_read(5'h10, vmem_read_0);
        axi_read(5'h14, vmem_read_1);
        axi_read(5'h18, vmem_read_2);

        if (ref_count != count_read)
            $fatal(1, "Reference step count %0d differs from AXI %0d", ref_count, count_read);
        if (vmem_read_0 !== ref_history_0[count_read] ||
            vmem_read_1 !== ref_history_1[count_read] ||
            vmem_read_2 !== ref_history_2[count_read])
            $fatal(1, "Three-neuron VMEM snapshots differ from reference at step %0d", count_read);
        if (vmem_read_0 === INITIAL_STATE[0])
            $fatal(1, "Neuron 0 did not respond to the programmed input current");

        // Read-only counters and state snapshots ignore software writes.
        axi_write(5'h0c, 32'hffffffff, 4'hf, 0, 0);
        expect_read(5'h0c, count_read);

        $display("PASS: AXI-Lite configured three_neurons_1D; %0d steps and three VMEM snapshots matched", count_read);
        $finish;
    end
endmodule
