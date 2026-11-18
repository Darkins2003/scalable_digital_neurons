from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
SOURCE = DIRECTORY.parent / 'fixed_point_precision/precision_model.c'

PROFILER = r'''
enum {
    PROFILE_STATE = 0, PROFILE_DERIVATIVE = 18, PROFILE_UPDATE = 36,
    PROFILE_SCALED_TRIANGLE = 54, PROFILE_TRIANGLE_EXPONENTIAL = 60,
    PROFILE_TRIANGLE_EXPONENT = 66, PROFILE_COUPLED_TRIANGLE = 72,
    PROFILE_CURRENTS = 78, PROFILE_KAPPA_SODIUM = 102,
    PROFILE_KAPPA_GATE = 105, PROFILE_KAPPA_POTASSIUM = 108,
    PROFILE_SODIUM_EXPONENT = 111, PROFILE_INHIBITORY_EXPONENT = 114,
    PROFILE_POTASSIUM_EXPONENT = 117, PROFILE_SCALE = 120,
    PROFILE_SCALED_WEIGHT = 138, PROFILE_SYNAPSE_PRODUCT = 156,
    PROFILE_SYNAPSE_SUM = 174, PROFILE_TOTAL_CURRENT = 192,
    PROFILE_MATRIX_PRODUCT = 195, PROFILE_MATRIX_SUM = 291,
    PROFILE_FIXED_MATRIX = 387, PROFILE_SLOPES = 419,
    PROFILE_CONSTANT = 423, PROFILE_EXTERNAL = 443,
    PROFILE_EXP_ARGUMENT = 444, PROFILE_EXP_OUTPUT = 600, PROFILE_PRODUCTS = 1024,
    PROFILE_CAPACITY = 5000
};

typedef struct {
    char name[112];
    const char *kind;
    const char *phase;
    int fractional;
    int width;
    int64_t minimum;
    int64_t maximum;
    int64_t first;
    uint64_t count;
    int minimum_step;
    int maximum_step;
} ValueProfile;

static ValueProfile value_profiles[PROFILE_CAPACITY];

static void profile_register(int identifier, const char *name, const char *kind, int fractional, int width, const char *phase) {
    ValueProfile *profile = &value_profiles[identifier];
    snprintf(profile->name, sizeof(profile->name), "%s", name);
    profile->kind = kind;
    profile->fractional = fractional;
    profile->width = width;
    profile->phase = phase;
}

static void profile_record(int identifier, int64_t value) {
    ValueProfile *profile = &value_profiles[identifier];
    if (!profile->count) { profile->first = value; }
    if (!profile->count || value < profile->minimum) { profile->minimum = value; profile->minimum_step = simulation_step; }
    if (!profile->count || value > profile->maximum) { profile->maximum = value; profile->maximum_step = simulation_step; }
    profile->count++;
}

static int32_t profile_observe(int identifier, int32_t value) {
    profile_record(identifier, value);
    return value;
}

static void profile_initialize(void) {
    const char *state_names[] = {"vmem", "vk", "vg", "vna"};
    const char *constant_names[] = {"timestep", "coupling", "triangle_scaling", "triangle_offset_excitatory", "triangle_offset_inhibitory", "synapse_bias_excitatory", "synapse_bias_inhibitory", "triangle_upper_bound", "negative_spike_threshold", "inhibitory_membrane_offset", "sodium_voltage_offset", "kappa", "expmel", "expvsat", "expmvgk", "expvna", "expek", "synapse_coefficient", "excitatory_scale", "current_one"};
    const int constant_fractional[] = {24,24,24,16,16,24,24,16,24,24,24,24,24,24,24,24,24,24,8,8};
    char name[112];
    for (int index = 0; index < 18; index++) {
        int neuron = index < 6 ? index / 2 : (index - 6) / 4;
        const char *field = index < 6 ? (index % 2 ? "ti" : "te") : state_names[(index - 6) % 4];
        snprintf(name, sizeof(name), "n%d.%s", neuron, field);
        profile_register(PROFILE_STATE + index, name, "state", index < 6 ? 16 : 24, 32, "after_update");
        snprintf(name, sizeof(name), "n%d.derivative_%s", neuron, field);
        profile_register(PROFILE_DERIVATIVE + index, name, "derivative", index < 6 ? 16 : 8, 32, "before_update");
        snprintf(name, sizeof(name), "n%d.update_%s", neuron, field);
        profile_register(PROFILE_UPDATE + index, name, "euler_update", index < 6 ? 16 : 24, 32, "before_update");
    }
    for (int index = 0; index < 6; index++) {
        const char *field = index % 2 ? "inhibitory" : "excitatory";
        int starts[] = {PROFILE_SCALED_TRIANGLE, PROFILE_TRIANGLE_EXPONENTIAL, PROFILE_TRIANGLE_EXPONENT, PROFILE_COUPLED_TRIANGLE};
        const char *labels[] = {"scaled_triangle", "triangle_exponential", "triangle_exponent", "coupled_triangle"};
        const char *kinds[] = {"scaled_triangle", "exponential_output", "exponent_argument", "scaled_triangle"};
        int fractional[] = {16,8,24,24};
        for (int part = 0; part < 4; part++) {
            snprintf(name, sizeof(name), "n%d.%s_%s", index / 2, labels[part], field);
            profile_register(starts[part] + index, name, kinds[part], fractional[part], 32, "before_update");
        }
    }
    for (int neuron = 0; neuron < 3; neuron++) {
        for (int index = 0; index < 8; index++) {
            snprintf(name, sizeof(name), "n%d.current_vector[%d]", neuron, index);
            profile_register(PROFILE_CURRENTS + neuron * 8 + index, name, "current_vector", 8, 32, "before_update");
        }
        int starts[] = {PROFILE_KAPPA_SODIUM, PROFILE_KAPPA_GATE, PROFILE_KAPPA_POTASSIUM, PROFILE_SODIUM_EXPONENT, PROFILE_INHIBITORY_EXPONENT, PROFILE_POTASSIUM_EXPONENT, PROFILE_TOTAL_CURRENT};
        const char *labels[] = {"kappa_sodium", "kappa_gate", "kappa_potassium", "sodium_exponent", "inhibitory_exponent", "potassium_exponent", "total_current"};
        for (int index = 0; index < 7; index++) {
            snprintf(name, sizeof(name), "n%d.%s", neuron, labels[index]);
            profile_register(starts[index] + neuron, name, index == 6 ? "total_current" : "exponent_argument", index == 6 ? 8 : 24, 32, "before_update");
        }
        for (int index = 0; index < 6; index++) {
            int starts[] = {PROFILE_SCALE, PROFILE_SCALED_WEIGHT, PROFILE_SYNAPSE_PRODUCT, PROFILE_SYNAPSE_SUM};
            const char *labels[] = {"synapse_scale", "scaled_weight", "synapse_product", "synapse_partial_sum"};
            int fractional[] = {8,24,8,8};
            for (int part = 0; part < 4; part++) {
                snprintf(name, sizeof(name), "n%d.%s[%d]", neuron, labels[part], index);
                profile_register(starts[part] + neuron * 6 + index, name, "synapse_calculation", fractional[part], 32, "before_update");
            }
        }
        for (int row = 0; row < 4; row++) {
            for (int column = 0; column < 8; column++) {
                snprintf(name, sizeof(name), "n%d.matrix_product[%d;%d]", neuron, row, column);
                profile_register(PROFILE_MATRIX_PRODUCT + neuron * 32 + row * 8 + column, name, "matrix_product_rescaled", 8, 32, "before_update");
                snprintf(name, sizeof(name), "n%d.matrix_partial_sum[%d;%d]", neuron, row, column);
                profile_register(PROFILE_MATRIX_SUM + neuron * 32 + row * 8 + column, name, "matrix_partial_sum", 8, 32, "before_update");
            }
        }
        for (int site = 0; site < SITE_COUNT; site++) {
            snprintf(name, sizeof(name), "n%d.exponential_input.%s", neuron, site_names[site]);
            profile_register(PROFILE_EXP_ARGUMENT + neuron * SITE_COUNT + site, name, "exponent_argument", 24, 32, "before_update");
            snprintf(name, sizeof(name), "n%d.exponential_output.%s", neuron, site_names[site]);
            profile_register(PROFILE_EXP_OUTPUT + neuron * SITE_COUNT + site, name, "exponential_output", 8, 32, "before_update");
        }
    }
    for (int row = 0; row < 4; row++) {
        for (int column = 0; column < 8; column++) {
            snprintf(name, sizeof(name), "neuron_matrix[%d;%d]", row, column);
            profile_register(PROFILE_FIXED_MATRIX + row * 8 + column, name, "constant", 23, 32, "initialisation");
        }
    }
    for (int row = 0; row < 2; row++) {
        for (int column = 0; column < 2; column++) {
            snprintf(name, sizeof(name), "triangle_slope[%d;%d]", row, column);
            profile_register(PROFILE_SLOPES + row * 2 + column, name, "constant", 16, 32, "initialisation");
        }
    }
    for (int index = 0; index < 20; index++) { profile_register(PROFILE_CONSTANT + index, constant_names[index], "constant", constant_fractional[index], 32, "initialisation"); }
    profile_register(PROFILE_EXTERNAL, "external_current_neuron0", "external_current", 8, 32, "before_update");
}

static void profile_write(const char *path) {
    FILE *output = fopen(path, "w");
    if (!output) { perror(path); exit(2); }
    fprintf(output, "value,kind,phase,width,fractional,minimum_raw,maximum_raw,first_raw,minimum_step,maximum_step,observations\n");
    for (int index = 0; index < PROFILE_CAPACITY; index++) {
        ValueProfile *profile = &value_profiles[index];
        if (profile->count) {
            fprintf(output, "%s,%s,%s,%d,%d,%lld,%lld,%lld,%d,%d,%llu\n", profile->name, profile->kind, profile->phase, profile->width, profile->fractional, (long long)profile->minimum, (long long)profile->maximum, (long long)profile->first, profile->minimum_step, profile->maximum_step, (unsigned long long)profile->count);
        }
    }
    fclose(output);
}
'''


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f'Profiling anchor changed: {before[:100]}')
    return source.replace(before, after, 1)


def generate(destination):
    source = SOURCE.read_text()
    table = DIRECTORY.parents[1] / 'EfficientAnalogNeuron-SNNsims/C_fixedpoint_modified/base_two_exponential.h'
    source = replace_once(source, '#include "../../EfficientAnalogNeuron-SNNsims/C_fixedpoint_modified/base_two_exponential.h"', f'#include "{table.as_posix()}"')
    source = replace_once(source, 'static int first_overflow_neuron = -1;', 'static int first_overflow_neuron = -1;\n' + PROFILER)
    source = replace_once(source, '    int64_t product = (int64_t)first * second;', '''    int64_t product = (int64_t)first * second;
    int profile_identifier = PROFILE_PRODUCTS + neuron_bank * SITE_COUNT * GROUP_COUNT * GROUP_COUNT + site * GROUP_COUNT * GROUP_COUNT + first_group * GROUP_COUNT + second_group;
    if (!value_profiles[profile_identifier].name[0]) {
        char profile_name[112];
        snprintf(profile_name, sizeof(profile_name), "raw_product.n%d.%s.%s_x_%s", neuron_bank == 3 ? -1 : neuron_bank, site_names[site], group_names[first_group], group_names[second_group]);
        profile_register(profile_identifier, profile_name, "raw_product", formats[first_group].fractional + formats[second_group].fractional, 64, "before_update");
    }
    profile_record(profile_identifier, product);''')
    source = replace_once(source, '    int fractional = formats[STATE].fractional;', '    profile_record(PROFILE_EXP_ARGUMENT + neuron_bank * SITE_COUNT + site, exponent);\n    int fractional = formats[STATE].fractional;')
    source = replace_once(source, '    return narrow(bits, raw, CURRENT, site);', '    return profile_observe(PROFILE_EXP_OUTPUT + neuron_bank * SITE_COUNT + site, narrow(bits, raw, CURRENT, site));')
    source = replace_once(source, 'if (argc != 6)', 'if (argc != 7)')
    source = replace_once(source, 'trace.csv ranges.csv summary.json', 'trace.csv ranges.csv summary.json values.csv')
    source = replace_once(source, '    fclose(configuration);', '''    fclose(configuration);
    const int expected_fractional[] = {24,23,8,16,24,24};
    for (int group = 0; group < GROUP_COUNT; group++) {
        if (formats[group].width != 32 || formats[group].fractional != expected_fractional[group]) { fprintf(stderr, "The current sweep requires the original 32-bit formats\\n"); return 2; }
    }
    profile_initialize();''')
    source = replace_once(source, '    int32_t one = encode(1, CURRENT, PARAMETER);', '''    int32_t one = encode(1, CURRENT, PARAMETER);
    for (int index = 0; index < 18; index++) { profile_record(PROFILE_STATE + index, state[index]); }
    for (int row = 0; row < 4; row++) {
        for (int column = 0; column < 8; column++) { profile_record(PROFILE_FIXED_MATRIX + row * 8 + column, fixed_matrix[row][column]); }
    }
    for (int row = 0; row < 2; row++) {
        for (int column = 0; column < 2; column++) { profile_record(PROFILE_SLOPES + row * 2 + column, fixed_slopes[row][column]); }
    }
    int32_t profile_constants[] = {timestep,coupling,triangle_scaling,triangle_offsets[0],triangle_offsets[1],biases[0],biases[1],upper_bound,negative_threshold,membrane_offset,sodium_offset,kappa,constants[0],constants[1],constants[2],constants[3],constants[4],synapse,excitatory_scale,one};
    for (int index = 0; index < 20; index++) { profile_record(PROFILE_CONSTANT + index, profile_constants[index]); }''')
    source = replace_once(source, '        int32_t external = rescale(stimulus_q8, 8, CURRENT, EXTERNAL);', '        int32_t external = profile_observe(PROFILE_EXTERNAL, rescale(stimulus_q8, 8, CURRENT, EXTERNAL));')
    source = replace_once(source, '            int32_t exponent = add(multiply(coupling, CONSTANT, scaled_triangles[index], TRIANGLE, STATE, COUPLED_TRIANGLE), biases[index % 2], STATE, SYNAPSE_EXPONENT);', '''            profile_record(PROFILE_SCALED_TRIANGLE + index, scaled_triangles[index]);
            int32_t coupled_triangle = profile_observe(PROFILE_COUPLED_TRIANGLE + index, multiply(coupling, CONSTANT, scaled_triangles[index], TRIANGLE, STATE, COUPLED_TRIANGLE));
            int32_t exponent = profile_observe(PROFILE_TRIANGLE_EXPONENT + index, add(coupled_triangle, biases[index % 2], STATE, SYNAPSE_EXPONENT));''')
    source = replace_once(source, '            triangle_exponentials[index] = exponential(exponent, SYNAPSE_EXPONENTIAL);', '            triangle_exponentials[index] = profile_observe(PROFILE_TRIANGLE_EXPONENTIAL + index, exponential(exponent, SYNAPSE_EXPONENTIAL));')
    source = replace_once(source, 'exponential(add(state[6 + 4 * neuron], membrane_offset, STATE, EXPONENT_SUM), EXPONENTIAL)', 'exponential(profile_observe(PROFILE_INHIBITORY_EXPONENT + neuron, add(state[6 + 4 * neuron], membrane_offset, STATE, EXPONENT_SUM)), EXPONENTIAL)')
    source = replace_once(source, '                int enabled = index == 2 * ((neuron + 2) % 3);', '                profile_record(PROFILE_SCALE + neuron * 6 + index, scale);\n                int enabled = index == 2 * ((neuron + 2) % 3);')
    source = replace_once(source, '                total_current = add(total_current, multiply(scaled_weight, CONSTANT, triangle_exponentials[index], CURRENT, CURRENT, SYNAPSE_PRODUCT), CURRENT, SYNAPSE_SUM);', '''                profile_record(PROFILE_SCALED_WEIGHT + neuron * 6 + index, scaled_weight);
                total_current = profile_observe(PROFILE_SYNAPSE_SUM + neuron * 6 + index, add(total_current, profile_observe(PROFILE_SYNAPSE_PRODUCT + neuron * 6 + index, multiply(scaled_weight, CONSTANT, triangle_exponentials[index], CURRENT, CURRENT, SYNAPSE_PRODUCT)), CURRENT, SYNAPSE_SUM));''')
    source = replace_once(source, '            for (int triangle = 0; triangle < 2; triangle++) {', '            profile_record(PROFILE_TOTAL_CURRENT + neuron, total_current);\n            for (int triangle = 0; triangle < 2; triangle++) {')
    source = replace_once(source, '            int32_t currents[8];', '''            profile_record(PROFILE_KAPPA_SODIUM + neuron, kappa_sodium);
            profile_record(PROFILE_KAPPA_GATE + neuron, kappa_gate);
            profile_record(PROFILE_KAPPA_POTASSIUM + neuron, kappa_potassium);
            int32_t currents[8];''')
    source = replace_once(source, '            currents[4] = subtract', '            profile_record(PROFILE_SODIUM_EXPONENT + neuron, sodium_exponent);\n            currents[4] = subtract')
    source = replace_once(source, 'exponential(add(voltage[0], kappa_potassium, STATE, EXPONENT_SUM), EXPONENTIAL)', 'exponential(profile_observe(PROFILE_POTASSIUM_EXPONENT + neuron, add(voltage[0], kappa_potassium, STATE, EXPONENT_SUM)), EXPONENTIAL)')
    source = replace_once(source, '            for (int row = 0; row < 4; row++) {', '            for (int index = 0; index < 8; index++) { profile_record(PROFILE_CURRENTS + neuron * 8 + index, currents[index]); }\n            for (int row = 0; row < 4; row++) {')
    source = replace_once(source, '                for (int column = 0; column < 8; column++) { sum = add(sum, multiply(fixed_matrix[row][column], MATRIX, currents[column], CURRENT, CURRENT, MATRIX_PRODUCT), CURRENT, MATRIX_SUM); }', '                for (int column = 0; column < 8; column++) { sum = profile_observe(PROFILE_MATRIX_SUM + neuron * 32 + row * 8 + column, add(sum, profile_observe(PROFILE_MATRIX_PRODUCT + neuron * 32 + row * 8 + column, multiply(fixed_matrix[row][column], MATRIX, currents[column], CURRENT, CURRENT, MATRIX_PRODUCT)), CURRENT, MATRIX_SUM)); }')
    source = replace_once(source, '            int32_t update = multiply', '            profile_record(PROFILE_DERIVATIVE + index, derivatives[index]);\n            int32_t update = multiply')
    source = replace_once(source, '            state[index] = add(state[index], update, group, NEXT_STATE);', '            profile_record(PROFILE_UPDATE + index, update);\n            state[index] = profile_observe(PROFILE_STATE + index, add(state[index], update, group, NEXT_STATE));')
    source = replace_once(source, "        fputc('\\n', trace);", "        fputc('\\n', trace);\n        if (total_overflows) { break; }")
    source = replace_once(source, '    fclose(summary);', '    fclose(summary);\n    profile_write(argv[6]);')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source)
    return destination
