from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import precision_support as study


DIRECTORY = Path(__file__).resolve().parent
DEFAULT_CURRENTS = tuple(range(0,101,5)) + tuple(range(125,1001,25))
DEFAULT_PROFILE_RESULTS = (DIRECTORY.parent/'input_current_sweep/results',DIRECTORY.parent/'input_current_sweep/results_extended/01_325_to_1000pA')


def integer_bits(minimum_raw, maximum_raw, fractional):
    for bits in range(1,65):
        scale = 1 << (bits - 1 + fractional)
        if minimum_raw >= -scale and maximum_raw <= scale - 1:
            return bits
    raise ValueError('Profile exceeds the supported integer range')


def derive_budgets(directories, headroom):
    formats = {tuple(value) for value in study.BASELINE.values()}
    budgets, source_cases, sources, sampled = {}, [], {}, set()
    reference = None
    for directory in directories:
        directory = directory.resolve()
        manifest = json.loads((directory/'manifest.json').read_text())
        content = {key:value for key,value in manifest.items() if key!='fingerprint'}
        if hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()!=manifest['fingerprint']:
            raise ValueError(f'Invalid range-study manifest: {directory}')
        for relative,expected in manifest['source_sha256'].items():
            if not study.profile_source_matches(relative,expected):
                raise ValueError(f'Range-study source changed: {relative}')
        identity = {key:manifest[key] for key in ('source_sha256','steps','timestep_ms','pulse_start','pulse_end','baseline_formats','measured_network')}
        if reference is None:
            reference = identity
        elif identity!=reference:
            raise ValueError('Range studies use different numerical experiments')
        if manifest['steps']!=190000 or manifest['pulse_start']!=60000 or manifest['pulse_end']!=140000 or manifest['baseline_formats']!={group:list(value) for group,value in study.BASELINE.items()}:
            raise ValueError('Range profiles must use the complete original 32-bit experiment')
        sources[str(directory)] = manifest['fingerprint']
        for path in sorted((directory/'runs').glob('*/completed.json')):
            case = json.loads(path.read_text())
            current = case['current_pa']
            if not 0<=current<=1000:
                continue
            if case['fingerprint']!=manifest['fingerprint'] or case['current_raw_q8'] not in manifest['current_raw_q8']:
                raise ValueError(f'Checkpoint provenance mismatch: {path}')
            if not case['numeric']['numerically_valid'] or not case['numeric']['identical_to_original_c'] or case['numeric']['completed_steps']!=190000:
                raise ValueError(f'Cannot derive complete operating budgets from invalid case: {path}')
            if current in sampled:
                raise ValueError(f'Overlapping range-study current: {current}')
            sampled.add(current)
            profile_rows = []
            for row in case['values']:
                key = (row['baseline_width'],row['fractional_bits'])
                if key in formats:
                    profile_rows.append((key,integer_bits(row['minimum_raw'],row['maximum_raw'],key[1]),row['value']))
            ranges_path = path.parent/'calculation_sites.csv'
            with ranges_path.open(newline='') as stream:
                for row in csv.DictReader(stream):
                    key = (int(row['width']),int(row['fractional']))
                    if key not in formats:
                        continue
                    low,high = float(row['minimum']),float(row['maximum'])
                    if not math.isfinite(low) or not math.isfinite(high):
                        raise ValueError('Nonfinite baseline operation range')
                    profile_rows.append((key,integer_bits(round(low*2**key[1]),round(high*2**key[1]),key[1]),f"operation.n{row['neuron']}.{row['signal']}"))
            for key,needed,value in profile_rows:
                if key not in budgets or needed>budgets[key]['observed_integer_bits']:
                    budgets[key] = dict(baseline_width=key[0],baseline_fractional_bits=key[1],baseline_q=f'Q{key[0]-key[1]}.{key[1]}',observed_integer_bits=needed,headroom_bits=headroom,allocated_integer_bits=needed+headroom,limiting_value=value,limiting_current_pa=current)
            source_cases.append(dict(current_pa=current,checkpoint_sha256=study.digest(path),operation_ranges_sha256=study.digest(ranges_path)))
    if not set(DEFAULT_CURRENTS).issubset(sampled):
        raise ValueError(f'Range profiles are missing required currents: {sorted(set(DEFAULT_CURRENTS)-sampled)}')
    if set(budgets)!=formats:
        raise ValueError('Missing baseline format groups in range profiles')
    group_integers = {group:budgets[tuple(study.BASELINE[group])]['allocated_integer_bits'] for group in study.GROUPS}
    return dict(operating_range_pa=[0,1000],integer_bits_include_sign=True,headroom_bits=headroom,shared_types=[budgets[key] for key in sorted(budgets)],group_integer_bits=group_integers,profiled_currents=sorted(sampled),range_manifest_fingerprints=sources,profile_checkpoints=sorted(source_cases,key=lambda row:row['current_pa']),range_experiment=reference,wide_product_policy='Full products remain signed 64-bit. Only the six existing configurable C groups receive the candidate widths.',limitation='Observed complete-run C envelopes, not universal bounds or RTL requirements. Candidate overflow is checked independently.')


def make_configurations(group_integers, widths=None):
    minimum = max(group_integers.values())
    selected = list(range(32,minimum-1,-1)) if widths is None else list(widths)
    if not selected or len(set(selected))!=len(selected) or any(width<minimum or width>32 for width in selected):
        raise ValueError(f'Use distinct widths from {minimum} through 32')
    return [dict(name=f'w{width:02d}_fixed_integer',stage='fixed_integer',width=width,integer_bits=group_integers,formats={group:(width,width-group_integers[group]) for group in study.GROUPS}) for width in sorted(selected,reverse=True)]


def make_manifest(arguments, budgets, configurations):
    paths = [Path(__file__),Path(study.__file__),DIRECTORY/'precision_model.c',study.REFERENCE,study.HELPER,study.MODEL,study.TABLE,DIRECTORY/'profile_source_compatibility.json']
    sources = {str(path.relative_to(study.PROJECT)):study.digest(path) for path in paths}
    value = dict(study='Fixed integer-bit C precision sweep',source_sha256=sources,operating_range_pa=[0,1000],budgets=budgets,configurations=configurations,currents=sorted(arguments.currents),steps=arguments.steps,pulse_start=60000,pulse_end=140000,timestep_ms=.001,reference_formats=study.BASELINE,compiler=study.command([arguments.gcc,'--version']).splitlines()[0],candidate_flags=['-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function'],reference_flags=['-std=c11','-O0','-w','-fwrapv','-DWIDE_MUL'],spike_threshold=1.4542,spike_matching_window_ms=.5,reference='Original 32-bit C model, exact harness verification at every current; no MATLAB or RTL comparisons',accuracy_acceptance='No automatic accuracy acceptance threshold is assigned.',keep_traces=arguments.keep_traces)
    value['fingerprint'] = hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return value


def write_plan(output, manifest):
    tables = output/'tables'
    tables.mkdir(parents=True,exist_ok=True)
    study.save_json(output/'integer_budgets.json',manifest['budgets'])
    study.save_json(output/'configurations.json',manifest['configurations'])
    study.write_rows(tables/'integer_budgets.csv',[dict(row,assigned_groups=', '.join(group for group,value in study.BASELINE.items() if value[1]==row['baseline_fractional_bits'])) for row in manifest['budgets']['shared_types']])
    rows = []
    for candidate in manifest['configurations']:
        timestep_fractional = candidate['formats']['timestep'][1]
        encoded_timestep = int(float(np.float32(.001))*2**timestep_fractional)
        row = dict(configuration=candidate['name'],width=candidate['width'],currents=len(manifest['currents']),encoded_timestep_raw=encoded_timestep,encoded_timestep_ms=encoded_timestep/2**timestep_fractional)
        for group in study.GROUPS:
            integer = manifest['budgets']['group_integer_bits'][group]
            row[group+'_integer_bits'] = integer
            row[group+'_fractional_bits'] = candidate['formats'][group][1]
            row[group+'_q'] = f'Q{integer}.{candidate["formats"][group][1]}'
        rows.append(row)
    study.write_rows(tables/'configuration_catalog.csv',rows)
    study.write_rows(tables/'tested_combinations.csv',[dict(configuration=row['configuration'],width=row['width'],current_pa=current) for row in rows for current in manifest['currents']])


def save_display(path, actual, expected):
    edges = np.linspace(0,len(actual),min(2000,len(actual))+1,dtype=int)
    middle = (edges[:-1]+edges[1:]-1)//2
    columns = [2,6,10]
    candidate,reference = actual[:,columns],expected[:,columns]
    error = candidate-reference
    values = dict(time_ms=(actual[middle,0]+1)*.001,candidate=candidate[middle],reference=reference[middle],error=error[middle])
    for label,trace in (('candidate',candidate),('reference',reference),('error',error)):
        values[label+'_minimum'] = np.minimum.reduceat(trace,edges[:-1],axis=0)
        values[label+'_maximum'] = np.maximum.reduceat(trace,edges[:-1],axis=0)
    np.savez_compressed(path,**values)


def load_saved(path, fingerprint, candidate, current):
    saved = json.loads(path.read_text())
    if saved['fingerprint']!=fingerprint or saved['summary']['configuration']!=candidate['name'] or saved['summary']['current_pa']!=current or saved['formats']!={group:list(value) for group,value in candidate['formats'].items()}:
        raise ValueError(f'Checkpoint mismatch: {path}')
    return saved


def prepare_reference(output, current, manifest, executable, original, stimulus, resume):
    candidate = dict(name='reference32',formats=study.BASELINE)
    directory = output/'runs/reference32'/f'current_{current:04d}'
    checkpoint = directory/'completed.json'
    compressed = directory/'reference_trace.npz'
    if resume and checkpoint.is_file():
        saved = load_saved(checkpoint,manifest['fingerprint'],candidate,current)
        if study.digest(compressed)!=saved['reference_trace_sha256']:
            raise ValueError('Saved reference trace checksum mismatch')
        with np.load(compressed) as stream:
            raw = stream['raw']
        return study.decode(raw,study.BASELINE),saved,True
    raw,numeric,ranges = study.run_model(executable,directory,study.BASELINE,stimulus)
    original_path = directory/'original_trace.csv'
    study.command([original,stimulus,original_path],directory)
    expected = study.read_raw(original_path)
    if not np.array_equal(raw,expected) or len(raw)!=manifest['steps'] or numeric['overflow_count'] or numeric['zero_constants']:
        raise ValueError(f'Original 32-bit C verification failed at {current} pA')
    np.savez_compressed(compressed,raw=raw)
    row = dict(configuration='reference32',stage='reference',width=32,current_pa=current,**numeric,numeric_valid=True,baseline_exact_match=True)
    saved = dict(fingerprint=manifest['fingerprint'],formats=study.BASELINE,summary=row,reference_trace_sha256=study.digest(compressed),completed_utc=datetime.now(timezone.utc).isoformat())
    study.save_json(checkpoint,saved)
    original_path.unlink()
    if not manifest['keep_traces']:
        (directory/'trace.csv').unlink()
    return study.decode(raw,study.BASELINE),saved,False


def evaluate(output,candidate,current,manifest,executable,stimulus,reference,resume):
    directory = output/'runs'/candidate['name']/f'current_{current:04d}'
    checkpoint = directory/'completed.json'
    display = directory/'voltage_comparison.npz'
    if resume and checkpoint.is_file():
        saved = load_saved(checkpoint,manifest['fingerprint'],candidate,current)
        if study.digest(display)!=saved['display_sha256']:
            raise ValueError('Saved waveform display checksum mismatch')
        return saved,True
    raw,numeric,ranges = study.run_model(executable,directory,candidate['formats'],stimulus)
    if len(raw)!=manifest['steps']:
        raise ValueError('Candidate did not complete the requested steps')
    actual = study.decode(raw,candidate['formats'])
    states,spikes,matches = study.accuracy(actual,reference,'reference32',current,candidate['name'])
    valid = numeric['overflow_count']==0 and numeric['zero_constants']==0
    for row in states+spikes+matches:
        row['numeric_valid'] = valid
    voltage = [row for row in states if row['state'].endswith('_vmem')]
    row = dict(configuration=candidate['name'],stage='fixed_integer',width=candidate['width'],current_pa=current,**numeric,numeric_valid=valid,baseline_voltage_rmse=max(value['rmse'] for value in voltage),maximum_voltage_absolute_error=max(value['maximum_absolute_error'] for value in voltage),maximum_voltage_nrmse_percent=max((value['normalised_rmse_percent'] for value in voltage if value['normalised_rmse_percent'] is not None),default=None),unmatched_reference_crossings=sum(value['unmatched_reference'] for value in spikes),unmatched_candidate_crossings=sum(value['unmatched_candidate'] for value in spikes),maximum_matched_crossing_error_ms=max((value['maximum_absolute_error_ms'] for value in spikes if value['maximum_absolute_error_ms'] is not None),default=None))
    save_display(display,actual,reference)
    saved = dict(fingerprint=manifest['fingerprint'],formats=candidate['formats'],summary=row,state_metrics=states,spike_metrics=spikes,spike_matches=matches,ranges=ranges,display_sha256=study.digest(display),completed_utc=datetime.now(timezone.utc).isoformat())
    study.save_json(checkpoint,saved)
    study.write_rows(directory/'state_metrics.csv',states)
    study.write_rows(directory/'spike_metrics.csv',spikes)
    if not manifest['keep_traces']:
        (directory/'trace.csv').unlink()
    return saved,False


def read_cases(output,manifest):
    cases = []
    configurations = {row['name']:row for row in manifest['configurations']}
    configurations['reference32'] = dict(name='reference32',formats=manifest['reference_formats'])
    for path in sorted((output/'runs').glob('*/current_*/completed.json')):
        candidate = configurations.get(path.parent.parent.name)
        if candidate is None:
            raise ValueError(f'Unknown saved configuration: {path}')
        current = int(path.parent.name.removeprefix('current_'))
        if current not in manifest['currents']:
            raise ValueError('Saved current is not in the manifest')
        cases.append(load_saved(path,manifest['fingerprint'],candidate,current))
    return cases


def report(output,manifest):
    from fixed_integer_report import make_report
    cases = read_cases(output,manifest)
    make_report(output,manifest,cases)


def main():
    parser = argparse.ArgumentParser(description='C precision study with fixed, range-derived integer bits and every feasible total width.')
    parser.add_argument('--output',type=Path,default=DIRECTORY/'results_fixed_integer')
    parser.add_argument('--profile-results',type=Path,nargs='+',default=DEFAULT_PROFILE_RESULTS)
    parser.add_argument('--headroom-bits',type=int,default=1)
    parser.add_argument('--widths',type=int,nargs='+')
    parser.add_argument('--currents',type=int,nargs='+',default=DEFAULT_CURRENTS)
    parser.add_argument('--steps',type=int,default=190000)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--gcc',default='gcc')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--report-only',action='store_true')
    parser.add_argument('--check-resume',action='store_true')
    parser.add_argument('--keep-traces',action='store_true')
    arguments = parser.parse_args()
    if arguments.headroom_bits<0 or arguments.workers<1 or not 140001<=arguments.steps<=190000 or len(set(arguments.currents))!=len(arguments.currents) or any(not 0<=current<=1000 for current in arguments.currents):
        parser.error('Use nonnegative headroom, positive workers, 140001..190000 steps and distinct integer currents in 0..1000 pA')
    output = arguments.output.resolve()
    manifest_path = output/'manifest.json'
    if arguments.report_only:
        report(output,json.loads(manifest_path.read_text()))
        return 0
    if arguments.check_resume and not arguments.resume:
        parser.error('--check-resume requires --resume')
    print('Deriving shared integer budgets from saved 0-1000 pA profiles...',flush=True)
    budgets = derive_budgets(arguments.profile_results,arguments.headroom_bits)
    configurations = make_configurations(budgets['group_integer_bits'],arguments.widths)
    manifest = make_manifest(arguments,budgets,configurations)
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text())
        if previous['fingerprint']!=manifest['fingerprint']:
            previous_content = {key:value for key,value in previous.items() if key!='fingerprint'}
            active_content = {key:value for key,value in manifest.items() if key!='fingerprint'}
            intact = hashlib.sha256(json.dumps(previous_content,sort_keys=True).encode()).hexdigest()==previous['fingerprint']
            previous_sources = previous_content.pop('source_sha256',{})
            active_sources = active_content.pop('source_sha256',{})
            compatible = intact and json.dumps(previous_content,sort_keys=True)==json.dumps(active_content,sort_keys=True) and study.compatible_source_sets(previous_sources,active_sources)
            if not compatible:
                raise ValueError('Existing results have different settings or numerical sources; use a new --output directory')
            if any((output/'runs').glob('*/current_*/completed.json')):
                study.save_json(output/'runner_compatibility.json',dict(reason='Shared helper extraction and import-path changes only; numerical sources and experiment settings are unchanged.',checkpoint_fingerprint=previous['fingerprint'],active_source_sha256=manifest['source_sha256']))
                manifest = previous
            print('Compatible helper cleanup: preserved settings and saved results.',flush=True)
        if not arguments.resume and not arguments.prepare_only:
            raise ValueError('Output already exists; use --resume to continue safely')
    if arguments.check_resume:
        cases = read_cases(output,manifest)
        print(f'PASS: {len(cases)} compatible saved runs. No simulations executed.',flush=True)
        return 0
    output.mkdir(parents=True,exist_ok=True)
    study.save_json(manifest_path,manifest)
    write_plan(output,manifest)
    requested = len(configurations)*len(manifest['currents'])
    print(f'{len(configurations)} widths, {len(manifest["currents"])} currents: {requested} candidate simulations plus {len(manifest["currents"])} original-format references.',flush=True)
    for row in budgets['shared_types']:
        print(f"{row['baseline_q']}: observed I={row['observed_integer_bits']}, allocated I={row['allocated_integer_bits']} including sign and headroom",flush=True)
    if arguments.prepare_only:
        report(output,manifest)
        return 0
    executable,original = study.build(output/'build',arguments.gcc)
    candidate_count,reference_count = 0,0
    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        for current in manifest['currents']:
            stimulus = output/'stimuli'/f'current_{current:04d}.txt'
            stimulus.parent.mkdir(exist_ok=True)
            if not stimulus.is_file():
                stimulus.write_text(f'{arguments.steps}\n'+''.join(f'{current*256 if 60000<=step<=140000 else 0}\n' for step in range(arguments.steps)))
            reference,saved,cached = prepare_reference(output,current,manifest,executable,original,stimulus,arguments.resume)
            reference_count += 1
            print(f'Reference {reference_count}/{len(manifest["currents"])} | {current} pA | exact original-C match | {"saved" if cached else "new"}',flush=True)
            futures = {executor.submit(evaluate,output,candidate,current,manifest,executable,stimulus,reference,arguments.resume):candidate for candidate in configurations}
            for future in as_completed(futures):
                saved,cached = future.result()
                candidate_count += 1
                row = saved['summary']
                print(f"[{candidate_count}/{requested}] {row['configuration']} | {current} pA | overflow {row['overflow_count']} | zero constants {row['zero_constants']} | Vmem RMSE {row['baseline_voltage_rmse']:.5g} | {'saved' if cached else 'new'}",flush=True)
                study.save_json(output/'progress.json',dict(status='running',candidate_runs_processed=candidate_count,requested_candidate_runs=requested,references_processed=reference_count,last_configuration=row['configuration'],last_current_pa=current),best_effort=True)
    report(output,manifest)
    study.save_json(output/'progress.json',dict(status='complete',completed_candidate_runs=candidate_count,requested_candidate_runs=requested,completed_reference_runs=reference_count),best_effort=True)
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print(f'Fixed-integer study failed: {error}',file=sys.stderr,flush=True)
        raise SystemExit(2)
