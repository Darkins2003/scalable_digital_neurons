module comparison_testbench;
    logic clock = 0;
    logic reset;
    logic [23:0] fractional_exponent;
    logic input_valid;
    logic [25:0] stimulus [0:19669];
    integer checked_outputs = 0;

    always begin
        #2;
        clock = ~clock;
    end

    logic signed [31:0] result_0;
    logic output_valid_0;
    logic [32:0] expected_0 [0:19669];
    maclaurin_0_logic instance_0 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_0), .output_valid(output_valid_0));

    logic signed [31:0] result_1;
    logic output_valid_1;
    logic [32:0] expected_1 [0:19669];
    sollya_0_logic instance_1 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_1), .output_valid(output_valid_1));

    logic signed [31:0] result_2;
    logic output_valid_2;
    logic [32:0] expected_2 [0:19669];
    maclaurin_1_lut instance_2 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_2), .output_valid(output_valid_2));

    logic signed [31:0] result_3;
    logic output_valid_3;
    logic [32:0] expected_3 [0:19669];
    maclaurin_1_dsp instance_3 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_3), .output_valid(output_valid_3));

    logic signed [31:0] result_4;
    logic output_valid_4;
    logic [32:0] expected_4 [0:19669];
    sollya_1_lut instance_4 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_4), .output_valid(output_valid_4));

    logic signed [31:0] result_5;
    logic output_valid_5;
    logic [32:0] expected_5 [0:19669];
    sollya_1_dsp instance_5 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_5), .output_valid(output_valid_5));

    logic signed [31:0] result_6;
    logic output_valid_6;
    logic [32:0] expected_6 [0:19669];
    maclaurin_2_lut instance_6 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_6), .output_valid(output_valid_6));

    logic signed [31:0] result_7;
    logic output_valid_7;
    logic [32:0] expected_7 [0:19669];
    maclaurin_2_dsp instance_7 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_7), .output_valid(output_valid_7));

    logic signed [31:0] result_8;
    logic output_valid_8;
    logic [32:0] expected_8 [0:19669];
    sollya_2_lut instance_8 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_8), .output_valid(output_valid_8));

    logic signed [31:0] result_9;
    logic output_valid_9;
    logic [32:0] expected_9 [0:19669];
    sollya_2_dsp instance_9 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_9), .output_valid(output_valid_9));

    logic signed [31:0] result_10;
    logic output_valid_10;
    logic [32:0] expected_10 [0:19669];
    maclaurin_3_lut instance_10 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_10), .output_valid(output_valid_10));

    logic signed [31:0] result_11;
    logic output_valid_11;
    logic [32:0] expected_11 [0:19669];
    maclaurin_3_dsp instance_11 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_11), .output_valid(output_valid_11));

    logic signed [31:0] result_12;
    logic output_valid_12;
    logic [32:0] expected_12 [0:19669];
    sollya_3_lut instance_12 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_12), .output_valid(output_valid_12));

    logic signed [31:0] result_13;
    logic output_valid_13;
    logic [32:0] expected_13 [0:19669];
    sollya_3_dsp instance_13 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_13), .output_valid(output_valid_13));

    logic signed [31:0] result_14;
    logic output_valid_14;
    logic [32:0] expected_14 [0:19669];
    maclaurin_4_lut instance_14 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_14), .output_valid(output_valid_14));

    logic signed [31:0] result_15;
    logic output_valid_15;
    logic [32:0] expected_15 [0:19669];
    maclaurin_4_dsp instance_15 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_15), .output_valid(output_valid_15));

    logic signed [31:0] result_16;
    logic output_valid_16;
    logic [32:0] expected_16 [0:19669];
    sollya_4_lut instance_16 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_16), .output_valid(output_valid_16));

    logic signed [31:0] result_17;
    logic output_valid_17;
    logic [32:0] expected_17 [0:19669];
    sollya_4_dsp instance_17 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_17), .output_valid(output_valid_17));

    logic signed [31:0] result_18;
    logic output_valid_18;
    logic [32:0] expected_18 [0:19669];
    research_linear_logic instance_18 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_18), .output_valid(output_valid_18));

    logic signed [31:0] result_19;
    logic output_valid_19;
    logic [32:0] expected_19 [0:19669];
    research_cubic_lut instance_19 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_19), .output_valid(output_valid_19));

    logic signed [31:0] result_20;
    logic output_valid_20;
    logic [32:0] expected_20 [0:19669];
    research_cubic_dsp instance_20 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_20), .output_valid(output_valid_20));

    logic signed [31:0] result_21;
    logic output_valid_21;
    logic [32:0] expected_21 [0:19669];
    rom_16_distributed instance_21 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_21), .output_valid(output_valid_21));

    logic signed [31:0] result_22;
    logic output_valid_22;
    logic [32:0] expected_22 [0:19669];
    rom_16_block instance_22 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_22), .output_valid(output_valid_22));

    logic signed [31:0] result_23;
    logic output_valid_23;
    logic [32:0] expected_23 [0:19669];
    rom_32_distributed instance_23 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_23), .output_valid(output_valid_23));

    logic signed [31:0] result_24;
    logic output_valid_24;
    logic [32:0] expected_24 [0:19669];
    rom_32_block instance_24 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_24), .output_valid(output_valid_24));

    logic signed [31:0] result_25;
    logic output_valid_25;
    logic [32:0] expected_25 [0:19669];
    rom_64_distributed instance_25 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_25), .output_valid(output_valid_25));

    logic signed [31:0] result_26;
    logic output_valid_26;
    logic [32:0] expected_26 [0:19669];
    rom_64_block instance_26 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_26), .output_valid(output_valid_26));

    logic signed [31:0] result_27;
    logic output_valid_27;
    logic [32:0] expected_27 [0:19669];
    rom_128_distributed instance_27 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_27), .output_valid(output_valid_27));

    logic signed [31:0] result_28;
    logic output_valid_28;
    logic [32:0] expected_28 [0:19669];
    rom_128_block instance_28 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_28), .output_valid(output_valid_28));

    logic signed [31:0] result_29;
    logic output_valid_29;
    logic [32:0] expected_29 [0:19669];
    rom_256_distributed instance_29 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_29), .output_valid(output_valid_29));

    logic signed [31:0] result_30;
    logic output_valid_30;
    logic [32:0] expected_30 [0:19669];
    rom_256_block instance_30 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_30), .output_valid(output_valid_30));

    logic signed [31:0] result_31;
    logic output_valid_31;
    logic [32:0] expected_31 [0:19669];
    rom_512_distributed instance_31 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_31), .output_valid(output_valid_31));

    logic signed [31:0] result_32;
    logic output_valid_32;
    logic [32:0] expected_32 [0:19669];
    rom_512_block instance_32 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_32), .output_valid(output_valid_32));

    logic signed [31:0] result_33;
    logic output_valid_33;
    logic [32:0] expected_33 [0:19669];
    rom_1024_distributed instance_33 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_33), .output_valid(output_valid_33));

    logic signed [31:0] result_34;
    logic output_valid_34;
    logic [32:0] expected_34 [0:19669];
    rom_1024_block instance_34 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_34), .output_valid(output_valid_34));

    logic signed [31:0] result_35;
    logic output_valid_35;
    logic [32:0] expected_35 [0:19669];
    rom_2048_distributed instance_35 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_35), .output_valid(output_valid_35));

    logic signed [31:0] result_36;
    logic output_valid_36;
    logic [32:0] expected_36 [0:19669];
    rom_2048_block instance_36 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_36), .output_valid(output_valid_36));

    logic signed [31:0] result_37;
    logic output_valid_37;
    logic [32:0] expected_37 [0:19669];
    rom_4096_distributed instance_37 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_37), .output_valid(output_valid_37));

    logic signed [31:0] result_38;
    logic output_valid_38;
    logic [32:0] expected_38 [0:19669];
    rom_4096_block instance_38 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_38), .output_valid(output_valid_38));

    logic signed [31:0] result_39;
    logic output_valid_39;
    logic [32:0] expected_39 [0:19669];
    rom_8192_distributed instance_39 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_39), .output_valid(output_valid_39));

    logic signed [31:0] result_40;
    logic output_valid_40;
    logic [32:0] expected_40 [0:19669];
    rom_8192_block instance_40 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_40), .output_valid(output_valid_40));

    logic signed [31:0] result_41;
    logic output_valid_41;
    logic [32:0] expected_41 [0:19669];
    rom_16384_distributed instance_41 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_41), .output_valid(output_valid_41));

    logic signed [31:0] result_42;
    logic output_valid_42;
    logic [32:0] expected_42 [0:19669];
    rom_16384_block instance_42 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_42), .output_valid(output_valid_42));

    logic signed [31:0] result_43;
    logic output_valid_43;
    logic [32:0] expected_43 [0:19669];
    rom_32768_distributed instance_43 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_43), .output_valid(output_valid_43));

    logic signed [31:0] result_44;
    logic output_valid_44;
    logic [32:0] expected_44 [0:19669];
    rom_32768_block instance_44 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_44), .output_valid(output_valid_44));

    logic signed [31:0] result_45;
    logic output_valid_45;
    logic [32:0] expected_45 [0:19669];
    rom_65536_distributed instance_45 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_45), .output_valid(output_valid_45));

    logic signed [31:0] result_46;
    logic output_valid_46;
    logic [32:0] expected_46 [0:19669];
    rom_65536_block instance_46 (.clock(clock), .reset(reset), .fractional_exponent(fractional_exponent), .input_valid(input_valid), .result(result_46), .output_valid(output_valid_46));

    initial begin
        $readmemh("validation/stimulus.mem", stimulus);
        $readmemh("validation/maclaurin_0_logic.mem", expected_0);
        $readmemh("validation/sollya_0_logic.mem", expected_1);
        $readmemh("validation/maclaurin_1_lut.mem", expected_2);
        $readmemh("validation/maclaurin_1_dsp.mem", expected_3);
        $readmemh("validation/sollya_1_lut.mem", expected_4);
        $readmemh("validation/sollya_1_dsp.mem", expected_5);
        $readmemh("validation/maclaurin_2_lut.mem", expected_6);
        $readmemh("validation/maclaurin_2_dsp.mem", expected_7);
        $readmemh("validation/sollya_2_lut.mem", expected_8);
        $readmemh("validation/sollya_2_dsp.mem", expected_9);
        $readmemh("validation/maclaurin_3_lut.mem", expected_10);
        $readmemh("validation/maclaurin_3_dsp.mem", expected_11);
        $readmemh("validation/sollya_3_lut.mem", expected_12);
        $readmemh("validation/sollya_3_dsp.mem", expected_13);
        $readmemh("validation/maclaurin_4_lut.mem", expected_14);
        $readmemh("validation/maclaurin_4_dsp.mem", expected_15);
        $readmemh("validation/sollya_4_lut.mem", expected_16);
        $readmemh("validation/sollya_4_dsp.mem", expected_17);
        $readmemh("validation/research_linear_logic.mem", expected_18);
        $readmemh("validation/research_cubic_lut.mem", expected_19);
        $readmemh("validation/research_cubic_dsp.mem", expected_20);
        $readmemh("validation/rom_16_distributed.mem", expected_21);
        $readmemh("validation/rom_16_block.mem", expected_22);
        $readmemh("validation/rom_32_distributed.mem", expected_23);
        $readmemh("validation/rom_32_block.mem", expected_24);
        $readmemh("validation/rom_64_distributed.mem", expected_25);
        $readmemh("validation/rom_64_block.mem", expected_26);
        $readmemh("validation/rom_128_distributed.mem", expected_27);
        $readmemh("validation/rom_128_block.mem", expected_28);
        $readmemh("validation/rom_256_distributed.mem", expected_29);
        $readmemh("validation/rom_256_block.mem", expected_30);
        $readmemh("validation/rom_512_distributed.mem", expected_31);
        $readmemh("validation/rom_512_block.mem", expected_32);
        $readmemh("validation/rom_1024_distributed.mem", expected_33);
        $readmemh("validation/rom_1024_block.mem", expected_34);
        $readmemh("validation/rom_2048_distributed.mem", expected_35);
        $readmemh("validation/rom_2048_block.mem", expected_36);
        $readmemh("validation/rom_4096_distributed.mem", expected_37);
        $readmemh("validation/rom_4096_block.mem", expected_38);
        $readmemh("validation/rom_8192_distributed.mem", expected_39);
        $readmemh("validation/rom_8192_block.mem", expected_40);
        $readmemh("validation/rom_16384_distributed.mem", expected_41);
        $readmemh("validation/rom_16384_block.mem", expected_42);
        $readmemh("validation/rom_32768_distributed.mem", expected_43);
        $readmemh("validation/rom_32768_block.mem", expected_44);
        $readmemh("validation/rom_65536_distributed.mem", expected_45);
        $readmemh("validation/rom_65536_block.mem", expected_46);
        for (integer cycle = 0; cycle < 19670; cycle = cycle + 1) begin
            @(negedge clock);
            {reset, input_valid, fractional_exponent} = stimulus[cycle];
            @(posedge clock);
            #0.1;
            if (output_valid_0 !== expected_0[cycle][32]) begin
                $fatal(1, "maclaurin_0_logic valid mismatch at cycle %0d", cycle);
            end
            if (expected_0[cycle][32]) begin
                if (result_0 !== expected_0[cycle][31:0]) begin
                    $fatal(1, "maclaurin_0_logic result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_0, expected_0[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_1 !== expected_1[cycle][32]) begin
                $fatal(1, "sollya_0_logic valid mismatch at cycle %0d", cycle);
            end
            if (expected_1[cycle][32]) begin
                if (result_1 !== expected_1[cycle][31:0]) begin
                    $fatal(1, "sollya_0_logic result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_1, expected_1[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_2 !== expected_2[cycle][32]) begin
                $fatal(1, "maclaurin_1_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_2[cycle][32]) begin
                if (result_2 !== expected_2[cycle][31:0]) begin
                    $fatal(1, "maclaurin_1_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_2, expected_2[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_3 !== expected_3[cycle][32]) begin
                $fatal(1, "maclaurin_1_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_3[cycle][32]) begin
                if (result_3 !== expected_3[cycle][31:0]) begin
                    $fatal(1, "maclaurin_1_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_3, expected_3[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_4 !== expected_4[cycle][32]) begin
                $fatal(1, "sollya_1_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_4[cycle][32]) begin
                if (result_4 !== expected_4[cycle][31:0]) begin
                    $fatal(1, "sollya_1_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_4, expected_4[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_5 !== expected_5[cycle][32]) begin
                $fatal(1, "sollya_1_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_5[cycle][32]) begin
                if (result_5 !== expected_5[cycle][31:0]) begin
                    $fatal(1, "sollya_1_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_5, expected_5[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_6 !== expected_6[cycle][32]) begin
                $fatal(1, "maclaurin_2_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_6[cycle][32]) begin
                if (result_6 !== expected_6[cycle][31:0]) begin
                    $fatal(1, "maclaurin_2_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_6, expected_6[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_7 !== expected_7[cycle][32]) begin
                $fatal(1, "maclaurin_2_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_7[cycle][32]) begin
                if (result_7 !== expected_7[cycle][31:0]) begin
                    $fatal(1, "maclaurin_2_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_7, expected_7[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_8 !== expected_8[cycle][32]) begin
                $fatal(1, "sollya_2_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_8[cycle][32]) begin
                if (result_8 !== expected_8[cycle][31:0]) begin
                    $fatal(1, "sollya_2_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_8, expected_8[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_9 !== expected_9[cycle][32]) begin
                $fatal(1, "sollya_2_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_9[cycle][32]) begin
                if (result_9 !== expected_9[cycle][31:0]) begin
                    $fatal(1, "sollya_2_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_9, expected_9[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_10 !== expected_10[cycle][32]) begin
                $fatal(1, "maclaurin_3_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_10[cycle][32]) begin
                if (result_10 !== expected_10[cycle][31:0]) begin
                    $fatal(1, "maclaurin_3_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_10, expected_10[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_11 !== expected_11[cycle][32]) begin
                $fatal(1, "maclaurin_3_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_11[cycle][32]) begin
                if (result_11 !== expected_11[cycle][31:0]) begin
                    $fatal(1, "maclaurin_3_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_11, expected_11[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_12 !== expected_12[cycle][32]) begin
                $fatal(1, "sollya_3_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_12[cycle][32]) begin
                if (result_12 !== expected_12[cycle][31:0]) begin
                    $fatal(1, "sollya_3_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_12, expected_12[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_13 !== expected_13[cycle][32]) begin
                $fatal(1, "sollya_3_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_13[cycle][32]) begin
                if (result_13 !== expected_13[cycle][31:0]) begin
                    $fatal(1, "sollya_3_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_13, expected_13[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_14 !== expected_14[cycle][32]) begin
                $fatal(1, "maclaurin_4_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_14[cycle][32]) begin
                if (result_14 !== expected_14[cycle][31:0]) begin
                    $fatal(1, "maclaurin_4_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_14, expected_14[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_15 !== expected_15[cycle][32]) begin
                $fatal(1, "maclaurin_4_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_15[cycle][32]) begin
                if (result_15 !== expected_15[cycle][31:0]) begin
                    $fatal(1, "maclaurin_4_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_15, expected_15[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_16 !== expected_16[cycle][32]) begin
                $fatal(1, "sollya_4_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_16[cycle][32]) begin
                if (result_16 !== expected_16[cycle][31:0]) begin
                    $fatal(1, "sollya_4_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_16, expected_16[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_17 !== expected_17[cycle][32]) begin
                $fatal(1, "sollya_4_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_17[cycle][32]) begin
                if (result_17 !== expected_17[cycle][31:0]) begin
                    $fatal(1, "sollya_4_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_17, expected_17[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_18 !== expected_18[cycle][32]) begin
                $fatal(1, "research_linear_logic valid mismatch at cycle %0d", cycle);
            end
            if (expected_18[cycle][32]) begin
                if (result_18 !== expected_18[cycle][31:0]) begin
                    $fatal(1, "research_linear_logic result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_18, expected_18[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_19 !== expected_19[cycle][32]) begin
                $fatal(1, "research_cubic_lut valid mismatch at cycle %0d", cycle);
            end
            if (expected_19[cycle][32]) begin
                if (result_19 !== expected_19[cycle][31:0]) begin
                    $fatal(1, "research_cubic_lut result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_19, expected_19[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_20 !== expected_20[cycle][32]) begin
                $fatal(1, "research_cubic_dsp valid mismatch at cycle %0d", cycle);
            end
            if (expected_20[cycle][32]) begin
                if (result_20 !== expected_20[cycle][31:0]) begin
                    $fatal(1, "research_cubic_dsp result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_20, expected_20[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_21 !== expected_21[cycle][32]) begin
                $fatal(1, "rom_16_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_21[cycle][32]) begin
                if (result_21 !== expected_21[cycle][31:0]) begin
                    $fatal(1, "rom_16_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_21, expected_21[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_22 !== expected_22[cycle][32]) begin
                $fatal(1, "rom_16_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_22[cycle][32]) begin
                if (result_22 !== expected_22[cycle][31:0]) begin
                    $fatal(1, "rom_16_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_22, expected_22[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_23 !== expected_23[cycle][32]) begin
                $fatal(1, "rom_32_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_23[cycle][32]) begin
                if (result_23 !== expected_23[cycle][31:0]) begin
                    $fatal(1, "rom_32_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_23, expected_23[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_24 !== expected_24[cycle][32]) begin
                $fatal(1, "rom_32_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_24[cycle][32]) begin
                if (result_24 !== expected_24[cycle][31:0]) begin
                    $fatal(1, "rom_32_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_24, expected_24[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_25 !== expected_25[cycle][32]) begin
                $fatal(1, "rom_64_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_25[cycle][32]) begin
                if (result_25 !== expected_25[cycle][31:0]) begin
                    $fatal(1, "rom_64_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_25, expected_25[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_26 !== expected_26[cycle][32]) begin
                $fatal(1, "rom_64_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_26[cycle][32]) begin
                if (result_26 !== expected_26[cycle][31:0]) begin
                    $fatal(1, "rom_64_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_26, expected_26[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_27 !== expected_27[cycle][32]) begin
                $fatal(1, "rom_128_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_27[cycle][32]) begin
                if (result_27 !== expected_27[cycle][31:0]) begin
                    $fatal(1, "rom_128_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_27, expected_27[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_28 !== expected_28[cycle][32]) begin
                $fatal(1, "rom_128_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_28[cycle][32]) begin
                if (result_28 !== expected_28[cycle][31:0]) begin
                    $fatal(1, "rom_128_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_28, expected_28[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_29 !== expected_29[cycle][32]) begin
                $fatal(1, "rom_256_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_29[cycle][32]) begin
                if (result_29 !== expected_29[cycle][31:0]) begin
                    $fatal(1, "rom_256_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_29, expected_29[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_30 !== expected_30[cycle][32]) begin
                $fatal(1, "rom_256_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_30[cycle][32]) begin
                if (result_30 !== expected_30[cycle][31:0]) begin
                    $fatal(1, "rom_256_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_30, expected_30[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_31 !== expected_31[cycle][32]) begin
                $fatal(1, "rom_512_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_31[cycle][32]) begin
                if (result_31 !== expected_31[cycle][31:0]) begin
                    $fatal(1, "rom_512_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_31, expected_31[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_32 !== expected_32[cycle][32]) begin
                $fatal(1, "rom_512_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_32[cycle][32]) begin
                if (result_32 !== expected_32[cycle][31:0]) begin
                    $fatal(1, "rom_512_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_32, expected_32[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_33 !== expected_33[cycle][32]) begin
                $fatal(1, "rom_1024_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_33[cycle][32]) begin
                if (result_33 !== expected_33[cycle][31:0]) begin
                    $fatal(1, "rom_1024_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_33, expected_33[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_34 !== expected_34[cycle][32]) begin
                $fatal(1, "rom_1024_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_34[cycle][32]) begin
                if (result_34 !== expected_34[cycle][31:0]) begin
                    $fatal(1, "rom_1024_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_34, expected_34[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_35 !== expected_35[cycle][32]) begin
                $fatal(1, "rom_2048_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_35[cycle][32]) begin
                if (result_35 !== expected_35[cycle][31:0]) begin
                    $fatal(1, "rom_2048_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_35, expected_35[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_36 !== expected_36[cycle][32]) begin
                $fatal(1, "rom_2048_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_36[cycle][32]) begin
                if (result_36 !== expected_36[cycle][31:0]) begin
                    $fatal(1, "rom_2048_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_36, expected_36[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_37 !== expected_37[cycle][32]) begin
                $fatal(1, "rom_4096_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_37[cycle][32]) begin
                if (result_37 !== expected_37[cycle][31:0]) begin
                    $fatal(1, "rom_4096_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_37, expected_37[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_38 !== expected_38[cycle][32]) begin
                $fatal(1, "rom_4096_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_38[cycle][32]) begin
                if (result_38 !== expected_38[cycle][31:0]) begin
                    $fatal(1, "rom_4096_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_38, expected_38[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_39 !== expected_39[cycle][32]) begin
                $fatal(1, "rom_8192_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_39[cycle][32]) begin
                if (result_39 !== expected_39[cycle][31:0]) begin
                    $fatal(1, "rom_8192_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_39, expected_39[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_40 !== expected_40[cycle][32]) begin
                $fatal(1, "rom_8192_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_40[cycle][32]) begin
                if (result_40 !== expected_40[cycle][31:0]) begin
                    $fatal(1, "rom_8192_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_40, expected_40[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_41 !== expected_41[cycle][32]) begin
                $fatal(1, "rom_16384_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_41[cycle][32]) begin
                if (result_41 !== expected_41[cycle][31:0]) begin
                    $fatal(1, "rom_16384_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_41, expected_41[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_42 !== expected_42[cycle][32]) begin
                $fatal(1, "rom_16384_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_42[cycle][32]) begin
                if (result_42 !== expected_42[cycle][31:0]) begin
                    $fatal(1, "rom_16384_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_42, expected_42[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_43 !== expected_43[cycle][32]) begin
                $fatal(1, "rom_32768_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_43[cycle][32]) begin
                if (result_43 !== expected_43[cycle][31:0]) begin
                    $fatal(1, "rom_32768_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_43, expected_43[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_44 !== expected_44[cycle][32]) begin
                $fatal(1, "rom_32768_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_44[cycle][32]) begin
                if (result_44 !== expected_44[cycle][31:0]) begin
                    $fatal(1, "rom_32768_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_44, expected_44[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_45 !== expected_45[cycle][32]) begin
                $fatal(1, "rom_65536_distributed valid mismatch at cycle %0d", cycle);
            end
            if (expected_45[cycle][32]) begin
                if (result_45 !== expected_45[cycle][31:0]) begin
                    $fatal(1, "rom_65536_distributed result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_45, expected_45[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
            if (output_valid_46 !== expected_46[cycle][32]) begin
                $fatal(1, "rom_65536_block valid mismatch at cycle %0d", cycle);
            end
            if (expected_46[cycle][32]) begin
                if (result_46 !== expected_46[cycle][31:0]) begin
                    $fatal(1, "rom_65536_block result mismatch at cycle %0d: actual=%0d expected=%0d", cycle, result_46, expected_46[cycle][31:0]);
                end
                checked_outputs = checked_outputs + 1;
            end
        end
        $display("PASS: all models matched Python, including bubbles and reset; checked outputs=%0d", checked_outputs);
        $finish;
    end
endmodule
