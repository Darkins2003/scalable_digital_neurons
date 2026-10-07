// AXI-Lite controlled three-neuron 1D network integration top.
module three_neuron_control_top (
    input  logic        s00_axi_aclk,
    input  logic        s00_axi_aresetn,
    input  logic [4:0]  s00_axi_awaddr,
    input  logic [2:0]  s00_axi_awprot,
    input  logic        s00_axi_awvalid,
    output logic        s00_axi_awready,
    input  logic [31:0] s00_axi_wdata,
    input  logic [3:0]  s00_axi_wstrb,
    input  logic        s00_axi_wvalid,
    output logic        s00_axi_wready,
    output logic [1:0]  s00_axi_bresp,
    output logic        s00_axi_bvalid,
    input  logic        s00_axi_bready,
    input  logic [4:0]  s00_axi_araddr,
    input  logic [2:0]  s00_axi_arprot,
    input  logic        s00_axi_arvalid,
    output logic        s00_axi_arready,
    output logic [31:0] s00_axi_rdata,
    output logic [1:0]  s00_axi_rresp,
    output logic        s00_axi_rvalid,
    input  logic        s00_axi_rready
);
    import neuron_params_generated_pkg::*;

    logic        reg_wr_en;
    logic [4:0]  reg_wr_addr;
    logic [31:0] reg_wr_data;
    logic [3:0]  reg_wr_strb;
    logic [4:0]  reg_rd_addr;
    logic [31:0] reg_rd_data;
    logic        ctrl_start;
    fixed_t      input_current;
    logic        network_step_valid;
    fixed_t      network_vmem_0;
    fixed_t      network_vmem_1;
    fixed_t      network_vmem_2;

    neuron_axil #(.C_S00_AXI_ADDR_WIDTH(5)) axi_adapter (.*);

    three_neuron_registers registers (
        .clk(s00_axi_aclk),
        .rst_n(s00_axi_aresetn),
        .wr_en(reg_wr_en),
        .wr_addr(reg_wr_addr),
        .wr_data(reg_wr_data),
        .wr_strb(reg_wr_strb),
        .rd_addr(reg_rd_addr),
        .rd_data(reg_rd_data),
        .ctrl_start(ctrl_start),
        .input_current(input_current),
        .network_step_valid(network_step_valid),
        .network_vmem_0(network_vmem_0),
        .network_vmem_1(network_vmem_1),
        .network_vmem_2(network_vmem_2)
    );

    three_neurons_1D network (
        .clk(s00_axi_aclk),
        .rst(!s00_axi_aresetn),
        .ctrl_start(ctrl_start),
        .current_in(input_current),
        .step_valid(network_step_valid),
        .vmem_0(network_vmem_0),
        .vmem_1(network_vmem_1),
        .vmem_2(network_vmem_2)
    );
endmodule
