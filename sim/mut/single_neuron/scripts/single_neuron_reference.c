/*
 * Trace generator for C_fixedpoint/Single_Neuron/neuron_fixed.c.
 *
 * The equations, float-to-fixed conversions, constants, matrix and operation
 * order follow that file. Multiplication uses C "long" by default, as the
 * original does. The optional WIDE_MUL build selects int64_t to reproduce
 * a platform with a 64-bit long on Windows. Input and output are raw signed
 * fixed-point integers, without float printing.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define ONE_Q24 16777216
#define ONE_Q8 256
#define FI(value, bits) ((int32_t)((value) * (1 << (bits))))

#ifdef WIDE_MUL
typedef int64_t reference_product_t;
#else
typedef long reference_product_t;
#endif

static int32_t mul_shift(int32_t a, int32_t b, unsigned bits) {
    return (int32_t)(((reference_product_t)a * (reference_product_t)b) >> bits);
}

static float two_power_of(int32_t exponent) {
    int32_t integer_part = exponent >> 24;
    int32_t fraction = exponent & 0x00ffffff;
    int32_t shift = integer_part - 16;
    int32_t base_q8;

    if (integer_part < -6)
        return 0.0f;
    if (shift >= 0)
        base_q8 = (ONE_Q24 + fraction) << shift;
    else
        base_q8 = (ONE_Q24 + fraction) >> -shift;

    return (float)base_q8;
}

static float two_power_of_cubic(int32_t exponent) {
    int32_t fraction = exponent & 0x00ffffff;
    int32_t correction_q24 =
        ONE_Q24 + ((mul_shift(fraction, fraction, 24) - fraction) >> 2);
    int32_t base_q8 = (int32_t)two_power_of(exponent);
    return (float)mul_shift(base_q8, correction_q24, 24);
}

static void fh_ode(const int32_t state[4], int32_t input_current,
                   const int32_t matrix[4][8], int32_t derivative[4],
                   int32_t expvna, int32_t expek, int32_t expmel,
                   int32_t expvsat, int32_t expmvgk, int32_t kp) {
    int32_t kp_vna = mul_shift(kp, state[3], 24);
    int32_t kp_vg = mul_shift(kp, state[2], 24);
    int32_t kp_vk = mul_shift(kp, state[1], 24);

    int32_t current_vector[8] = {
        input_current,
        ONE_Q8 - mul_shift(expmel, (int32_t)two_power_of_cubic(state[0]), 24),
        mul_shift((int32_t)two_power_of(kp_vna),
                  ONE_Q8 - mul_shift(expvna, (int32_t)two_power_of(state[0]), 24), 8),
        (int32_t)two_power_of(kp_vg),
        ONE_Q8 - mul_shift(expvsat,
                           (int32_t)two_power_of(-state[3] - 390120603), 24),
        (int32_t)(two_power_of_cubic(state[0] + kp_vk) -
                  (float)mul_shift(expek, (int32_t)two_power_of(kp_vk), 24)),
        ONE_Q8 - mul_shift(expmvgk, (int32_t)two_power_of(state[1]), 24),
        (int32_t)(two_power_of(state[2]) - two_power_of(state[3]))
    };

    for (int row = 0; row < 4; row++) {
        derivative[row] = 0;
        for (int column = 0; column < 8; column++)
            derivative[row] = (int32_t)(
                (int64_t)derivative[row] +
                mul_shift(matrix[row][column], current_vector[column], 23));
    }
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s stimulus.txt c_trace.csv\n", argv[0]);
        return 2;
    }

    printf("C reference uses %zu-bit multiplication\n",
           sizeof(reference_product_t) * 8);

    FILE *stimulus = fopen(argv[1], "r");
    if (!stimulus) {
        perror(argv[1]);
        return 2;
    }
    FILE *trace = fopen(argv[2], "w");
    if (!trace) {
        perror(argv[2]);
        fclose(stimulus);
        return 2;
    }

    /* Source values copied from neuron_fixed.c, before fixed-point conversion. */
    float initial_state[4] = {-2.8309, 2.1341, -4.4310, -4.4310};
    float dt = 0.001;
    float expmel_float = 7.3306;
    float expvsat_float = 6.6116;
    float expmvgk_float = 0.2279;
    float expvna_float = 0.0182;
    float expek_float = 0.1364;
    float source_matrix[4][8] = {
        {70.785082606739/1000, 20.2173858708657/1000,
         1.32921811478727/1000, 2387.77324751470/1000,
         -23893.5281204093/1000, -9026.24819333978/1000,
         135.171307831437/1000, -232.108910489866/1000},
        {70.7850826067390/1000, 20.2173858708657/1000,
         1.32921811478727/1000, 2387.77324751470/1000,
         -23893.5281204093/1000, -9026.24819333978/1000,
         410.668585361385/1000, -232.108910489866/1000},
        {69.6603580753146/1000, 19.8961460133584/1000,
         1.30809778595160/1000, 4377.58428711028/1000,
         -43804.8015540837/1000, -8882.82754034463/1000,
         133.023532053490/1000, 425.533002564754/1000},
        {65.3065856956075/1000, 18.6526368875235/1000,
         1.22634167432962/1000, 20587.9115563489/1000,
         -206015.309127084/1000, -8327.65081907309/1000,
         124.709561300147/1000, 23636.4240515513/1000}
    };

    int32_t state[4];
    int32_t matrix[4][8];
    for (int i = 0; i < 4; i++) {
        state[i] = FI(initial_state[i], 24);
        for (int j = 0; j < 8; j++)
            matrix[i][j] = FI(source_matrix[i][j], 23);
    }

    int32_t dt_q24 = FI(dt, 24);
    int32_t expmel = FI(expmel_float, 24);
    int32_t expvsat = FI(expvsat_float, 24);
    int32_t expmvgk = FI(expmvgk_float, 24);
    int32_t expvna = FI(expvna_float, 24);
    int32_t expek = FI(expek_float, 24);
    int32_t kp = FI(-0.75f, 24);

    int number_of_steps;
    if (fscanf(stimulus, "%d", &number_of_steps) != 1 || number_of_steps <= 0) {
        fprintf(stderr, "First line of stimulus file must be a positive step count\n");
        fclose(stimulus);
        fclose(trace);
        return 2;
    }

    fprintf(trace, "step,current,vmem,vk,vg,vna\n");
    for (int step = 0; step < number_of_steps; step++) {
        int input_current;
        int32_t derivative[4];
        if (fscanf(stimulus, "%d", &input_current) != 1) {
            fprintf(stderr, "Missing input current for step %d\n", step);
            fclose(stimulus);
            fclose(trace);
            return 2;
        }

        fh_ode(state, input_current, matrix, derivative,
               expvna, expek, expmel, expvsat, expmvgk, kp);
        for (int j = 0; j < 4; j++)
            state[j] = (int32_t)((int64_t)state[j] +
                                 mul_shift(derivative[j], dt_q24, 8));

        fprintf(trace, "%d,%d,%d,%d,%d,%d\n", step, input_current,
                state[0], state[1], state[2], state[3]);
    }

    fclose(stimulus);
    fclose(trace);
    return 0;
}
