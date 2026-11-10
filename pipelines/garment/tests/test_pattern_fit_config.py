"""pattern_fit 설정 경로 해석과 목표 sample 읽기 (GarmentCode 없이 도는 부분만)."""
import json
from pathlib import Path

import pytest

import pattern_fit as pf

CFG = pf.REPO_ROOT / 'pipelines' / 'garment' / 'configs' / 'pattern_fit_v0.json'


def test_repo_root_is_repository():
    assert (pf.REPO_ROOT / 'pipelines' / 'garment' / 'pattern_fit.py').is_file()


def test_relative_path_resolves_against_repo_root_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # 실제 실행은 cwd = GarmentCode 루트
    assert pf.resolve_repo_path('samples/garment_v1.json') == (pf.REPO_ROOT / 'samples' / 'garment_v1.json').resolve()


def test_absolute_path_kept(tmp_path):
    p = tmp_path / 'x.yaml'
    assert pf.resolve_repo_path(str(p)) == p


@pytest.mark.parametrize('key', pf.CFG_PATH_KEYS)
@pytest.mark.parametrize('bad', [None, ''])
def test_missing_or_empty_path_is_error(key, bad):
    cfg = {k: 'a' for k in pf.CFG_PATH_KEYS}
    cfg[key] = bad
    with pytest.raises(ValueError):
        pf.resolve_config(cfg)
    del cfg[key]
    with pytest.raises(ValueError):
        pf.resolve_config(cfg)


def test_shipped_config_targets_are_repo_relative():
    cfg = json.loads(CFG.read_text(encoding='utf-8'))
    assert not Path(cfg['targets_json']).is_absolute()
    assert 'FIT_RULER' not in cfg['targets_json']
    resolved = pf.resolve_config(cfg)
    assert Path(resolved['targets_json']).is_file()
    assert resolved['tolerance_cm'] == 1.0  # 명세서 6장 초기 목표. 완화하지 않는다


def test_targets_read_from_common_sample_without_change():
    cfg = pf.resolve_config(json.loads(CFG.read_text(encoding='utf-8')))
    targets, sample = pf.load_targets(cfg['targets_json'])
    raw = json.loads(Path(cfg['targets_json']).read_text(encoding='utf-8'))
    assert targets == {f: raw['measurements'].get(f) for f in pf.FIELDS}
    meta = pf.target_meta(sample)
    assert meta['waist_girth_cm'] == raw['measurements'].get('waist_girth_cm')
    assert meta['waist_position_matched'] == raw['measurement_meta'].get('waist_position_matched')
    assert meta['waist_fitted'] is False  # 허리는 C3b 전까지 맞춤 대상이 아니다
    assert isinstance(meta['is_measured'], bool)
    assert meta['source_ref']


def test_target_meta_missing_values_are_none():
    meta = pf.target_meta({'measurements': {}, 'measurement_meta': {}})
    assert meta['waist_girth_cm'] is None and meta['is_measured'] is None and meta['source_ref'] is None
