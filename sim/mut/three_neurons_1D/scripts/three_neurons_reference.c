/* Step trace for the original fixed-point 3-neuron synfire model. */
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#ifdef WIDE_MUL
#define long int64_t
#endif
#define main original_synfire_main
#include "../../../../../EfficientAnalogNeuron-SNNsims/C_fixedpoint/1D_Synfire/Synfire_1D_3neur_fixed.c"
#undef main

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s stimulus.txt c_trace.csv\n", argv[0]);
        return 2;
    }
    FILE *stimulus = fopen(argv[1], "r");
    FILE *trace = fopen(argv[2], "w");
    if (!stimulus || !trace) { perror("stimulus/trace"); return 2; }
    int steps;
    if (fscanf(stimulus, "%d", &steps) != 1 || steps < 1) return 2;

    float weights[3][6] = {
        {2.5f, 2.5f, 2.5f, 2.5f, 0.26f, 2.5f},
        {0.26f, 2.5f, 2.5f, 2.5f, 2.5f, 2.5f},
        {2.5f, 2.5f, 0.26f, 2.5f, 2.5f, 2.5f}
    };
    float synapse_matrix[3][6] = {0};
    compute_synapse_mat(weights, 2.1425f, synapse_matrix);
    int fixed_synapse_matrix[3][6];
    float_synarray_to_fix(synapse_matrix, fixed_synapse_matrix);

    float initial[18];
    int state[18], vmem[3], derivative[18];
    initialize_y(initial);
    for (int j = 0; j < 18; ++j)
        state[j] = j < 6 ? fi(initial[j], 16) : fi(initial[j], 24);
    update_Vmem(state, vmem);

    float slopes[2][2] = {{-71.2378f, 13.4597f}, {-272.0602f, 3.4893f}};
    int fixed_slopes[2][2];
    float_array2_to_fix(slopes, fixed_slopes);
    float matrix[4][8] = {
        {70.785082606739/1000,20.2173858708657/1000,1.32921811478727/1000,2387.77324751470/1000,-23893.5281204093/1000,-9026.24819333978/1000,135.171307831437/1000,-232.108910489866/1000},
        {70.7850826067390/1000,20.2173858708657/1000,1.32921811478727/1000,2387.77324751470/1000,-23893.5281204093/1000,-9026.24819333978/1000,410.668585361385/1000,-232.108910489866/1000},
        {69.6603580753146/1000,19.8961460133584/1000,1.30809778595160/1000,4377.58428711028/1000,-43804.8015540837/1000,-8882.82754034463/1000,133.023532053490/1000,425.533002564754/1000},
        {65.3065856956075/1000,18.6526368875235/1000,1.22634167432962/1000,20587.9115563489/1000,-206015.309127084/1000,-8327.65081907309/1000,124.709561300147/1000,23636.4240515513/1000}
    };
    int fixed_matrix[4][8];
    float_array_to_fix(matrix, fixed_matrix);
    const int dt = fi(0.001f, 24);
    const int kp = fi(-0.75f, 24);
    const int expmel = fi(7.3306f, 24), expvsat = fi(6.6116f, 24);
    const int expmvgk = fi(0.2279f, 24), expvna = fi(0.0182f, 24);
    const int expek = fi(0.1364f, 24);
    fprintf(trace, "step,current,n0_vmem,n0_vk,n0_vg,n0_vna,n1_vmem,n1_vk,n1_vg,n1_vna,n2_vmem,n2_vk,n2_vg,n2_vna,n0_te,n0_ti,n1_te,n1_ti,n2_te,n2_ti\n");
    for (int step = 0; step < steps; ++step) {
        int external[3] = {0};
        if (fscanf(stimulus, "%d", &external[0]) != 1) {
            fprintf(stderr, "Missing stimulus for step %d\n", step);
            return 2;
        }
        Network_ODE(derivative, state, vmem, fixed_synapse_matrix, external,
                    kp, expmel, expvsat, expmvgk, expvna, expek,
                    fixed_slopes, fixed_matrix);
        for (int j = 0; j < 18; ++j)
            state[j] += j < 6 ? mul_16_24_16(derivative[j], dt)
                                : mul_24_8_24(derivative[j], dt);
        update_Vmem(state, vmem);
        fprintf(trace, "%d,%d", step, external[0]);
        for (int j = 6; j < 18; ++j) fprintf(trace, ",%d", state[j]);
        for (int j = 0; j < 6; ++j) fprintf(trace, ",%d", state[j]);
        fputc('\n', trace);
    }
    fclose(stimulus);
    fclose(trace);
    printf("C reference uses %d-bit multiplication\n",
#ifdef WIDE_MUL
           64);
#else
           (int)(sizeof(long) * 8));
#endif
    return 0;
}
