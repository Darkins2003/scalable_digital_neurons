`timescale 1ns / 1ps

// One outstanding AXI4-Lite read and write. Address and write data may
// arrive on different cycles. The register model owns all register storage.
module neuron_axil_slave_lite_v1_0_S00_AXI #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 4
) (
    input  wire                                S_AXI_ACLK,
    input  wire                                S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]       S_AXI_AWADDR,
    input  wire [2:0]                          S_AXI_AWPROT,
    input  wire                                S_AXI_AWVALID,
    output wire                                S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]       S_AXI_WDATA,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0]   S_AXI_WSTRB,
    input  wire                                S_AXI_WVALID,
    output wire                                S_AXI_WREADY,
    output wire [1:0]                          S_AXI_BRESP,
    output reg                                 S_AXI_BVALID,
    input  wire                                S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]       S_AXI_ARADDR,
    input  wire [2:0]                          S_AXI_ARPROT,
    input  wire                                S_AXI_ARVALID,
    output wire                                S_AXI_ARREADY,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]       S_AXI_RDATA,
    output wire [1:0]                          S_AXI_RRESP,
    output reg                                 S_AXI_RVALID,
    input  wire                                S_AXI_RREADY,

    output wire                                reg_wr_en,
    output wire [C_S_AXI_ADDR_WIDTH-1:0]       reg_wr_addr,
    output wire [C_S_AXI_DATA_WIDTH-1:0]       reg_wr_data,
    output wire [(C_S_AXI_DATA_WIDTH/8)-1:0]   reg_wr_strb,
    output wire [C_S_AXI_ADDR_WIDTH-1:0]       reg_rd_addr,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]       reg_rd_data
);
    reg aw_pending;
    reg w_pending;
    reg [C_S_AXI_ADDR_WIDTH-1:0] aw_addr;
    reg [C_S_AXI_DATA_WIDTH-1:0] w_data;
    reg [(C_S_AXI_DATA_WIDTH/8)-1:0] w_strb;

    assign S_AXI_AWREADY = !aw_pending && !S_AXI_BVALID;
    assign S_AXI_WREADY  = !w_pending && !S_AXI_BVALID;
    assign S_AXI_BRESP   = 2'b00;
    assign S_AXI_ARREADY = !S_AXI_RVALID;
    assign S_AXI_RRESP   = 2'b00;

    assign reg_wr_en   = aw_pending && w_pending && !S_AXI_BVALID;
    assign reg_wr_addr = aw_addr;
    assign reg_wr_data = w_data;
    assign reg_wr_strb = w_strb;
    assign reg_rd_addr = S_AXI_ARADDR;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            aw_pending  <= 1'b0;
            w_pending   <= 1'b0;
            aw_addr     <= '0;
            w_data      <= '0;
            w_strb      <= '0;
            S_AXI_BVALID <= 1'b0;
            S_AXI_RVALID <= 1'b0;
            S_AXI_RDATA  <= '0;
        end else begin
            if (S_AXI_AWVALID && S_AXI_AWREADY) begin
                aw_addr    <= S_AXI_AWADDR;
                aw_pending <= 1'b1;
            end
            if (S_AXI_WVALID && S_AXI_WREADY) begin
                w_data    <= S_AXI_WDATA;
                w_strb    <= S_AXI_WSTRB;
                w_pending <= 1'b1;
            end
            if (reg_wr_en) begin
                aw_pending   <= 1'b0;
                w_pending    <= 1'b0;
                S_AXI_BVALID <= 1'b1;
            end else if (S_AXI_BVALID && S_AXI_BREADY) begin
                S_AXI_BVALID <= 1'b0;
            end

            if (S_AXI_ARVALID && S_AXI_ARREADY) begin
                S_AXI_RDATA  <= reg_rd_data;
                S_AXI_RVALID <= 1'b1;
            end else if (S_AXI_RVALID && S_AXI_RREADY) begin
                S_AXI_RVALID <= 1'b0;
            end
        end
    end

    // AXI protection fields are deliberately unused by this local peripheral.
    wire unused_prot = &{1'b0, S_AXI_AWPROT, S_AXI_ARPROT};
endmodule
