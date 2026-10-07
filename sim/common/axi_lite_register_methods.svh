// Include after axi_lite_manager.svh in a testbench that imports a register package.
task automatic expect_read(input logic [$bits(araddr)-1:0] address, input logic [$bits(rdata)-1:0] expected);
        logic [$bits(rdata)-1:0] actual;

        axi_read(address, actual);
        if (actual !== expected) begin
            $fatal(1, "Register %h: expected %h, got %h", address, expected, actual);
        end
endtask

task automatic write_field(input field_t field_desc, input logic [31:0] value);
    logic [31:0] field_mask;
    logic [31:0] register_value;
    logic [31:0] write_value;

    if (field_desc.width == 0 || field_desc.lsb + field_desc.width > 32)
        $fatal(1, "Invalid field layout at register %h", field_desc.parent.offset);

    field_mask = 32'hffff_ffff >> (32 - field_desc.width);
    if ((value & ~field_mask) != 0)
        $fatal(1, "Field value %h exceeds %0d bits", value, field_desc.width);

    case (field_desc.access_type)
        RO: $fatal(1, "Cannot write read-only field at register %h", field_desc.parent.offset);
        RW: begin
            if (field_desc.width == 32) begin
                write_value = value;
            end else begin
                axi_read(field_desc.parent.offset, register_value);
                write_value = (register_value & ~(field_mask << field_desc.lsb)) |
                              ((value & field_mask) << field_desc.lsb);
            end
            axi_write(field_desc.parent.offset, write_value, 4'hf, 0, 0);
        end
        WO, W1T: begin
            // Other command fields receive zero, so they are not triggered.
            write_value = (value & field_mask) << field_desc.lsb;
            axi_write(field_desc.parent.offset, write_value, 4'hf, 0, 0);
        end
        default: $fatal(1, "Unsupported field access type");
    endcase
endtask

task automatic read_field(input field_t field_desc, output logic [31:0] value);
    logic [31:0] register_value;
    logic [31:0] field_mask;

    if (field_desc.width == 0 || field_desc.lsb + field_desc.width > 32)
        $fatal(1, "Invalid field layout at register %h", field_desc.parent.offset);
    if (field_desc.access_type == WO || field_desc.access_type == W1T)
        $fatal(1, "Cannot read write-only field at register %h", field_desc.parent.offset);

    field_mask = 32'hffff_ffff >> (32 - field_desc.width);
    axi_read(field_desc.parent.offset, register_value);
    value = (register_value >> field_desc.lsb) & field_mask;
endtask

task automatic expect_field(input field_t field_description, input logic [31:0] expected);
        logic [31:0] actual;

        read_field(field_description, actual);
        if (actual !== expected) begin
            $fatal(1, "Field at register %h bit %0d: expected %h, got %h", field_description.parent.offset, field_description.lsb, expected, actual);
        end
endtask
