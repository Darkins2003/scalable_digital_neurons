    logic register_reset_n = 1'b0;
    logic register_write_enable = 1'b0;
    logic [4:0] register_write_address = '0;
    logic [31:0] register_write_data = '0;
    logic [3:0] register_write_strobes = '0;
    logic [4:0] register_read_address = '0;
    logic [31:0] register_read_data;
    logic register_start;
    fixed_t register_input_current;
    logic register_network_step_valid = 1'b0;
    fixed_t register_network_voltage_0 = '0;
    fixed_t register_network_voltage_1 = '0;
    fixed_t register_network_voltage_2 = '0;

    three_neuron_registers register_model (
        .clk(clk), .rst_n(register_reset_n),
        .wr_en(register_write_enable), .wr_addr(register_write_address),
        .wr_data(register_write_data), .wr_strb(register_write_strobes),
        .rd_addr(register_read_address), .rd_data(register_read_data),
        .ctrl_start(register_start),
        .input_current(register_input_current),
        .network_step_valid(register_network_step_valid),
        .network_vmem_0(register_network_voltage_0),
        .network_vmem_1(register_network_voltage_1),
        .network_vmem_2(register_network_voltage_2)
    );

    task automatic reset_register_model;
        @(negedge clk);
        register_reset_n = 1'b0;
        register_write_enable = 1'b0;
        register_network_step_valid = 1'b0;
        repeat (2) begin
            @(negedge clk);
        end
        register_reset_n = 1'b1;
    endtask

    task automatic write_register(input logic [4:0] address, input logic [31:0] data, input logic [3:0] write_strobes);
        @(negedge clk);
        register_write_address = address;
        register_write_data = data;
        register_write_strobes = write_strobes;
        register_write_enable = 1'b1;
        @(negedge clk);
        register_write_enable = 1'b0;
    endtask

    task automatic expect_register(input logic [4:0] address, input logic [31:0] expected);
        register_read_address = address;
        #1;
        if (register_read_data !== expected) begin
            $fatal(1, "Register %h: expected %h, got %h", address, expected, register_read_data);
        end
    endtask

    task automatic drive_register_step(input fixed_t voltage_0, input fixed_t voltage_1, input fixed_t voltage_2);
        @(negedge clk);
        register_network_voltage_0 = voltage_0;
        register_network_voltage_1 = voltage_1;
        register_network_voltage_2 = voltage_2;
        register_network_step_valid = 1'b1;
        @(negedge clk);
        register_network_step_valid = 1'b0;
    endtask
