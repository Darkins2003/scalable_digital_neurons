package three_neuron_regs_pkg;
    import neuron_params_generated_pkg::*;

    typedef enum logic [1:0] {
        RO,
        WO,
        RW,
        W1T  // Write 1 to trigger a command; reads return zero.
    } reg_access_t;

    typedef struct packed {
        logic [4:0]  offset;
        logic [31:0] reset_value;
        reg_access_t access_type;
    } reg_t;

    typedef struct packed {
        reg_t parent;
        logic [5:0] lsb;
        logic [5:0] width;
        reg_access_t access_type;
    } field_t;

    localparam reg_t REG_CONTROL = '{
        offset: 5'h00,
        reset_value: 32'h00000000,
        access_type: WO
    };

    localparam field_t CONTROL_START = '{
        parent: REG_CONTROL,
        lsb: 6'd0,
        width: 6'd1,
        access_type: W1T
    };

    localparam reg_t REG_CURRENT = '{
        offset: 5'h04,
        reset_value: 32'h00000000,
        access_type: RW
    };

    localparam field_t CURRENT_VALUE = '{
        parent: REG_CURRENT,
        lsb: 6'd0,
        width: 6'd32,
        access_type: RW
    };

    localparam reg_t REG_STATUS = '{
        offset: 5'h08,
        reset_value: 32'h00000000,
        access_type: RO
    };

    localparam field_t STATUS_START_REQUESTED = '{
        parent: REG_STATUS,
        lsb: 6'd0,
        width: 6'd1,
        access_type: RO
    };

    localparam field_t STATUS_HAS_STEP = '{
        parent: REG_STATUS,
        lsb: 6'd1,
        width: 6'd1,
        access_type: RO
    };

    localparam reg_t REG_STEP_COUNT = '{
        offset: 5'h0c,
        reset_value: 32'h00000000,
        access_type: RO
    };

    localparam field_t STEP_COUNT_VALUE = '{
        parent: REG_STEP_COUNT,
        lsb: 6'd0,
        width: 6'd32,
        access_type: RO
    };

    localparam reg_t REG_VMEM_0 = '{
        offset: 5'h10,
        reset_value: INITIAL_STATE[0],
        access_type: RO
    };

    localparam field_t VMEM_0_VALUE = '{
        parent: REG_VMEM_0,
        lsb: 6'd0,
        width: 6'd32,
        access_type: RO
    };

    localparam reg_t REG_VMEM_1 = '{
        offset: 5'h14,
        reset_value: INITIAL_STATE[0],
        access_type: RO
    };

    localparam field_t VMEM_1_VALUE = '{
        parent: REG_VMEM_1,
        lsb: 6'd0,
        width: 6'd32,
        access_type: RO
    };

    localparam reg_t REG_VMEM_2 = '{
        offset: 5'h18,
        reset_value: INITIAL_STATE[0],
        access_type: RO
    };

    localparam field_t VMEM_2_VALUE = '{
        parent: REG_VMEM_2,
        lsb: 6'd0,
        width: 6'd32,
        access_type: RO
    };
endpackage
