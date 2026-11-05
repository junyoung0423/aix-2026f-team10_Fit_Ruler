"""GarmentCode 티셔츠 패턴을 SKU 목표 실측에 맞춘다 (명세서 6장 '패턴 최적화', T02).

- 패턴 생성용 몸은 설정의 body_yaml 하나로 고정한다(mean_all). 사용자 몸으로 다시 만들지 않는다(R06).
- 디자인 파라미터(몸 치수 대비 비율)만 yaml range 안에서 바꾼다.
- 목표: samples/garment_v1.json measurements. null 항목은 맞추지 않는다(0으로 채우지 않음).
- 판정: 항목마다 |패턴 재측정 - 목표| <= tolerance_cm (명세서 6장 초기 목표 1.0 cm). 기준을 바꾸지 않는다.
- 패턴 자기 교차는 실패.

실행 (cwd = GarmentCode 루트, PYTHONPATH = GarmentCode 루트):
    python pattern_fit.py sensitivity <fit_config.json> <out_dir>
    python pattern_fit.py fit <fit_config.json> <out_dir>
    python pattern_fit.py generate <design.yaml> <body.yaml> <out_dir>

고정 패턴은 fit 프로세스 안에서 만든 패턴을 쓰지 않고, 고정한 디자인 yaml로 새 프로세스에서 generate 한다.
한 프로세스에서 패턴을 여러 번 만들면 봉제선 목록 순서가 바뀔 수 있다(기하·봉제선 집합은 같음, C3에서 확인).
"""
import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pattern_measure as pm  # noqa: E402

FIELDS = ('chest_girth_cm', 'shoulder_width_cm', 'sleeve_length_cm', 'body_length_cm')


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get_param(design, dotted):
    d = design
    for k in dotted.split('.'):
        d = d[k]
    return d


def set_value(design, dotted, value):
    p = get_param(design, dotted)
    p['v'] = int(round(value)) if p.get('type') == 'int' else float(value)


class Generator:
    """GarmentCode MetaGarment로 패턴을 메모리에서 만든다. 같은 입력이면 같은 패턴(C3에서 확인)."""

    def __init__(self, body_yaml, design_yaml):
        from assets.bodies.body_params import BodyParameters
        from assets.garment_programs.meta_garment import MetaGarment
        self.MetaGarment = MetaGarment
        self.body = BodyParameters(str(body_yaml))
        self.base = yaml.safe_load(Path(design_yaml).read_text(encoding='utf-8'))['design']
        self.calls = 0

    def design_with(self, values):
        d = copy.deepcopy(self.base)
        for k, v in values.items():
            set_value(d, k, v)
        return d

    def generate(self, values):
        self.calls += 1
        design = self.design_with(values)
        garment = self.MetaGarment('t-shirt', self.body, design)
        pattern = garment.assembly()
        selfint = bool(garment.is_self_intersecting()) or bool(pattern.is_self_intersecting())
        return pattern, design, selfint

    def measure(self, values):
        pattern, design, selfint = self.generate(values)
        m, detail = pm.measure(pattern.pattern)
        return m, detail, selfint, pattern, design


def load_targets(sample_path):
    s = json.loads(Path(sample_path).read_text(encoding='utf-8'))
    meas = s['measurements']
    return {f: meas.get(f) for f in FIELDS}, s


def cmd_sensitivity(cfg, out):
    gen = Generator(cfg['body_yaml'], cfg['design_yaml'])
    base_m, _, base_si, _, _ = gen.measure({})
    rows = []
    for name in cfg['sensitivity_params']:
        p = get_param(gen.base, name)
        lo, hi = p['range']
        v0 = p['v']
        step = cfg['sensitivity_step_frac'] * (hi - lo)
        if p.get('type') == 'int':
            step = max(1, round(step))
        v1 = v0 + step if v0 + step <= hi else v0 - step
        m1, _, si, _, _ = gen.measure({name: v1})
        d = {f: round((m1[f] - base_m[f]) / (v1 - v0) * (hi - lo), 3) for f in FIELDS}
        rows.append({'param': name, 'v0': v0, 'v1': v1, 'range': [lo, hi], 'self_intersecting': si,
                     'delta_cm_over_full_range(linearized)': d})
        print(name, v0, '->', v1, d, 'selfint' if si else '', flush=True)
    res = {'base_measurements': base_m, 'base_self_intersecting': base_si, 'rows': rows}
    (out / 'sensitivity.json').write_text(json.dumps(res, indent=2), encoding='utf-8')


def cmd_fit(cfg, cfg_path, out):
    t0 = time.time()
    targets, sample = load_targets(cfg['targets_json'])
    tol = cfg['tolerance_cm']
    gen = Generator(cfg['body_yaml'], cfg['design_yaml'])
    params = cfg['fit_params']  # {dotted: 맞추는 측정 항목}
    names = list(params)
    bounds = [get_param(gen.base, n)['range'] for n in names]
    x0 = np.array([get_param(gen.base, n)['v'] for n in names], float)
    fitted_fields = [f for f in params.values() if targets[f] is not None]

    base_m, _, base_si, _, _ = gen.measure({})
    history = []

    def resid(x):
        m, _, si, _, _ = gen.measure(dict(zip(names, x)))
        r = np.array([m[f] - targets[f] for f in fitted_fields])
        history.append({'x': x.round(6).tolist(), 'resid': r.round(4).tolist(), 'self_intersecting': si})
        return r

    sol = least_squares(resid, x0, bounds=(np.array([b[0] for b in bounds]), np.array([b[1] for b in bounds])),
                        diff_step=cfg['diff_step'], xtol=1e-10, ftol=1e-10, gtol=1e-10, max_nfev=cfg['max_nfev'])
    values = dict(zip(names, [float(v) for v in sol.x]))
    m, detail, selfint, pattern, design = gen.measure(values)

    report = {}
    for f in FIELDS:
        tgt = targets[f]
        if tgt is None:
            report[f] = {'target': None, 'pattern': round(m[f], 3), 'error': None, 'ok': None,
                         'reason': 'target null'}
            continue
        err = m[f] - tgt
        ok = abs(err) <= tol
        report[f] = {'target': tgt, 'pattern': round(m[f], 3), 'default_pattern': round(base_m[f], 3),
                     'error': round(err, 3), 'ok': ok, 'controlled_by': [n for n, ff in params.items() if ff == f] or None}
    at_bound = {n: (abs(values[n] - b[0]) < 1e-6 or abs(values[n] - b[1]) < 1e-6) for n, b in zip(names, bounds)}
    all_ok = all(r['ok'] for r in report.values() if r['ok'] is not None) and not selfint

    out.mkdir(parents=True, exist_ok=True)
    (out / 'design_fitted.yaml').write_text(yaml.safe_dump({'design': design}, allow_unicode=True, sort_keys=False),
                                            encoding='utf-8')
    result = {
        'status': 'FITTED' if all_ok else 'FIT_FAILED',
        'tolerance_cm': tol,
        'measurements': report,
        'fitted_params': values,
        'params_at_bound': at_bound,
        'self_intersecting': selfint,
        'default_self_intersecting': base_si,
        'detail': detail,
        'optimizer': {'method': 'scipy.optimize.least_squares (trf, bounds = yaml range)',
                      'nfev': int(sol.nfev), 'status': int(sol.status), 'message': sol.message,
                      'generator_calls': gen.calls, 'seconds': round(time.time() - t0, 1)},
        'fit_config': {'path': str(cfg_path), 'sha256': sha256_file(cfg_path), 'name': cfg['name'], 'version': cfg['version']},
        'inputs': {'body_yaml': cfg['body_yaml'], 'body_yaml_sha256': sha256_file(cfg['body_yaml']),
                   'design_yaml': cfg['design_yaml'], 'design_yaml_sha256': sha256_file(cfg['design_yaml']),
                   'targets_json': cfg['targets_json'], 'targets_json_sha256': sha256_file(cfg['targets_json']),
                   'targets_source': sample['measurement_meta'].get('source'),
                   'targets_is_measured': sample['measurement_meta'].get('is_measured')},
        'history': history,
    }
    (out / 'fit_result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'measurements', 'fitted_params', 'params_at_bound',
                                              'self_intersecting')}, indent=2, ensure_ascii=False))
    print('optimizer', result['optimizer'])


def cmd_generate(design_yaml, body_yaml, out):
    """고정 디자인 yaml + 몸 yaml -> 패턴 파일(새 프로세스에서 한 번). 측정값도 남긴다."""
    gen = Generator(body_yaml, design_yaml)
    pattern, _, selfint = gen.generate({})
    m, detail = pm.measure(pattern.pattern)
    pattern.name = 'pattern'
    pattern.serialize(str(out), tag='', to_subfolder=False, with_3d=False, with_text=False,
                      view_ids=False, with_printable=False)
    res = {'measurements_cm': m, 'detail': detail, 'self_intersecting': selfint,
           'design_yaml': str(design_yaml), 'design_yaml_sha256': sha256_file(design_yaml),
           'body_yaml': str(body_yaml), 'body_yaml_sha256': sha256_file(body_yaml),
           'pattern_sha256': {p.name: sha256_file(p) for p in sorted(out.glob('pattern_*'))}}
    (out / 'generate_result.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
    print(json.dumps(res, indent=2))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        ap = argparse.ArgumentParser()
        ap.add_argument('cmd')
        ap.add_argument('design_yaml')
        ap.add_argument('body_yaml')
        ap.add_argument('out_dir')
        a = ap.parse_args()
        out = Path(a.out_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        cmd_generate(Path(a.design_yaml).resolve(), Path(a.body_yaml).resolve(), out)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['sensitivity', 'fit'])
    ap.add_argument('config')
    ap.add_argument('out_dir')
    a = ap.parse_args()
    cfg_path = Path(a.config).resolve()
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    out = Path(a.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == 'sensitivity':
        cmd_sensitivity(cfg, out)
    else:
        cmd_fit(cfg, cfg_path, out)


if __name__ == '__main__':
    main()
