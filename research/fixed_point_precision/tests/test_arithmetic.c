#include <assert.h>
#define main precision_model_main
#include "../precision_model.c"
#undef main

int main(void) {
    for (int group = 0; group < GROUP_COUNT; group++) { formats[group] = (Format){32, 24}; }
    formats[CURRENT] = (Format){32, 8};
    formats[TRIANGLE] = (Format){32, 16};
    formats[MATRIX] = (Format){32, 23};
    assert(signed_bits(255, 8) == -1);
    assert(signed_bits(128, 8) == -128);
    assert(floor_shift(-3, 1) == -2);
    assert(floor_shift(-1, 40) == -1);
    assert(exponential(0, EXPONENTIAL) == 256);
    assert(exponential(-16777216, EXPONENTIAL) == 128);
    assert(exponential(16777216, EXPONENTIAL) == 512);
    for (int exponent = -40 * 16777216; exponent < 30 * 16777216; exponent += 7919) { assert(exponential(exponent, EXPONENTIAL) == base_two_exponential(exponent)); }
    formats[STATE] = (Format){16, 8};
    assert(exponential(128, EXPONENTIAL) == (int32_t)(fractional_exponent_estimation_table[512] >> 16));
    formats[STATE] = (Format){8, 4};
    assert(exponential(1, EXPONENTIAL) == (int32_t)(fractional_exponent_estimation_table[64] >> 16));
    assert(add(127, 1, STATE, NEXT_STATE) == -128);
    assert(measurements[3][NEXT_STATE][STATE].overflows == 1);
    assert(measurements[3][NEXT_STATE][STATE].maximum == 8);
    assert(multiply(-3, STATE, 8, STATE, STATE, UPDATE) == -2);
    assert(rescale(-1, 8, STATE, UPDATE) == -1);
    assert(encode(.001, STATE, PARAMETER) == 0);
    assert(zero_constants == 1);
    formats[CURRENT] = (Format){8, 4};
    assert(exponential(112, EXPONENTIAL) == 0);
    assert(total_overflows > 1);
    puts("PASS: signed wrapping, floor shifts, mixed scales, lookup addressing, pre-narrowing overflow and zero constants");
    return 0;
}
