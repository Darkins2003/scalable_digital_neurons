// Include inside a testbench module with the usual AXI-Lite signal names and clk.
// Address and data widths come from that module's signals.
task automatic send_write_address(input logic [$bits(awaddr)-1:0] address, input int delay_cycles);
        repeat (delay_cycles) begin
            @(negedge clk);
        end

        @(negedge clk);
        awaddr = address;
        awvalid = 1'b1;
        do begin
            @(posedge clk);
        end while (!awready);

        @(negedge clk);
        awvalid = 1'b0;
endtask

task automatic send_write_data(input logic [$bits(wdata)-1:0] data, input logic [$bits(wstrb)-1:0] write_strobes, input int delay_cycles);
        repeat (delay_cycles) begin
            @(negedge clk);
        end

        @(negedge clk);
        wdata = data;
        wstrb = write_strobes;
        wvalid = 1'b1;
        do begin
            @(posedge clk);
        end while (!wready);

        @(negedge clk);
        wvalid = 1'b0;
endtask

task automatic axi_write(input logic [$bits(awaddr)-1:0] address, input logic [$bits(wdata)-1:0] data, input logic [$bits(wstrb)-1:0] write_strobes, input int address_delay_cycles, input int data_delay_cycles);
        fork
            send_write_address(address, address_delay_cycles);
            send_write_data(data, write_strobes, data_delay_cycles);
        join

        @(negedge clk);
        bready = 1'b1;
        do begin
            @(posedge clk);
        end while (!bvalid);
        if (bresp !== 2'b00) begin
            $fatal(1, "AXI write error at %h", address);
        end

        @(negedge clk);
        bready = 1'b0;
endtask

task automatic axi_read(input logic [$bits(araddr)-1:0] address, output logic [$bits(rdata)-1:0] data);
        @(negedge clk);
        araddr = address;
        arvalid = 1'b1;
        do begin
            @(posedge clk);
        end while (!arready);

        @(negedge clk);
        arvalid = 1'b0;
        rready = 1'b1;
        do begin
            @(posedge clk);
        end while (!rvalid);
        if (rresp !== 2'b00) begin
            $fatal(1, "AXI read error at %h", address);
        end

        data = rdata;
        @(negedge clk);
        rready = 1'b0;
endtask
