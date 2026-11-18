from __future__ import annotations

import html
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.colors as colours
import matplotlib.pyplot as plt
import numpy as np

from sweep_analysis import aggregate_profiles


DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parent / 'fixed_point_precision'))
from plotting_support import png_table, number, decorate, save_figure


NEURON_COLOURS = ('#266c98', '#c45d2b', '#63823f')


def exploratory(axis, currents):
    if max(currents) > 150:
        axis.axvspan(max(150, min(currents)), max(currents), color='#fff0dc', alpha=.55, zorder=0)
        axis.axvline(150, color='#a47c49', linestyle=':', linewidth=1)


def make_report(output, cases, manifest, tables):
    cases = sorted(cases, key=lambda value: value['current_pa'])
    behaviour, values, aggregate, crossings, numeric = tables
    currents = [case['current_pa'] for case in cases]
    valid = {case['current_pa']: case['numeric']['numerically_valid'] for case in cases}
    plots = output / 'plots'
    table_images = output / 'tables/images'
    for name in ('behaviour', 'states', 'intermediates', 'waveforms'):
        (plots / name).mkdir(parents=True, exist_ok=True)
    if not aggregate:
        (output / 'report.html').write_text('<h1>No numerically valid complete runs</h1><p>No integer-bit recommendations were made. Inspect tables/numeric_checks.csv and the individual run profiles.</p>', encoding='utf-8')
        return
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    metric_lookup = {(row['current_pa'], row['neuron']): row for row in behaviour}
    value_lookup = {(row['current_pa'], row['value']): row for row in values}
    for metric, title, ylabel, filename in (
        ('crossings_total', 'Upward threshold crossings during the complete experiment', f"Crossings in {manifest['steps'] * .001:g} ms", '01_spike_counts.png'),
        ('pulse_firing_rate_hz', 'Firing rate within the applied-current pulse', 'Pulse-window rate (Hz)', '02_pulse_firing_rate.png'),
        ('maximum_excursion_peak', 'Largest voltage peak following an upward crossing', 'Peak voltage, normalised units', '03_spike_peaks.png'),
        ('first_pulse_crossing_latency_ms', 'Delay from pulse onset to first crossing', 'Latency (ms)', '04_first_spike_latency.png')):
        figure, axis = plt.subplots(figsize=(12, 6), layout='constrained')
        for neuron, colour in enumerate(NEURON_COLOURS):
            series = [metric_lookup[current, neuron][metric] if valid[current] and metric_lookup[current, neuron][metric] is not None else np.nan for current in currents]
            axis.plot(currents, series, color=colour, linewidth=1.4, label=f'Neuron {neuron}')
        exploratory(axis, currents)
        decorate(axis, ylabel)
        axis.set_xlabel('External pulse current applied to neuron 0 (pA)')
        axis.set_title(title + '\n32-bit C model | Shading above 150 pA marks exploratory currents | Invalid runs omitted', fontsize=12)
        axis.legend()
        save_figure(figure, plots / 'behaviour' / filename)

    figure, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True, sharey=True, layout='constrained')
    for neuron, axis in enumerate(axes):
        selected = [row for row in crossings if row['neuron'] == neuron and valid[row['current_pa']]]
        axis.scatter([row['crossing_time_ms'] for row in selected], [row['current_pa'] for row in selected], s=2, color=NEURON_COLOURS[neuron], alpha=.7, rasterized=True)
        axis.axvspan(manifest['pulse_start'] * .001, (manifest['pulse_end'] + 1) * .001, color='#dce7f1', alpha=.45)
        if max(currents) > 150:
            axis.axhline(150, color='#9e733c', linestyle=':', linewidth=1)
        axis.set_ylabel(f'Neuron {neuron}\nInput current (pA)')
        decorate(axis)
    axes[-1].set_xlabel('Time (ms)')
    figure.suptitle('When do the neurons fire as input current changes?\nEach dot is an upward threshold crossing. Blue shading marks the applied pulse; currents above 150 pA are exploratory.', fontsize=13)
    save_figure(figure, plots / 'behaviour/05_crossing_raster.png')

    figure, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True, layout='constrained')
    activity = []
    duration_ms = manifest['steps'] * manifest['timestep_ms']
    time_edges = np.append(np.arange(0, duration_ms, min(10, duration_ms)), duration_ms)
    for case in cases:
        with np.load(output / 'runs' / case['directory_name'] / 'voltage_display.npz') as display:
            activity.append(display['activity'].astype(float) if case['numeric']['numerically_valid'] else np.full((3, len(time_edges) - 1), np.nan))
    activity = np.array(activity)
    current_edges = np.array([currents[0] - .5, currents[0] + .5]) if len(currents) == 1 else np.concatenate(([currents[0] - .5 * (currents[1] - currents[0])], .5 * (np.array(currents[:-1]) + np.array(currents[1:])), [currents[-1] + .5 * (currents[-1] - currents[-2])]))
    for neuron, axis in enumerate(axes):
        image = axis.pcolormesh(time_edges, current_edges, activity[:, neuron, :], shading='flat', cmap='Blues', vmin=0, vmax=max(1, np.nanmax(activity)))
        axis.set_ylabel(f'Neuron {neuron}\nInput current (pA)')
        axis.axvline(manifest['pulse_start'] * .001, color='#c57b31', linewidth=1)
        axis.axvline((manifest['pulse_end'] + 1) * .001, color='#c57b31', linewidth=1)
        if max(currents) > 150:
            axis.axhline(150, color='#c57b31', linestyle=':')
    axes[-1].set_xlabel('Time (ms)')
    figure.colorbar(image, ax=axes, label=f'Upward crossings per {min(10, duration_ms):g} ms interval', shrink=.8)
    figure.suptitle('Activity before, during and after the pulse\nOrange vertical lines mark pulse boundaries. This is a count map, not a membrane-voltage image.', fontsize=13)
    save_figure(figure, plots / 'behaviour/06_activity_map.png')

    state_names = [f'n{neuron}.{field}' for neuron in range(3) for field in ('vmem','vk','vg','vna','te','ti')]
    for field in ('vmem', 'vk', 'vg', 'vna', 'te', 'ti'):
        figure, axis = plt.subplots(figsize=(12, 6), layout='constrained')
        for neuron, colour in enumerate(NEURON_COLOURS):
            name = f'n{neuron}.{field}'
            minimum = [value_lookup[current, name]['minimum'] if valid[current] else np.nan for current in currents]
            maximum = [value_lookup[current, name]['maximum'] if valid[current] else np.nan for current in currents]
            axis.plot(currents, minimum, color=colour, linestyle='--', linewidth=1.1)
            axis.plot(currents, maximum, color=colour, linewidth=1.3, label=f'Neuron {neuron}')
        exploratory(axis, currents)
        decorate(axis, 'Observed value, normalised state units')
        axis.set_xlabel('External pulse current (pA)')
        axis.set_title(f'{field}: actual minimum and maximum values\nDashed = minimum; solid = maximum. Includes initial state and all recorded post-update values.', fontsize=12)
        axis.legend()
        save_figure(figure, plots / 'states' / f'range_{field}.png')
    state_bits = np.array([[value_lookup[current, name]['integer_bits_observed'] if valid[current] else np.nan for current in currents] for name in state_names])
    maximum_bits = int(np.nanmax(state_bits))
    figure, axis = plt.subplots(figsize=(14, 8), layout='constrained')
    colourmap = plt.get_cmap('YlGnBu', maximum_bits)
    image = axis.imshow(state_bits, aspect='auto', interpolation='nearest', cmap=colourmap, norm=colours.BoundaryNorm(np.arange(.5, maximum_bits + 1.5), maximum_bits))
    tick_indices = np.unique(np.linspace(0, len(currents) - 1, min(16, len(currents))).astype(int))
    axis.set(yticks=np.arange(len(state_names)), yticklabels=state_names, xticks=tick_indices, xticklabels=[f'{currents[index]:g}' for index in tick_indices], xlabel='External pulse current (pA)', title='Integer bits needed by each stored state at each current\nIncludes the sign bit. Headroom is not included in this plot; invalid runs are omitted.')
    figure.colorbar(image, ax=axis, ticks=np.arange(1, maximum_bits + 1), label='Observed integer bits including sign')
    save_figure(figure, plots / 'states/required_integer_bits.png')

    for group, names, ylabel, filename in (
        ('Total neuron input current', [f'n{neuron}.total_current' for neuron in range(3)], 'Total input current (pA)', '01_total_current.png'),
        ('Neuron voltage derivatives', [f'n0.derivative_{state}' for state in ('vmem', 'vk', 'vg', 'vna')], 'Normalised state change per ms', '02_neuron0_derivatives.png')):
        figure, axis = plt.subplots(figsize=(12, 6), layout='constrained')
        for name in names:
            axis.plot(currents, [value_lookup[current, name]['maximum'] if valid[current] else np.nan for current in currents], label=name)
            axis.plot(currents, [value_lookup[current, name]['minimum'] if valid[current] else np.nan for current in currents], linestyle='--', linewidth=.9)
        exploratory(axis, currents)
        decorate(axis, ylabel)
        axis.set(xlabel='External pulse current (pA)', title=group + '\nSolid = maximum; dashed = minimum. These ranges are separate from stored-state ranges.')
        axis.legend(fontsize=9)
        save_figure(figure, plots / 'intermediates' / filename)

    selected_cases = []
    valid_cases = [case for case in cases if case['numeric']['numerically_valid']]
    for target in (0, 20, 40, 80, 150, 200, max(currents)):
        if valid_cases:
            case = min(valid_cases, key=lambda case: abs(case['current_pa'] - target))
            if case not in selected_cases:
                selected_cases.append(case)
    figure, axes = plt.subplots(math.ceil(len(selected_cases) / 2), 2, figsize=(15, 3 * math.ceil(len(selected_cases) / 2)), sharex=True, sharey=True, layout='constrained', squeeze=False)
    for axis, case in zip(axes.flat, selected_cases):
        with np.load(output / 'runs' / case['directory_name'] / 'voltage_display.npz') as display:
            axis.fill_between(display['time_ms'], display['minimum_voltage'][:, 0], display['maximum_voltage'][:, 0], color='#266c98', alpha=.28, linewidth=0)
            axis.plot(display['time_ms'], display['voltage'][:, 0], color='#266c98', linewidth=.8)
        axis.axvspan(manifest['pulse_start'] * .001, (manifest['pulse_end'] + 1) * .001, color='#e9dcc2', alpha=.3)
        count = case['behaviour'][0]['crossings_total']
        axis.set_title(f"{case['current_pa']:g} pA | {count} total upward crossings")
        axis.set(xlabel='Time (ms)', ylabel='Neuron 0 membrane voltage')
        decorate(axis)
    for axis in list(axes.flat)[len(selected_cases):]:
        axis.axis('off')
    figure.suptitle('Example waveforms across the input-current range\nThe thin line is a display subset; the blue band retains each display bin\'s full minimum/maximum. Metrics use every sample.', fontsize=12)
    save_figure(figure, plots / 'waveforms/01_neuron0_examples.png')
    for case in selected_cases:
        figure, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True, layout='constrained')
        with np.load(output / 'runs' / case['directory_name'] / 'voltage_display.npz') as display:
            for neuron, axis in enumerate(axes):
                axis.fill_between(display['time_ms'], display['minimum_voltage'][:, neuron], display['maximum_voltage'][:, neuron], color=NEURON_COLOURS[neuron], alpha=.28, linewidth=0)
                axis.plot(display['time_ms'], display['voltage'][:, neuron], color=NEURON_COLOURS[neuron], linewidth=.8)
                axis.axvspan(manifest['pulse_start'] * .001, (manifest['pulse_end'] + 1) * .001, color='#e9dcc2', alpha=.3)
                decorate(axis, f'Neuron {neuron}\nMembrane voltage')
        axes[-1].set_xlabel('Time (ms)')
        figure.suptitle(f"{case['current_pa']:g} pA: three-neuron voltage response\nNormalised units. Display-bin envelope preserves extrema; this is not a MATLAB comparison.", fontsize=13)
        save_figure(figure, plots / 'waveforms' / f"{case['directory_name']}.png")

    lower, upper = manifest['intended_range_pa']
    operating_aggregate = aggregate_profiles([row for row in values if lower <= row['current_pa'] <= upper], manifest['headroom_bits'])
    operating_states = [row for row in operating_aggregate if row['kind'] == 'state']
    for filename, data in (('state_integer_bits_operating_range.csv', operating_states), ('all_value_ranges_operating_range.csv', operating_aggregate)):
        if data:
            with (output / 'tables' / filename).open('w', newline='', encoding='utf-8') as destination:
                writer = csv.DictWriter(destination, fieldnames=list(data[0]))
                writer.writeheader()
                writer.writerows(data)
    for state_rows, filename, title in (([row for row in aggregate if row['kind'] == 'state'], '01_state_integer_bits.png', f'Stored states: all tested currents ({min(currents):g} to {max(currents):g} pA)'), (operating_states, '02_state_integer_bits_operating_range.png', f'Stored states: intended range only ({lower:g} to {upper:g} pA)')):
        if not state_rows:
            continue
        state_rows = sorted(state_rows, key=lambda row: state_names.index(row['value']))
        rows = []
        for row in state_rows:
            integer = row['integer_bits_with_headroom']
            rows.append([row['value'], number(row['minimum'], 6), number(row['minimum_current_pa']), number(row['maximum'], 6), number(row['maximum_current_pa']), str(row['integer_bits_observed']), str(integer), *[str(width - integer) if width >= integer else 'No fit' for width in (28,24,20,16)]])
        png_table(table_images / filename, title, f"Integer counts include sign; the suggested allowance adds {manifest['headroom_bits']} headroom bit(s). Only numerically valid currents in the stated scope contribute.", ['State', 'Minimum', 'At pA', 'Maximum', 'At pA', 'Observed\ninteger bits', 'With\nheadroom', 'F at\n28 bits', 'F at\n24 bits', 'F at\n20 bits', 'F at\n16 bits'], rows, 'Initial values and all simulation samples are included. F = total width minus suggested integer bits.\nFractional budgets are proposals, not validated reduced-width models. Intermediates and constants require their own formats.', widths=[.15] + [.085] * 10, row_colours=[NEURON_COLOURS[int(row['value'][1])] for row in state_rows])

    behaviour_pages = []
    for offset in range(0, len(cases), 25):
        selected = cases[offset:offset + 25]
        rows, cell_colours = [], {}
        for index, case in enumerate(selected):
            rows.append([number(case['current_pa']), ', '.join(str(row['crossings_total']) for row in case['behaviour']), ', '.join(str(row['crossings_during_pulse']) for row in case['behaviour']), ', '.join(number(row['pulse_firing_rate_hz']) for row in case['behaviour']), ', '.join(number(row['maximum_excursion_peak']) for row in case['behaviour']), str(case['numeric']['overflow_count']), 'YES' if case['numeric']['numerically_valid'] else 'NO'])
            if not case['numeric']['numerically_valid']:
                for column in range(7):
                    cell_colours[index, column] = '#fce0dc'
        filename = f'behaviour_{offset // 25 + 1:02d}.png'
        behaviour_pages.append(filename)
        png_table(table_images / filename, f"Behaviour: {selected[0]['current_pa']:g} to {selected[-1]['current_pa']:g} pA", 'Triplets are neurons 0, 1 and 2. The external current is applied only to neuron 0.', ['Input pA', 'Crossings\nfull run', 'Crossings\nduring pulse', 'Pulse rate Hz\nN0, N1, N2', 'Largest excursion peak\nN0, N1, N2', 'Overflow\nevents', 'Numeric\nvalid'], rows, 'A spike is counted as an upward crossing of 1.4542. One sustained above-threshold excursion can count once.\nRate uses crossings within the applied pulse, not the whole experiment. Peak values are normalised voltage, not pA.\nRed rows are invalid/incomplete and excluded from recommended integer budgets; no biological or mathematical accuracy claim is made.', widths=[.08,.15,.15,.2,.24,.09,.09])

    variable_pages = []
    kind_groups = defaultdict(list)
    for row in aggregate:
        kind_groups[row['kind']].append(row)
    for kind, group in sorted(kind_groups.items()):
        for offset in range(0, len(group), 24):
            selected = group[offset:offset + 24]
            rows = [[row['value'], number(row['minimum'], 6), number(row['minimum_current_pa']), number(row['maximum'], 6), number(row['maximum_current_pa']), str(row['fractional_bits']), str(row['integer_bits_observed']), str(row['integer_bits_with_headroom']), str(row['width_to_preserve_fractional_bits'])] for row in selected]
            filename = f'variables_{kind}_{offset // 24 + 1:02d}.png'
            variable_pages.append(filename)
            png_table(table_images / filename, f'Individual numerical values: {kind.replace("_", " ")}', 'Ranges combine numerically valid currents only. The current producing each extreme is shown separately.', ['Value', 'Minimum', 'At pA', 'Maximum', 'At pA', 'Existing\nfraction bits', 'Observed\ninteger bits', 'With\nheadroom', 'Min W keeping\nexisting F'], rows, 'Raw integer extrema are retained exactly in CSV. Display values are rounded; integer budgets are computed from exact raw integers.\nMin W keeping existing F = observed integer bits + existing fractional bits, without added headroom.\nRaw products retain 64-bit arithmetic; their binary-point position differs by operand format. No narrower arithmetic is implemented here.', widths=[.35,.115,.055,.115,.055,.07,.07,.08,.09], figure_width=18)

    if selected_cases:
        highlights = [f"<li>{case['current_pa']:g} pA: total crossings {', '.join(str(row['crossings_total']) for row in case['behaviour'])}; maximum neuron-0 voltage {case['behaviour'][0]['maximum_vmem']:.6g}.</li>" for case in selected_cases]
    else:
        highlights = ['<li>No numerically valid runs were available.</li>']
    content = ['<!doctype html><html><head><meta charset="utf-8"><title>Input-current sweep</title><style>body{font:16px system-ui,sans-serif;color:#20344a;max-width:1500px;margin:35px auto;padding:0 24px;background:#f5f7fa}section,details{background:white;border:1px solid #d8e0e8;border-radius:10px;padding:20px;margin:20px 0}img{width:100%;height:auto}summary{font-size:20px;font-weight:600;cursor:pointer}p,li{line-height:1.6}a{color:#2166ac}.note{background:#fff1dc;border-left:5px solid #bd762b;padding:14px}</style></head><body>', '<h1>Input current: behaviour and integer range</h1>', f'<p>{len(cases)} completed currents out of {len(manifest["current_raw_q8"])} requested. Every case uses the existing 32-bit fixed-point C arithmetic.</p>', '<p class="note">These are measured ranges for this network, pulse and simulation duration. They are not universal bounds or MATLAB/RTL accuracy results. Above 150 pA is exploratory. Every completed valid trace was compared against the original C model.</p>', '<section><h2>Start here</h2><ul>', *highlights, '</ul><p>Compare spike counts, timing and peak voltage. Then inspect integer requirements separately for states and intermediate values.</p></section>']
    for filename in ('01_spike_counts.png','02_pulse_firing_rate.png','03_spike_peaks.png','04_first_spike_latency.png','05_crossing_raster.png','06_activity_map.png'):
        content.append(f'<section><a href="plots/behaviour/{filename}"><img src="plots/behaviour/{filename}" loading="lazy"></a></section>')
    content.append('<section><h2>Integer bits for each stored state</h2><p>The intended range is separated from the wider exploratory sweep so a design decision for 0–150 pA need not use extrema found only above 150 pA.</p><a href="tables/images/01_state_integer_bits.png"><img src="tables/images/01_state_integer_bits.png"></a>')
    if operating_states:
        content.append('<a href="tables/images/02_state_integer_bits_operating_range.png"><img src="tables/images/02_state_integer_bits_operating_range.png"></a>')
    content.append('<img src="plots/states/required_integer_bits.png"></section>')
    content.append('<details><summary>All six state types: minimum and maximum versus current</summary>')
    for field in ('vmem','vk','vg','vna','te','ti'):
        content.append(f'<img loading="lazy" src="plots/states/range_{field}.png">')
    content.append('</details><section><h2>Example membrane voltages</h2><img src="plots/waveforms/01_neuron0_examples.png"></section><details><summary>Individual waveform examples for all three neurons</summary>')
    for case in selected_cases:
        content.append(f'<img loading="lazy" src="plots/waveforms/{case["directory_name"]}.png">')
    content.append('</details><details><summary>Currents and derivative ranges</summary><img src="plots/intermediates/01_total_current.png"><img src="plots/intermediates/02_neuron0_derivatives.png"></details>')
    content.append('<details><summary>All current levels: readable behaviour tables</summary>')
    for filename in behaviour_pages:
        content.append(f'<a href="tables/images/{filename}"><img loading="lazy" src="tables/images/{filename}"></a>')
    content.append('</details><details><summary>Every profiled numerical variable: readable range tables</summary>')
    for filename in variable_pages:
        content.append(f'<a href="tables/images/{filename}"><img loading="lazy" src="tables/images/{filename}"></a>')
    content.append('</details><section><h2>Data and definitions</h2><ul>')
    for filename in ('behaviour_by_current.csv','state_integer_bits.csv','state_integer_bits_operating_range.csv','all_value_ranges.csv','all_value_ranges_operating_range.csv','all_values_by_current.csv','numeric_checks.csv','upward_crossings.csv','transitions.csv'):
        if (output/'tables'/filename).exists():
            content.append(f'<li><a href="tables/{filename}">{filename}</a></li>')
    content.append('</ul><p>Integer bits include sign. Stored states include initial values. Intermediate ranges are profiled at their actual evaluation sites; they are not inferred from final state voltages. Constants are the original encoded 32-bit values. Raw products are measured before fractional rescaling. Diagnostic loops and flags are not proposed neuron datapath values.</p><p>Pulse counts and rates use the stated pulse interval; a threshold crossing alone does not establish a complete physiological spike or depolarisation block. Numerical failures are flagged and excluded from recommendations. Headroom is a selected policy, not a proof.</p></section></body></html>')
    (output / 'report.html').write_text('\n'.join(content), encoding='utf-8')
    (output / 'README.md').write_text('# Input-current sweep results\n\n[Open the illustrated report](report.html).\n\n- [State integer-bit table](tables/images/01_state_integer_bits.png)\n- [Spike counts versus current](plots/behaviour/01_spike_counts.png)\n- [Example waveforms](plots/waveforms/01_neuron0_examples.png)\n- [Every variable range, CSV](tables/all_value_ranges.csv)\n- [All behaviour tables and range tables, PNG](tables/images/)\n\nAll 32-bit results describe the measured network and pulse. They do not certify universal integer limits or mathematical accuracy. Inputs above 150 pA are exploratory.\n', encoding='utf-8')
