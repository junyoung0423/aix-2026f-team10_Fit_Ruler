"""착장 지표 계산 (순수 numpy). 시뮬레이션과 분리해 같은 메시에 같은 결과를 낸다.

Blender 안(blender_drape.py)과 밖(analyze_drape.py, 테스트)에서 같은 함수를 쓴다.
침투 검사의 '면 중심 -> 몸 표면 부호 거리'만 Blender BVH로 구하고, 비율 계산은 여기서 한다.

기준값은 함수 인자(설정 파일 thresholds 블록)로만 받는다. 이 파일에 수치 기준을 두지 않는다.
"""
import numpy as np


def triangles(faces):
    """면 목록에서 삼각형만 (M, 3) 배열로. 삼각형이 아닌 면 수도 돌려준다."""
    tris = [fc for fc in faces if len(fc) == 3]
    return np.asarray(tris, dtype=int).reshape(-1, 3), len(faces) - len(tris)


def unique_edges(tris):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


def edge_stretch(rest, cur, tris):
    """면의 변 기준 신장 비율(현재 길이 / 원래 길이). 봉제 loose edge는 면이 아니므로 제외된다."""
    rest, cur = np.asarray(rest, float), np.asarray(cur, float)
    e = unique_edges(tris)
    rest_len = np.linalg.norm(rest[e[:, 0]] - rest[e[:, 1]], axis=1)
    cur_len = np.linalg.norm(cur[e[:, 0]] - cur[e[:, 1]], axis=1)
    return e, cur_len / np.maximum(rest_len, 1e-9)


def seam_gaps(cur, stitch_pairs):
    """봉제 쌍(a, b, stitch_id)의 남은 거리(m)."""
    p = np.asarray(stitch_pairs, dtype=int).reshape(-1, 3)
    cur = np.asarray(cur, float)
    return np.linalg.norm(cur[p[:, 0]] - cur[p[:, 1]], axis=1)


def frame_displacement_median(prev, cur):
    return float(np.median(np.linalg.norm(np.asarray(cur, float) - np.asarray(prev, float), axis=1)))


def stable_median(disp_hist, window):
    """마지막 window 프레임의 '프레임별 정점 이동량 중앙값'의 중앙값. 기록이 모자라면 None."""
    if len(disp_hist) < window:
        return None
    return float(np.median(np.asarray(disp_hist[-window:], float)))


def tri_areas(v, tris):
    v = np.asarray(v, float)
    a, b, c = v[tris[:, 0]], v[tris[:, 1]], v[tris[:, 2]]
    return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)


def face_centers(v, tris):
    return np.asarray(v, float)[tris].mean(axis=1)


def penetration(areas, signed_dist, depth_m, body_closed):
    """몸 내부로 depth_m보다 깊은 면적 비율.

    signed_dist: 면 중심의 몸 표면 부호 거리(바깥 +), 판정 못한 면은 NaN.
    몸 메시가 닫혀 있지 않거나 판정 못한 면이 있으면 status='UNVERIFIABLE'(명세서 6장 '검증 불가').
    """
    signed_dist = np.asarray(signed_dist, float)
    areas = np.asarray(areas, float)
    unknown = int(np.isnan(signed_dist).sum())
    deep = np.nan_to_num(signed_dist, nan=0.0) < -depth_m
    ratio = float(areas[deep].sum() / areas.sum())
    status = 'OK' if (body_closed and unknown == 0) else 'UNVERIFIABLE'
    return ratio, unknown, status


def evaluate(rest, faces, cur, stitch_pairs, disp_hist, signed_dist, body_closed, thresholds):
    """명세서 6장 착장 검사. 키·반올림은 시험 스크립트(runs/tee_test) 결과와 같게 유지한다."""
    th = thresholds
    tris, n_non_tri = triangles(faces)
    cur = np.asarray(cur, float)
    has_nan = bool(np.isnan(cur).any())

    _, stretch = edge_stretch(rest, cur, tris)
    st = stable_median(disp_hist, th['stable_window_frames'])
    pen_ratio, unknown, pen_status = penetration(
        tri_areas(cur, tris), signed_dist, th['penetration_depth_m'], body_closed)
    gap = seam_gaps(cur, stitch_pairs)

    stable_ok = st is not None and st <= th['stable_median_m_per_frame']
    result = {
        'stable_last10_median_mm': None if st is None else round(st * 1000, 3),
        'stable_ok': stable_ok,
        'penetration_area_ratio': round(pen_ratio, 4),
        'penetration_ok': pen_status == 'OK' and pen_ratio <= th['penetration_area_ratio_max'],
        'penetration_status': pen_status,
        'penetration_unknown_faces': unknown,
        'stretch_max': round(float(stretch.max()), 3),
        'stretch_p99': round(float(np.percentile(stretch, 99)), 3),
        'stretch_ok': float(stretch.max()) <= th['stretch_ratio_max'],
        'nan': has_nan,
        'seam_gap_max_mm': round(float(gap.max()) * 1000, 2),
        'seam_gap_median_mm': round(float(np.median(gap)) * 1000, 2),
        'non_triangle_faces': n_non_tri,
    }
    result['drape_ok'] = (result['stable_ok'] and result['penetration_ok']
                          and result['stretch_ok'] and not has_nan)
    return result


def per_panel_stretch(rest, faces, cur, panel_of_vertex, panel_names, limit):
    """패널별 최대 신장과 limit 초과 변 수 (분석용)."""
    tris, _ = triangles(faces)
    e, stretch = edge_stretch(rest, cur, tris)
    pov = np.asarray(panel_of_vertex)
    out = []
    for pi, name in enumerate(panel_names):
        m = pov[e[:, 0]] == pi
        out.append({'panel': name,
                    'stretch_max': round(float(stretch[m].max()), 3) if m.any() else None,
                    'n_over_limit': int((m & (stretch > limit)).sum()),
                    'n_edges': int(m.sum())})
    worst = e[int(np.argmax(stretch))]
    return out, np.asarray(cur, float)[worst].round(3).tolist()


def per_stitch_gap(cur, stitch_pairs, panel_of_vertex, panel_names):
    """봉제선별 남은 거리 (분석용)."""
    p = np.asarray(stitch_pairs, dtype=int).reshape(-1, 3)
    gap = seam_gaps(cur, p)
    pov = np.asarray(panel_of_vertex)
    out = []
    for sid in np.unique(p[:, 2]):
        m = p[:, 2] == sid
        a, b = p[m][0, 0], p[m][0, 1]
        out.append({'stitch': int(sid), 'panel_1': panel_names[pov[a]], 'panel_2': panel_names[pov[b]],
                    'gap_max_mm': round(float(gap[m].max()) * 1000, 2),
                    'gap_median_mm': round(float(np.median(gap[m])) * 1000, 2),
                    'n_pairs': int(m.sum())})
    return out
