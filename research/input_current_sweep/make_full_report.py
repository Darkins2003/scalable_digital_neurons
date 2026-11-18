from __future__ import annotations

import csv
import html
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np

import run_current_sweep as sweep
from sweep_analysis import aggregate_profiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fixed_point_precision'))
from plotting_support import png_table, number, decorate, save_figure


KIND_LABELS = {
    'state': 'Neuron states', 'derivative': 'State derivatives', 'euler_update': 'Euler increments',
    'scaled_triangle': 'Scaled / coupled triangles', 'exponential_output': 'Exponential outputs',
    'exponent_argument': 'Exponential arguments', 'current_vector': 'Current vector',
    'synapse_calculation': 'Synapse calculations', 'total_current': 'Total neuron current',
    'matrix_product_rescaled': 'Rescaled matrix products', 'matrix_partial_sum': 'Matrix partial sums',
    'constant': 'Constants / matrix coefficients', 'external_current': 'External input', 'raw_product': 'Full 64-bit products',
}
COLOURS = ('#216c99', '#bd512d', '#548437', '#84549e', '#ac7b13', '#267b76', '#d05c87')


def escape(value):
    return html.escape(str(value))


def current_axis(axis, maximum=1_000_000):
    axis.set_xscale('log')
    axis.set_xlim(1, maximum)
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, position: f'{value/1_000_000:g}M' if value >= 1_000_000 else f'{value/1000:g}k' if value >= 1000 else f'{value:g}'))
    axis.set_xlabel('Input current (pA), logarithmic spacing')
    decorate(axis)


def format_groups(case):
    groups = defaultdict(list)
    for row in case['values']:
        groups[row['kind'], row['baseline_width'], row['fractional_bits']].append(row)
    return groups


def collect_overflows(cases, timestep):
    primary, flagged = [], []
    for case in cases:
        numeric = case['numeric']
        if not numeric['overflow_count']:
            continue
        with (case['_source_directory'] / 'runs' / case['directory_name'] / 'calculation_sites.csv').open(newline='') as stream:
            for row in csv.DictReader(stream):
                if not int(row['overflow_count']):
                    continue
                is_primary = (int(row['neuron']), row['signal'], row['group']) == (numeric['first_overflow_neuron'], numeric['first_overflow_signal'], numeric['first_overflow_group'])
                record = dict(current_pa=case['current_pa'], neuron=int(row['neuron']), signal=row['signal'], format_group=row['group'], width=int(row['width']), fractional_bits=int(row['fractional']), available_integer_bits=int(row['width']) - int(row['fractional']), first_flagged_step=int(row['first_overflow_step']), first_flagged_time_ms=(int(row['first_overflow_step']) + 1) * timestep, overflow_events=int(row['overflow_count']), primary_trigger=is_primary)
                flagged.append(record)
                if is_primary:
                    primary.append(record)
    return primary, flagged


def make_bit_data(cases):
    rows, maxima = [], {}
    for case in cases:
        if not case['numeric']['numerically_valid']:
            continue
        for key, values in format_groups(case).items():
            limiting = max(values, key=lambda row: row['integer_bits_observed'])
            required = limiting['integer_bits_observed']
            rows.append(dict(current_pa=case['current_pa'], variable_type=key[0], width=key[1], fractional_bits=key[2], available_integer_bits=key[1] - key[2], required_integer_bits=required, spare_integer_bits=key[1] - key[2] - required, limiting_variable=limiting['value'], variables_in_group=len(values)))
            if key not in maxima or required > maxima[key]['required_integer_bits']:
                maxima[key] = rows[-1]
    return rows, maxima


def table_html(headers, rows, identifier=''):
    return f'<div class="table-scroll"><table id="{identifier}"><thead><tr>' + ''.join(f'<th>{escape(value)}</th>' for value in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{escape(value)}</td>' for value in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def plot_bits(output, cases, bit_rows):
    lookup = {(row['current_pa'], row['variable_type'], row['width'], row['fractional_bits']): row for row in bit_rows}
    groups = sorted({(row['variable_type'], row['width'], row['fractional_bits']) for row in bit_rows})
    currents = [case['current_pa'] for case in cases]
    failed = [case['current_pa'] for case in cases if not case['numeric']['numerically_valid']]
    filenames = []
    for offset in range(0, len(KIND_LABELS), 4):
        kinds = list(KIND_LABELS)[offset:offset + 4]
        figure, axes = plt.subplots(len(kinds), 2, figsize=(16, 3.5 * len(kinds)), layout='constrained', squeeze=False)
        for axes_row, kind in zip(axes, kinds):
            for colour_index, key in enumerate(key for key in groups if key[0] == kind):
                series = [lookup.get((current,) + key, {}).get('required_integer_bits', np.nan) for current in currents]
                for axis in axes_row:
                    axis.plot(currents, series, '.-', markersize=2, linewidth=1, color=COLOURS[colour_index % len(COLOURS)], label=f'{key[1]} bits, F={key[2]}: observed I')
                    axis.axhline(key[1] - key[2], linestyle='--', color=COLOURS[colour_index % len(COLOURS)], linewidth=.8, label=f'Existing I={key[1] - key[2]}')
            axes_row[0].set(xlim=(1,300), xlabel='Input current (pA), linear spacing')
            decorate(axes_row[0])
            current_axis(axes_row[1])
            for axis in axes_row:
                axis.set_title(KIND_LABELS[kind], fontsize=11)
                axis.set_ylabel('Integer bits, including sign')
                axis.yaxis.set_major_locator(MaxNLocator(integer=True))
                axis.legend(fontsize=6.5, ncol=2, loc='upper left')
            if failed:
                axes_row[1].scatter(failed, [.015] * len(failed), marker='x', s=8, color='#b7352d', transform=axes_row[1].get_xaxis_transform(), clip_on=False)
        figure.suptitle('Bits needed by each variable type: detailed low-current view and full sweep\nSolid: largest observed requirement among members of that format. Dashed: existing capacity. Red marks: invalid runs, excluded.', fontsize=12)
        name = f'bits_by_type_{offset // 4 + 1:02d}.png'
        save_figure(figure, output / 'plots' / name)
        filenames.append(name)
    return filenames


def plot_states(output, cases):
    currents = [case['current_pa'] for case in cases]
    maps = [{row['value']: row for row in case['values']} for case in cases]
    for measurement, filename, title, ylabel in (
        ('integer_bits_observed', 'state_integer_bits.png', 'Integer bits needed by every neuron state', 'Integer bits, including sign'),
        ('maximum', 'state_ranges.png', 'How each neuron state changes with input current', 'Normalised state value'),
    ):
        figure, axes = plt.subplots(3, 2, figsize=(15, 12), layout='constrained')
        for axis, field in zip(axes.flat, ('vmem', 'vk', 'vg', 'vna', 'te', 'ti')):
            for neuron, colour in enumerate(COLOURS[:3]):
                series = [values[f'n{neuron}.{field}'][measurement] if case['numeric']['numerically_valid'] else np.nan for case, values in zip(cases, maps)]
                axis.plot(currents, series, color=colour, label=f'Neuron {neuron}' + (' max' if measurement == 'maximum' else ''), linewidth=1)
                if measurement == 'maximum':
                    minimum = [values[f'n{neuron}.{field}']['minimum'] if case['numeric']['numerically_valid'] else np.nan for case, values in zip(cases, maps)]
                    axis.plot(currents, minimum, color=colour, linestyle='--', linewidth=.8, label=f'Neuron {neuron} min')
            current_axis(axis, maximum=10_000)
            axis.set_title(field)
            axis.set_ylabel(ylabel)
            if measurement == 'integer_bits_observed':
                axis.yaxis.set_major_locator(MaxNLocator(integer=True))
            axis.legend(fontsize=7, ncol=3)
        figure.suptitle(title + '\nValid full runs only, starting at 1 pA. All stored samples and initial values contribute.', fontsize=13)
        save_figure(figure, output / 'plots' / filename)


def plot_overflow(output, cases, primary, flagged, timestep):
    figure, axes = plt.subplots(2, 1, figsize=(15, 10), layout='constrained')
    labels = sorted({f"{row['signal']} / {row['format_group']}" for row in primary})
    for index, label in enumerate(labels):
        selected = [row for row in primary if f"{row['signal']} / {row['format_group']}" == label]
        colour = COLOURS[index % len(COLOURS)]
        axes[0].scatter([row['current_pa'] for row in selected], [index] * len(selected), color=colour, marker='x', s=24)
        axes[1].scatter([row['current_pa'] for row in selected], [row['first_flagged_time_ms'] - 60 for row in selected], color=colour, s=20, label=label)
    valid_currents = [case['current_pa'] for case in cases if case['numeric']['numerically_valid']]
    axes[0].scatter(valid_currents, [-1] * len(valid_currents), color='#3b8444', s=12)
    axes[0].set(yticks=range(-1, len(labels)), yticklabels=['Valid complete run'] + labels, title='First calculation to overflow at each tested input')
    axes[1].set(ylabel='Time from pulse onset to first flagged step (ms)', title='How quickly arithmetic fails after the pulse begins')
    axes[1].legend(fontsize=8, ncol=2)
    for axis in axes:
        current_axis(axis)
    figure.suptitle('Overflow across the entire sweep from 1 pA\nPrimary triggers only. Later flags in the same step may be consequences. Sampled failures are not a monotonic limit.', fontsize=12)
    save_figure(figure, output / 'plots/overflow_map.png')
    summary = []
    for key in sorted({(row['signal'], row['format_group'], row['neuron']) for row in flagged}):
        affected = [row for row in flagged if (row['signal'], row['format_group'], row['neuron']) == key]
        triggers = [row for row in affected if row['primary_trigger']]
        first = min(affected, key=lambda row: row['current_pa'])
        summary.append(dict(signal=key[0], format_group=key[1], neuron=key[2], lowest_tested_flagged_current_pa=first['current_pa'], lowest_tested_primary_current_pa=min((row['current_pa'] for row in triggers), default=None), currents_flagged=len(affected), primary_trigger_currents=len(triggers), available_integer_bits=first['available_integer_bits']))
    return summary


def make_waveforms(output, cases):
    data = output / 'data'
    data.mkdir(exist_ok=True)
    catalog = []
    for case in cases:
        valid = bool(case['numeric']['numerically_valid'])
        identifier = f"current_{case['current_raw_q8']}"
        with np.load(case['_source_directory'] / 'runs' / case['directory_name'] / 'voltage_display.npz') as display:
            kept = slice(None) if valid else slice(None, -1)
            arrays = {name: np.round(display[name][kept], 7).tolist() for name in ('time_ms', 'voltage', 'minimum_voltage', 'maximum_voltage')}
        (data / f'{identifier}.js').write_text('window.waveformCache[' + json.dumps(identifier) + ']=' + json.dumps(arrays, separators=(',', ':')) + ';', encoding='utf-8')
        catalog.append(dict(id=identifier, current=case['current_pa'], valid=valid, stop=case['numeric']['completed_steps'] * .001, signal=case['numeric']['first_overflow_signal'], counts=[row['crossings_total'] for row in case['behaviour']] if valid else None))
    targets = ([1,5,10,15,20,30,40,60,80,100,150,200], [250,300,325,500,750,1000,1500,2500,4000,6000,7500,8500], [7750,8000,8250,8750,10000,12500,25000,100000,250000,500000,750000,1000000])
    filenames = []
    for page, group in enumerate(targets, 1):
        selected = []
        for target in group:
            case = min(cases, key=lambda case: abs(case['current_pa'] - target))
            if case not in selected:
                selected.append(case)
        figure, axes = plt.subplots(math.ceil(len(selected) / 3), 3, figsize=(16, 3 * math.ceil(len(selected) / 3)), layout='constrained', squeeze=False)
        for axis, case in zip(axes.flat, selected):
            valid = case['numeric']['numerically_valid']
            with np.load(case['_source_directory'] / 'runs' / case['directory_name'] / 'voltage_display.npz') as display:
                kept = slice(None) if valid else slice(None, -1)
                axis.fill_between(display['time_ms'][kept], display['minimum_voltage'][kept, 0], display['maximum_voltage'][kept, 0], color=COLOURS[0], alpha=.22, linewidth=0)
                axis.plot(display['time_ms'][kept], display['voltage'][kept, 0], linewidth=.8, color=COLOURS[0])
            axis.axhline(1.4542, color='#999999', linewidth=.7, linestyle=':')
            axis.axvspan(60, 140.001, alpha=.1, color='#bc9d63')
            if not valid:
                axis.axvspan(case['numeric']['completed_steps'] * .001, 190, color='#c34737', alpha=.13)
                axis.text(.98, .94, f"STOP: {case['numeric']['first_overflow_signal']}", transform=axis.transAxes, ha='right', va='top', color='#9b2e23', fontsize=8)
            axis.set(xlim=(0,190), ylim=(-4,13) if page < 3 else None, title=f"{case['current_pa']:g} pA | {'complete' if valid else 'incomplete'}", xlabel='Time (ms)', ylabel='Neuron 0 Vmem')
            decorate(axis)
        for axis in list(axes.flat)[len(selected):]:
            axis.axis('off')
        figure.suptitle('Vmem across current levels' + (' | common voltage scale for direct comparison' if page < 3 else ' | red regions were not simulated') + '\nBlue shading retains display-bin minima and maxima; dotted line is the counting threshold.', fontsize=12)
        filename = f'vmem_examples_{page:02d}.png'
        save_figure(figure, output / 'plots' / filename)
        filenames.append(filename)
    return catalog, filenames


def create_report(output, reference_manifest, original_cases, extended_cases, band_summaries):
    all_cases = sorted(original_cases + extended_cases, key=lambda case: case['current_raw_q8'])
    if len({case['current_raw_q8'] for case in all_cases}) != len(all_cases):
        raise ValueError('Overlapping current checkpoints')
    cases = [case for case in all_cases if case['current_pa'] >= 1]
    valid = [case for case in cases if case['numeric']['numerically_valid']]
    failed = [case for case in cases if not case['numeric']['numerically_valid']]
    plots, tables = output / 'plots', output / 'tables'
    plots.mkdir(exist_ok=True)
    (tables / 'images').mkdir(parents=True, exist_ok=True)
    print(f'Building report for {len(cases)} currents from 1 pA; {len(failed)} invalid cases...', flush=True)
    timestep = reference_manifest['timestep_ms']
    primary, flagged = collect_overflows(cases, timestep)
    bit_rows, maxima = make_bit_data(cases)
    aggregate = aggregate_profiles([row for case in cases for row in case['values']], reference_manifest['headroom_bits'])
    state_rows = [row for row in aggregate if row['kind'] == 'state']
    sweep.baseline.write_rows(tables / 'all_value_ranges_extended.csv', aggregate)
    sweep.baseline.write_rows(tables / 'state_integer_bits_extended.csv', state_rows)
    sweep.baseline.write_rows(tables / 'integer_bits_by_type_and_current.csv', bit_rows)
    sweep.baseline.write_rows(tables / 'all_values_by_current.csv', [row for case in cases for row in case['values']])
    if flagged:
        sweep.baseline.write_rows(tables / 'overflow_sites_by_current.csv', flagged)
        sweep.baseline.write_rows(tables / 'primary_overflows.csv', primary)
    numeric_rows = []
    for case in cases:
        numeric = case['numeric']
        numeric_rows.append(dict(current_pa=case['current_pa'], numerically_valid=numeric['numerically_valid'], completed_time_ms=numeric['completed_steps'] * timestep, completed_steps=numeric['completed_steps'], full_trace_matches_original_c=numeric['identical_to_original_c'], crossings_n0=case['behaviour'][0]['crossings_total'] if numeric['numerically_valid'] else None, crossings_n1=case['behaviour'][1]['crossings_total'] if numeric['numerically_valid'] else None, crossings_n2=case['behaviour'][2]['crossings_total'] if numeric['numerically_valid'] else None, overflow_count=numeric['overflow_count'], first_overflow_signal=numeric['first_overflow_signal'], first_overflow_group=numeric['first_overflow_group'], first_overflow_neuron=numeric['first_overflow_neuron'], first_overflow_step=numeric['first_overflow_step']))
    sweep.baseline.write_rows(tables / 'extended_current_summary.csv', numeric_rows)
    if failed:
        sweep.baseline.write_rows(tables / 'numerical_failures.csv', [row for row in numeric_rows if not row['numerically_valid']])
    print('Plotting every variable type and the overflow sites...', flush=True)
    bit_figures = plot_bits(output, cases, bit_rows)
    plot_states(output, cases)
    overflow_summary = plot_overflow(output, cases, primary, flagged, timestep)
    if overflow_summary:
        sweep.baseline.write_rows(tables / 'overflow_onset_by_site.csv', overflow_summary)
    figure, axes = plt.subplots(1,2,figsize=(16,5),layout='constrained')
    for neuron, colour in enumerate(COLOURS[:3]):
        counts = [case['behaviour'][neuron]['crossings_total'] if case['numeric']['numerically_valid'] else np.nan for case in cases]
        for axis in axes:
            axis.plot([case['current_pa'] for case in cases], counts, color=colour, label=f'Neuron {neuron}', linewidth=1)
    axes[0].set(xlim=(1,300),xlabel='Input current (pA)')
    decorate(axes[0])
    current_axis(axes[1])
    for axis in axes:
        axis.set_ylabel('Upward threshold crossings in 190 ms')
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))
        axis.legend()
    figure.suptitle('All tested currents starting at 1 pA | invalid cases omitted\nA sustained above-threshold response can count once even if small ripples remain.',fontsize=12)
    save_figure(figure,plots/'crossings_from_1pa.png')
    print('Preparing selectable Vmem traces and waveform comparison sheets...', flush=True)
    catalog, waveform_figures = make_waveforms(output, cases)
    state_table = [[row['value'], number(row['minimum'],6), number(row['maximum'],6), f"{row['maximum_current_pa']:g}", row['integer_bits_observed'], row['integer_bits_with_headroom']] for row in state_rows]
    png_table(tables/'images/states_from_1pa.png', 'Neuron-state integer ranges from 1 pA upward', 'All initial values and samples, using valid complete runs only.', ['State','Minimum','Maximum','Max at pA','Integer bits\nincluding sign','With one\nheadroom bit'], state_table, 'Observed requirements are not a proof for every possible stimulus. Fractional-bit choices still need accuracy testing.',widths=[.2,.17,.17,.15,.16,.15])
    group_table = [[KIND_LABELS[key[0]],f'{key[1]} / {key[2]}',row['available_integer_bits'],row['required_integer_bits'],row['spare_integer_bits'],f"{row['current_pa']:g}"] for key,row in sorted(maxima.items())]
    group_headers = ['Variable type','Width / F','Available I','Peak needed I','Spare I','Peak at pA']
    for offset in range(0,len(group_table),20):
        png_table(tables/f'images/type_budgets_{offset//20+1:02d}.png','Integer-bit budgets by variable type','Separate rows preserve different binary-point positions within the same type.',group_headers,group_table[offset:offset+20],'I includes sign. Values use valid full runs only. Wide products use 64-bit capacity. Peak current is the first sampled current attaining that bit count.',widths=[.33,.14,.13,.14,.12,.14])
    current_table = [[f"{case['current_pa']:g}", 'YES' if case['numeric']['numerically_valid'] else 'NO', ', '.join(str(row['crossings_total']) for row in case['behaviour']) if case['numeric']['numerically_valid'] else 'Incomplete', f"{case['numeric']['completed_steps']*timestep:.3f}",case['numeric']['first_overflow_signal'] or '-',case['numeric']['first_overflow_group'] or '-'] for case in cases]
    current_headers = ['Input pA','Valid','Crossings N0, N1, N2','Completed ms','First overflow site','Format group']
    print('Writing PNG tables for every tested current, including 1-300 pA...', flush=True)
    for offset in range(0,len(current_table),24):
        page_rows = current_table[offset:offset+24]
        shades = {(row,column):'#fce0dc' for row,values in enumerate(page_rows) if values[1]=='NO' for column in range(6)}
        png_table(tables/f'images/all_currents_{offset//24+1:02d}.png',f'All results: {page_rows[0][0]} to {page_rows[-1][0]} pA','Every tested positive current appears in order. Red rows encountered arithmetic overflow.',current_headers,page_rows,'Only complete valid runs have crossing counts. Current spacing increases beyond 300 pA; untested currents are not interpolated measurements.',widths=[.12,.08,.25,.15,.25,.15],cell_colours=shades)
    overflow_table = [[row['signal'],row['format_group'],row['neuron'],f"{row['lowest_tested_flagged_current_pa']:g}", '-' if row['lowest_tested_primary_current_pa'] is None else f"{row['lowest_tested_primary_current_pa']:g}",row['available_integer_bits']] for row in overflow_summary]
    overflow_headers = ['Calculation site','Format group','Neuron','First flag at pA','First primary at pA','Available I']
    for offset in range(0,len(overflow_table),20):
        png_table(tables/f'images/overflow_onset_{offset//20+1:02d}.png','When each calculation starts to overflow','Lowest tested current, not an exact universal current limit.',overflow_headers,overflow_table[offset:offset+20],'Primary = first overflow in execution order. Other sites can be affected later in that same step.\nThe saved checks identify a calculation site and neuron, not always an individual stored-state index.',widths=[.28,.15,.09,.17,.18,.13])
    first_failure = min((case['current_pa'] for case in failed),default=None)
    document = PAGE_START.replace('CATALOG_DATA',json.dumps(catalog,separators=(',',':')))
    document += f'<p class="lead">{len(cases)} tested currents from 1 to {max(case["current_pa"] for case in cases):,.0f} pA. {len(valid)} valid complete runs and {len(failed)} numerical stops. First sampled overflow: {first_failure:g} pA.</p>' if first_failure is not None else f'<p>{len(cases)} tested positive currents; no detected overflow.</p>'
    document += '<p>Sampling: 1-300 pA in 1 pA steps; 325-1,000 in 25 pA steps; 1,250-10,000 in 250 pA steps; 12,500-100,000 in 2,500 pA steps; 125,000-1,000,000 in 25,000 pA steps. The saved 0 pA control is retained in the original study.</p>'
    document += WAVEFORM_SECTION
    document += '<section id="examples"><h2>Vmem comparison sheets</h2><p>Start with the low-current page, then inspect the high-current page. The first two sheets share the same voltage scale. Every tested current is also available in the selectors above.</p>'
    document += ''.join(f'<details><summary>{label}</summary><a href="plots/{filename}"><img loading="lazy" src="plots/{filename}"></a></details>' for filename,label in zip(waveform_figures,('1-200 pA','250-8,500 pA','Overflow examples')))
    document += '</section><section id="bits"><h2>Integer bits by variable type</h2><p>Integer bits <strong>include the sign bit</strong>. A type uses the maximum requirement among its members. Separate curves show different fractional positions F. Dashed lines show existing capacity I = width - F. Failed runs are gaps, never valid range measurements.</p>'
    document += ''.join(f'<a href="plots/{name}"><img loading="lazy" src="plots/{name}"></a>' for name in bit_figures)
    document += table_html(group_headers,group_table) + '<p><a href="tables/integer_bits_by_type_and_current.csv">Every type at every valid current, CSV</a> | <a href="tables/all_values_by_current.csv">Every individual variable at every current, CSV</a> (invalid profiles are labelled and may include the affected final step).</p></section>'
    document += '<section id="states"><h2>Individual neuron states</h2><img loading="lazy" src="plots/state_integer_bits.png"><img loading="lazy" src="plots/state_ranges.png"><img loading="lazy" src="tables/images/states_from_1pa.png"></section>'
    document += '<section id="overflow"><h2>When and where overflow begins</h2><p>Green dots are complete runs. Other rows identify the <strong>first triggering calculation</strong> at each failed current. The model stops at the end of that step. Additional sites can overflow as a consequence, so their flags are listed separately below. Failure is not monotonic with current; for example 8,500 pA completes although 7,750-8,250 pA fail.</p><img loading="lazy" src="plots/overflow_map.png">'
    document += table_html(overflow_headers,overflow_table) + '<p>Site labels such as <code>update / state</code> identify a calculation and neuron. Existing diagnostics do not always retain the specific state index. No exact per-state overflow threshold is inferred from these labels.</p><p><a href="tables/primary_overflows.csv">First triggering site for every failed current</a> | <a href="tables/overflow_sites_by_current.csv">All flags through each stopping step</a> | <a href="tables/overflow_onset_by_site.csv">First sampled failure by site</a></p></section>'
    document += '<section id="all"><h2>All tested currents, starting at 1 pA</h2><img loading="lazy" src="plots/crossings_from_1pa.png"><label>Find a current or status <input id="result-filter" placeholder="e.g. 80, 1000, incomplete" oninput="filterResults(this.value)"></label>' + table_html(current_headers,current_table,'current-results')
    document += '<p><a href="tables/extended_current_summary.csv">Complete current summary, CSV</a> | <a href="tables/all_value_ranges_extended.csv">Aggregate ranges of every variable</a></p><details><summary>PNG tables for every tested current</summary>'
    document += ''.join(f'<a href="tables/images/all_currents_{page:02d}.png"><img loading="lazy" src="tables/images/all_currents_{page:02d}.png"></a>' for page in range(1,math.ceil(len(current_table)/24)+1))
    document += '</details><details><summary>PNG tables of integer budgets and overflow onset</summary>'
    document += ''.join(f'<img loading="lazy" src="tables/images/{prefix}_{page:02d}.png">' for prefix,length in (('type_budgets',len(group_table)),('overflow_onset',len(overflow_table))) for page in range(1,math.ceil(length/20)+1))
    document += '</details></section><footer>Same 32-bit three-neuron C model, 190 ms, pulse 60-140.001 ms on neuron 0. All valid runs match the original C trace. This report does not establish accuracy against a floating-point, MATLAB or hardware reference. Observed integer requirements are not universal bounds.</footer></main>' + PAGE_SCRIPT + '</body></html>'
    (output/'report.html').write_text(document,encoding='utf-8')
    from make_sv_bit_report import generate
    generate(output)
    summary = dict(status='complete' if len(extended_cases)==136 else 'partial',additional_currents=len(extended_cases),reused_original_currents=len(original_cases),combined_currents=len(all_cases),reported_positive_currents=len(cases),report_starts_at_pa=1,largest_tested_current_pa=max(case['current_pa'] for case in cases),valid_complete_currents=sum(case['numeric']['numerically_valid'] for case in all_cases),invalid_currents=len(failed),additional_valid_currents=sum(case['numeric']['numerically_valid'] for case in extended_cases),additional_overflow_currents=sum(bool(case['numeric']['overflow_count']) for case in extended_cases),largest_tested_valid_current_pa=max(case['current_pa'] for case in valid),lowest_tested_overflow_current_pa=first_failure,bands=band_summaries,limitation='Observed requirements from valid complete runs. Overflow onset is sampled and nonmonotonic. Site checks do not always identify a stored-state index.')
    sweep.baseline.save_json(output/'study_summary.json',summary)
    print(f'Report ready: {output / "report.html"}',flush=True)
    return summary


PAGE_START = '''<!doctype html><html><head><meta charset="utf-8"><title>Input-current sweep from 1 pA</title><style>
*{box-sizing:border-box}body{margin:0;background:#f2f5f7;color:#213547;font:15px system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:34px}h2{font-size:25px}p{line-height:1.65}.lead{font-size:20px}nav{position:sticky;top:0;z-index:3;display:flex;gap:18px;flex-wrap:wrap;padding:14px;background:#203b55}nav a{color:white}a{color:#17638d}section{padding:24px;margin:24px 0;background:white;border:1px solid #dae2e8;border-radius:8px;scroll-margin-top:70px}img{width:100%;height:auto}details{margin:18px 0}summary{cursor:pointer;font-size:18px;font-weight:650;padding:10px}.controls{display:flex;gap:18px;flex-wrap:wrap;align-items:center;padding:14px;background:#edf3f7}select,input,button{font:inherit;padding:7px;border:1px solid #bac8d2;border-radius:4px}button{cursor:pointer}.wave-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:18px}.wave-card{border:1px solid #d3dde5;padding:12px}.wave-card select{width:100%}canvas{width:100%;height:320px;display:block}.status{font-size:13px;min-height:40px;line-height:1.5}.bad{color:#a32921}.table-scroll{overflow:auto;max-height:650px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:13px}th{background:#203b55;color:white;position:sticky;top:0}th,td{padding:10px;border:1px solid #d8e1e8;text-align:left}tbody tr:nth-child(odd){background:#eff4f7}footer{line-height:1.7;padding:20px}.hint{border-left:4px solid #bd7f30;padding:10px 18px;background:#fff5e6}@media(max-width:800px){.wave-grid{grid-template-columns:1fr}main{padding:12px}section{padding:14px}} </style></head><body><nav><a href="#vmem">Compare Vmem</a><a href="#examples">Example sheets</a><a href="#bits">Bits by type</a><a href="sv_integer_bits.html">SV names + Q + bits</a><a href="#states">States</a><a href="#overflow">Overflow onset</a><a href="#all">All results</a></nav><main><h1>Input current: every tested value from 1 pA</h1><script>const waveformCatalog=CATALOG_DATA;window.waveformCache={};</script>'''


WAVEFORM_SECTION = '''<section id="vmem"><h2>Compare Vmem at any tested current</h2><p>Choose four currents below. Use the previous/next buttons to move through <strong>every tested value</strong>. The common voltage scale lets you compare heights directly. Zoom into the pulse onset to see the first response.</p><div class="controls"><label>Neuron <select id="neuron" onchange="redrawAll()"><option value="0">0 (external input)</option><option value="1">1</option><option value="2">2</option></select></label><label>Time window <select id="time-window" onchange="redrawAll()"><option value="0,190">Full run: 0-190 ms</option><option value="55,145">Pulse: 55-145 ms</option><option value="59.9,61">Pulse onset: 59.9-61 ms</option><option value="60,60.1">First 0.1 ms of pulse</option><option value="135,155">Pulse end: 135-155 ms</option></select></label><label><input type="checkbox" id="shared-scale" checked onchange="redrawAll()"> Common voltage scale</label><label><input type="checkbox" id="envelope" checked onchange="redrawAll()"> Show min/max envelope</label><button onclick="preset([1,20,80,150])">Low currents</button><button onclick="preset([300,1000,7500,8500])">High valid currents</button><button onclick="preset([7500,7750,8000,8500])">Overflow boundary</button></div><div class="wave-grid" id="wave-grid"></div><p class="hint">Voltage is in the model's normalised units. The dotted line is the 1.4542 crossing threshold. Orange shading marks the pulse. Red shading marks the uncomputed period after overflow. Display data retain bin extrema but are not full-resolution samples; the final display bin of a failed run is omitted to avoid showing contaminated values.</p></section>'''


PAGE_SCRIPT = '''<script>
const pendingLoads={};
function loadWaveform(item){if(window.waveformCache[item.id])return Promise.resolve();if(pendingLoads[item.id])return pendingLoads[item.id];pendingLoads[item.id]=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='data/'+item.id+'.js';script.onload=resolve;script.onerror=()=>reject(new Error('Cannot load '+item.current+' pA'));document.head.appendChild(script)});return pendingLoads[item.id]}
const grid=document.getElementById('wave-grid');
for(let index=0;index<4;index++){const card=document.createElement('div');card.className='wave-card';card.innerHTML='<select id="current-'+index+'" onchange="redrawAll()">'+waveformCatalog.map((item,position)=>'<option value="'+position+'">'+item.current.toLocaleString()+' pA'+(item.valid?'':' | OVERFLOW')+'</option>').join('')+'</select><div style="display:flex;justify-content:space-between;margin:8px 0"><button onclick="stepCurrent('+index+',-1)">Previous tested current</button><button onclick="stepCurrent('+index+',1)">Next tested current</button></div><canvas id="canvas-'+index+'"></canvas><div class="status" id="status-'+index+'"></div>';grid.appendChild(card)}
function stepCurrent(index,step){const selector=document.getElementById('current-'+index);selector.value=Math.max(0,Math.min(waveformCatalog.length-1,Number(selector.value)+step));redrawAll()}
function preset(currents){currents.forEach((current,index)=>{let closest=0;waveformCatalog.forEach((item,position)=>{if(Math.abs(item.current-current)<Math.abs(waveformCatalog[closest].current-current))closest=position});document.getElementById('current-'+index).value=closest});redrawAll()}
let redrawVersion=0;
async function redrawAll(){const version=++redrawVersion;const items=Array.from({length:4},(_,index)=>waveformCatalog[Number(document.getElementById('current-'+index).value)]);try{await Promise.all(items.map(loadWaveform));if(version!==redrawVersion)return;const neuron=Number(document.getElementById('neuron').value);const limits=document.getElementById('time-window').value.split(',').map(Number);let common=[Infinity,-Infinity];items.forEach(item=>{const data=window.waveformCache[item.id];data.time_ms.forEach((time,position)=>{if(time>=limits[0]&&time<=limits[1]){common[0]=Math.min(common[0],data.minimum_voltage[position][neuron]);common[1]=Math.max(common[1],data.maximum_voltage[position][neuron])}})});items.forEach((item,index)=>drawWaveform(index,item,neuron,limits,document.getElementById('shared-scale').checked?common:null))}catch(error){document.querySelectorAll('.status').forEach(status=>status.textContent=error.message)}}
function drawWaveform(index,item,neuron,limits,shared){const canvas=document.getElementById('canvas-'+index),context=canvas.getContext('2d'),ratio=window.devicePixelRatio||1,width=canvas.clientWidth,height=320;canvas.width=width*ratio;canvas.height=height*ratio;context.scale(ratio,ratio);context.clearRect(0,0,width,height);const data=window.waveformCache[item.id],positions=[];data.time_ms.forEach((time,position)=>{if(time>=limits[0]&&time<=limits[1])positions.push(position)});let lower=shared?shared[0]:Math.min(...positions.map(position=>data.minimum_voltage[position][neuron])),upper=shared?shared[1]:Math.max(...positions.map(position=>data.maximum_voltage[position][neuron]));if(!Number.isFinite(lower)||!Number.isFinite(upper)){lower=-3;upper=3}const padding=Math.max(.2,(upper-lower)*.12);lower-=padding;upper+=padding;const left=57,top=18,right=width-16,bottom=height-45;const x=time=>left+(time-limits[0])/(limits[1]-limits[0])*(right-left),y=voltage=>bottom-(voltage-lower)/(upper-lower)*(bottom-top);context.save();context.beginPath();context.rect(left,top,right-left,bottom-top);context.clip();context.fillStyle='#f7f1e5';context.fillRect(x(60),top,x(140.001)-x(60),bottom-top);if(!item.valid){context.fillStyle='#fae2df';context.fillRect(x(item.stop),top,x(190)-x(item.stop),bottom-top)}context.strokeStyle='#dce4eb';context.lineWidth=.6;for(let tick=0;tick<=4;tick++){const py=top+(bottom-top)*tick/4;context.beginPath();context.moveTo(left,py);context.lineTo(right,py);context.stroke()}context.setLineDash([3,4]);context.strokeStyle='#999';context.beginPath();context.moveTo(left,y(1.4542));context.lineTo(right,y(1.4542));context.stroke();context.setLineDash([]);if(document.getElementById('envelope').checked&&positions.length){context.fillStyle='rgba(33,108,153,.22)';context.beginPath();positions.forEach((position,number)=>{const px=x(data.time_ms[position]),py=y(data.maximum_voltage[position][neuron]);number?context.lineTo(px,py):context.moveTo(px,py)});positions.slice().reverse().forEach(position=>context.lineTo(x(data.time_ms[position]),y(data.minimum_voltage[position][neuron])));context.closePath();context.fill()}context.beginPath();context.strokeStyle='#216c99';context.lineWidth=1.3;positions.forEach((position,number)=>{const px=x(data.time_ms[position]),py=y(data.voltage[position][neuron]);number?context.lineTo(px,py):context.moveTo(px,py)});context.stroke();context.restore();context.strokeStyle='#60778a';context.strokeRect(left,top,right-left,bottom-top);context.fillStyle='#435767';context.font='11px system-ui';for(let tick=0;tick<=4;tick++){context.textAlign='right';const value=upper-(upper-lower)*tick/4;context.fillText(value.toFixed(2),left-7,top+(bottom-top)*tick/4+4);context.textAlign='center';const time=limits[0]+(limits[1]-limits[0])*tick/4;context.fillText(time.toFixed(limits[1]-limits[0]<2?3:0),left+(right-left)*tick/4,bottom+18)}context.fillText('Time (ms)',(left+right)/2,height-5);context.save();context.translate(13,(top+bottom)/2);context.rotate(-Math.PI/2);context.fillText('Vmem (normalised)',0,0);context.restore();const status=document.getElementById('status-'+index);status.className='status'+(item.valid?'':' bad');status.textContent=item.valid?'Complete 190 ms; crossings N0/N1/N2: '+item.counts.join(' / '):'INCOMPLETE: first overflow at '+item.stop.toFixed(3)+' ms in '+item.signal+'. Final display bin omitted.';if(!positions.length){context.textAlign='center';context.fillText('No safe saved samples in this time window',(left+right)/2,(top+bottom)/2)}}
function filterResults(query){query=query.toLowerCase().trim();document.querySelectorAll('#current-results tbody tr').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(query))}
window.addEventListener('resize',redrawAll);preset([1,20,80,150]);
</script>'''
