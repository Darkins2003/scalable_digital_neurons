from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
RTL = DIRECTORY.parents[1] / 'ip/scalable_digital_neurons/hdl'
LABELS = {'state':'Neuron states','current_vector':'Current vector','total_current':'Total neuron current','external_current':'External input','derivative':'Derivatives','euler_update':'Euler increments','scaled_triangle':'Scaled / coupled triangles','exponent_argument':'Exponential arguments','exponential_output':'Exponential outputs','synapse_calculation':'Synapse calculations','matrix_product_rescaled':'Matrix products','matrix_partial_sum':'Matrix partial sums','constant':'Constants','raw_product':'Full multiplication products'}
STATE_INDEX = {'vmem':0,'vk':1,'vg':2,'vna':3}
CONSTANTS = {'coupling':'SYNAPSE_EFFECTIVE_COUPLING_Q24','current_one':'ONE_Q8','excitatory_scale':'SYNAPSE_EXCITATORY_SCALE_Q8','expek':'EXPEK','expmel':'EXPMEL','expmvgk':'EXPMVGK','expvna':'EXPVNA','expvsat':'EXPVSAT','inhibitory_membrane_offset':'SYNAPSE_INHIBITORY_VMEM_OFFSET_Q24','kappa':'KP','negative_spike_threshold':'TRIANGLE_SPIKE_THRESHOLD_Q24 (negated)','sodium_voltage_offset':'VNA_OFFSET_Q24','synapse_bias_excitatory':'SYNAPSE_EXP_BIAS_Q24[0]','synapse_bias_inhibitory':'SYNAPSE_EXP_BIAS_Q24[1]','synapse_coefficient':'SYNFIRE_1D_3_SYNAPSE_COEFFICIENT_Q24','timestep':'DT','triangle_offset_excitatory':'SYNAPSE_GATE_OFFSET_Q16[0]','triangle_offset_inhibitory':'SYNAPSE_GATE_OFFSET_Q16[1]','triangle_scaling':'SYNAPSE_TRIANGLE_SCALE_Q24','triangle_upper_bound':'TRIANGLE_UPPER_BOUND_Q16'}


def rtl_mapping(value, kind):
    neuron_match = re.match(r'n(\d)\.(.*)', value)
    neuron, name = (int(neuron_match[1]), neuron_match[2]) if neuron_match else (None, value)
    if kind == 'state':
        if name in STATE_INDEX:
            return 'single_neuron', f'neuron_state_variables[{STATE_INDEX[name]}][{neuron}]', 'Stored state'
        channel = 'excitatory' if name == 'te' else 'inhibitory'
        return 'synaptic_triangular_generator', f'{channel}_triangular_state_reg[{neuron}]', 'Stored state'
    if kind == 'current_vector':
        return 'compute_current_vector', name, f'Output for neuron {neuron}'
    if kind == 'total_current':
        return 'three_neurons_1D', f'current_in_neuron[{neuron}]', 'Arithmetic equivalent; network summation order differs'
    if kind == 'external_current':
        return 'three_neurons_1D', 'current_in', 'External stimulus port'
    if kind in ('derivative','euler_update'):
        field = name.split('_',1)[1]
        if field in STATE_INDEX:
            return 'matrix_mul_and_euler_update', f'{"dy_dt" if kind == "derivative" else "mul_dy_dt_dt"}[{STATE_INDEX[field]}]', f'Arithmetic equivalent for neuron {neuron}'
        channel = 'excitatory' if field == 'te' else 'inhibitory'
        if kind == 'derivative':
            return 'synaptic_triangular_generator', f'TRIANGLE_SLOPE_MATRIX_Q16[{0 if field == "te" else 1}][selected slope]', 'C derivative; RTL uses precomputed timestep-times-slope increments'
        return 'synaptic_triangular_generator', f'mul_{channel}_dt_slope', f'Equivalent precomputed Euler increment for neuron {neuron}'
    if kind == 'scaled_triangle':
        channel = 'excitatory' if name.endswith('excitatory') else 'inhibitory'
        if name.startswith('coupled'):
            return 'synaptic_pulse_generator', f'{channel}_exponent_argument', f'Coupled value before bias; neuron {neuron}'
        return 'synaptic_pulse_generator', f'pipe[7].scaled_{channel}_triangular_state', f'Scaled triangle plus gate offset; neuron {neuron}'
    if kind == 'exponent_argument':
        if 'triangle_exponent' in name or 'synapse_exponential' in name:
            return 'synaptic_pulse_generator', 'exponent', f'Shared exponent input; neuron {neuron}'
        if name == 'inhibitory_exponent':
            return 'synapse', 'exponent', f'Inhibitory synapse exponent; neuron {neuron}'
        names = {'kappa_potassium':'mul_kp_vk','kappa_gate':'exponent','kappa_sodium':'exponent','potassium_exponent':'combined_exponent','sodium_exponent':'phase_1_pipe[0].term_i3','exponential_input.exponential':'selected_exponent'}
        return 'compute_current_vector', names.get(name,'selected_exponent'), f'Shared calculation / operand equivalent; neuron {neuron}'
    if kind == 'exponential_output':
        module = 'synaptic_pulse_generator' if 'triangle_' in name or 'synapse_exponential' in name else 'compute_current_vector / synapse'
        signal = 'excitatory_pulse / inhibitory_pulse' if 'triangle_' in name else 'result_base_two_exponential / inhibitory_scale'
        if 'triangle_exponential_excitatory' in name:
            signal = 'excitatory_pulse'
        elif 'triangle_exponential_inhibitory' in name:
            signal = 'inhibitory_pulse'
        return module, signal, f'Exponentiation result, possibly shared between operations; neuron {neuron}'
    if kind == 'matrix_product_rescaled':
        return 'matrix_mul_and_euler_update', name.replace('matrix_product','products').replace(';',']['), f'Rescaled product for neuron {neuron}'
    if kind == 'matrix_partial_sum':
        return 'matrix_mul_and_euler_update', 'layer_one_sums / layer_two_sums / dy_dt', 'C sequential prefix sum; no one-to-one RTL register because RTL uses a tree'
    if kind == 'synapse_calculation':
        if name.startswith('scaled_weight'):
            return 'synapse', 'excitatory_scaled_coefficient / inhibitory_scaled_coefficient', f'Coefficient arithmetic equivalent; neuron {neuron}, C channel {name[name.index("["):]}'
        if name.startswith('synapse_scale'):
            return 'synapse', 'SYNAPSE_EXCITATORY_SCALE_Q8 / inhibitory_scale', f'Channel-dependent scale; neuron {neuron}'
        if name.startswith('synapse_product'):
            return 'synapse', 'excitatory_current_contribution / inhibitory_current_contribution', f'Channel contribution; neuron {neuron}'
        return 'three_neurons_1D', 'current_in_neuron', 'C sequential synapse prefix sum; no one-to-one RTL register'
    if kind == 'constant':
        if value.startswith('neuron_matrix'):
            return 'neuron_params_generated_pkg', value.replace('neuron_matrix','NEURON_MATRIX').replace(';',']['), 'Matrix coefficient'
        if value.startswith('triangle_slope'):
            return 'neuron_params_generated_pkg', value.replace('triangle_slope','TRIANGLE_SLOPE_MATRIX_Q16').replace(';',']['), 'Slope constant; RTL increment table precomputes DT times slope'
        return 'neuron_params_generated_pkg / neuron_params_pkg', CONSTANTS.get(value,value), 'Constant or equivalent RTL expression'
    if kind == 'raw_product':
        return 'signed_32_32_multiplication', 'product', f'C full product at {value}; Q describes full-product operand scaling. RTL multiplier instances use product; optimised/precomputed sites may have no live product register'
    raise ValueError(f'Unmapped variable: {value}, {kind}')


def load_data(results):
    with (results/'tables/extended_current_summary.csv').open(newline='') as stream:
        numeric = list(csv.DictReader(stream))
    numeric = sorted((row for row in numeric if float(row['current_pa']) >= 1),key=lambda row:float(row['current_pa']))
    currents = [float(row['current_pa']) for row in numeric]
    indices = {current:index for index,current in enumerate(currents)}
    valid = [row['numerically_valid']=='True' for row in numeric]
    records = {}
    with (results/'tables/all_values_by_current.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            current = float(row['current_pa'])
            if current not in indices:
                continue
            name = row['value']
            width, fractional = int(row['baseline_width']),int(row['fractional_bits'])
            if name not in records:
                module, signal, note = rtl_mapping(name,row['kind'])
                records[name] = dict(name=name,kind=row['kind'],width=width,fractional=fractional,q=f'Q{width-fractional}.{fractional}',capacity=width-fractional,module=module,signal=signal,note=note,bits=[None]*len(currents))
            if (records[name]['width'],records[name]['fractional']) != (width,fractional):
                raise ValueError(f'Format changed for {name}')
            if valid[indices[current]] and row['numerically_valid']=='True':
                records[name]['bits'][indices[current]] = int(row['integer_bits_observed'])
    groups = defaultdict(list)
    for record in records.values():
        groups[record['kind'],record['width'],record['fractional']].append(record)
    summaries = []
    for (kind,width,fractional),members in sorted(groups.items(),key=lambda item:(list(LABELS).index(item[0][0]),item[0][2])):
        summaries.append(dict(name=LABELS[kind],kind=kind,width=width,fractional=fractional,q=f'Q{width-fractional}.{fractional}',capacity=width-fractional,module='; '.join(sorted({row['module'] for row in members})),signal='; '.join(sorted({re.sub(r'\[\d+\]','[index]',row['signal']) for row in members})),note=f'Maximum across {len(members)} profiled values with this format',bits=[max((row['bits'][index] for row in members if row['bits'][index] is not None),default=None) for index in range(len(currents))]))
    individuals = sorted(records.values(),key=lambda row:(list(LABELS).index(row['kind']),row['name']))
    return dict(currents=currents,valid=valid,groups=summaries,individuals=individuals,failures=[dict(current=float(row['current_pa']),signal=row['first_overflow_signal'],group=row['first_overflow_group']) for row in numeric if row['numerically_valid']!='True'])


def important_records(data):
    records = []
    for field, label in (('vmem','Membrane voltage Vmem'),('vk','Potassium state Vk'),('vg','Gate state Vg'),('vna','Sodium state Vna'),('te','Excitatory triangle Te'),('ti','Inhibitory triangle Ti')):
        members = [record for record in data['individuals'] if record['kind']=='state' and record['name'].split('.',1)[-1]==field]
        record = dict(members[0])
        record['name'] = label
        record['signal'] = re.sub(r'\[\d+\]$', '[n]', record['signal'])
        record['note'] = 'Largest requirement across neurons 0, 1 and 2 at each input current.'
        record['bits'] = [max((member['bits'][index] for member in members if member['bits'][index] is not None),default=None) for index in range(len(data['currents']))]
        records.append(record)
    for kind,fractional,label,signal in (('current_vector',8,'Current vector','current_vector[0:7]'),('total_current',8,'Total current entering a neuron','current_in_neuron[n]'),('derivative',8,'Voltage-state derivatives','dy_dt[0:3]'),('euler_update',24,'Voltage-state Euler increments','mul_dy_dt_dt[0:3]')):
        record = dict(next(record for record in data['groups'] if record['kind']==kind and record['fractional']==fractional))
        record.update(name=label,signal=signal)
        records.append(record)
    return records


def generate(results):
    data = load_data(results)
    data['important'] = important_records(data)
    output = results/'sv_integer_bits.html'
    escaped = lambda value:html.escape(str(value))
    rows = []
    for index,record in enumerate(data['individuals']):
        rows.append(dict(report_name=record['name'],sv_module=record['module'],sv_signal_or_equivalent=record['signal'],mapping_note=record['note'],q_format=record['q'],width=record['width'],fractional_bits=record['fractional'],available_integer_bits=record['capacity']))
    with (results/'tables/sv_variable_mapping.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pieces = [PAGE_START, f'<h1>SystemVerilog signals and integer-bit requirements</h1><p class="lead">Start with the 10 important variables below. All {len(data["individuals"])} individual quantities are retained in the expandable sections. {len(data["currents"])} tested currents, starting at 1 pA.</p>', '<p>Q<strong>I.F</strong>: I includes the sign bit; I + F equals the word width. The Q label is the <strong>existing signal format</strong>; for quantities without a direct RTL register it is the C profile format. Blue curves show the minimum integer bits observed during a valid complete run; orange dashed lines show existing capacity. Red markers identify failed runs, whose ranges are omitted.</p>', '<details class="method-notes"><summary>Measurement and RTL-mapping notes</summary><p class="note">These are saved C-model measurements mapped to the current RTL names, not new RTL measurements. Equivalent expressions, shared arithmetic sites, precomputed operations and C-only prefix sums are labelled explicitly. A prefix sum in C does not prove the same range for every node in the RTL adder tree. Wide-product Q formats describe operand scaling.</p></details>', '<div class="controls"><label>Inspect current <select id="current" onchange="updateNumbers()">' + ''.join(f'<option value="{index}" {"selected" if current==80 else ""}>{current:g} pA{" | OVERFLOW" if not data["valid"][index] else ""}</option>' for index,current in enumerate(data['currents'])) + '</select></label><label>Graph range <select id="range" onchange="redraw()"><option value="300">1-300 pA (linear)</option><option value="10000" selected>1-10,000 pA (log)</option><option value="1000000">1-1,000,000 pA (log)</option></select></label><label>Find signal <input id="search" placeholder="vmem, current_vector, Q8.24..." oninput="filterRows()"></label><span id="status"></span></div>',  '<p>Blue: integer bits needed. Dashed orange: existing capacity. Select a current to update every reading; hover for a tested point. Each important panel covers all three neurons.</p><nav><a href="#important">Important variables</a><a href="#all-groups" onclick="document.getElementById(&quot;all-groups&quot;).open=true">All types</a><a href="#all-individuals" onclick="document.getElementById(&quot;all-individuals&quot;).open=true">All individual signals</a><a href="report.html">Full sweep report</a></nav>', '<section id="important"><h2>Important variables</h2><p>The six stored states and the main current/update signals. Graphs show the largest integer-bit requirement among the covered signals at each tested current, without extra headroom.</p><div class="cards">']
    for index,record in enumerate(data['important']):
        search=' '.join(str(record[key]) for key in ('name','kind','module','signal','q','note'))
        pieces.append(f'<article class="card result" data-search="{escaped(search)}"><div class="card-head"><h3>{escaped(record["name"])}</h3><strong class="q">{record["q"]}</strong></div><p class="module">{escaped(record["module"])}</p><code>{escaped(record["signal"])}</code><p class="note-small">{escaped(record["note"])}</p><canvas data-section="important" data-index="{index}"></canvas><p class="reading" data-section="important" data-index="{index}"></p></article>')
    pieces.append('</div></section><details id="all-groups" class="full-results"><summary>All variable types and formats (26 groups)</summary><section id="groups"><div class="cards">')
    for index,record in enumerate(data['groups']):
        pieces.append(f'<article class="card result" data-search="{escaped(str(record))}"><div class="card-head"><h3>{escaped(record["name"])}</h3><strong class="q">{record["q"]}</strong></div><p class="module">{escaped(record["module"])}</p><code>{escaped(record["signal"])}</code><p>{record["width"]} total bits; {record["capacity"]} integer/sign bits; {record["fractional"]} fractional bits.</p><p>{escaped(record["note"])}</p><canvas data-section="groups" data-index="{index}"></canvas><p class="reading" data-section="groups" data-index="{index}"></p></article>')
    pieces.append('</div></section></details><details id="all-individuals" class="full-results"><summary>Every individual profiled quantity (486 entries)</summary><section id="individuals"><p>Neuron-indexed C values can share a time-multiplexed RTL port or intermediate; their neuron number remains in the report name.</p><table><thead><tr><th>SV name and module</th><th>Current Q format</th><th>Required integer bits versus input current (pA)</th><th>At selected current</th></tr></thead><tbody>')
    for index,record in enumerate(data['individuals']):
        search=' '.join(str(record[key]) for key in ('name','kind','module','signal','q','note'))
        pieces.append(f'<tr class="result" data-search="{escaped(search)}"><td><code>{escaped(record["signal"])}</code><p class="module">{escaped(record["module"])}</p><p class="source">Report: {escaped(record["name"])}</p><p class="note-small">{escaped(record["note"])}</p></td><td><strong>{record["q"]}</strong><p>{record["width"]} bits total<br>I = {record["capacity"]}<br>F = {record["fractional"]}</p></td><td><canvas data-section="individuals" data-index="{index}"></canvas></td><td class="reading" data-section="individuals" data-index="{index}"></td></tr>')
    pieces.append('</tbody></table></section></details><footer>Required bits are observed minima including sign, without extra headroom. One extra bit is an optional range allowance, not a universal guarantee. Changing the format can change behaviour and needs another validation run. Invalid runs cannot provide complete integer requirements. All 0 pA data remain in the original study.</footer></main><div id="tooltip"></div>')
    pieces.append('<script>const results='+json.dumps(data,separators=(',',':'))+';</script>'+PAGE_SCRIPT+'</body></html>')
    output.write_text('\n'.join(pieces),encoding='utf-8')
    provenance=dict(report_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs={name:hashlib.sha256((results/'tables'/name).read_bytes()).hexdigest() for name in ('extended_current_summary.csv','all_values_by_current.csv')},rtl_sha256={str(path.relative_to(RTL)):hashlib.sha256(path.read_bytes()).hexdigest() for path in RTL.rglob('*.sv')},profiled_quantities=len(rows),format_groups=len(data['groups']),tested_positive_currents=len(data['currents']))
    (results/'sv_integer_bits_manifest.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(f'Created {output}: {len(rows)} individual graphs and {len(data["groups"])} format-group graphs.',flush=True)
    return output


PAGE_START = '''<!doctype html><html><head><meta charset="utf-8"><title>SV signals, Q formats and required integer bits</title><style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f2f5f8;color:#203449;font:15px system-ui,sans-serif}main{max-width:1700px;padding:28px;margin:auto}h1{font-size:32px}h2{margin-top:35px}p{line-height:1.55}.lead{font-size:20px}.controls{position:sticky;top:0;z-index:10;background:#203b55;color:white;padding:14px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}input,select{font:inherit;padding:7px;border:1px solid #c4d1dc;border-radius:4px}nav{display:flex;gap:25px;flex-wrap:wrap;margin:20px 0}a{color:#16648d}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.card{background:white;border:1px solid #d3dfe8;border-radius:8px;padding:20px;min-width:0}.card-head{display:flex;justify-content:space-between;align-items:center;gap:12px}h3{margin:0}.q{padding:8px;background:#e8f2f8;color:#0f587e;border-radius:5px;white-space:nowrap}.full-results{margin:24px 0;padding:18px;background:white;border:1px solid #d3dfe8;border-radius:8px}.full-results>summary{font-size:20px;font-weight:650;cursor:pointer}.method-notes>summary{cursor:pointer;color:#52697b}.module,.source,.note-small{color:#5c6c7a;font-size:12px;margin:7px 0}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}canvas{display:block;width:100%;height:205px}.reading{font-weight:600;font-size:13px}.note{padding:14px;border-left:4px solid #c48b35;background:#fff4e2}table{width:100%;border-collapse:collapse;table-layout:fixed;background:white}th{background:#203b55;color:white;padding:12px;text-align:left}th:nth-child(1){width:31%}th:nth-child(2){width:12%}th:nth-child(3){width:43%}th:nth-child(4){width:14%}td{border:1px solid #d7e1e9;padding:12px;vertical-align:middle}tr:nth-child(even){background:#f7f9fb}td canvas{height:170px}footer{padding:24px;line-height:1.6;color:#576c7b}#tooltip{position:fixed;display:none;pointer-events:none;z-index:20;padding:9px;background:#203b55;color:white;font-size:12px;border-radius:5px;max-width:290px}section{scroll-margin-top:110px}[hidden]{display:none!important}@media(max-width:900px){main{padding:12px}.cards{grid-template-columns:1fr}table,tbody,tr,td{display:block;width:100%}thead{display:none}tr{margin-bottom:22px}td{border-bottom:0}.controls{position:static}}
</style></head><body><main>'''


PAGE_SCRIPT = '''<script>
const canvases=[...document.querySelectorAll('canvas')],visible=new Set();
function selectedIndex(){return Number(document.getElementById('current').value)}
function recordFor(element){return results[element.dataset.section][Number(element.dataset.index)]}
function currentLabel(current){return current>=1000000?(current/1000000)+'M':current>=1000?(current/1000)+'k':String(current)}
function updateNumbers(){const index=selectedIndex(),current=results.currents[index];document.querySelectorAll('.reading').forEach(element=>{const record=recordFor(element),bits=record.bits[index];element.textContent=bits===null?currentLabel(current)+' pA: incomplete / overflow':currentLabel(current)+' pA: needs '+bits+' integer bits; '+(record.capacity-bits)+' spare';element.style.color=bits===null?'#b13227':'#175b80'});document.getElementById('status').textContent=results.valid[index]?'Valid complete simulation':'Incomplete: required bits unavailable';redraw()}
function graph(canvas){const record=recordFor(canvas),maximum=Number(document.getElementById('range').value),logarithmic=maximum>300,context=canvas.getContext('2d'),width=canvas.clientWidth,height=canvas.clientHeight,ratio=window.devicePixelRatio||1;if(width<20||height<20)return;canvas.width=width*ratio;canvas.height=height*ratio;context.scale(ratio,ratio);const left=37,right=width-14,top=14,bottom=height-34;const peak=Math.max(record.capacity,...record.bits.filter(value=>value!==null)),upper=peak+1;const x=current=>left+(logarithmic?Math.log10(current)/Math.log10(maximum):(current-1)/(maximum-1))*(right-left),y=bits=>bottom-bits/upper*(bottom-top);context.fillStyle='white';context.fillRect(0,0,width,height);context.font='10px system-ui';context.strokeStyle='#dbe4eb';context.lineWidth=.6;const interval=Math.max(1,Math.ceil(upper/5));for(let bits=0;bits<=upper;bits+=interval){context.beginPath();context.moveTo(left,y(bits));context.lineTo(right,y(bits));context.stroke();context.fillStyle='#536b7c';context.textAlign='right';context.fillText(String(bits),left-6,y(bits)+3)}context.setLineDash([5,4]);context.strokeStyle='#bc7625';context.lineWidth=1;context.beginPath();context.moveTo(left,y(record.capacity));context.lineTo(right,y(record.capacity));context.stroke();context.setLineDash([]);let open=false;context.beginPath();context.strokeStyle='#176f9c';context.lineWidth=1.6;results.currents.forEach((current,index)=>{if(current>maximum)return;const bits=record.bits[index];if(bits===null){open=false;return}if(open)context.lineTo(x(current),y(bits));else{context.moveTo(x(current),y(bits));open=true}});context.stroke();context.fillStyle='#176f9c';results.currents.forEach((current,index)=>{if(current<=maximum&&record.bits[index]!==null){context.beginPath();context.arc(x(current),y(record.bits[index]),1.2,0,2*Math.PI);context.fill()}});context.fillStyle='#b9362b';results.currents.forEach((current,index)=>{if(current<=maximum&&!results.valid[index])context.fillRect(x(current)-1,bottom-5,2,4)});const selected=selectedIndex();if(results.currents[selected]<=maximum){context.strokeStyle='#6c8494';context.setLineDash([2,3]);context.beginPath();context.moveTo(x(results.currents[selected]),top);context.lineTo(x(results.currents[selected]),bottom);context.stroke();context.setLineDash([]);if(record.bits[selected]!==null){context.fillStyle='#176f9c';context.beginPath();context.arc(x(results.currents[selected]),y(record.bits[selected]),3,0,2*Math.PI);context.fill()}}const ticks=logarithmic?[1,10,100,1000,10000,100000,1000000].filter(current=>current<=maximum):[1,50,100,150,200,250,300];context.fillStyle='#536b7c';context.textAlign='center';ticks.forEach(current=>context.fillText(currentLabel(current),x(current),bottom+15));context.fillText('Input current (pA)',(left+right)/2,height-3);context.save();context.translate(10,(top+bottom)/2);context.rotate(-Math.PI/2);context.fillText('Integer bits incl. sign',0,0);context.restore();canvas.graphState={left,right,maximum,logarithmic}}
function redraw(){visible.forEach(canvas=>{if(!canvas.closest('.result').hidden)graph(canvas)})}
function filterRows(){const query=document.getElementById('search').value.toLowerCase();document.querySelectorAll('.result').forEach(element=>element.hidden=!element.dataset.search.toLowerCase().includes(query));document.querySelectorAll('.full-results').forEach(section=>section.open=Boolean(query)&&[...section.querySelectorAll('.result')].some(element=>!element.hidden));requestAnimationFrame(redraw)}
const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){visible.add(entry.target);graph(entry.target)}else visible.delete(entry.target)})},{rootMargin:'300px'});canvases.forEach(canvas=>{observer.observe(canvas);canvas.addEventListener('mousemove',event=>{if(!canvas.graphState)return;const state=canvas.graphState,rect=canvas.getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(event.clientX-rect.left-state.left)/(state.right-state.left))),current=state.logarithmic?Math.pow(10,fraction*Math.log10(state.maximum)):1+fraction*(state.maximum-1);let nearest=0;results.currents.forEach((candidate,index)=>{if(candidate<=state.maximum&&Math.abs(Math.log(candidate/current))<Math.abs(Math.log(results.currents[nearest]/current)))nearest=index});const record=recordFor(canvas),bits=record.bits[nearest],tooltip=document.getElementById('tooltip');tooltip.textContent=results.currents[nearest]+' pA: '+(bits===null?'incomplete / overflow; no valid requirement':bits+' integer/sign bits needed; existing capacity '+record.capacity);tooltip.style.display='block';tooltip.style.left=Math.min(event.clientX+12,window.innerWidth-300)+'px';tooltip.style.top=Math.max(5,event.clientY-45)+'px'});canvas.addEventListener('mouseleave',()=>document.getElementById('tooltip').style.display='none')});window.addEventListener('resize',redraw);updateNumbers();
</script>'''


def main():
    parser=argparse.ArgumentParser(description='Build a standalone HTML view of RTL names, current Q formats and integer bits versus input current.')
    parser.add_argument('--results',type=Path,default=DIRECTORY/'results_extended')
    arguments=parser.parse_args()
    generate(arguments.results.resolve())


if __name__=='__main__':
    main()
