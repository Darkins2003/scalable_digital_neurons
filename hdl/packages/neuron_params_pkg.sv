package neuron_params_pkg;

    import neuron_params_generated_pkg::*;

    localparam int NUM_NEURONS = 3;

    localparam fixed_t ONE_Q24 = 32'sd16777216; // 1 x 1=2^24
    localparam fixed_t ONE_Q8 = 32'sd256; // 1 x 1=2^8
    localparam fixed_t VNA_OFFSET_Q24 = 32'sd390120603;

endpackage
