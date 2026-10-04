import neuron_params_generated_pkg::*;

module three_neuron_registers (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        wr_en,
    input  logic [4:0]  wr_addr,
    input  logic [31:0] wr_data,
    input  logic [3:0]  wr_strb,
    input  logic [4:0]  rd_addr,
    output logic [31:0] rd_data,
    output logic        run_enable,
    output fixed_t      input_current,
    input  logic        network_step_valid,
    input  fixed_t      network_vmem_0,
    input  fixed_t      network_vmem_1,
    input  fixed_t      network_vmem_2
);
    localparam logic [4:0] CONTROL    = 5'h00;
    localparam logic [4:0] CURRENT    = 5'h04;
    localparam logic [4:0] STATUS     = 5'h08;
    localparam logic [4:0] STEP_COUNT = 5'h0c;
    localparam logic [4:0] VMEM_0     = 5'h10;
    localparam logic [4:0] VMEM_1     = 5'h14;
    localparam logic [4:0] VMEM_2     = 5'h18;

    logic [31:0] completed_steps;
    fixed_t vmem_snapshot_0;
    fixed_t vmem_snapshot_1;
    fixed_t vmem_snapshot_2;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            run_enable     <= 1'b0;
            input_current  <= '0;
            completed_steps <= '0;
            vmem_snapshot_0 <= INITIAL_STATE[0];
            vmem_snapshot_1 <= INITIAL_STATE[0];
            vmem_snapshot_2 <= INITIAL_STATE[0];
        end else begin
            if (network_step_valid && run_enable) begin
                completed_steps <= completed_steps + 1'b1;
                vmem_snapshot_0 <= network_vmem_0;
                vmem_snapshot_1 <= network_vmem_1;
                vmem_snapshot_2 <= network_vmem_2;
            end

            if (wr_en) begin
                case (wr_addr)
                    CONTROL: if (wr_strb[0]) begin
                        run_enable <= wr_data[0];
                        if (wr_data[0] && !run_enable) begin
                            completed_steps <= '0;
                            vmem_snapshot_0 <= INITIAL_STATE[0];
                            vmem_snapshot_1 <= INITIAL_STATE[0];
                            vmem_snapshot_2 <= INITIAL_STATE[0];
                        end
                    end
                    CURRENT: begin
                        for (int byte_index = 0; byte_index < 4; byte_index++)
                            if (wr_strb[byte_index])
                                input_current[byte_index*8 +: 8] <= wr_data[byte_index*8 +: 8];
                    end
                    default: ; // Status and neuron state snapshots are read only.
                endcase
            end
        end
    end

    always_comb begin
        case (rd_addr)
            CONTROL:    rd_data = {31'b0, run_enable};
            CURRENT:    rd_data = input_current;
            STATUS:     rd_data = {30'b0, (completed_steps != 0), run_enable};
            STEP_COUNT: rd_data = completed_steps;
            VMEM_0:     rd_data = vmem_snapshot_0;
            VMEM_1:     rd_data = vmem_snapshot_1;
            VMEM_2:     rd_data = vmem_snapshot_2;
            default:    rd_data = '0;
        endcase
    end
endmodule
