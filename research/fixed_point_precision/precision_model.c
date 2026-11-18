#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "../../EfficientAnalogNeuron-SNNsims/C_fixedpoint_modified/base_two_exponential.h"

enum { STATE, MATRIX, CURRENT, TRIANGLE, CONSTANT, TIMESTEP, GROUP_COUNT };
enum { INITIAL, COEFFICIENT, SLOPE, PARAMETER, EXTERNAL, SCALED_TRIANGLE, COUPLED_TRIANGLE, SYNAPSE_EXPONENT, SYNAPSE_EXPONENTIAL, SYNAPSE_SCALE, SCALED_WEIGHT, SYNAPSE_PRODUCT, SYNAPSE_SUM, TOTAL_CURRENT, STATE_PRODUCT, EXPONENT_SUM, EXPONENTIAL, CURRENT_PRODUCT, CURRENT_DIFFERENCE, MATRIX_PRODUCT, MATRIX_SUM, TRIANGLE_DERIVATIVE, UPDATE, NEXT_STATE, SITE_COUNT };

static const char *group_names[] = {"state", "matrix", "current", "triangle", "constant", "timestep"};
static const char *site_names[] = {"initial", "coefficient", "slope", "parameter", "external", "scaled_triangle", "coupled_triangle", "synapse_exponent", "synapse_exponential", "synapse_scale", "scaled_weight", "synapse_product", "synapse_sum", "total_current", "state_product", "exponent_sum", "exponential", "current_product", "current_difference", "matrix_product", "matrix_sum", "triangle_derivative", "update", "next_state"};

typedef struct { int width; int fractional; } Format;
typedef struct { double minimum; double maximum; uint64_t count; uint64_t overflows; uint64_t lost; int first_step; } Measurement;

static Format formats[GROUP_COUNT];
static Measurement measurements[4][SITE_COUNT][GROUP_COUNT];
static Measurement products[4];
static int neuron_bank = 3;
static int simulation_step = -1;
static uint64_t total_overflows = 0;
static uint64_t zero_constants = 0;
static uint64_t lost_updates = 0;
static int first_overflow_step = -2;
static int first_overflow_site = -1;
static int first_overflow_group = -1;
static int first_overflow_neuron = -1;

static void measure(Measurement *measurement, double value) {
    if (!measurement->count || value < measurement->minimum) { measurement->minimum = value; }
    if (!measurement->count || value > measurement->maximum) { measurement->maximum = value; }
    measurement->count++;
}

static int32_t signed_bits(uint64_t bits, int width) {
    uint64_t modulus = UINT64_C(1) << width;
    bits &= modulus - 1;
    return (int32_t)((bits & (modulus >> 1)) ? (int64_t)bits - (int64_t)modulus : (int64_t)bits);
}

static int32_t narrow(uint64_t bits, double mathematical_raw, int group, int site) {
    Measurement *measurement = &measurements[neuron_bank][site][group];
    Format format = formats[group];
    measure(measurement, ldexp(mathematical_raw, -format.fractional));
    if (mathematical_raw < -ldexp(1, format.width - 1) || mathematical_raw > ldexp(1, format.width - 1) - 1) {
        if (!measurement->overflows) { measurement->first_step = simulation_step; }
        measurement->overflows++;
        total_overflows++;
        if (first_overflow_site < 0) {
            first_overflow_step = simulation_step;
            first_overflow_site = site;
            first_overflow_group = group;
            first_overflow_neuron = neuron_bank;
        }
    }
    return signed_bits(bits, format.width);
}

static int64_t floor_shift(int64_t value, int shift) {
    if (!shift) { return value; }
    if (shift >= 63) { return value < 0 ? -1 : 0; }
    if (value >= 0) { return value / (INT64_C(1) << shift); }
    return -1 - ((-1 - value) / (INT64_C(1) << shift));
}

static int32_t rescale(int64_t value, int source_fractional, int group, int site) {
    int shift = source_fractional - formats[group].fractional;
    if (shift >= 0) {
        int64_t shifted = floor_shift(value, shift);
        return narrow((uint64_t)shifted, shifted, group, site);
    }
    uint64_t bits = -shift >= 64 ? 0 : (uint64_t)value << -shift;
    return narrow(bits, ldexp((double)value, -shift), group, site);
}

static int32_t encode(double value, int group, int site) {
    double raw = trunc(ldexp((double)value, formats[group].fractional));
    int64_t integer = (int64_t)raw;
    int32_t result = narrow((uint64_t)integer, raw, group, site);
    if (value != 0 && result == 0) { zero_constants++; }
    return result;
}

static int32_t add(int32_t first, int32_t second, int group, int site) {
    int64_t sum = (int64_t)first + second;
    return narrow((uint64_t)sum, sum, group, site);
}

static int32_t subtract(int32_t first, int32_t second, int group, int site) {
    int64_t difference = (int64_t)first - second;
    return narrow((uint64_t)difference, difference, group, site);
}

static int32_t multiply(int32_t first, int first_group, int32_t second, int second_group, int result_group, int site) {
    int64_t product = (int64_t)first * second;
    measure(&products[neuron_bank], (double)product);
    return rescale(product, formats[first_group].fractional + formats[second_group].fractional, result_group, site);
}

static int32_t exponential(int32_t exponent, int site) {
    int fractional = formats[STATE].fractional;
    int64_t integer = floor_shift(exponent, fractional);
    int64_t remainder = (int64_t)exponent - integer * (INT64_C(1) << fractional);
    unsigned address = fractional >= 10 ? (unsigned)(remainder >> (fractional - 10)) : (unsigned)(remainder << (10 - fractional));
    uint64_t table_value = fractional_exponent_estimation_table[address];
    int shift = (int)integer + formats[CURRENT].fractional - 24;
    double raw = floor(ldexp((double)table_value, shift));
    uint64_t bits;
    if (shift >= 0) { bits = shift >= 64 ? 0 : table_value << shift; }
    else { bits = -shift >= 64 ? 0 : table_value >> -shift; }
    return narrow(bits, raw, CURRENT, site);
}

static void write_measurements(const char *path) {
    FILE *output = fopen(path, "w");
    if (!output) { perror(path); exit(2); }
    fprintf(output, "neuron,signal,group,width,fractional,minimum,maximum,count,overflow_count,first_overflow_step,lost_updates\n");
    for (int neuron = 0; neuron < 4; neuron++) {
        for (int site = 0; site < SITE_COUNT; site++) {
            for (int group = 0; group < GROUP_COUNT; group++) {
                Measurement *measurement = &measurements[neuron][site][group];
                if (measurement->count) {
                    fprintf(output, "%d,%s,%s,%d,%d,%.17g,%.17g,%llu,%llu,%d,%llu\n", neuron == 3 ? -1 : neuron, site_names[site], group_names[group], formats[group].width, formats[group].fractional, (double)measurement->minimum, (double)measurement->maximum, (unsigned long long)measurement->count, (unsigned long long)measurement->overflows, measurement->overflows ? measurement->first_step : -2, (unsigned long long)measurement->lost);
                }
            }
        }
        if (products[neuron].count) {
            fprintf(output, "%d,full_product_raw,wide_product,64,0,%.17g,%.17g,%llu,0,-2,0\n", neuron == 3 ? -1 : neuron, (double)products[neuron].minimum, (double)products[neuron].maximum, (unsigned long long)products[neuron].count);
        }
    }
    fclose(output);
}

int main(int argc, char **argv) {
    if (argc != 6) { fprintf(stderr, "Usage: precision_model configuration.txt stimulus.txt trace.csv ranges.csv summary.json\n"); return 2; }
    FILE *configuration = fopen(argv[1], "r");
    FILE *stimulus = fopen(argv[2], "r");
    FILE *trace = fopen(argv[3], "w");
    if (!configuration || !stimulus || !trace) { perror("configuration/stimulus/trace"); return 2; }
    for (int group = 0; group < GROUP_COUNT; group++) {
        if (fscanf(configuration, "%d %d", &formats[group].width, &formats[group].fractional) != 2 || formats[group].width < 2 || formats[group].width > 32 || formats[group].fractional < 0 || formats[group].fractional >= formats[group].width) { fprintf(stderr, "Invalid format\n"); return 2; }
    }
    fclose(configuration);
    int steps;
    if (fscanf(stimulus, "%d", &steps) != 1 || steps < 1) { return 2; }
    float matrix[4][8] = {
        {70.785082606739/1000,20.2173858708657/1000,1.32921811478727/1000,2387.77324751470/1000,-23893.5281204093/1000,-9026.24819333978/1000,135.171307831437/1000,-232.108910489866/1000},
        {70.785082606739/1000,20.2173858708657/1000,1.32921811478727/1000,2387.77324751470/1000,-23893.5281204093/1000,-9026.24819333978/1000,410.668585361385/1000,-232.108910489866/1000},
        {69.6603580753146/1000,19.8961460133584/1000,1.30809778595160/1000,4377.58428711028/1000,-43804.8015540837/1000,-8882.82754034463/1000,133.023532053490/1000,425.533002564754/1000},
        {65.3065856956075/1000,18.6526368875235/1000,1.22634167432962/1000,20587.9115563489/1000,-206015.309127084/1000,-8327.65081907309/1000,124.709561300147/1000,23636.4240515513/1000}
    };
    float slopes[2][2] = {{-71.2378f,13.4597f},{-272.0602f,3.4893f}};
    int32_t fixed_matrix[4][8], fixed_slopes[2][2], state[18];
    for (int row = 0; row < 4; row++) {
        for (int column = 0; column < 8; column++) { fixed_matrix[row][column] = encode(matrix[row][column], MATRIX, COEFFICIENT); }
    }
    for (int row = 0; row < 2; row++) {
        for (int column = 0; column < 2; column++) { fixed_slopes[row][column] = encode(slopes[row][column], TRIANGLE, SLOPE); }
    }
    float initial[] = {-2.8309f,2.1341f,-4.4310f,-4.4310f};
    for (int index = 0; index < 18; index++) { state[index] = encode(index < 6 ? (double)(float)144.2695 : initial[(index - 6) % 4], index < 6 ? TRIANGLE : STATE, INITIAL); }
    int32_t timestep = encode((float)0.001, TIMESTEP, PARAMETER);
    int32_t coupling = encode(-10066329.0 / 16777216, CONSTANT, PARAMETER);
    int32_t triangle_scaling = encode(0xCCCCC / 16777216.0, CONSTANT, PARAMETER);
    int32_t triangle_offsets[] = {encode(8509364.0 / 65536, TRIANGLE, PARAMETER),encode(945487.0 / 65536, TRIANGLE, PARAMETER)};
    int32_t biases[] = {encode(86, STATE, PARAMETER),encode(19, STATE, PARAMETER)};
    int32_t upper_bound = encode(0x009044FD / 65536.0, TRIANGLE, PARAMETER);
    int32_t negative_threshold = encode(-1.4542, STATE, PARAMETER);
    int32_t membrane_offset = encode(13.2053 - 21, STATE, PARAMETER);
    int32_t sodium_offset = encode(390120603.0 / 16777216, STATE, PARAMETER);
    int32_t kappa = encode(-0.75, CONSTANT, PARAMETER);
    int32_t constants[] = {encode(7.3306f, CONSTANT, PARAMETER),encode(6.6116f, CONSTANT, PARAMETER),encode(0.2279f, CONSTANT, PARAMETER),encode(0.0182f, CONSTANT, PARAMETER),encode(0.1364f, CONSTANT, PARAMETER)};
    float weight = 0.26f;
    float synapse_value = (float)((float)2.1425 * pow(2, (-0.75 * weight / (0.025 * log(2))) + 9.9658));
    int32_t synapse = encode(synapse_value, CONSTANT, COEFFICIENT);
    int32_t excitatory_scale = encode(88.0 / 256, CURRENT, PARAMETER);
    int32_t one = encode(1, CURRENT, PARAMETER);
    fprintf(trace, "step,current,n0_vmem,n0_vk,n0_vg,n0_vna,n1_vmem,n1_vk,n1_vg,n1_vna,n2_vmem,n2_vk,n2_vg,n2_vna,n0_te,n0_ti,n1_te,n1_ti,n2_te,n2_ti\n");
    for (simulation_step = 0; simulation_step < steps; simulation_step++) {
        int stimulus_q8;
        if (fscanf(stimulus, "%d", &stimulus_q8) != 1) { fprintf(stderr, "Missing stimulus\n"); return 2; }
        int32_t external = rescale(stimulus_q8, 8, CURRENT, EXTERNAL);
        int32_t scaled_triangles[6], triangle_exponentials[6], derivatives[18];
        for (int index = 0; index < 6; index++) {
            neuron_bank = index / 2;
            scaled_triangles[index] = add(multiply(state[index], TRIANGLE, triangle_scaling, CONSTANT, TRIANGLE, SCALED_TRIANGLE), triangle_offsets[index % 2], TRIANGLE, SCALED_TRIANGLE);
            int32_t exponent = add(multiply(coupling, CONSTANT, scaled_triangles[index], TRIANGLE, STATE, COUPLED_TRIANGLE), biases[index % 2], STATE, SYNAPSE_EXPONENT);
            triangle_exponentials[index] = exponential(exponent, SYNAPSE_EXPONENTIAL);
        }
        for (int neuron = 0; neuron < 3; neuron++) {
            neuron_bank = neuron;
            int32_t total_current = 0;
            for (int index = 0; index < 6; index++) {
                int32_t scale = index % 2 == 0 ? excitatory_scale : subtract(0, exponential(add(state[6 + 4 * neuron], membrane_offset, STATE, EXPONENT_SUM), EXPONENTIAL), CURRENT, SYNAPSE_SCALE);
                int enabled = index == 2 * ((neuron + 2) % 3);
                int32_t scaled_weight = multiply(enabled ? synapse : 0, CONSTANT, scale, CURRENT, CONSTANT, SCALED_WEIGHT);
                total_current = add(total_current, multiply(scaled_weight, CONSTANT, triangle_exponentials[index], CURRENT, CURRENT, SYNAPSE_PRODUCT), CURRENT, SYNAPSE_SUM);
            }
            total_current = add(total_current, neuron == 0 ? external : 0, CURRENT, TOTAL_CURRENT);
            for (int triangle = 0; triangle < 2; triangle++) {
                int above = add(state[6 + 4 * neuron], negative_threshold, STATE, EXPONENT_SUM) >= 0;
                int32_t derivative = fixed_slopes[triangle][above ? 0 : 1];
                int32_t value = state[2 * neuron + triangle];
                if ((value >= upper_bound && derivative >= 0) || (value <= 0 && derivative <= 0)) { derivative = 0; }
                derivatives[2 * neuron + triangle] = narrow((uint64_t)(int64_t)derivative, derivative, TRIANGLE, TRIANGLE_DERIVATIVE);
            }
            int32_t *voltage = &state[6 + 4 * neuron];
            int32_t kappa_sodium = multiply(kappa, CONSTANT, voltage[3], STATE, STATE, STATE_PRODUCT);
            int32_t kappa_gate = multiply(kappa, CONSTANT, voltage[2], STATE, STATE, STATE_PRODUCT);
            int32_t kappa_potassium = multiply(kappa, CONSTANT, voltage[1], STATE, STATE, STATE_PRODUCT);
            int32_t currents[8];
            currents[0] = total_current;
            currents[1] = subtract(one, multiply(constants[0], CONSTANT, exponential(voltage[0], EXPONENTIAL), CURRENT, CURRENT, CURRENT_PRODUCT), CURRENT, CURRENT_DIFFERENCE);
            currents[2] = multiply(exponential(kappa_sodium, EXPONENTIAL), CURRENT, subtract(one, multiply(constants[3], CONSTANT, exponential(voltage[0], EXPONENTIAL), CURRENT, CURRENT, CURRENT_PRODUCT), CURRENT, CURRENT_DIFFERENCE), CURRENT, CURRENT, CURRENT_PRODUCT);
            currents[3] = exponential(kappa_gate, EXPONENTIAL);
            int32_t sodium_exponent = subtract(subtract(0, voltage[3], STATE, EXPONENT_SUM), sodium_offset, STATE, EXPONENT_SUM);
            currents[4] = subtract(one, multiply(constants[1], CONSTANT, exponential(sodium_exponent, EXPONENTIAL), CURRENT, CURRENT, CURRENT_PRODUCT), CURRENT, CURRENT_DIFFERENCE);
            currents[5] = subtract(exponential(add(voltage[0], kappa_potassium, STATE, EXPONENT_SUM), EXPONENTIAL), multiply(constants[4], CONSTANT, exponential(kappa_potassium, EXPONENTIAL), CURRENT, CURRENT, CURRENT_PRODUCT), CURRENT, CURRENT_DIFFERENCE);
            currents[6] = subtract(one, multiply(constants[2], CONSTANT, exponential(voltage[1], EXPONENTIAL), CURRENT, CURRENT, CURRENT_PRODUCT), CURRENT, CURRENT_DIFFERENCE);
            currents[7] = subtract(exponential(voltage[2], EXPONENTIAL), exponential(voltage[3], EXPONENTIAL), CURRENT, CURRENT_DIFFERENCE);
            for (int row = 0; row < 4; row++) {
                int32_t sum = 0;
                for (int column = 0; column < 8; column++) { sum = add(sum, multiply(fixed_matrix[row][column], MATRIX, currents[column], CURRENT, CURRENT, MATRIX_PRODUCT), CURRENT, MATRIX_SUM); }
                derivatives[6 + 4 * neuron + row] = sum;
            }
        }
        for (int index = 0; index < 18; index++) {
            neuron_bank = index < 6 ? index / 2 : (index - 6) / 4;
            int group = index < 6 ? TRIANGLE : STATE;
            int32_t update = multiply(derivatives[index], index < 6 ? TRIANGLE : CURRENT, timestep, TIMESTEP, group, UPDATE);
            if (derivatives[index] != 0 && timestep != 0 && update == 0) { measurements[neuron_bank][UPDATE][group].lost++; lost_updates++; }
            state[index] = add(state[index], update, group, NEXT_STATE);
        }
        fprintf(trace, "%d,%d", simulation_step, external);
        for (int index = 6; index < 18; index++) { fprintf(trace, ",%d", state[index]); }
        for (int index = 0; index < 6; index++) { fprintf(trace, ",%d", state[index]); }
        fputc('\n', trace);
    }
    fclose(stimulus);
    fclose(trace);
    write_measurements(argv[4]);
    FILE *summary = fopen(argv[5], "w");
    if (!summary) { perror(argv[5]); return 2; }
    fprintf(summary, "{\"overflow_count\":%llu,\"zero_constants\":%llu,\"lost_updates\":%llu,\"first_overflow_step\":%d,\"first_overflow_signal\":\"%s\",\"first_overflow_group\":\"%s\",\"first_overflow_neuron\":%d}\n", (unsigned long long)total_overflows, (unsigned long long)zero_constants, (unsigned long long)lost_updates, first_overflow_step, first_overflow_site < 0 ? "" : site_names[first_overflow_site], first_overflow_group < 0 ? "" : group_names[first_overflow_group], first_overflow_neuron == 3 ? -1 : first_overflow_neuron);
    fclose(summary);
    return 0;
}
