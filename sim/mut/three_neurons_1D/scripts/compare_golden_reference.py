from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


IP_DIRECTORY = Path(__file__).resolve().parents[4]
PROJECT_DIRECTORY = IP_DIRECTORY.parents[1]
MODEL_DIRECTORY = PROJECT_DIRECTORY / 'EfficientAnalogNeuron-SNNsims/MATLAB/Golden_reference'
DEFAULT_RESULTS_DIRECTORY = IP_DIRECTORY / 'build/sim/three_neurons_1D/tc_011_golden_reference_trace'
DEFAULT_FIXED_TRACE = DEFAULT_RESULTS_DIRECTORY / 'hdl_trace.csv'
STATE_NAMES = tuple(f'n{neuron}_{state}' for neuron in range(3) for state in ('vmem', 'vk', 'vg', 'vna')) + tuple(f'n{neuron}_{state}' for neuron in range(3) for state in ('te', 'ti'))


def read_trace(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline='', encoding='utf-8-sig') as source:
        names = next(csv.reader(source))
    if len(names) != len(set(names)):
        raise ValueError(f'Duplicate column names in {path}')
    values = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2, encoding='utf-8-sig')
    if not values.size or values.shape[1] != len(names) or not np.isfinite(values).all():
        raise ValueError(f'Empty, non-finite or malformed trace: {path}')
    missing = set(('step', 'current', *STATE_NAMES)) - set(names)
    if missing:
        raise ValueError(f'Missing columns in {path}: {sorted(missing)}')
    result = dict(zip(names, values.T))
    if not np.array_equal(result['step'], np.arange(len(values))):
        raise ValueError(f'Steps must be consecutive integers starting at zero: {path}')
    return result


def spike_times(time: np.ndarray, voltage: np.ndarray, threshold: float) -> np.ndarray:
    crossings = np.flatnonzero((voltage[:-1] < threshold) & (voltage[1:] >= threshold))
    fractions = (threshold-voltage[crossings]) / (voltage[crossings+1]-voltage[crossings])
    return time[crossings] + fractions*(time[crossings+1]-time[crossings])


def match_spikes(golden: np.ndarray, fixed: np.ndarray, window: float) -> list[tuple[int, int]]:
    counts = np.zeros((len(golden)+1, len(fixed)+1), dtype=int)
    costs = np.zeros_like(counts, dtype=float)
    decisions = np.zeros_like(counts)
    for golden_index in range(1, len(golden)+1):
        for fixed_index in range(1, len(fixed)+1):
            candidates = [(counts[golden_index-1, fixed_index], costs[golden_index-1, fixed_index], 1), (counts[golden_index, fixed_index-1], costs[golden_index, fixed_index-1], 2)]
            difference = abs(golden[golden_index-1]-fixed[fixed_index-1])
            if difference <= window:
                candidates.append((counts[golden_index-1, fixed_index-1]+1, costs[golden_index-1, fixed_index-1]+difference, 3))
            count, cost, decision = min(candidates, key=lambda candidate: (-candidate[0], candidate[1]))
            counts[golden_index, fixed_index] = count
            costs[golden_index, fixed_index] = cost
            decisions[golden_index, fixed_index] = decision
    golden_index, fixed_index = len(golden), len(fixed)
    matches = []
    while golden_index and fixed_index:
        decision = decisions[golden_index, fixed_index]
        if decision == 3:
            matches.append((golden_index-1, fixed_index-1))
            golden_index -= 1
            fixed_index -= 1
        elif decision == 1:
            golden_index -= 1
        else:
            fixed_index -= 1
    return list(reversed(matches))


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def file_hash(path: Path) -> str:
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def make_plots(time: np.ndarray, golden: dict[str, np.ndarray], fixed: dict[str, np.ndarray], destination: Path, fixed_label: str) -> None:
    figure, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 2, 2, 1]})
    for neuron in range(3):
        field = f'n{neuron}_vmem'
        axes[neuron].plot(time, golden[field], label='Golden MATLAB reference', linewidth=1.15, color='#146c94')
        axes[neuron].plot(time, fixed[field], label=fixed_label, linewidth=1, linestyle='--', color='#d55e00')
        axes[neuron].set_ylabel(f'Neuron {neuron}\nVmem (normalised)')
        axes[neuron].grid(alpha=.25)
    axes[0].legend(loc='upper right')
    axes[3].plot(time, golden['current'], color='#333333', linewidth=1)
    axes[3].set_ylabel('External input\n(pA)')
    axes[3].set_xlabel('Nominal simulated time (ms)')
    axes[3].grid(alpha=.25)
    figure.suptitle(f'Three-neuron synfire ring: golden reference versus {fixed_label}')
    figure.tight_layout()
    figure.savefig(destination / 'vmem_overlay.png', dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for neuron in range(3):
        field = f'n{neuron}_vmem'
        axes[neuron].plot(time, fixed[field]-golden[field], color='#7b3294', linewidth=.9)
        axes[neuron].axhline(0, color='#777777', linewidth=.6)
        axes[neuron].set_ylabel(f'Neuron {neuron}\nVoltage error')
        axes[neuron].grid(alpha=.25)
    axes[-1].set_xlabel('Nominal simulated time (ms)')
    figure.suptitle(f'{fixed_label} minus golden reference (normalised voltage units)')
    figure.tight_layout()
    figure.savefig(destination / 'vmem_error.png', dpi=180)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare the recorded MATLAB golden trace against a decoded three-neuron simulation trace.')
    parser.add_argument('--golden', type=Path, default=MODEL_DIRECTORY / 'results/golden_reference_trace.csv')
    parser.add_argument('--fixed', type=Path, default=DEFAULT_FIXED_TRACE, help='Step-indexed C or RTL CSV containing raw signed fixed-point integers.')
    parser.add_argument('--fixed-label', default='IP RTL')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_RESULTS_DIRECTORY)
    parser.add_argument('--check-golden', action='store_true', help='Validate the saved MATLAB trace before starting the simulation.')
    parser.add_argument('--allow-prefix', action='store_true', help='Compare a shorter fixed-point run against the same initial steps of the saved golden trace.')
    parser.add_argument('--state-fractional-bits', type=int, default=24)
    parser.add_argument('--triangle-fractional-bits', type=int, default=16)
    parser.add_argument('--current-fractional-bits', type=int, default=8)
    parser.add_argument('--timestep-ms', type=float, default=.001)
    parser.add_argument('--spike-threshold', type=float, default=1.4542)
    parser.add_argument('--spike-match-window-ms', type=float, default=.5)
    arguments = parser.parse_args()
    if any(value < 0 or value > 31 for value in (arguments.state_fractional_bits, arguments.triangle_fractional_bits, arguments.current_fractional_bits)):
        parser.error('Fractional bit counts must be between 0 and 31.')
    if arguments.timestep_ms <= 0 or arguments.spike_match_window_ms <= 0:
        parser.error('Timestep and spike matching window must be positive.')
    try:
        golden_path = arguments.golden.resolve()
        fixed_path = arguments.fixed.resolve()
        golden = read_trace(golden_path)
        golden_total_samples = len(golden['step'])
        if 'time_ms' not in golden:
            raise ValueError('Golden trace must contain time_ms.')
        time = golden['time_ms']
        if not np.allclose(time, (golden['step']+1)*arguments.timestep_ms, rtol=0, atol=1e-9):
            raise ValueError('Golden sample times do not match the supplied nominal timestep.')
        if arguments.check_golden:
            print(f'Golden reference ready: {len(time)} completed steps from {golden_path}')
            return 0
        if not fixed_path.is_file():
            raise FileNotFoundError(f'{fixed_path} does not exist. Run tc_011_golden_reference_trace or supply --fixed PATH.')
        fixed_raw = read_trace(fixed_path)
        if arguments.allow_prefix and len(fixed_raw['step']) < golden_total_samples:
            golden = {field: values[:len(fixed_raw['step'])] for field, values in golden.items()}
            time = golden['time_ms']
        if not np.array_equal(golden['step'], fixed_raw['step']):
            raise ValueError('Trace lengths or step indices differ. Only matching initial steps can be compared with --allow-prefix.')
        for field in ('current', *STATE_NAMES):
            if not np.array_equal(fixed_raw[field], np.rint(fixed_raw[field])):
                raise ValueError(f'Fixed trace column {field} must contain raw integer values.')
            if np.any((fixed_raw[field] < -(2**31)) | (fixed_raw[field] > 2**31-1)):
                raise ValueError(f'Fixed trace column {field} exceeds the signed 32-bit range.')
        fixed = {'current': fixed_raw['current']/2**arguments.current_fractional_bits}
        for field in STATE_NAMES:
            fractional_bits = arguments.triangle_fractional_bits if field.endswith(('_te', '_ti')) else arguments.state_fractional_bits
            fixed[field] = fixed_raw[field]/2**fractional_bits
        if not np.allclose(golden['current'], fixed['current'], rtol=0, atol=1e-12):
            raise ValueError('Input current differs between the two traces.')

        metrics = []
        for field in STATE_NAMES:
            difference = fixed[field]-golden[field]
            reference_range = float(np.ptp(golden[field]))
            root_mean_square_error = float(np.sqrt(np.mean(difference**2)))
            metrics.append({'state': field, 'rmse': root_mean_square_error, 'maximum_absolute_error': float(np.max(np.abs(difference))), 'mean_error': float(np.mean(difference)), 'golden_range': reference_range, 'range_normalised_rmse_percent': 100*root_mean_square_error/reference_range if reference_range else None})

        spike_metrics, spike_rows = [], []
        for neuron in range(3):
            field = f'n{neuron}_vmem'
            golden_spikes = spike_times(time, golden[field], arguments.spike_threshold)
            fixed_spikes = spike_times(time, fixed[field], arguments.spike_threshold)
            matches = match_spikes(golden_spikes, fixed_spikes, arguments.spike_match_window_ms)
            matched_golden = {pair[0] for pair in matches}
            matched_fixed = {pair[1] for pair in matches}
            differences = np.array([fixed_spikes[fixed_index]-golden_spikes[golden_index] for golden_index, fixed_index in matches])
            spike_metrics.append({'neuron': neuron, 'golden_spikes': len(golden_spikes), 'fixed_spikes': len(fixed_spikes), 'matched_spikes': len(matches), 'unmatched_golden_spikes': len(golden_spikes)-len(matches), 'unmatched_fixed_spikes': len(fixed_spikes)-len(matches), 'mean_absolute_timing_error_ms': float(np.mean(np.abs(differences))) if len(matches) else None, 'maximum_absolute_timing_error_ms': float(np.max(np.abs(differences))) if len(matches) else None, 'mean_timing_bias_ms': float(np.mean(differences)) if len(matches) else None})
            ordinal_differences = fixed_spikes-golden_spikes if len(fixed_spikes) == len(golden_spikes) and len(golden_spikes) else np.array([])
            spike_metrics[-1].update({'ordinal_mean_absolute_timing_error_ms': float(np.mean(np.abs(ordinal_differences))) if len(ordinal_differences) else None, 'ordinal_maximum_absolute_timing_error_ms': float(np.max(np.abs(ordinal_differences))) if len(ordinal_differences) else None, 'ordinal_last_spike_timing_bias_ms': float(ordinal_differences[-1]) if len(ordinal_differences) else None})
            for golden_index, fixed_index in matches:
                spike_rows.append({'neuron': neuron, 'status': 'matched', 'golden_time_ms': float(golden_spikes[golden_index]), 'fixed_time_ms': float(fixed_spikes[fixed_index]), 'fixed_minus_golden_ms': float(fixed_spikes[fixed_index]-golden_spikes[golden_index])})
            for index, spike in enumerate(golden_spikes):
                if index not in matched_golden:
                    spike_rows.append({'neuron': neuron, 'status': 'unmatched_golden', 'golden_time_ms': float(spike), 'fixed_time_ms': None, 'fixed_minus_golden_ms': None})
            for index, spike in enumerate(fixed_spikes):
                if index not in matched_fixed:
                    spike_rows.append({'neuron': neuron, 'status': 'unmatched_fixed', 'golden_time_ms': None, 'fixed_time_ms': float(spike), 'fixed_minus_golden_ms': None})

        destination = arguments.output_dir.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        write_rows(destination / 'state_metrics.csv', metrics)
        write_rows(destination / 'spike_metrics.csv', spike_metrics)
        if spike_rows:
            write_rows(destination / 'spike_matches.csv', spike_rows)
        else:
            with (destination / 'spike_matches.csv').open('w', encoding='utf-8') as output:
                output.write('neuron,status,golden_time_ms,fixed_time_ms,fixed_minus_golden_ms\n')
        summary = {'golden_trace': str(golden_path), 'golden_sha256': file_hash(golden_path), 'fixed_trace': str(fixed_path), 'fixed_sha256': file_hash(fixed_path), 'fixed_label': arguments.fixed_label, 'samples': len(time), 'nominal_timestep_ms': arguments.timestep_ms, 'state_fractional_bits': arguments.state_fractional_bits, 'triangle_fractional_bits': arguments.triangle_fractional_bits, 'current_fractional_bits': arguments.current_fractional_bits, 'spike_threshold': arguments.spike_threshold, 'spike_match_window_ms': arguments.spike_match_window_ms, 'error_sign': 'fixed minus golden', 'time_alignment': 'same completed step, nominal timestep; no waveform shifts or warping', 'state_metrics': metrics, 'spike_metrics': spike_metrics}
        summary.update({'golden_total_samples': golden_total_samples, 'comparison_is_prefix': len(time) < golden_total_samples})
        (destination / 'comparison_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
        make_plots(time, golden, fixed, destination, arguments.fixed_label)
        print(f'Compared {len(time)} completed steps; stimulus and step indices match.')
        if len(time) < golden_total_samples:
            print(f'Compared only the first {len(time)} of {golden_total_samples} saved golden steps.')
        for row in metrics:
            if row['state'].endswith('_vmem'):
                normalised_error = f"{row['range_normalised_rmse_percent']:.4g}%" if row['range_normalised_rmse_percent'] is not None else 'undefined (zero reference range)'
                print(f"{row['state']}: RMSE={row['rmse']:.6g}, max absolute error={row['maximum_absolute_error']:.6g}, range-normalised RMSE={normalised_error}")
        for row in spike_metrics:
            print(f"Neuron {row['neuron']}: golden={row['golden_spikes']} spikes, fixed={row['fixed_spikes']}, matched={row['matched_spikes']} within {arguments.spike_match_window_ms:g} ms")
        print(f'Results: {destination}')
        return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f'Comparison could not complete: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
