from __future__ import annotations

import csv
from decimal import Decimal

import numpy as np


STATE_NAMES = tuple(f'n{neuron}.{state}' for neuron in range(3) for state in ('vmem', 'vk', 'vg', 'vna')) + tuple(f'n{neuron}.{state}' for neuron in range(3) for state in ('te', 'ti'))


def current_grid(minimum, maximum, step):
    values = [Decimal(str(value)) * 256 for value in (minimum, maximum, step)]
    if any(value != value.to_integral_value() for value in values):
        raise ValueError('Currents and increments must be exactly representable in Q8 (multiples of 1/256 pA).')
    minimum_raw, maximum_raw, increment_raw = map(int, values)
    if increment_raw <= 0 or maximum_raw < minimum_raw or minimum_raw < -(2 ** 31) or maximum_raw >= 2 ** 31:
        raise ValueError('Invalid current range or increment.')
    if (maximum_raw - minimum_raw) % increment_raw:
        raise ValueError('The maximum current must lie on the selected current grid.')
    result = list(range(minimum_raw, maximum_raw + 1, increment_raw))
    if len(result) > 10000:
        raise ValueError('Use at most 10000 current levels per sweep.')
    return result


def current_name(raw):
    value = format(Decimal(raw) / 256, 'f')
    pieces = value.split('.')
    whole = pieces[0].replace('-', '').zfill(3)
    return 'current_' + ('minus_' if raw < 0 else '') + whole + ('p' + pieces[1] if len(pieces) > 1 else '')


def integer_bits(minimum_raw, maximum_raw, fractional):
    minimum_raw, maximum_raw = int(minimum_raw), int(maximum_raw)
    if minimum_raw > maximum_raw:
        raise ValueError('Minimum exceeds maximum.')
    positive = max(1, maximum_raw.bit_length() + 1) if maximum_raw >= 0 else 1
    negative = (-minimum_raw - 1).bit_length() + 1 if minimum_raw < 0 else 1
    return max(1, max(positive, negative) - fractional)


def read_profiles(path, current_pa, timestep_ms, headroom):
    with path.open(newline='') as source:
        raw_rows = list(csv.DictReader(source))
    result = []
    for raw in raw_rows:
        fractional = int(raw['fractional'])
        low, high = int(raw['minimum_raw']), int(raw['maximum_raw'])
        needed = integer_bits(low, high, fractional)
        minimum_step, maximum_step = int(raw['minimum_step']), int(raw['maximum_step'])
        offset = int(raw['phase'] == 'after_update')
        result.append(dict(current_pa=current_pa, value=raw['value'], kind=raw['kind'], phase=raw['phase'], baseline_width=int(raw['width']), fractional_bits=fractional, minimum_raw=low, maximum_raw=high, first_raw=int(raw['first_raw']), minimum=low / 2 ** fractional, maximum=high / 2 ** fractional, minimum_time_ms=0 if minimum_step < 0 else (minimum_step + offset) * timestep_ms, maximum_time_ms=0 if maximum_step < 0 else (maximum_step + offset) * timestep_ms, minimum_at_initialisation=minimum_step < 0, maximum_at_initialisation=maximum_step < 0, integer_bits_observed=needed, integer_bits_with_headroom=needed + headroom, width_to_preserve_fractional_bits=needed + fractional, remaining_integer_headroom_bits=int(raw['width']) - fractional - needed, observations=int(raw['observations'])))
    if len({row['value'] for row in result}) != len(result):
        raise ValueError('Duplicate numerical variable profile names.')
    return result


def upward_crossings(time_ms, voltage, threshold):
    indices = np.flatnonzero((voltage[:-1] < threshold) & (voltage[1:] >= threshold))
    fractions = (threshold - voltage[indices]) / (voltage[indices + 1] - voltage[indices])
    return indices, time_ms[indices] + fractions * (time_ms[indices + 1] - time_ms[indices])


def analyse_voltage(raw, profiles, current_pa, timestep_ms, pulse_start, pulse_end, threshold):
    initial = {row['value']: row['first_raw'] / 2 ** row['fractional_bits'] for row in profiles if row['kind'] == 'state'}
    time_ms = np.arange(len(raw) + 1) * timestep_ms
    voltage = np.vstack(([initial[f'n{neuron}.vmem'] for neuron in range(3)], raw[:, [2, 6, 10]] / 2 ** 24))
    pulse_start_ms = pulse_start * timestep_ms
    pulse_end_ms = (pulse_end + 1) * timestep_ms
    pulse_duration_ms = max(0, min(time_ms[-1], pulse_end_ms) - pulse_start_ms)
    metrics, spikes = [], []
    block_edges = np.append(np.arange(0, time_ms[-1], min(10, time_ms[-1])), time_ms[-1])
    activity = []
    for neuron in range(3):
        indices, crossings = upward_crossings(time_ms, voltage[:, neuron], threshold)
        pulse = crossings[(crossings >= pulse_start_ms) & (crossings < pulse_end_ms)]
        intervals = np.diff(pulse)
        peaks = []
        for index, crossing_index in enumerate(indices):
            end = indices[index + 1] + 1 if index + 1 < len(indices) else len(voltage)
            below = np.flatnonzero(voltage[crossing_index + 1:end, neuron] < threshold)
            if len(below):
                end = crossing_index + 2 + int(below[0])
            peak = float(np.max(voltage[crossing_index + 1:end, neuron]))
            peaks.append(peak)
            spikes.append(dict(current_pa=current_pa, neuron=neuron, crossing_number=index + 1, crossing_time_ms=float(crossings[index]), excursion_peak_voltage=peak, during_pulse=bool(pulse_start_ms <= crossings[index] < pulse_end_ms)))
        tail_start = pulse_start_ms + .75 * (pulse_end_ms - pulse_start_ms)
        late_samples = (time_ms >= tail_start) & (time_ms < pulse_end_ms)
        late_spikes = int(np.count_nonzero((crossings >= tail_start) & (crossings < pulse_end_ms)))
        above_fraction = float(np.mean(voltage[late_samples, neuron] >= threshold)) if np.any(late_samples) else None
        behaviour = 'no upward crossings' if not len(crossings) else 'no crossings during pulse' if not len(pulse) else 'single crossing during pulse' if len(pulse) == 1 else 'repeated crossings during pulse'
        metrics.append(dict(current_pa=current_pa, neuron=neuron, crossings_total=len(crossings), crossings_pre_pulse=int(np.count_nonzero(crossings < pulse_start_ms)), crossings_during_pulse=len(pulse), crossings_post_pulse=int(np.count_nonzero(crossings >= pulse_end_ms)), pulse_firing_rate_hz=len(pulse) * 1000 / pulse_duration_ms if pulse_duration_ms else None, first_pulse_crossing_latency_ms=float(pulse[0] - pulse_start_ms) if len(pulse) else None, last_crossing_ms=float(crossings[-1]) if len(crossings) else None, mean_pulse_isi_ms=float(np.mean(intervals)) if len(intervals) else None, pulse_isi_coefficient_of_variation=float(np.std(intervals) / np.mean(intervals)) if len(intervals) > 1 else None, minimum_vmem=float(np.min(voltage[:, neuron])), maximum_vmem=float(np.max(voltage[:, neuron])), mean_excursion_peak=float(np.mean(peaks)) if peaks else None, maximum_excursion_peak=max(peaks) if peaks else None, late_pulse_crossings=late_spikes, late_pulse_fraction_above_threshold=above_fraction, behaviour=behaviour))
        activity.append(np.histogram(crossings, bins=block_edges)[0])
    blocks = np.array_split(np.arange(len(time_ms)), min(4000, len(time_ms)))
    centre_time = np.array([.5 * (time_ms[index[0]] + time_ms[index[-1]]) for index in blocks])
    minimum_display = np.array([np.min(voltage[index], axis=0) for index in blocks])
    maximum_display = np.array([np.max(voltage[index], axis=0) for index in blocks])
    mid_display = np.array([voltage[index[len(index) // 2]] for index in blocks])
    display = dict(time_ms=centre_time, voltage=mid_display, minimum_voltage=minimum_display, maximum_voltage=maximum_display, activity=np.array(activity), activity_time_edges=block_edges)
    return metrics, spikes, display


def aggregate_profiles(rows, headroom):
    groups = {}
    for row in rows:
        if not row['numerically_valid']:
            continue
        name = row['value']
        if name not in groups:
            groups[name] = dict(row, minimum_current_pa=row['current_pa'], maximum_current_pa=row['current_pa'], valid_currents=1)
            continue
        entry = groups[name]
        if row['minimum_raw'] < entry['minimum_raw']:
            for field in ('minimum_raw', 'minimum', 'minimum_time_ms', 'minimum_at_initialisation'):
                entry[field] = row[field]
            entry['minimum_current_pa'] = row['current_pa']
        if row['maximum_raw'] > entry['maximum_raw']:
            for field in ('maximum_raw', 'maximum', 'maximum_time_ms', 'maximum_at_initialisation'):
                entry[field] = row[field]
            entry['maximum_current_pa'] = row['current_pa']
        entry['valid_currents'] += 1
    result = []
    for name in sorted(groups):
        row = groups[name]
        needed = integer_bits(row['minimum_raw'], row['maximum_raw'], row['fractional_bits'])
        result.append(dict(value=name, kind=row['kind'], phase=row['phase'], baseline_width=row['baseline_width'], fractional_bits=row['fractional_bits'], minimum_raw=row['minimum_raw'], maximum_raw=row['maximum_raw'], minimum=row['minimum'], minimum_current_pa=row['minimum_current_pa'], minimum_time_ms=row['minimum_time_ms'], maximum=row['maximum'], maximum_current_pa=row['maximum_current_pa'], maximum_time_ms=row['maximum_time_ms'], integer_bits_observed=needed, integer_bits_with_headroom=needed + headroom, width_to_preserve_fractional_bits=needed + row['fractional_bits'], valid_currents=row['valid_currents']))
    return result
