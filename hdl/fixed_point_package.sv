package fixed_point_package;

    import neuron_params_generated_pkg::*;

    function automatic fixed_t mul_24_24_24(input fixed_t a, input fixed_t b);
        // Multiplies 2 32 bit signed numbers, each with 24 fractional bits.
        // 24 LSB are removed so the result has 24 fractional bits. 
        // Result is then truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> STATE_FRAC_BITS; // Mutliply and shift right by 24 bits
        out = fixed_t'(product); // Truncate to 32 bits

        return out;
    endfunction

    function automatic fixed_t mul_24_16_16(input fixed_t a, input fixed_t b);
        // Multiplies a Q8.24 value by a Q16.16 value.
        // Remove 24 fractional bits to return a Q16.16 result, truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> STATE_FRAC_BITS;
        out = fixed_t'(product);

        return out;
    endfunction

    function automatic fixed_t mul_16_24_24(input fixed_t a, input fixed_t b);
        // Multiplies a Q16.16 value by a Q8.24 value.
        // Remove 16 fractional bits to return a Q8.24 result, truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> TRIANGLE_FRAC_BITS;
        out = fixed_t'(product);

        return out;
    endfunction

    function automatic fixed_t mul_24_8_8(input fixed_t a, input fixed_t b);
        // Multiplies 2 32 bit signed numbers, one with 24 fractional bits and the other with 8 fractional bits.
        // 24 LSB are removed so the result has 8 fractional bits. 
        // Result is then truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> STATE_FRAC_BITS; // Mutliply and shift right by 24 bits
        out = fixed_t'(product); // Truncate to 32 bits

        return out;
    endfunction

    function automatic fixed_t mul_24_8_24(input fixed_t a, input fixed_t b);
        // Multiplies a Q24 value by a Q8 value.
        // Remove 8 fractional bits to return a Q24 result, truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> CURRENT_FRAC_BITS;
        out = fixed_t'(product);

        return out;
    endfunction

    function automatic fixed_t mul_23_8_8(input fixed_t a, input fixed_t b);
        // Multiplies a Q23 matrix coefficient by a Q8 current-vector value.
        // Remove 23 fractional bits to return a Q8 result, truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> MATRIX_FRAC_BITS;
        out = fixed_t'(product);

        return out;
    endfunction

    function automatic fixed_t mul_8_8_8(input fixed_t a, input fixed_t b);
        // Multiplies 2 32 bit signed numbers, each with 8 fractional bits.
        // 8 LSB are removed so the result has 8 fractional bits.
        // Result is then truncated to 32 bits.
        logic signed [63:0] product;
        fixed_t out;

        product = ( $signed({{32{a[VALUE_WIDTH-1]}}, a}) * $signed({{32{b[VALUE_WIDTH-1]}}, b}) ) >>> CURRENT_FRAC_BITS; // Multiply and shift right by 8 bits
        out = fixed_t'(product); // Truncate to 32 bits

        return out;
    endfunction

endpackage
