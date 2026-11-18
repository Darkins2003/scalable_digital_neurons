from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


DIRECTORY = Path(__file__).resolve().parent
PROJECT = DIRECTORY.parents[1]
GROUPS = ('state', 'matrix', 'current', 'triangle', 'constant', 'timestep')
BASELINE = dict(zip(GROUPS, ((32, 24), (32, 23), (32, 8), (32, 16), (32, 24), (32, 24))))
HELPER = PROJECT / 'ip/scalable_digital_neurons/sim/mut/three_neurons_1D/scripts/compare_golden_reference.py'
REFERENCE = HELPER.with_name('three_neurons_reference.c')
MODEL = PROJECT / 'EfficientAnalogNeuron-SNNsims/C_fixedpoint_modified/1D_Synfire/Synfire_1D_3neur_fixed.c'
TABLE = MODEL.parents[1] / 'base_two_exponential.h'
SPECIFICATION = importlib.util.spec_from_file_location('golden_comparison', HELPER)
COMPARISON = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(COMPARISON)
FIELDS = ('step', 'current', *COMPARISON.STATE_NAMES)
DISABLED_PROGRESS_PATHS = set()


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def profile_source_matches(relative, expected):
    path = PROJECT / relative
    if path.is_file() and digest(path) == expected:
        return True
    compatibility = json.loads((DIRECTORY / 'profile_source_compatibility.json').read_text())
    alias = compatibility['source_aliases'].get(Path(relative).as_posix())
    if alias is None or alias['previous_sha256'] != expected:
        return False
    current = PROJECT / alias['current_path']
    return current.is_file() and digest(current) == alias['current_sha256']


def compatible_source_sets(previous, active):
    compatibility = json.loads((DIRECTORY / 'profile_source_compatibility.json').read_text())
    expected_paths = set()
    for relative, expected in previous.items():
        if not profile_source_matches(relative, expected):
            return False
        alias = compatibility['source_aliases'].get(Path(relative).as_posix())
        expected_paths.add(alias['current_path'] if alias and alias['previous_sha256'] == expected else Path(relative).as_posix())
    expected_paths.add('research/fixed_point_precision/profile_source_compatibility.json')
    if expected_paths != {Path(relative).as_posix() for relative in active}:
        return False
    return all((PROJECT / relative).is_file() and digest(PROJECT / relative) == expected for relative, expected in active.items())


def save_json(path, value, best_effort=False):
    if best_effort and path in DISABLED_PROGRESS_PATHS:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, allow_nan=False) + '\n'
    if path.is_file() and path.read_text(encoding='utf-8') == payload:
        return True
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(payload)
        for attempt in range(6):
            try:
                temporary.replace(path)
                return True
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(min(.05 * 2 ** attempt, .5))
    except PermissionError:
        if not best_effort:
            raise
        DISABLED_PROGRESS_PATHS.add(path)
        print(f'Warning: Windows blocked {path.name}; continuing with saved per-run checkpoints and terminal progress.', file=sys.stderr, flush=True)
        return False
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except PermissionError:
            pass


def write_rows(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def command(arguments, directory=DIRECTORY, environment=None):
    result = subprocess.run(list(map(str, arguments)), cwd=directory, text=True, capture_output=True, env=environment)
    if result.returncode:
        raise RuntimeError(f'Command failed: {arguments}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def build(destination, compiler):
    destination.mkdir(parents=True, exist_ok=True)
    executable = destination / 'precision_model.exe'
    reference = destination / 'reference.exe'
    command([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Wno-unused-function', DIRECTORY / 'precision_model.c', '-lm', '-o', executable])
    command([compiler, '-std=c11', '-O0', '-w', '-fwrapv', '-DWIDE_MUL', REFERENCE, '-lm', '-o', reference])
    return executable, reference


def read_raw(path):
    with path.open(encoding='utf-8-sig') as source:
        header = next(csv.reader(source))
    if tuple(header) != FIELDS:
        raise ValueError(f'Unexpected trace fields: {path}')
    values = np.loadtxt(path, delimiter=',', skiprows=1, dtype=np.int64, ndmin=2)
    if not np.array_equal(values[:, 0], np.arange(len(values))):
        raise ValueError(f'Invalid step sequence: {path}')
    return values


def decode(raw, formats):
    decoded = raw.astype(float)
    for index, field in enumerate(FIELDS[1:], 1):
        group = 'current' if field == 'current' else 'triangle' if field.endswith(('_te', '_ti')) else 'state'
        decoded[:, index] /= 2 ** formats[group][1]
    return decoded


def accuracy(actual, expected, name, current, configuration):
    if actual.shape != expected.shape or not np.array_equal(actual[:, :2], expected[:, :2]):
        raise ValueError('Steps or decoded input current differ between comparison traces')
    time_ms = (actual[:, 0] + 1) * .001
    state_rows, spike_rows, match_rows = [], [], []
    for index, field in enumerate(FIELDS[2:], 2):
        error = actual[:, index] - expected[:, index]
        span = float(np.ptp(expected[:, index]))
        root_mean_square = float(np.sqrt(np.mean(error * error)))
        state_rows.append(dict(configuration=configuration, current_pa=current, reference=name, state=field, rmse=root_mean_square, maximum_absolute_error=float(np.max(np.abs(error))), normalised_rmse_percent=100 * root_mean_square / span if span else None))
    for neuron in range(3):
        column = 2 + 4 * neuron
        expected_spikes = COMPARISON.spike_times(time_ms, expected[:, column], 1.4542)
        actual_spikes = COMPARISON.spike_times(time_ms, actual[:, column], 1.4542)
        pairs = COMPARISON.match_spikes(expected_spikes, actual_spikes, .5)
        errors = np.array([actual_spikes[second] - expected_spikes[first] for first, second in pairs])
        ordinal_count = min(len(actual_spikes), len(expected_spikes))
        ordinal = actual_spikes[:ordinal_count] - expected_spikes[:ordinal_count]
        spike_rows.append(dict(configuration=configuration, current_pa=current, reference=name, neuron=neuron, reference_spikes=len(expected_spikes), candidate_spikes=len(actual_spikes), matched_spikes=len(pairs), unmatched_reference=len(expected_spikes) - len(pairs), unmatched_candidate=len(actual_spikes) - len(pairs), mean_signed_error_ms=float(np.mean(errors)) if errors.size else None, mean_absolute_error_ms=float(np.mean(np.abs(errors))) if errors.size else None, maximum_absolute_error_ms=float(np.max(np.abs(errors))) if errors.size else None, ordinal_last_delay_ms=float(ordinal[-1]) if ordinal_count else None, ordinal_maximum_absolute_error_ms=float(np.max(np.abs(ordinal))) if ordinal_count else None))
        for first, second in pairs:
            match_rows.append(dict(configuration=configuration, current_pa=current, reference=name, neuron=neuron, matching='window_0.5_ms', reference_time_ms=float(expected_spikes[first]), candidate_time_ms=float(actual_spikes[second]), error_ms=float(actual_spikes[second] - expected_spikes[first])))
        for index in range(ordinal_count):
            match_rows.append(dict(configuration=configuration, current_pa=current, reference=name, neuron=neuron, matching='ordinal_diagnostic', reference_time_ms=float(expected_spikes[index]), candidate_time_ms=float(actual_spikes[index]), error_ms=float(ordinal[index])))
    return state_rows, spike_rows, match_rows


def run_model(executable, directory, formats, stimulus):
    directory.mkdir(parents=True, exist_ok=True)
    configuration = directory / 'formats.txt'
    configuration.write_text(''.join(f'{formats[group][0]} {formats[group][1]}\n' for group in GROUPS))
    start = time.perf_counter()
    command([executable, configuration, stimulus, directory / 'trace.csv', directory / 'ranges.csv', directory / 'numeric.json'])
    seconds = time.perf_counter() - start
    summary = json.loads((directory / 'numeric.json').read_text())
    summary['execution_seconds'] = seconds
    with (directory / 'ranges.csv').open(newline='') as source:
        ranges = list(csv.DictReader(source))
    for row in ranges:
        magnitude = max(abs(float(row['minimum'])), abs(float(row['maximum'])))
        width, fractional = int(row['width']), int(row['fractional'])
        row['headroom_bits'] = math.log2((2 ** (width - fractional - 1)) / magnitude) if magnitude else None
    write_rows(directory / 'ranges.csv', ranges)
    return read_raw(directory / 'trace.csv'), summary, ranges


def required_integer_bits(minimum, maximum):
    for bits in range(1, 65):
        if minimum >= -(2 ** (bits - 1)) and maximum < 2 ** (bits - 1):
            return bits
    raise ValueError('Range exceeds diagnostic support')
