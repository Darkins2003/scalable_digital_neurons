import argparse
from pathlib import Path

import summarize_results


DIRECTORY = Path(__file__).resolve().parent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate the organised Q24 FPGA tables and trade-off plots without rerunning Vivado.")
    parser.add_argument("--clock-mhz", type=float, default=250)
    arguments = parser.parse_args()
    summarize_results.summarize(DIRECTORY / "results" / f"{arguments.clock_mhz:g}MHz")
