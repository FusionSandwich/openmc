"""Plot retained cold-query measurements; no transport qualification inference."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    paths = {phase: args.raw / f'cold-{phase}-16-01/campaign.json' for phase in ('off', 'on')}
    campaigns = {phase: json.loads(path.read_text()) for phase, path in paths.items()}
    assert all(c['block_valid'] for c in campaigns.values())
    measured = {}
    for phase, campaign in campaigns.items():
        measured[phase] = {}
        for mode in range(3):
            values = [statistics.mean(r['ns'] for r in a['rows']) for a in campaign['attempts']
                      if a['phase'] == 'measured' and a['mode'] == mode and a['valid']]
            assert len(values) == 7
            measured[phase][str(mode)] = dict(values_ns=values, median_ns=statistics.median(values),
                iqr_ns=np.quantile(values, [.25, .75]).tolist(),
                filter_metrics=campaign['aggregates'][str(mode)]['filter_metrics'])
    before = json.loads((args.raw/'torus-sentinel-before-01.json').read_text())
    after = json.loads((args.raw/'torus-sentinel-after-01.json').read_text())
    sentinel = {}
    for name, records in [('before', before), ('after', after)]:
        values = [r['result']['ns_per_query'] for r in records if not r['warmup']]
        sentinel[name] = dict(values_ns=values, median_ns=statistics.median(values),
            cv=statistics.stdev(values)/statistics.mean(values))
    summary = dict(campaign_sha256={phase: hashlib.sha256(p.read_bytes()).hexdigest()
        for phase, p in paths.items()}, measured=measured, sentinel=sentinel,
        ratios=campaigns['off']['paired_ratios'],
        ratio_definition='median baseline bank-mean ns/query / median changed bank-mean ns/query',
        instrumentation_note='ON/OFF are separate blocks; their median ratio is descriptive, not paired overhead qualification',
        scope='16 unique circular nonplanar tube rays, no application memoization; 7 repetitions per mode; no transport or matched Embree ratio')
    summary['off_median_ratios'] = {str(m): measured['off']['0']['median_ns']/measured['off'][str(m)]['median_ns'] for m in (1, 2)}
    summary['on_off_descriptive_ratios'] = {str(m): measured['on'][str(m)]['median_ns']/measured['off'][str(m)]['median_ns'] for m in range(3)}
    (args.output/'fast_path_03.json').write_text(json.dumps(summary, indent=2)+'\n')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout='constrained')
    labels = ['Exact reference', 'Bounds only', 'Bounds + local solve']
    colors = ['#637486', '#b48540', '#167b75']
    for m in range(3):
        values = np.asarray(measured['off'][str(m)]['values_ns'])/1.e6
        axes[0].scatter(np.full(7, m)+np.linspace(-.06, .06, 7), values, color=colors[m], s=22)
        axes[0].hlines(np.median(values), m-.22, m+.22, color=colors[m], linewidth=3)
    axes[0].set(xticks=range(3), xticklabels=labels, ylabel='Mean per-query cost within bank (ms; log scale)',
                title='Seven measured repetitions, counters OFF', yscale='log')
    axes[0].tick_params(axis='x', labelsize=9)
    data = campaigns['off']['aggregates']['2']['per_category_ns_distribution']
    names = ['bbox_miss', 'bbox_intersect_physical_miss', 'inside_exit', 'near_normal_entry', 'rigid_transform', 'seam_grazing']
    short = ['Box miss', 'Local miss', 'Inside exit', 'Near entry', 'Transformed', 'Seam/grazing']
    medians = [data[n]['median']/1.e6 for n in names]
    tails = [data[n]['p95']/1.e6 for n in names]
    axes[1].scatter(medians, range(6), label='Median', color=colors[2])
    axes[1].scatter(tails, range(6), label='P95', color=colors[1], marker='|', s=120)
    axes[1].set(yticks=range(6), yticklabels=short, xlabel='Query cost (ms; log scale)',
                title='Changed solver: retained category costs', xscale='log')
    axes[1].invert_yaxis()
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(axis='x' if ax is axes[1] else 'y', alpha=.2)
    fig.suptitle('StellarCSG cold circular-tube distance experiment', fontsize=14)
    fig.savefig(args.output/'fast_path_03.png', dpi=160)
    print(json.dumps({k: summary[k] for k in ['off_median_ratios','on_off_descriptive_ratios','sentinel']}, indent=2))


if __name__ == '__main__':
    main()
