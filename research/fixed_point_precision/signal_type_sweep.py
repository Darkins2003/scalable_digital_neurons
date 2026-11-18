from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import precision_support as study
import run_fixed_integer_study as runner


SIGNAL_TYPES = {'state': ('state',), 'constant': ('constant',), 'timestep': ('timestep',), 'matrix': ('matrix',), 'current': ('current',), 'triangle': ('triangle',)}
TYPE_LABELS = {'state': 'State', 'constant': 'Constant', 'timestep': 'Timestep', 'matrix': 'Matrix', 'current': 'Current / voltage derivatives', 'triangle': 'Triangle', 'shared': 'State / constant / timestep (previous combined sweep)'}


def make_configurations(integer_bits):
    configurations = [dict(name='type_individual_baseline_w32',stage='signal_type',width=32,signal_type='baseline',formats={group:(32,32-integer_bits[group]) for group in study.GROUPS})]
    for signal_type, groups in SIGNAL_TYPES.items():
        minimum = max(integer_bits[group] for group in groups)
        for width in range(31,minimum-1,-1):
            formats = {group:(width if group in groups else 32,(width if group in groups else 32)-integer_bits[group]) for group in study.GROUPS}
            configurations.append(dict(name=f'type_{signal_type}_w{width:02d}',stage='signal_type',width=width,signal_type=signal_type,formats=formats))
    return configurations


def run(output, workers=4, compiler='gcc', resume=False, prepare_only=False):
    parent = json.loads((output/'manifest.json').read_text())
    content = {key:value for key,value in parent.items() if key!='fingerprint'}
    if hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()!=parent['fingerprint']:
        raise ValueError('Existing precision manifest checksum mismatch')
    if parent['steps']!=190000 or parent['pulse_start']!=60000 or parent['pulse_end']!=140000:
        raise ValueError('Signal-type sweep requires the complete 190 ms experiment')
    for path in (runner.DIRECTORY/'precision_model.c',study.REFERENCE,study.HELPER,study.MODEL,study.TABLE):
        relative = str(path.relative_to(study.PROJECT))
        if parent['source_sha256'].get(relative)!=study.digest(path):
            raise ValueError(f'Numerical source differs from the existing sweep: {relative}')
    configurations = make_configurations(parent['budgets']['group_integer_bits'])
    arguments = SimpleNamespace(currents=[80],steps=190000,gcc=compiler,keep_traces=False)
    manifest = runner.make_manifest(arguments,parent['budgets'],configurations)
    manifest.pop('fingerprint')
    manifest['study'] = 'One signal type at a time, 80 pA, down to zero fractional bits'
    manifest['parent_fingerprint'] = parent['fingerprint']
    manifest['source_sha256'][str(Path(__file__).relative_to(study.PROJECT))] = study.digest(Path(__file__))
    manifest['fingerprint'] = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    destination = output/'individual_signal_type_sweep'
    manifest_path = destination/'manifest.json'
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text())
        if previous['fingerprint']!=manifest['fingerprint']:
            raise ValueError('Signal-type sweep settings or sources changed; preserve the existing results and use a separate output')
        if not resume and not prepare_only:
            raise ValueError('Signal-type results already exist; use --resume')
    destination.mkdir(parents=True,exist_ok=True)
    study.save_json(manifest_path,manifest)
    runner.write_plan(destination,manifest)
    print(f'Signal-type sweep: {len(configurations)} unique candidates at 80 pA; other signal types stay at 32 bits.',flush=True)
    if prepare_only:
        return
    executable, original = study.build(destination/'build',compiler)
    stimulus = destination/'stimuli/current_0080.txt'
    stimulus.parent.mkdir(exist_ok=True)
    stimulus.write_text('190000\n'+''.join('20480\n' if 60000<=step<=140000 else '0\n' for step in range(190000)),encoding='utf-8')
    reference, saved, cached = runner.prepare_reference(destination,80,manifest,executable,original,stimulus,resume)
    print('80 pA reference verified against original C.',flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(runner.evaluate,destination,candidate,80,manifest,executable,stimulus,reference,resume):candidate for candidate in configurations}
        for completed, future in enumerate(as_completed(futures),1):
            saved, cached = future.result()
            row = saved['summary']
            print(f"[{completed}/{len(configurations)}] {row['configuration']} | overflow {row['overflow_count']} | zero constants {row['zero_constants']} | Vmem RMSE {row['baseline_voltage_rmse']:.5g} | {'saved' if cached else 'new'}",flush=True)
            study.save_json(destination/'progress.json',dict(status='running',completed=completed,total=len(configurations),last_configuration=row['configuration']),best_effort=True)
    study.save_json(destination/'progress.json',dict(status='complete',completed=len(configurations),total=len(configurations)),best_effort=True)
