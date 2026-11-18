from __future__ import annotations



import argparse

import csv

import hashlib

import json

from pathlib import Path



import numpy as np

from scipy.signal import correlate, correlation_lags, find_peaks





DIRECTORY=Path(__file__).resolve().parent

PEAK_HEIGHT=1.4542

PEAK_PROMINENCE=1.0

PEAK_SEPARATION_MS=1.0

MAXIMUM_LAG_MS=10.0





def normalised_correlation(reference,candidate,timestep_ms,maximum_lag_ms=MAXIMUM_LAG_MS):

    reference=np.asarray(reference,dtype=float)

    candidate=np.asarray(candidate,dtype=float)

    if reference.ndim!=1 or reference.shape!=candidate.shape or len(reference)<3 or timestep_ms<=0:

        raise ValueError('Correlation requires equal-length one-dimensional sampled signals')

    count=len(reference)

    lags=correlation_lags(count,count)

    selected=(np.abs(lags)*timestep_ms<=maximum_lag_ms)&(count-np.abs(lags)>=.9*count)

    raw=correlate(reference,candidate,method='fft')[selected]

    lags=lags[selected]

    reference_start=np.maximum(lags,0)

    reference_end=count+np.minimum(lags,0)

    candidate_start=np.maximum(-lags,0)

    candidate_end=count-np.maximum(lags,0)

    overlap=reference_end-reference_start

    reference_sum=np.concatenate(([0.],np.cumsum(reference)))

    candidate_sum=np.concatenate(([0.],np.cumsum(candidate)))

    reference_squares=np.concatenate(([0.],np.cumsum(reference*reference)))

    candidate_squares=np.concatenate(([0.],np.cumsum(candidate*candidate)))

    first=reference_sum[reference_end]-reference_sum[reference_start]

    second=candidate_sum[candidate_end]-candidate_sum[candidate_start]

    first_energy=np.maximum(reference_squares[reference_end]-reference_squares[reference_start]-first*first/overlap,0)

    second_energy=np.maximum(candidate_squares[candidate_end]-candidate_squares[candidate_start]-second*second/overlap,0)

    covariance=raw-first*second/overlap

    denominator=np.sqrt(first_energy*second_energy)

    valid=(first_energy>overlap*1e-12)&(second_energy>overlap*1e-12)

    scores=np.full(len(lags),np.nan)

    scores[valid]=np.clip(covariance[valid]/denominator[valid],-1,1)

    return lags*timestep_ms,scores





def peak_counts(voltage,timestep_ms):

    distance=max(1,int(np.ceil(PEAK_SEPARATION_MS/timestep_ms)))

    counts=[len(find_peaks(voltage[:,neuron],height=PEAK_HEIGHT,prominence=PEAK_PROMINENCE,distance=distance)[0]) for neuron in range(3)]

    return counts





def sampled_waveforms(display_path):

    with np.load(display_path) as display:

        time=display['time_ms']

        candidate=display['candidate']

        reference=display['reference']

    timestep=float((time[-1]-time[0])/(len(time)-1))

    uniform=np.linspace(time[0],time[-1],len(time))

    candidate=np.column_stack([np.interp(uniform,time,candidate[:,neuron]) for neuron in range(3)])

    reference=np.column_stack([np.interp(uniform,time,reference[:,neuron]) for neuron in range(3)])

    return uniform,candidate,reference,timestep





def calculate_case(display_path):

    uniform,candidate,reference,timestep=sampled_waveforms(display_path)

    keep=(uniform>=60)&(uniform<=190)

    score_rows=[]

    for neuron in range(3):

        lags,scores=normalised_correlation(reference[keep,neuron],candidate[keep,neuron],timestep)

        score_rows.append([None if not np.isfinite(value) else round(float(value),8) for value in scores])

    return dict(timestep_ms=timestep,lags_ms=np.round(lags,8).tolist(),correlation_by_neuron=score_rows,candidate_peaks=peak_counts(candidate,timestep),reference_peaks=peak_counts(reference,timestep))





def export_waveform_files(output,display_path,candidate_key,reference_key,digest,previous_exports,exports):

    folder=output/'comparison_waveforms'

    folder.mkdir(exist_ok=True)

    candidate_path=folder/f'{candidate_key}.js'

    reference_path=folder/f'{reference_key}.js'

    candidate_ready=candidate_path.is_file() and previous_exports.get(candidate_key)==digest

    reference_ready=reference_path.is_file() and (reference_key in exports or reference_key in previous_exports)

    if candidate_ready and reference_ready:

        exports[candidate_key]=digest

        exports[reference_key]=previous_exports.get(reference_key,digest)

        return

    time,candidate,reference,timestep=sampled_waveforms(display_path)

    distance=max(1,int(np.ceil(PEAK_SEPARATION_MS/timestep)))

    def save(path,key,values,include_time):

        peaks=[find_peaks(values[:,neuron],height=PEAK_HEIGHT,prominence=PEAK_PROMINENCE,distance=distance)[0].tolist() for neuron in range(3)]

        payload=dict(voltage=np.round(values,8).tolist(),peak_indices=peaks)

        if include_time:payload['time_ms']=np.round(time,8).tolist()

        path.write_text('window.comparisonWaveforms['+json.dumps(key)+']='+json.dumps(payload,separators=(',',':'),allow_nan=False)+';',encoding='utf-8')

    if not candidate_ready:save(candidate_path,candidate_key,candidate,False)

    if not reference_ready:save(reference_path,reference_key,reference,True)

    exports[candidate_key]=digest

    exports[reference_key]=previous_exports.get(reference_key,digest)





def best_alignment(lags,scores,limit=5):

    eligible=[index for index,(lag,score) in enumerate(zip(lags,scores)) if score is not None and abs(lag)<=limit]

    if not eligible:

        return None,None

    index=min(eligible,key=lambda index:(-scores[index],abs(lags[index]),lags[index]))

    return scores[index],lags[index]





def generate(output):

    output=Path(output)

    manifest=json.loads((output/'manifest.json').read_text())

    currents=manifest['currents']

    widths=[row['width'] for row in manifest['configurations']]
    configurations=[dict(row,source_output=output,source_fingerprint=manifest['fingerprint'],sweeps=['all']) for row in manifest['configurations']]
    sweeps={'all':dict(label='All types together',widths=widths)}
    type_manifest_paths=[output/'signal_type_sweep/manifest.json',output/'individual_signal_type_sweep/manifest.json']
    for type_manifest_path in type_manifest_paths:
        if not type_manifest_path.is_file():
            continue
        from signal_type_sweep import SIGNAL_TYPES, TYPE_LABELS
        type_manifest=json.loads(type_manifest_path.read_text())
        if type_manifest['parent_fingerprint']!=manifest['fingerprint']:
            raise ValueError('Signal-type results belong to a different parent study')
        available_types={row['signal_type'] for row in type_manifest['configurations'] if row['signal_type']!='baseline'}
        selected_types={name:groups for name,groups in SIGNAL_TYPES.items() if name in available_types and name not in sweeps}
        for name,groups in selected_types.items():
            minimum=max(manifest['budgets']['group_integer_bits'][group] for group in groups)
            sweeps[name]=dict(label=TYPE_LABELS[name],widths=list(range(32,minimum-1,-1)))
        for row in type_manifest['configurations']:
            selected=list(selected_types) if row['signal_type']=='baseline' else [row['signal_type']]
            if not selected or any(name not in selected_types for name in selected):
                continue
            configurations.append(dict(row,source_output=type_manifest_path.parent,source_fingerprint=type_manifest['fingerprint'],sweeps=selected))

    rows=[]

    references={}

    cache=output/'similarity_cache'

    cache.mkdir(exist_ok=True)

    export_manifest=output/'comparison_waveforms/manifest.json'

    previous_exports=json.loads(export_manifest.read_text()) if export_manifest.is_file() else {}

    exports={}

    method=dict(version=1,analysis_window_ms=[60,190],peak_window='Entire saved run, excluding incomplete endpoint peaks',peak_height=PEAK_HEIGHT,peak_prominence=PEAK_PROMINENCE,peak_separation_ms=PEAK_SEPARATION_MS,maximum_lag_ms=MAXIMUM_LAG_MS,normalisation='Pearson correlation with mean and energy recalculated on the overlapping samples at each lag; at least 90 percent overlap',lag_sign='Positive shifts the candidate later; negative shifts it earlier',sampling='Derived from the retained 2000-point display samples, not the original full traces')

    csv_rows=[]

    for configuration in configurations:

        for current in currents:

            if configuration['sweeps']!=['all'] and current!=80:
                continue

            directory=configuration['source_output']/'runs'/configuration['name']/f'current_{current:04d}'

            checkpoint=directory/'completed.json'

            display=directory/'voltage_comparison.npz'

            if not checkpoint.is_file():

                continue

            saved=json.loads(checkpoint.read_text())

            if saved['fingerprint']!=configuration['source_fingerprint']:

                raise ValueError('Candidate checkpoint fingerprint differs from manifest')

            digest=hashlib.sha256(display.read_bytes()).hexdigest()

            if digest!=saved['display_sha256']:

                raise ValueError(f'Waveform checksum mismatch: {display}')

            key=hashlib.sha256(json.dumps(dict(method=method,display_sha256=digest),sort_keys=True).encode()).hexdigest()

            cache_file=cache/f'{configuration["name"]}_{current:04d}.json'

            if cache_file.is_file():

                cached=json.loads(cache_file.read_text())

            else:

                cached={}

            if cached.get('fingerprint')!=key:

                cached=dict(fingerprint=key,metrics=calculate_case(display))

                temporary=cache_file.with_suffix('.tmp')

                temporary.write_text(json.dumps(cached,allow_nan=False,separators=(',',':')))

                temporary.replace(cache_file)

            metrics=cached['metrics']

            if current in references and references[current]['peaks']!=metrics['reference_peaks']:

                raise ValueError('Reference peak counts disagree between candidates')

            reference_key=f'reference_{current:04d}'

            candidate_key=f'w{configuration["width"]}_current_{current:04d}' if configuration['sweeps']==['all'] else f'{configuration["name"]}_current_{current:04d}'

            export_waveform_files(output,display,candidate_key,reference_key,digest,previous_exports,exports)

            references[current]=dict(peaks=metrics['reference_peaks'],timestep_ms=metrics['timestep_ms'],waveform_key=reference_key)

            summary=saved['summary']

            faults=[]

            if summary['overflow_count']:faults.append('Overflow')

            if summary['zero_constants']:faults.append('Zeroed constants')

            record=dict(configuration=configuration['name'],sweeps=configuration['sweeps'],formats=configuration['formats'],width=configuration['width'],current=current,valid=summary['numeric_valid'],faults=' + '.join(faults) or 'None',waveform_key=candidate_key,reference_key=reference_key,**metrics)

            rows.append(record)

            for neuron in range(3):

                score,lag=best_alignment(metrics['lags_ms'],metrics['correlation_by_neuron'][neuron])

                csv_rows.append(dict(configuration=configuration['name'],signal_type=' / '.join(configuration['sweeps']),width=record['width'],current_pa=current,neuron=neuron,numeric_valid=record['valid'],candidate_total_peaks=sum(metrics['candidate_peaks']),reference_total_peaks=sum(metrics['reference_peaks']),candidate_neuron_peaks=metrics['candidate_peaks'][neuron],reference_neuron_peaks=metrics['reference_peaks'][neuron],maximum_normalised_correlation=score if record['valid'] else None,best_candidate_shift_ms=lag if record['valid'] else None,search_limit_ms=5,sample_spacing_ms=metrics['timestep_ms'],source_resolution='Saved display samples; approximate full-trace measurement'))

    if csv_rows:

        with (output/'tables/similarity_by_current.csv').open('w',newline='') as stream:

            writer=csv.DictWriter(stream,fieldnames=list(csv_rows[0]))

            writer.writeheader()

            writer.writerows(csv_rows)

    payload=dict(currents=currents,widths=widths,sweeps=sweeps,rows=rows,references=references,method=method)

    if exports:export_manifest.write_text(json.dumps(exports,indent=2)+'\n')

    controls=(DIRECTORY/'similarity_plot_controls.js').read_text(encoding='utf-8')
    (output/'similarity_plot_controls.js').write_text(controls,encoding='utf-8')
    page=PAGE.replace('RESULT_DATA',json.dumps(payload,separators=(',',':'),allow_nan=False)).replace('PLOT_CODE','</script><script src="similarity_plot_controls.js"></script><script>')

    (output/'comparison_table.html').write_text(page,encoding='utf-8')

    (output/'similarity_method.json').write_text(json.dumps(method,indent=2)+'\n')

    print(f'Created {output/"comparison_table.html"}: {len(rows)} saved width/current cases.',flush=True)





PAGE='''<!doctype html><html><head><meta charset="utf-8"><title>Compare C precision widths</title><style>

*{box-sizing:border-box}body{margin:0;background:#f2f5f8;color:#21394b;font:15px system-ui,sans-serif}main{max-width:1800px;margin:auto;padding:28px}h1{font-size:30px}p{line-height:1.6}.controls{display:flex;gap:22px;align-items:center;flex-wrap:wrap;background:white;border:1px solid #d3dfe8;padding:18px;border-radius:8px}input,select{font:inherit;padding:7px}input[type=number]{width:100px}input[type=range]{width:300px;padding:0}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #d6e1e8;padding:13px;text-align:left}th{background:#203b55;color:white}.reference{background:#e4eef5;font-weight:650}.invalid{background:#fbe8e3;color:#92382c}tbody tr:nth-child(even):not(.invalid):not(.reference){background:#f1f5f8}.warning{border-left:4px solid #bf842b;background:#fff2df;padding:14px}.scroll{overflow:auto;margin:20px 0}a{color:#176991}.hint{font-size:13px;color:#506b7d}details{background:white;padding:16px;border:1px solid #d6e1e8;margin-top:20px}summary{cursor:pointer;font-weight:650}#notice{font-weight:600;color:#815a17}#current-label{font-size:21px}.comparison-layout{display:grid;grid-template-columns:minmax(610px,1.1fr) minmax(440px,1fr);gap:20px;align-items:start}.plot-panel{background:white;padding:16px;border:1px solid #d6e1e8;border-radius:8px;position:sticky;top:16px;margin-top:20px;min-width:0}.plot-panel h2{font-size:19px;margin:0 0 8px}.plot-panel h3{font-size:14px;margin:15px 0 2px}.plot-panel canvas{width:100%;height:210px;display:block}.plot-panel #correlation-plot{height:185px}.plot-panel .legend{font-size:12px}.reference-colour{color:#176b9a}.candidate-colour{color:#d0642f}tr[data-width]{cursor:pointer}tr[data-width]:hover{outline:2px solid #b2cadb;outline-offset:-2px}tr.selected-width{outline:3px solid #246e9b;outline-offset:-3px}#plot-status{min-height:36px}.plot-panel select{font-size:12px;padding:4px}@media(max-width:1180px){.comparison-layout{grid-template-columns:1fr}.plot-panel{position:static}}code{font-size:13px}</style></head><body><main>

<h1>Compare every width at one input current</h1><p><a href="report.html">Back to the full precision report</a>  |  <a href="tables/similarity_by_current.csv">Download the similarity table</a></p>

<p class="warning"><strong>Sampled-waveform estimates.</strong> The full candidate traces were removed after the simulation. These new measurements use the retained 2,000-point display traces (approximately 0.095 ms between samples for a 190 ms run). They are not full-resolution correlation or peak measurements. Existing RMSE and crossing metrics in the main report used every simulation sample.</p>

<div class="controls"><label>Sweep<br><select id="sweep-type" onchange="selectSweep(this.value)"></select></label><label>Input current<br><input type="range" id="current-slider" min="0" value="0" step="1" oninput="selectIndex(Number(this.value))"></label><label>Type current (pA)<br><input type="number" id="current-number" min="0" max="1000" onchange="typeCurrent(this.value)"></label><label>Bit width<br><input type="range" id="width-slider" min="18" max="32" value="32" step="1" oninput="selectWidth(Number(this.value))"></label><label>Type width (bits)<br><input type="number" id="width-number" min="18" max="32" value="32" onchange="selectWidth(Number(this.value))"></label><label>Correlation for<br><select id="neuron" onchange="render()"><option value="0">Neuron 0</option><option value="1">Neuron 1</option><option value="2">Neuron 2</option></select></label><label>Search shifts up to<br><select id="lag-limit" onchange="render()"><option value="1">+/-1 ms</option><option value="2">+/-2 ms</option><option value="5" selected>+/-5 ms</option><option value="10">+/-10 ms</option></select></label></div>

<p id="sweep-description" class="hint"></p><p id="current-label"></p><p id="notice" aria-live="polite"></p><p class="hint">Peak counts total all three neurons. Correlation and shift refer to the selected neuron. Every recorded width appears below. Use the bit-width slider or click a row to update the plots.</p>

<div class="comparison-layout"><div class="scroll"><table><thead><tr><th>Width</th><th>Total candidate peaks<br>All neurons</th><th>Total reference peaks<br>All neurons</th><th>Maximum normalised<br>cross-correlation</th><th>Best shift applied<br>to candidate (ms)</th><th>Arithmetic faults</th></tr></thead><tbody id="results"></tbody></table></div><aside class="plot-panel"><h2 id="plot-heading">Selected waveform</h2><p id="plot-status" class="hint" aria-live="polite"></p><p id="plot-formats" class="hint"></p><div class="legend"><span class="reference-colour">Blue: original reference</span>  |  <span class="candidate-colour">Orange: selected candidate</span>  |  dots: counted local peaks</div><label class="hint">View <select id="plot-window" onchange="drawSelectedPlots()"><option value="60,190">60-190 ms (correlation interval)</option><option value="0,190">Full run, 0-190 ms</option><option value="60,100">60-100 ms</option><option value="140,190">140-190 ms</option></select></label><h3>Original times</h3><canvas id="original-plot"></canvas><h3 id="aligned-heading">After the best time shift</h3><canvas id="aligned-plot"></canvas><h3>Correlation versus candidate shift</h3><canvas id="correlation-plot"></canvas><p class="hint">Only a horizontal time shift is applied; voltages are not rescaled. Pulse shading uses the reference timing. Blank edges have no shifted samples. The correlation plot uses the selected search range.</p></aside></div>

<p><strong>Correlation:</strong> closer to +1 means a more similar shape after shifting. It is not a percentage overlap and does not prove matching amplitude or voltage offset. <strong>Shift:</strong> positive means move the candidate later, negative means move it earlier. One constant shift cannot remove accumulating timing drift.</p>

<details><summary>How the measurements are defined</summary><p>For each neuron, correlation uses the 60-190 ms portion of its saved voltage trace, excluding the long quiet warm-up. Mean subtraction and normalisation are recalculated on the overlapping samples at every shift; at least 90% of the analysis window must overlap. The maximum is searched only within the displayed shift range to avoid arbitrary alignment to a different firing cycle. Shift resolution is the saved sample spacing. Constant or nearly constant signals have undefined correlation and display N/A.</p><p>Peaks are <strong>local voltage maxima</strong> in the entire saved run, with height at least 1.4542, prominence at least 1 normalised voltage unit, and separation at least 1 ms. Small ripples are excluded. Incomplete events at the boundaries are not counted as peaks. This is different from upward-threshold-crossing counts; an end-of-run crossing can exist without a complete observed peak. The same peak rule is applied to reference and candidate.</p><p>Invalid arithmetic runs show diagnostic peak counts but have no reported similarity score. No waveform pass/fail limits have been assumed. Full-resolution versions of these measurements require regenerating the candidate traces.</p></details>

<script>const data=RESULT_DATA;

let currentIndex=0;let selectedWidth=data.widths[0];let selectedSweep="all";
function activeWidths(){return data.sweeps[selectedSweep].widths}
function selectedRow(current,width){return data.rows.find(row=>row.current===current&&row.width===width&&row.sweeps.includes(selectedSweep))}
function selectSweep(value){selectedSweep=value;const individual=value!=="all";document.getElementById("current-slider").disabled=individual;document.getElementById("current-number").disabled=individual;document.getElementById("sweep-description").textContent=individual?"80 pA only. Reduce "+data.sweeps[value].label+" to zero fractional bits; all other types stay at 32 bits. No accuracy stopping rule is applied.":"Every signal type changes width together.";for(const id of ["width-slider","width-number"]){document.getElementById(id).min=Math.min(...activeWidths());document.getElementById(id).max=32;}if(!activeWidths().includes(selectedWidth))selectedWidth=32;document.getElementById("width-slider").value=selectedWidth;document.getElementById("width-number").value=selectedWidth;if(individual)selectIndex(data.currents.indexOf(80));else render();}

function alignment(row,neuron,limit){let best=null;row.lags_ms.forEach((lag,index)=>{const score=row.correlation_by_neuron[neuron][index];if(score===null||Math.abs(lag)>limit)return;if(best===null||score>best.score||(score===best.score&&Math.abs(lag)<Math.abs(best.lag)))best={score,lag}});return best}

function selectIndex(index){currentIndex=Math.max(0,Math.min(data.currents.length-1,index));document.getElementById('current-slider').value=currentIndex;document.getElementById('current-number').value=data.currents[currentIndex];document.getElementById('notice').textContent='';render()}

function typeCurrent(value){const requested=Number(value);if(!Number.isFinite(requested)||value==='')return;let nearest=0;data.currents.forEach((current,index)=>{if(Math.abs(current-requested)<Math.abs(data.currents[nearest]-requested))nearest=index});selectIndex(nearest);if(data.currents[nearest]!==requested)document.getElementById('notice').textContent=requested+' pA was not tested. Showing the nearest recorded current: '+data.currents[nearest]+' pA. No results are interpolated.'}

function render(){const current=data.currents[currentIndex],neuron=Number(document.getElementById('neuron').value),limit=Number(document.getElementById('lag-limit').value);document.getElementById('current-label').textContent=current+' pA | neuron '+neuron+' correlation and shift';const reference=data.references[String(current)];let markup='';if(reference){const total=reference.peaks.reduce((sum,count)=>sum+count,0);markup='<tr class="reference"><td>Original reference</td><td>'+total+'</td><td>'+total+'</td><td>---</td><td>0</td><td>None</td></tr>'}activeWidths().forEach(width=>{const row=selectedRow(current,width);if(!row){markup+='<tr><td>'+width+'</td><td colspan="5">Not yet simulated</td></tr>';return}const best=row.valid?alignment(row,neuron,limit):null;markup+='<tr data-width="'+width+'" tabindex="0" onclick="selectWidth('+width+')" onkeydown="if(event.key===&quot;Enter&quot;||event.key===&quot; &quot;){event.preventDefault();selectWidth('+width+')}" class="'+(row.valid?'':'invalid')+(width===selectedWidth?' selected-width':'')+'"><td>'+width+'</td><td>'+row.candidate_peaks.reduce((sum,count)=>sum+count,0)+(row.valid?'':' *')+'</td><td>'+row.reference_peaks.reduce((sum,count)=>sum+count,0)+'</td><td>'+(best?best.score.toFixed(4):row.valid?'N/A':'Invalid arithmetic')+'</td><td>'+(best?(best.lag>0?'+':'')+best.lag.toFixed(3):'---')+'</td><td>'+row.faults+'</td></tr>'});document.getElementById('results').innerHTML=markup;requestPlotUpdate()}

PLOT_CODE

document.getElementById('sweep-type').innerHTML=Object.entries(data.sweeps).map(([key,value])=>'<option value="'+key+'">'+value.label+'</option>').join('');selectSweep('all');document.getElementById('width-slider').min=Math.min(...data.widths);document.getElementById('width-slider').max=Math.max(...data.widths);document.getElementById('width-slider').value=selectedWidth;document.getElementById('width-number').value=selectedWidth;document.getElementById('current-slider').max=data.currents.length-1;selectIndex(Math.max(0,data.currents.indexOf(80)));

</script></main></body></html>'''





def main():

    parser=argparse.ArgumentParser(description='Create sampled-waveform similarity and peak-count tables from saved precision display traces.')

    parser.add_argument('--output',type=Path,default=DIRECTORY/'results_fixed_integer')

    parser.add_argument('--run-type-sweep',action='store_true',help='Sweep each signal group independently at 80 pA, down to zero fractional bits')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--gcc',default='gcc')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    arguments=parser.parse_args()
    if arguments.workers<1:
        parser.error('--workers must be positive')
    if arguments.run_type_sweep:
        from signal_type_sweep import run
        run(arguments.output.resolve(),arguments.workers,arguments.gcc,arguments.resume,arguments.prepare_only)

    generate(arguments.output.resolve())





if __name__=='__main__':

    main()

