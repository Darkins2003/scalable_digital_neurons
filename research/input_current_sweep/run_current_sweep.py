from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import instrument_model
import sweep_analysis


DIRECTORY = Path(__file__).resolve().parent
PROJECT = DIRECTORY.parents[1]
sys.path.insert(0, str(DIRECTORY.parent / 'fixed_point_precision'))
import precision_support as baseline


def write_tables(output, cases, manifest):
    tables = output / 'tables'
    tables.mkdir(parents=True, exist_ok=True)
    behaviour, values, crossings, numeric = [], [], [], []
    for case in sorted(cases, key=lambda case: case['current_raw_q8']):
        behaviour.extend(case['behaviour'])
        values.extend(case['values'])
        crossings.extend(case['crossings'])
        numeric.append(case['numeric'])
    aggregate = sweep_analysis.aggregate_profiles(values, manifest['headroom_bits'])
    states = [row for row in aggregate if row['kind'] == 'state']
    baseline.write_rows(tables / 'behaviour_by_current.csv', behaviour)
    baseline.write_rows(tables / 'all_values_by_current.csv', values)
    baseline.write_rows(tables / 'all_value_ranges.csv', aggregate)
    baseline.write_rows(tables / 'state_integer_bits.csv', states)
    baseline.write_rows(tables / 'upward_crossings.csv', crossings)
    baseline.write_rows(tables / 'numeric_checks.csv', numeric)
    transitions = []
    previous = None
    for case in sorted(cases, key=lambda case: case['current_raw_q8']):
        if previous:
            count_changes = [f"n{neuron}: {previous['behaviour'][neuron]['crossings_during_pulse']} to {case['behaviour'][neuron]['crossings_during_pulse']}" for neuron in range(3) if previous['behaviour'][neuron]['crossings_during_pulse'] != case['behaviour'][neuron]['crossings_during_pulse']]
            before = {row['value']: row['integer_bits_observed'] for row in previous['values']}
            bit_changes = [row['value'] for row in case['values'] if row['value'] in before and row['integer_bits_observed'] != before[row['value']]]
            if count_changes or bit_changes or previous['numeric']['numerically_valid'] != case['numeric']['numerically_valid']:
                transitions.append(dict(previous_current_pa=previous['current_pa'], current_pa=case['current_pa'], pulse_count_changes='; '.join(count_changes), values_with_integer_bit_changes=len(bit_changes), changed_values='; '.join(bit_changes), numeric_status_changed=previous['numeric']['numerically_valid'] != case['numeric']['numerically_valid']))
        previous = case
    baseline.write_rows(tables / 'transitions.csv', transitions)
    return behaviour, values, aggregate, crossings, numeric


def make_manifest(arguments, currents, compiler):
    table = PROJECT / 'EfficientAnalogNeuron-SNNsims/C_fixedpoint_modified/base_two_exponential.h'
    sources = [Path(__file__), DIRECTORY / 'instrument_model.py', DIRECTORY / 'sweep_analysis.py', instrument_model.SOURCE, baseline.MODEL, table, baseline.REFERENCE, Path(baseline.__file__)]
    return dict(source_sha256={str(path.relative_to(PROJECT)): baseline.digest(path) for path in sources}, current_raw_q8=currents, steps=arguments.steps, timestep_ms=.001, pulse_start=arguments.pulse_start, pulse_end=arguments.pulse_end, headroom_bits=arguments.headroom_bits, spike_threshold=1.4542, baseline_formats=baseline.BASELINE, compiler=compiler, profile_compiler_flags=['-std=c11', '-O2', '-fwrapv'], reference_compiler_flags=['-std=c11', '-O0', '-fwrapv', '-DWIDE_MUL'], measured_network='Three-neuron excitatory ring, weight 0.26, original initial conditions', intended_range_pa=[0, 150], diagnostic_stop='Stop at end of first step with detected overflow; exclude invalid runs from range recommendations', analysis_scope='Observed fixed-point C behaviour, not mathematical accuracy or a new RTL verification')


def main():
    parser = argparse.ArgumentParser(description='Sweep input current in the existing 32-bit three-neuron model and profile individual numeric values.')
    parser.add_argument('--minimum-current', default='0')
    parser.add_argument('--maximum-current', default='300')
    parser.add_argument('--current-step', default='1')
    parser.add_argument('--steps', type=int, default=190000)
    parser.add_argument('--pulse-start', type=int, default=60000)
    parser.add_argument('--pulse-end', type=int, default=140000)
    parser.add_argument('--headroom-bits', type=int, default=1)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--gcc', default='gcc')
    parser.add_argument('--output', type=Path, default=DIRECTORY / 'results')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--keep-traces', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    arguments = parser.parse_args()
    if arguments.steps < 1 or arguments.workers < 1 or arguments.headroom_bits < 0 or not 0 <= arguments.pulse_start <= arguments.pulse_end < arguments.steps:
        parser.error('Use positive steps/workers, nonnegative headroom and a complete pulse interval inside the simulation.')
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'manifest.json'
    if arguments.report_only:
        manifest = json.loads(manifest_path.read_text())
        cases = [json.loads(path.read_text()) for path in (output / 'runs').glob('*/completed.json')]
        if any(case['fingerprint'] != manifest['fingerprint'] for case in cases):
            raise ValueError('Saved case fingerprint differs from the sweep manifest.')
    else:
        currents = sweep_analysis.current_grid(arguments.minimum_current, arguments.maximum_current, arguments.current_step)
        compiler = baseline.command([arguments.gcc, '--version']).splitlines()[0]
        manifest = make_manifest(arguments, currents, compiler)
        fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        manifest['fingerprint'] = fingerprint
        if manifest_path.exists() and json.loads(manifest_path.read_text())['fingerprint'] != fingerprint:
            raise ValueError('Existing sweep uses different sources or settings; choose a new --output directory.')
        baseline.save_json(manifest_path, manifest)
        build = DIRECTORY / 'build'
        build.mkdir(parents=True, exist_ok=True)
        generated = instrument_model.generate(build / 'profile_model.c')
        executable, reference = build / 'profile_model.exe', build / 'original_reference.exe'
        baseline.command([arguments.gcc, '-std=c11', '-O2', '-fwrapv', '-Wall', '-Wextra', '-Wno-unused-function', generated, '-lm', '-o', executable])
        baseline.command([arguments.gcc, '-std=c11', '-O0', '-fwrapv', '-w', '-DWIDE_MUL', baseline.REFERENCE, '-lm', '-o', reference])
        configuration = build / 'formats.txt'
        configuration.write_text(''.join(f'{baseline.BASELINE[group][0]} {baseline.BASELINE[group][1]}\n' for group in baseline.GROUPS))
        directories = {}
        for current_raw in currents:
            directory = output / 'runs' / sweep_analysis.current_name(current_raw)
            directory.mkdir(parents=True, exist_ok=True)
            directories[current_raw] = directory

        def run_current(current_raw):
            directory = directories[current_raw]
            checkpoint = directory / 'completed.json'
            if arguments.resume and checkpoint.is_file():
                saved = json.loads(checkpoint.read_text())
                if saved['fingerprint'] != fingerprint:
                    raise ValueError(f'Checkpoint fingerprint differs: {checkpoint}')
                return saved, True
            current_pa = current_raw / 256
            stimulus = directory / 'stimulus.txt'
            stimulus.write_text(f'{arguments.steps}\n' + ''.join(f'{current_raw if arguments.pulse_start <= step <= arguments.pulse_end else 0}\n' for step in range(arguments.steps)))
            raw_path, original_path = directory / 'trace.csv', directory / 'original_trace.csv'
            ranges_path, numeric_path, profile_path = directory / 'calculation_sites.csv', directory / 'numeric.json', directory / 'value_profiles.csv'
            start = time.perf_counter()
            baseline.command([executable, configuration, stimulus, raw_path, ranges_path, numeric_path, profile_path], directory)
            model_seconds = time.perf_counter() - start
            numeric = json.loads(numeric_path.read_text())
            raw = baseline.read_raw(raw_path)
            start = time.perf_counter()
            baseline.command([reference, stimulus, original_path], directory)
            reference_raw = baseline.read_raw(original_path)
            reference_seconds = time.perf_counter() - start
            good_rows = len(raw) if not numeric['overflow_count'] else max(0, numeric['first_overflow_step'])
            if not np.array_equal(raw[:good_rows], reference_raw[:good_rows]):
                raise ValueError(f'Profiling changed the original C arithmetic at {current_pa} pA.')
            if not numeric['overflow_count'] and len(raw) != arguments.steps:
                raise ValueError('The profiling model stopped without an overflow flag.')
            valid = numeric['overflow_count'] == 0 and numeric['zero_constants'] == 0 and len(raw) == arguments.steps
            profiles = sweep_analysis.read_profiles(profile_path, current_pa, manifest['timestep_ms'], arguments.headroom_bits)
            for row in profiles:
                row['numerically_valid'] = valid
            metrics, crossings, display = sweep_analysis.analyse_voltage(raw, profiles, current_pa, manifest['timestep_ms'], arguments.pulse_start, arguments.pulse_end, manifest['spike_threshold'])
            for row in metrics:
                row['numerically_valid'] = valid
            np.savez_compressed(directory / 'voltage_display.npz', **display)
            numeric.update(current_pa=current_pa, numerically_valid=valid, completed_steps=len(raw), requested_steps=arguments.steps, identical_to_original_c=not numeric['overflow_count'], checked_steps=good_rows, profiled_c_seconds=model_seconds, original_c_and_read_seconds=reference_seconds, completed_utc=datetime.now(timezone.utc).isoformat())
            saved = dict(fingerprint=fingerprint, current_raw_q8=current_raw, current_pa=current_pa, directory_name=directory.name, numeric=numeric, values=profiles, behaviour=metrics, crossings=crossings, raw_trace_sha256=baseline.digest(raw_path))
            baseline.save_json(checkpoint, saved)
            baseline.write_rows(directory / 'behaviour.csv', metrics)
            if crossings:
                baseline.write_rows(directory / 'crossings.csv', crossings)
            if not arguments.keep_traces:
                raw_path.unlink()
                original_path.unlink()
                stimulus.unlink()
            return saved, False

        cases = []
        print(f'Sweeping {len(currents)} currents: {currents[0] / 256:g} to {currents[-1] / 256:g} pA. Every run uses the original 32-bit formats.', flush=True)
        with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
            futures = [executor.submit(run_current, current) for current in currents]
            for future in as_completed(futures):
                case, cached = future.result()
                cases.append(case)
                count = [row['crossings_total'] for row in case['behaviour']]
                print(f"[{len(cases)}/{len(currents)}] {case['current_pa']:g} pA | crossings {count} | overflow {case['numeric']['overflow_count']} | {'saved' if cached else 'new'} | profiled C {case['numeric']['profiled_c_seconds']:.2f}s", flush=True)
                baseline.save_json(output / 'progress.json', dict(completed=len(cases), requested=len(currents), current_pa=case['current_pa'], status='running'), best_effort=True)
    if not cases:
        raise ValueError('No completed cases are available.')
    tables = write_tables(output, cases, manifest)
    from make_report import make_report
    make_report(output, cases, manifest, tables)
    report = dict(status='complete' if len(cases) == len(manifest['current_raw_q8']) else 'partial', completed_currents=len(cases), requested_currents=len(manifest['current_raw_q8']), currents_minimum_pa=min(case['current_pa'] for case in cases), currents_maximum_pa=max(case['current_pa'] for case in cases), profiled_variables=len(tables[2]), valid_currents=sum(case['numeric']['numerically_valid'] for case in cases), overflow_currents=[case['current_pa'] for case in cases if case['numeric']['overflow_count']], exact_original_c_cases=sum(case['numeric']['identical_to_original_c'] for case in cases), observed_states=len([row for row in tables[2] if row['kind'] == 'state']), profiled_c_seconds_total=sum(case['numeric']['profiled_c_seconds'] for case in cases), manifest_fingerprint=manifest['fingerprint'], limitation='Observed envelope of this network, pulse and 32-bit arithmetic; no universal integer-range guarantee and no new MATLAB/RTL accuracy comparison.')
    baseline.save_json(output / 'study_summary.json', report)
    baseline.save_json(output / 'progress.json', dict(completed=len(cases), requested=len(manifest['current_raw_q8']), status=report['status']), best_effort=True)
    print(json.dumps(report, indent=2), flush=True)
    print(f"Open {output / 'report.html'}", flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Current sweep failed: {error}', file=sys.stderr, flush=True)
        raise SystemExit(2)
