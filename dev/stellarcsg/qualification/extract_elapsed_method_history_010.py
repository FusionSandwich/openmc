"""Extract recorded elapsed seconds; never infer time from a calculation rate."""

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path


def median(values):
    values = list(values)
    if not values:
        return None
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError('Invalid recorded elapsed time')
    return statistics.median(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    rows, artifacts = [], []
    archived = 'openmc-stellarcsg-composite/dev/stellarcsg/benchmarks/raw/'

    def read(relative):
        content = (args.workspace / relative).read_bytes()
        artifacts.append({'path': relative, 'sha256': hashlib.sha256(content).hexdigest()})
        return json.loads(content)

    def add(artifact, family, method, histories, repetitions, **fields):
        rows.append(dict(artifact=artifact, family=family, method=method,
                         histories_per_run=histories, observations=repetitions,
                         cold_geometry_build_s=None, **fields))

    relative = archived + 'composite_blanket_interop/c0_coil_controls.json'
    data = read(relative)
    for case in data['cases']:
        raw = [item for item in case['raw'] if not item['warmup']]
        if len(raw) != data['measured_repetitions']:
            raise ValueError('Unexpected C0 measured repetition count')
        add(relative, 'analytic circular coil', case['case'], data['histories'], len(raw),
            initialization_s=median(item['initialization_time_s'] for item in raw),
            transport_s=median(item['transport_time_s'] for item in raw),
            process_wall_s=None, measurement='median measured runs, warmup excluded',
            raw_lost_particles=[item['lost_particles'] for item in raw],
            original_record_commit='1f2d53a537337616f4e87bc48ad573cc4f0bc509')

    relative = archived + 'wistell_coil_set_openmc_20260831.json'
    data = read(relative)
    for name, case in data['results'].items():
        raw = [item for item in case['raw'] if not item['warmup']]
        if len(raw) != data['measured_repetitions']:
            raise ValueError('Unexpected coil-set measured repetition count')
        add(relative, '48 WISTELL circular 1 cm tubes', name,
            data['histories_per_repetition'], len(raw),
            initialization_s=median(item['initialization_time_s'] for item in raw),
            transport_s=median(item['transport_time_s'] for item in raw),
            process_wall_s=median(item['wall_time_s'] for item in raw),
            raw_return_codes=[item['return_code'] for item in raw],
            measurement='median measured runs, warmup excluded',
            original_record_commit='1353d0ae5d2d64422cc7dd8a6f144cdabfa0d000',
            original_binary=data['binary'])

    relative = archived + 'wistell_coil_span_vs_dagmc_20260831.json'
    data = read(relative)
    for case in data['results']:
        add(relative, 'WISTELL representative coil031', case['method'],
            data['protocol']['particles_per_repetition'], len(case['transport_time_s']),
            initialization_s=None, transport_s=median(case['transport_time_s']),
            process_wall_s=None, measurement='median recorded transport array')

    relative = archived + 'wistell_openmc_patch_vs_fine_mesh_20260831.json'
    data = read(relative)
    for name in ('native_csg', 'fine_direct_dagmc'):
        case = data[name]
        add(relative, 'historical general WISTELL plasma', name,
            data['histories_per_repetition'], len(case['transport_s_raw']),
            initialization_s=None, transport_s=median(case['transport_s_raw']),
            process_wall_s=None, measurement='median recorded transport array',
            original_record_commit='4e97b2480489e27c1939554bbab1750ebcf551a5',
            binary_sha256=data['binary_sha256'], library_sha256=data['libopenmc_sha256'],
            geometry_payload_sha256=data['native_source_sha256'],
            geometry_payload='csg_surface.h5',
            payload_metadata_note='Raw native_source_sha256 names geometry HDF5, not C++ source')

    for fixture, name in (('p00-magnet-material-bank-02', 'priority components'),
                          ('p00-magnet-union-bank-01', 'common-material union')):
        relative = ('stellarcsg-local-continuation-20260925/dev/stellarcsg/reports/'
                    f'local-cont-20260925/{fixture}/receipt.json')
        data = read(relative)
        text = data['run']['stdout_tail']

        def recorded_timer(label):
            found = re.search(re.escape(label) + r'\s*=\s*([0-9.eE+-]+) seconds', text)
            return float(found.group(1)) if found else None

        add(relative, 'derived periodic P00 faceted winding-pack candidate', name, data['histories'], 1,
            initialization_s=recorded_timer('Total time for initialization'),
            transport_s=recorded_timer('Time in transport only'), process_wall_s=None,
            native_total_timer_s=recorded_timer('Total time elapsed'),
            raw_return_codes=[data['run']['exit_code']],
            measurement='single material-entry/track validation; not production speed acceptance')

    for name in ('cache', 'flat_ring'):
        relative = ('stellarcsg-astra-kernel-20260926/dev/stellarcsg/reports/'
                    f'coil-profile-20260926/meaningful-coil-009/{name}/receipt.json')
        data = read(relative)
        add(relative, 'current round-tube diagnostic', name, data['completed_histories'], 1,
            initialization_s=data['initialization_seconds'], transport_s=data['transport_seconds'],
            process_wall_s=data['external_process_wall_seconds'],
            measurement='one 20k tally-enabled pilot; different proxy shapes')

    relative = ('stellarcsg-astra-kernel-20260926/dev/stellarcsg/reports/'
                'plasma-best-time-20260926/transport-009-01/block-result.json')
    # The full plasma pilot record is preserved as evidence; its schema is owned
    # by that experiment, so this extractor does not guess missing timer keys.
    read(relative)
    result = dict(schema='stellarcsg.elapsed-method-history/v1', rows=rows,
                  artifacts=artifacts, unknown_policy='null means NOT_RECORDED, not zero',
                  ranking_policy='rank only within the same workload; no normalized or inferred times',
                  execution='metadata extraction only; no simulation/build',
                  plasma_20k_record=relative)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'rows': len(rows), 'artifacts': len(artifacts), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
