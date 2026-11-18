from decimal import Decimal


def print_timing_results(title, frequency_mhz, measurements):
    clock_period_ns = Decimal(1000) / Decimal(frequency_mhz)
    print(f"{title} | {frequency_mhz} MHz | period = {clock_period_ns:.6f} ns")
    for name, samples, cycles in measurements:
        mean_ns = Decimal(cycles) * clock_period_ns
        print(f"TIMING: {name} samples={samples} cycles min/mean/max={cycles}/{cycles:.3f}/{cycles} mean_ns={mean_ns:.3f}")


def main():
    print("CALCULATED TIMING FROM RECORDED CYCLE COUNTS")
    print("Frequency conversion only; not a new simulation or hardware measurement.")
    print()
    print_timing_results("BEFORE TIMING OPTIMISATION", "50", [
        ("neuron_0_latency", 128, 20),
        ("neuron_1_latency", 128, 20),
        ("neuron_2_latency", 128, 20),
        ("network_update_latency", 128, 63),
        ("network_update_interval", 127, 65),
        ("startup_to_first_update", 1, 91),
        ("startup_synapse_pass", 1, 26),
    ])
    print()
    print_timing_results("AFTER TIMING OPTIMISATION", "218", [
        ("neuron_0_latency", 128, 59),
        ("neuron_1_latency", 128, 59),
        ("neuron_2_latency", 128, 59),
        ("network_update_latency", 128, 171),
        ("network_update_interval", 127, 173),
        ("startup_to_first_update", 1, 226),
        ("startup_synapse_pass", 1, 53),
    ])

    print()
    print_timing_results("ADDITIONAL RECORDED RESULTS", "50", [
        ("neuron_0_latency", 128, 21),
        ("neuron_1_latency", 128, 21),
        ("neuron_2_latency", 128, 21),
        ("network_update_latency", 128, 37),
        ("network_update_interval", 127, 38),
        ("startup_to_first_update", 1, 51),
        ("startup_synapse_pass", 1, 13),
    ])


if __name__ == "__main__":
    main()
