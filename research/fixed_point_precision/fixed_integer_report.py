from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path

import numpy as np

import precision_support as study


def table(headers,rows):
    escape=lambda value:html.escape(str(value))
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{escape(value)}</th>' for value in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{escape(value)}</td>' for value in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def number(value):
    return '-' if value is None else f'{value:.5g}' if isinstance(value,float) else str(value)


def make_plots(output,manifest,candidates):
    if not candidates:
        return []
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    plots=output/'plots'
    plots.mkdir(exist_ok=True)
    widths=[row['width'] for row in manifest['configurations']]
    currents=manifest['currents']
    lookup={(row['summary']['width'],row['summary']['current_pa']):row for row in candidates}
    errors=np.full((len(widths),len(currents)),np.nan)
    counts=np.full_like(errors,np.nan)
    validity=np.zeros_like(errors)
    for index,width in enumerate(widths):
        for column,current in enumerate(currents):
            case=lookup.get((width,current))
            if case is None:
                continue
            row=case['summary']
            validity[index,column]=4 if row['overflow_count'] and row['zero_constants'] else 2 if row['overflow_count'] else 3 if row['zero_constants'] else 1
            if row['numeric_valid']:
                errors[index,column]=np.log10(max(row['baseline_voltage_rmse'],1e-12))
                counts[index,column]=row['unmatched_reference_crossings']+row['unmatched_candidate_crossings']
    names=[]
    for values,filename,title,label in ((errors,'01_voltage_error.png','Vmem error against original 32-bit C','log10 of worst-neuron voltage RMSE'),(counts,'02_crossing_mismatches.png','Unmatched threshold crossings across three neurons','Unmatched reference + candidate crossings'),(validity,'03_numeric_status.png','Numerical validity at every width and current','Status')):
        figure,axis=plt.subplots(figsize=(15,max(4,len(widths)*.35)),layout='constrained')
        if filename=='03_numeric_status.png':
            image=axis.imshow(values,aspect='auto',interpolation='nearest',cmap=ListedColormap(['#e5e9ee','#498852','#c54435','#e8ab45','#84529c']),norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5,4.5],5))
            colour=figure.colorbar(image,ax=axis,ticks=range(5))
            colour.ax.set_yticklabels(['Pending','No detected overflow / zero constant','Overflow','Zero constant','Both'])
        else:
            colour_map=plt.get_cmap('viridis').copy()
            colour_map.set_bad('#e5e9ee')
            image=axis.imshow(np.ma.masked_invalid(values),aspect='auto',interpolation='nearest',cmap=colour_map)
            figure.colorbar(image,ax=axis,label=label)
        positions=sorted(set(np.linspace(0,len(currents)-1,min(14,len(currents)),dtype=int)))
        axis.set(xticks=positions,xticklabels=[currents[index] for index in positions],yticks=range(len(widths)),yticklabels=widths,xlabel='Tested input current (pA); columns are equally spaced tested points',ylabel='Total candidate width (bits)',title=title+'\nGrey error cells are pending or numerically invalid. Numerical validity does not imply acceptable accuracy.')
        figure.savefig(plots/filename,dpi=160,facecolor='white')
        plt.close(figure)
        names.append(filename)
    selected_currents=[current for current in (80,1000) if current in currents]
    selected_widths=[width for width in dict.fromkeys([32,28,24,20,min(widths)]) if width in widths]
    for current in selected_currents:
        for width in selected_widths:
            case=lookup.get((width,current))
            if case is None:
                continue
            row=case['summary']
            path=output/'runs'/row['configuration']/f'current_{current:04d}'/'voltage_comparison.npz'
            with np.load(path) as display:
                figure,axes=plt.subplots(2,1,figsize=(13,7),sharex=True,layout='constrained')
                time=display['time_ms']
                axes[0].fill_between(time,display['reference_minimum'][:,0],display['reference_maximum'][:,0],color='#1c6594',alpha=.17,linewidth=0)
                axes[0].fill_between(time,display['candidate_minimum'][:,0],display['candidate_maximum'][:,0],color='#cb612d',alpha=.17,linewidth=0)
                axes[0].plot(time,display['reference'][:,0],color='#1c6594',linewidth=1,label='Original 32-bit C reference')
                axes[0].plot(time,display['candidate'][:,0],color='#cb612d',linewidth=.8,label=f'{width}-bit fixed-integer candidate')
                axes[1].fill_between(time,display['error_minimum'][:,0],display['error_maximum'][:,0],color='#a13c54',alpha=.25,linewidth=0)
                axes[1].plot(time,display['error'][:,0],color='#a13c54',linewidth=.8)
                axes[0].set(ylabel='Neuron 0 Vmem (normalised)')
                axes[1].set(ylabel='Candidate minus reference',xlabel='Nominal time (ms)')
                axes[0].legend(fontsize=9)
                for axis in axes:
                    axis.axvspan(60,140.001,color='#bfa874',alpha=.12)
                    axis.grid(alpha=.2)
                figure.suptitle(f'{width} bits at {current} pA | '+('No detected overflow or zero constants' if row['numeric_valid'] else 'NUMERICALLY INVALID: diagnostic trace only')+'\nShading retains display-bin extrema. Metrics use every sample.',fontsize=12)
                filename=f'example_w{width}_current_{current:04d}.png'
                figure.savefig(plots/filename,dpi=160,facecolor='white')
                plt.close(figure)
                names.append(filename)
    return names


def make_report(output,manifest,cases):
    output=Path(output)
    tables=output/'tables'
    tables.mkdir(exist_ok=True)
    references=[case for case in cases if case['summary']['stage']=='reference']
    candidates=[case for case in cases if case['summary']['stage']=='fixed_integer']
    candidates.sort(key=lambda case:(-case['summary']['width'],case['summary']['current_pa']))
    summaries=[case['summary'] for case in candidates]
    study.write_rows(tables/'summary.csv',summaries)
    study.write_rows(tables/'reference_checks.csv',[case['summary'] for case in references])
    for field in ('state_metrics','spike_metrics','spike_matches'):
        study.write_rows(tables/f'{field}.csv',[row for case in candidates for row in case[field]])
    study.write_rows(tables/'operation_ranges.csv',[dict(configuration=case['summary']['configuration'],current_pa=case['summary']['current_pa'],numeric_valid=case['summary']['numeric_valid'],**row) for case in candidates for row in case['ranges']])
    requested=len(manifest['configurations'])*len(manifest['currents'])
    status='complete' if len(candidates)==requested and len(references)==len(manifest['currents']) else 'partial' if cases else 'prepared'
    with (tables/'configuration_catalog.csv').open(newline='') as stream:
        catalog=list(csv.DictReader(stream))
    by_width=[]
    for configuration in manifest['configurations']:
        selected=[row for row in summaries if row['configuration']==configuration['name']]
        valid=[row for row in selected if row['numeric_valid']]
        by_width.append(dict(configuration=configuration['name'],width=configuration['width'],requested_currents=len(manifest['currents']),completed_currents=len(selected),numerically_valid_currents=len(valid),overflow_cases=sum(row['overflow_count']>0 for row in selected),zero_constant_cases=sum(row['zero_constants']>0 for row in selected),worst_valid_voltage_rmse=max((row['baseline_voltage_rmse'] for row in valid),default=None),worst_valid_voltage_absolute_error=max((row['maximum_voltage_absolute_error'] for row in valid),default=None),maximum_valid_unmatched_crossings=max((row['unmatched_reference_crossings']+row['unmatched_candidate_crossings'] for row in valid),default=None)))
    study.write_rows(tables/'summary_by_width.csv',by_width)
    filenames=make_plots(output,manifest,candidates)
    budgets=manifest['budgets']['shared_types']
    group_rows=[[row['baseline_q'],', '.join(group for group,value in study.BASELINE.items() if value[1]==row['baseline_fractional_bits']),row['observed_integer_bits'],row['headroom_bits'],row['allocated_integer_bits'],row['limiting_value'],row['limiting_current_pa']] for row in budgets]
    catalog_rows=[[row['width'],*[row[group+'_q'] for group in study.GROUPS],row['encoded_timestep_ms']] for row in catalog]
    width_rows=[[row['width'],f"{row['completed_currents']}/{row['requested_currents']}",row['numerically_valid_currents'],row['overflow_cases'],row['zero_constant_cases'],number(row['worst_valid_voltage_rmse']),number(row['maximum_valid_unmatched_crossings'])] for row in by_width]
    current_rows=[[row['width'],row['current_pa'],'YES' if row['numeric_valid'] else 'NO',row['overflow_count'],row['zero_constants'],row['lost_updates'],number(row['baseline_voltage_rmse']),row['unmatched_reference_crossings'],row['unmatched_candidate_crossings'],row['first_overflow_signal'] or '-'] for row in summaries]
    pieces=['<!doctype html><html><head><meta charset="utf-8"><title>Fixed-integer C precision study</title><style>body{font:15px system-ui,sans-serif;color:#20374b;background:#f2f5f8;margin:0}main{max-width:1550px;margin:auto;padding:28px}section{padding:22px;background:white;border:1px solid #d4dfe8;border-radius:8px;margin:22px 0}p{line-height:1.6}.scroll{overflow:auto;max-height:650px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:10px;border:1px solid #d4dfe8;text-align:left}th{background:#203b55;color:white;position:sticky;top:0}tr:nth-child(even){background:#f0f5f8}img{max-width:100%;height:auto}a{color:#1c6693}summary{cursor:pointer;font-size:19px;font-weight:650}nav{display:flex;gap:20px;flex-wrap:wrap}.note{background:#fff1dc;padding:14px;border-left:4px solid #c1882c}</style></head><body><main><h1>Fixed integer bits: C precision sweep</h1>',f'<p><strong>Status: {status.upper()}</strong>. {len(candidates)}/{requested} candidate runs and {len(references)}/{len(manifest["currents"])} original-format references completed.</p>',f'<p>Operating range: 0-1,000 pA. {len(manifest["currents"])} currents; {len(manifest["configurations"])} total widths; {manifest["steps"]:,} steps per run. Integer allocations include sign and {manifest["budgets"]["headroom_bits"]} headroom bit(s). Shared types keep fixed integer bits; F = width - I.</p>','<p class="note">Reference = original 32-bit C formats, checked step by step against the original C harness at each current. The reallocated 32-bit configuration is a candidate, not the reference. These are C-model results, not RTL or MATLAB accuracy results. Numerical validity does not establish acceptable accuracy.</p>','<nav><a href="#budgets">Integer budgets</a><a href="#formats">Every configuration</a><a href="#results">Results by width</a><a href="#examples">Voltage and error examples</a><a href="#all">All current results</a></nav>','<section id="budgets"><h2>Fixed integer allocations</h2>',table(['Original shared Q type','C groups','Observed I','Headroom','Allocated I','Limiting value / site','At pA'],group_rows),'<p>Derived from all valid saved profiles within 0-1,000 pA, including exact raw variable extrema and checked pre-truncation operation ranges. Full multiplication products remain signed 64-bit.</p></section>','<section id="formats"><h2>Every tested configuration</h2>',table(['Width',*study.GROUPS,'Encoded DT, ms'],catalog_rows),'<p>Time labels and stimulus timing remain nominal 0.001 ms steps. The encoded Euler timestep varies with precision and can become zero; its value is shown explicitly. Zero-fractional-bit formats are allowed and still tested.</p><p><a href="tables/configuration_catalog.csv">Configuration table, CSV</a> | <a href="tables/tested_combinations.csv">Every width/current combination, CSV</a></p></section>','<section id="results"><h2>Results by width</h2>',table(['Width','Completed','Numeric valid','Overflow cases','Zero-constant cases','Worst valid Vmem RMSE','Worst valid unmatched crossings'],width_rows)]
    for name in filenames[:3]:
        pieces.append(f'<a href="plots/{name}"><img src="plots/{name}"></a>')
    pieces.append('<p>No accuracy pass/fail threshold has been assumed. RMSE measures the entire waveform; crossing counts/times measure upward crossings of 1.4542. Matching uses a 0.5 ms window. Lost Euler updates are reported, not treated as proof of failure on their own. Metrics for invalid runs are diagnostic only.</p></section><section id="examples"><h2>Membrane voltage and separate signed-error plots</h2>')
    if not candidates:
        pieces.append('<p>No simulations have run yet. Comparison plots will appear after simulations complete.</p>')
    for name in filenames[3:]:
        pieces.append(f'<details><summary>{html.escape(name.removesuffix(".png"))}</summary><img loading="lazy" src="plots/{name}"></details>')
    result_links = '<p><a href="tables/summary.csv">All numeric results</a> | <a href="tables/state_metrics.csv">All-state accuracy</a> | <a href="tables/spike_metrics.csv">Crossing counts and timing</a> | <a href="tables/operation_ranges.csv">Operation ranges and overflow checks</a></p>' if summaries else '<p>Result CSV files will appear after simulations complete.</p>'
    pieces.extend(['</section><section id="all"><h2>Every completed width/current result</h2>',table(['Width','Current pA','Numeric valid','Overflow events','Zero constants','Lost updates','Diagnostic Vmem RMSE','Unmatched reference','Unmatched candidate','First overflow site'],current_rows),result_links,'</section></main></body></html>'])
    (output/'report.html').write_text('\n'.join(pieces),encoding='utf-8')
    if candidates:
        from make_similarity_table import generate
        generate(output)
        report_path=output/'report.html'
        report_page=report_path.read_text(encoding='utf-8')
        report_page=report_page.replace('<nav>','<nav><a href="comparison_table.html">Interactive width comparison table</a>',1)
        report_path.write_text(report_page,encoding='utf-8')
    summary=dict(status=status,requested_candidate_runs=requested,completed_candidate_runs=len(candidates),requested_reference_runs=len(manifest['currents']),completed_reference_runs=len(references),numerically_valid_candidate_runs=sum(row['numeric_valid'] for row in summaries),baseline_exact_match=all(case['summary'].get('baseline_exact_match',False) for case in references) if references else None,widths=[row['width'] for row in manifest['configurations']],currents=manifest['currents'],headroom_bits=manifest['budgets']['headroom_bits'],accuracy_acceptance='Not assigned; report trade-offs without claiming an optimum or an acceptable minimum width.',reference='Original 32-bit C only',manifest_fingerprint=manifest['fingerprint'])
    study.save_json(output/'study_summary.json',summary)
    print(f'Open {output/"report.html"} | {status}: {len(candidates)}/{requested} candidate runs',flush=True)
