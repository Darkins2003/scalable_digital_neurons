# PYNQ-Z2 PL clock: 125 MHz reference on H16.
set_property -dict { PACKAGE_PIN H16 IOSTANDARD LVCMOS33 } [get_ports s00_axi_aclk]
create_clock -name sys_clk -period 8.000 [get_ports s00_axi_aclk]
