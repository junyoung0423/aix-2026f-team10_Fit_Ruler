"""Blender 봉제·착장 (명세서 6장 "사용자별 착장과 원본 렌더").

export_panels.py가 만든 drape_input.json과 설정 파일(configs/drape_vN.json)을 읽어
  1) 떨어진 패널 + 봉제선 loose edge로 옷 메시를 만들고
  2) 몸에 충돌, 옷에 천(봉제 스프링, 자기 충돌)을 설정한 뒤
  3) 처음 sew_frames 동안은 중력 없이 봉제하고, 이후 중력을 켜 안정화한다.
  4) metrics.py로 안정·침투·신장·NaN을 검사하고 (기준값은 설정 thresholds 블록)
  5) .blend, 옷 OBJ, 착장 좌표(.npy), 정면 확인 PNG, 지표 JSON을 저장한다.

시뮬레이션·재질·충돌 값은 모두 설정 파일에서 읽는다. 이 파일에 수치 상수를 두지 않는다.

사용:
    blender --background --python blender_drape.py -- <drape_input.json> <out_dir> <config.json> [max_frames]
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
from drape_config import load_config, sha256_file  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:]
    in_path, out_dir, cfg_path = Path(argv[0]).resolve(), Path(argv[1]).resolve(), Path(argv[2]).resolve()
    max_frames = int(argv[3]) if len(argv) > 3 else None
    return in_path, out_dir, cfg_path, max_frames


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mesh(name, verts, faces, edges=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, list(edges), faces)
    mesh.validate()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup_body(body, cfg):
    obj = make_mesh('body', body['vertices'], body['faces'])
    obj.modifiers.new('Collision', 'COLLISION')
    bc = cfg['body_collision']
    obj.collision.thickness_outer = bc['thickness_outer']
    obj.collision.cloth_friction = bc['cloth_friction']
    obj.color = tuple(cfg['preview']['body_rgba'])
    return obj


def setup_garment(g, cfg, max_frames):
    pairs = [(a, b) for a, b, _ in g['stitch_pairs']]
    obj = make_mesh('garment', g['vertices'], g['faces'], pairs)
    obj.data.shade_smooth()
    obj.color = tuple(cfg['preview']['garment_rgba'])

    cloth = obj.modifiers.new('Cloth', 'CLOTH')
    s = cloth.settings
    cc = cfg['cloth']
    s.quality = cc['quality']
    s.mass = cc['mass']
    s.air_damping = cc['air_damping']
    s.tension_stiffness = cc['tension_stiffness']
    s.compression_stiffness = cc['compression_stiffness']
    s.shear_stiffness = cc['shear_stiffness']
    s.bending_stiffness = cc['bending_stiffness']
    s.use_sewing_springs = cc['use_sewing_springs']
    s.sewing_force_max = cc['sewing_force_max']  # 0 = 제한 없음

    c = cloth.collision_settings
    col = cfg['cloth_collision']
    c.collision_quality = col['collision_quality']
    c.distance_min = col['distance_min']
    c.use_self_collision = col['use_self_collision']
    c.self_distance_min = col['self_distance_min']
    c.self_friction = col['self_friction']

    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = max_frames

    sch = cfg['schedule']
    ew = s.effector_weights
    ew.gravity = 0.0
    ew.keyframe_insert('gravity', frame=1)
    ew.keyframe_insert('gravity', frame=sch['sew_frames'])
    ew.gravity = 1.0
    ew.keyframe_insert('gravity', frame=sch['sew_frames'] + sch['gravity_ramp_frames'])
    return obj


def evaluated_coords(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = obj.evaluated_get(dg).to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    obj.evaluated_get(dg).to_mesh_clear()
    return co.reshape(-1, 3) @ np.asarray(obj.matrix_world)[:3, :3].T + np.asarray(obj.matrix_world)[:3, 3]


def simulate(garment, cfg, max_frames):
    th, sch = cfg['thresholds'], cfg['schedule']
    window = th['stable_window_frames']
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, max_frames
    prev = None
    disp_hist = []
    t0 = time.time()
    last = 1
    for f in range(1, max_frames + 1):
        scene.frame_set(f)
        co = evaluated_coords(garment)
        if prev is not None:
            disp_hist.append(metrics.frame_displacement_median(prev, co))
        prev = co
        last = f
        if f % 10 == 0:
            print(f'frame {f}: median disp {disp_hist[-1] * 1000:.2f} mm, {time.time() - t0:.1f} s', flush=True)
        if f >= sch['sew_frames'] + sch['min_frames_after_sew'] and len(disp_hist) >= window:
            if metrics.stable_median(disp_hist, window) <= th['stable_median_m_per_frame']:
                break
    return prev, disp_hist, last, time.time() - t0


def body_bvh(body):
    return BVHTree.FromPolygons([tuple(v) for v in body['vertices']], [tuple(fc) for fc in body['faces']])


def signed_distances(bvh, points):
    """점 -> 몸 표면 최근접점 부호 거리(법선 방향 +). 최근접점을 못 찾으면 NaN."""
    out = np.full(len(points), np.nan)
    for i, p in enumerate(points):
        loc, normal, _, _ = bvh.find_nearest(p)
        if loc is None:
            continue
        out[i] = float(np.dot(p - np.asarray(loc), np.asarray(normal)))
    return out


def setup_preview(cfg, out_png):
    pv = cfg['preview']
    scene = bpy.context.scene
    scene.render.engine = pv['engine']
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.render.resolution_x, scene.render.resolution_y = pv['resolution']
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('world')
    scene.world.color = tuple(pv['background_rgb'])

    cam_data = bpy.data.cameras.new('front_cam')
    cam_data.lens = pv['camera_lens_mm']
    cam = bpy.data.objects.new('front_cam', cam_data)
    scene.collection.objects.link(cam)
    cam.location = tuple(pv['camera_location_m'])  # 정면 -Y 쪽에서 +Y 방향을 본다
    cam.rotation_euler = tuple(math.radians(a) for a in pv['camera_rotation_deg'])
    scene.camera = cam
    scene.render.filepath = str(out_png)


def main():
    in_path, out_dir, cfg_path, max_frames_arg = parse_args()
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg, cfg_rec = load_config(cfg_path)
    th = cfg['thresholds']
    max_frames = th['max_frames'] if max_frames_arg is None else max_frames_arg
    if max_frames > th['max_frames']:
        raise ValueError(f'max_frames {max_frames} > thresholds.max_frames {th["max_frames"]}')
    data = json.loads(in_path.read_text(encoding='utf-8'))
    g, body = data['garment'], data['body']

    reset_scene()
    setup_body(body, cfg)
    garment = setup_garment(g, cfg, max_frames)

    # 초기 배치 침투(기록만). 오류 처리 기준은 아직 없다 -> C1 리뷰 '팀 합의 필요'.
    bvh = body_bvh(body)
    tris, _ = metrics.triangles(g['faces'])
    rest = np.asarray(g['vertices'])
    init_sd = signed_distances(bvh, metrics.face_centers(rest, tris))
    init_ratio, _, _ = metrics.penetration(metrics.tri_areas(rest, tris), init_sd,
                                           th['penetration_depth_m'], body['is_watertight'])

    co, disp_hist, last_frame, sim_s = simulate(garment, cfg, max_frames)
    sd = signed_distances(bvh, metrics.face_centers(co, tris))
    result = metrics.evaluate(rest, g['faces'], co, g['stitch_pairs'], disp_hist, sd,
                              body['is_watertight'], th)
    failed = [k for k in ('stable_ok', 'penetration_ok', 'stretch_ok') if not result[k]]
    if result['nan']:
        failed.append('nan')
    result.update({
        'error_code': None if result['drape_ok'] else 'DRAPE_INVALID',
        'failed_checks': failed,
        'initial_penetration_area_ratio': round(init_ratio, 4),
        'frames': last_frame,
        'max_frames': max_frames,
        'max_frames_overridden': max_frames_arg is not None,
        'sim_seconds': round(sim_s, 1),
        'blender': bpy.app.version_string,
        'n_garment_verts': len(co),
        'config': cfg_rec,
        'drape_input_sha256': sha256_file(in_path),
        'body_is_watertight': body['is_watertight'],
    })
    print(json.dumps(result, indent=2), flush=True)

    np.save(out_dir / 'garment_draped_co.npy', co)
    (out_dir / 'drape_trace.json').write_text(json.dumps(
        {'disp_median_m_per_frame': disp_hist, 'signed_dist_m': sd.tolist()}))

    setup_preview(cfg, out_dir / 'front.png')
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / 'drape.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.wm.obj_export(filepath=str(out_dir / 'garment_draped.obj'), export_selected_objects=True,
                          apply_modifiers=True, forward_axis='Y', up_axis='Z', export_materials=False)
    (out_dir / 'drape_metrics.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
