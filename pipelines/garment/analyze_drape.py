"""착장 결과를 Blender 없이 다시 계산하고, 신장·봉제선 벌어짐이 큰 곳을 패널·봉제선별로 요약한다.

같은 메시에 같은 결과가 나오는지 보려고 blender_drape.py와 같은 metrics.evaluate를 쓴다.
침투의 부호 거리는 Blender BVH 결과(drape_trace.json)를 그대로 받는다.

사용: python analyze_drape.py <run_dir> [--config <drape_vN.json>]
    run_dir 안의 drape_input.json, garment_draped_co.npy, drape_trace.json, drape_metrics.json을 읽어
    analysis.json을 쓴다.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
from drape_config import load_config  # noqa: E402

COMPARED_KEYS = ('stable_last10_median_mm', 'stable_ok', 'penetration_area_ratio', 'penetration_ok',
                 'penetration_status', 'penetration_unknown_faces', 'stretch_max', 'stretch_p99',
                 'stretch_ok', 'nan', 'seam_gap_max_mm', 'seam_gap_median_mm', 'drape_ok')


def analyze(run_dir, config_path=None):
    run_dir = Path(run_dir).resolve()
    data = json.loads((run_dir / 'drape_input.json').read_text(encoding='utf-8'))
    blender_result = json.loads((run_dir / 'drape_metrics.json').read_text(encoding='utf-8'))
    trace = json.loads((run_dir / 'drape_trace.json').read_text(encoding='utf-8'))
    co = np.load(run_dir / 'garment_draped_co.npy')
    cfg, cfg_rec = load_config(config_path or blender_result['config']['path'])
    if cfg_rec['sha256'] != blender_result['config']['sha256']:
        raise ValueError('config sha256 differs from the one used in Blender run')
    th = cfg['thresholds']

    g = data['garment']
    rest = np.asarray(g['vertices'])
    assert len(co) == len(rest), (len(co), len(rest))
    sd = np.asarray(trace['signed_dist_m'], dtype=float)
    offline = metrics.evaluate(rest, g['faces'], co, g['stitch_pairs'], trace['disp_median_m_per_frame'],
                               sd, data['body']['is_watertight'], th)
    mismatch = {k: [blender_result[k], offline[k]] for k in COMPARED_KEYS if blender_result[k] != offline[k]}

    names = [p['name'] for p in g['panels']]
    panels, worst = metrics.per_panel_stretch(rest, g['faces'], co, g['panel_of_vertex'], names,
                                              th['stretch_ratio_max'])
    stitches = metrics.per_stitch_gap(co, g['stitch_pairs'], g['panel_of_vertex'], names)
    out = {
        'config': cfg_rec,
        'offline_metrics': offline,
        'matches_blender_metrics': not mismatch,
        'mismatch': mismatch,
        'stretch_by_panel': panels,
        'worst_stretch_edge_xyz_m': worst,
        'seam_gap_by_stitch': stitches,
    }
    (run_dir / 'analysis.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--config')
    args = ap.parse_args()
    out = analyze(args.run_dir, args.config)
    print('matches blender metrics:', out['matches_blender_metrics'], out['mismatch'])
    print('stretch by panel (limit', out['config']['name'], '):')
    for p in out['stretch_by_panel']:
        print(f"  {p['panel']:16s} max {p['stretch_max']}  over {p['n_over_limit']} of {p['n_edges']}")
    print('worst edge xyz m:', out['worst_stretch_edge_xyz_m'])
    print('seam gap by stitch (mm):')
    for s in out['seam_gap_by_stitch']:
        print(f"  stitch {s['stitch']:2d} {s['panel_1']:>16s} - {s['panel_2']:<16s} "
              f"max {s['gap_max_mm']:6.2f}  median {s['gap_median_mm']:5.2f}  n {s['n_pairs']}")


if __name__ == '__main__':
    main()
