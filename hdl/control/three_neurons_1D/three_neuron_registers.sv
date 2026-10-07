import neuron_params_generated_pkg::*;
import three_neuron_regs_pkg::*;

module three_neuron_registers (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        wr_en,
    input  logic [4:0]  wr_addr,
    input  logic [31:0] wr_data,
    input  logic [3:0]  wr_strb,
    input  logic [4:0]  rd_addr,
    output logic [31:0] rd_data,
    output logic        ctrl_start,
    output fixed_t      input_current,
    input  logic        network_step_valid,
    input  fixed_t      network_vmem_0,
    input  fixed_t      network_vmem_1,
    input  fixed_t      network_vmem_2
);
    logic [31:0] completed_steps;
    logic [31:0] status_value;
    logic run_requested;
    fixed_t vmem_snapshot_0;
    fixed_t vmem_snapshot_1;
    fixed_t vmem_snapshot_2;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            ctrl_start     <= 1'b0;
            run_requested  <= REG_CONTROL.reset_value[CONTROL_START.lsb];
            input_current  <= fixed_t'(REG_CURRENT.reset_value);
            completed_steps <= REG_STEP_COUNT.reset_value;
            vmem_snapshot_0 <= fixed_t'(REG_VMEM_0.reset_value);
            vmem_snapshot_1 <= fixed_t'(REG_VMEM_1.reset_value);
            vmem_snapshot_2 <= fixed_t'(REG_VMEM_2.reset_value);
        end else begin
            ctrl_start <= 1'b0;

            if (network_step_valid) begin
                completed_steps <= completed_steps + 1'b1;
                vmem_snapshot_0 <= network_vmem_0;
                vmem_snapshot_1 <= network_vmem_1;
                vmem_snapshot_2 <= network_vmem_2;
            end

            if (wr_en) begin
                case (wr_addr)
                    REG_CONTROL.offset: if (wr_strb[0]) begin
                        if (wr_data[CONTROL_START.lsb]) begin
                            ctrl_start <= 1'b1;
                            run_requested <= 1'b1;
                        end
                    end
                    REG_CURRENT.offset: begin
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
        status_value = REG_STATUS.reset_value;
        status_value[STATUS_START_REQUESTED.lsb] = run_requested;
        status_value[STATUS_HAS_STEP.lsb] = (completed_steps != REG_STEP_COUNT.reset_value);
        case (rd_addr)
            REG_CONTROL.offset:    rd_data = REG_CONTROL.reset_value;
            REG_CURRENT.offset:    rd_data = input_current;
            REG_STATUS.offset:     rd_data = status_value;
            REG_STEP_COUNT.offset: rd_data = completed_steps;
            REG_VMEM_0.offset:     rd_data = vmem_snapshot_0;
            REG_VMEM_1.offset:     rd_data = vmem_snapshot_1;
            REG_VMEM_2.offset:     rd_data = vmem_snapshot_2;
            default:    rd_data = '0;
        endcase
    end
endmodule
