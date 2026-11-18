from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import run_current_sweep as sweep
from make_full_report import create_report


DIRECTORY = Path(__file__).resolve().parent
BANDS = (
    ('01_325_to_1000pA', 325, 1000, 25),
    ('02_1250_to_10000pA', 1250, 10000, 250),
    ('03_12500_to_100000pA', 12500, 100000, 2500),
    ('04_125000_to_1000000pA', 125000, 1000000, 25000),
)
MATCH_FIELDS = ('source_sha256', 'steps', 'timestep_ms', 'pulse_start', 'pulse_end', 'headroom_bits', 'spike_threshold', 'baseline_formats', 'compiler', 'profile_compiler_flags', 'reference_compiler_flags', 'measured_network', 'intended_range_pa')


def checked_cases(directory, expected_currents=None):
    manifest = json.loads((directory / 'manifest.json').read_text())
    for relative, expected in manifest['source_sha256'].items():
        if not sweep.baseline.profile_source_matches(relative, expected):
            raise ValueError(f'Numerical source changed since {directory}: {relative}')
    if expected_currents is not None and manifest['current_raw_q8'] != expected_currents:
        raise ValueError(f'Unexpected current grid in {directory}')
    result = []
    for checkpoint in (directory / 'runs').glob('*/completed.json'):
        case = json.loads(checkpoint.read_text())
        if case['fingerprint'] != manifest['fingerprint'] or case['current_raw_q8'] not in manifest['current_raw_q8']:
            raise ValueError(f'Invalid checkpoint provenance: {checkpoint}')
        case['_source_directory'] = directory
        result.append(case)
    if len({case['current_raw_q8'] for case in result}) != len(result):
        raise ValueError('Duplicate current checkpoints')
    return manifest, result


def main():
    parser = argparse.ArgumentParser(description='Extend the input-current investigation to 1,000,000 pA in four progressively coarser bands.')
    parser.add_argument('--output', type=Path, default=DIRECTORY / 'results_extended')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--gcc', default='gcc')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    print('Loading original checkpoints and checking source hashes...', flush=True)
    original_manifest, original_cases = checked_cases(DIRECTORY / 'results')
    all_extended, band_summaries, band_fingerprints = [], [], {}
    for name, minimum, maximum, step in BANDS:
        directory = output / name
        expected = list(range(minimum * 256, maximum * 256 + 1, step * 256))
        reusable = False
        if arguments.resume and (directory / 'study_summary.json').is_file():
            stored = json.loads((directory / 'study_summary.json').read_text())
            if stored['status'] == 'complete':
                saved_manifest, saved = checked_cases(directory, expected)
                reusable = len(saved) == len(expected)
        if not arguments.report_only and not reusable:
            command = [sys.executable, '-u', str(DIRECTORY / 'run_current_sweep.py'), '--minimum-current', str(minimum), '--maximum-current', str(maximum), '--current-step', str(step), '--output', str(directory), '--workers', str(arguments.workers), '--gcc', arguments.gcc]
            if arguments.resume:
                command.append('--resume')
            print(f'Extended band: {minimum:,} to {maximum:,} pA, step {step:,} pA', flush=True)
            subprocess.run(command, check=True)
        if not (directory / 'manifest.json').is_file():
            continue
        print(f'Loading saved band: {minimum:,}-{maximum:,} pA', flush=True)
        manifest, cases = checked_cases(directory, expected)
        for field in MATCH_FIELDS:
            if manifest[field] != original_manifest[field]:
                raise ValueError(f'Extended band changed the original experiment: {field}')
        all_extended.extend(cases)
        band_fingerprints[name] = manifest['fingerprint']
        band_summaries.append(dict(directory=name, minimum_pa=minimum, maximum_pa=maximum, step_pa=step, completed_currents=len(cases), valid_currents=sum(case['numeric']['numerically_valid'] for case in cases), overflow_currents=sum(case['numeric']['overflow_count'] > 0 for case in cases)))
    if not all_extended:
        raise ValueError('No extended cases are available.')
    summary = create_report(output, original_manifest, original_cases, all_extended, band_summaries)
    sweep.baseline.save_json(output / 'extended_manifest.json', dict(original_fingerprint=original_manifest['fingerprint'], band_fingerprints=band_fingerprints, bands=BANDS, extension_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), report_script_sha256=hashlib.sha256((DIRECTORY / 'make_full_report.py').read_bytes()).hexdigest(), original_experiment_unchanged=True))
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Open {output / 'report.html'}", flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Extended current sweep failed: {error}', file=sys.stderr, flush=True)
        raise SystemExit(2)
