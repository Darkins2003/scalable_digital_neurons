# Shared AXI-Lite testbench helpers

Include `axi_lite_manager.svh` for `axi_write` and `axi_read`. It uses the
testbench's clock and AXI-Lite signals.

Include `axi_lite_register_methods.svh` after the manager for `expect_read`,
`write_field`, `read_field`, and `expect_field`. Field methods require an imported
register package defining `field_t` and its access types.

The common `sim/run_testcase.ps1` runner adds this directory to every MUT's
include path.
