# pipelines/garment — 의류 준비·착장 (C 담당, 초안)

GarmentCode 패턴을 패널 + 봉제선 쌍으로 내보내고, Blender cloth로 기준 몸에 착장한 뒤
명세서 6장 검사(안정·침투·신장·NaN)를 한다. 상태: **초안(C1)**. 모든 수치 기준은 명세서의
**초기 검증값**이며 검증된 성능이 아니다.

## 환경 (이미 설치됨)

| 항목 | 위치 / 버전 |
|---|---|
| Python | 3.9.13 `C:\dev\python39` (PATH 미등록), 가상환경 `C:\dev\venvs\garmentcode` (pygarment 2.0.2, numpy 1.26.4, trimesh, pytest) |
| GarmentCode | `C:\dev\GarmentCode` (MIT, 커밋 d449629). 원본은 고치지 않는다. 실행 시 cwd·PYTHONPATH = GarmentCode 루트 (system.json이 상대경로) |
| Blender | 5.2.3 LTS `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, `--background`로만 실행 |
| 장비 | CPU만 (NVIDIA GPU 없음 → GarmentCode warp 시뮬레이터 사용 불가) |

새 파일·산출물은 ASCII 경로(`C:\dev\...`)에 둔다. Blender에 넘기는 경로는 모두 절대경로다.

## 실행

레포 루트(`C:\dev\FIT_RULER-c`)에서:

```powershell
# 단위 테스트
C:\dev\venvs\garmentcode\Scripts\python.exe -m pytest pipelines\garment\tests -q

# 착장 한 번 (export -> Blender -> 분석). 출력 C:\dev\fitruler_c\runs\C1\<name>\
C:\dev\venvs\garmentcode\Scripts\python.exe pipelines\garment\run_drape.py `
  --spec pipelines\garment\fixtures\tee_gc_default\t-shirt__261103-16-24-09_specification.json `
  --body C:\dev\GarmentCode\assets\bodies\mean_all.obj `
  --config pipelines\garment\configs\drape_v0.json --name tee_base
```

옵션: `--out-root` (기본 `C:\dev\fitruler_c\runs\C1`), `--max-frames N` (짧은 시험용, 설정의 300 이하만),
`--gc-root`, `--blender`. 출력 폴더가 이미 있으면 덮어쓰지 않고 멈춘다.

단계별로 따로 돌릴 때:

```powershell
# export (cwd = GarmentCode)
cd C:\dev\GarmentCode; $env:PYTHONPATH='C:\dev\GarmentCode'
C:\dev\venvs\garmentcode\Scripts\python.exe C:\dev\FIT_RULER-c\pipelines\garment\export_panels.py <spec.json> <body.obj> <out_dir> --config <drape_v0.json>
# 착장
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python C:\dev\FIT_RULER-c\pipelines\garment\blender_drape.py -- <out_dir>\drape_input.json <out_dir> <drape_v0.json> [max_frames]
# Blender 없이 지표 재계산
C:\dev\venvs\garmentcode\Scripts\python.exe C:\dev\FIT_RULER-c\pipelines\garment\analyze_drape.py <out_dir>
```

## 파일

| 파일 | 역할 |
|---|---|
| `coords.py` | GarmentCode → 명세서 좌표 변환 (순수 numpy) |
| `drape_config.py` | 설정 파일 읽기, 이름·버전·sha256 기록 |
| `metrics.py` | 신장·봉제선 벌어짐·안정·침투 비율 계산 (순수 numpy, Blender 안팎 공용) |
| `export_panels.py` | GarmentCode 패턴 → 패널 메시 + 봉제 쌍 → `drape_input.json` |
| `blender_drape.py` | Blender 봉제·착장·검사·저장 |
| `analyze_drape.py` | 같은 메시로 지표 재계산(Blender 결과와 비교), 패널·봉제선별 요약 |
| `run_drape.py` | 위 셋을 묶는 실행 래퍼, `run_summary.json` |
| `configs/drape_v0.json` | 시뮬레이션·재질·충돌·봉제 일정·검사 기준(thresholds)·시간 제한. 버전 고정 |
| `fixtures/tee_gc_default/` | 시험 패턴: GarmentCode 기본 `t-shirt.yaml`, 몸 mean_all로 만든 specification |
| `tests/` | pytest |

설정 값을 바꿀 때는 파일을 고치지 말고 새 버전 파일(`drape_v1.json` …)을 만든다. 한 번에 한 값만 바꾼다.
모든 지표 JSON에 설정 파일 이름·버전·sha256이 들어간다 (`.gitattributes`로 LF 고정 → 체크아웃마다 같은 해시).

## 좌표 규약 (명세서 6장, D와 합의 전 초안)

- 결과: m 단위, Z축 위, 인체 정면 -Y. 바닥 Z=0, 몸 중심 X=0 (GarmentCode 기준 몸은 이미 근처라 이동은 아직 0).
- GarmentCode: 옷 cm, 몸 m, 둘 다 Y축 위, 정면 +Z.
- 변환: 회전 `[[1,0,0],[0,0,-1],[0,1,0]]` (X축 +90°, det = 1), 옷 ×0.01, 몸 ×1.
  원본 축·행렬·배율은 `drape_input.json`의 `transform_from_garmentcode`에 남긴다.
- 의류 실측은 바꾸지 않는다(R06). 다른 몸에는 같은 패턴을 다시 export·착장한다.

## 산출물 (`C:\dev\fitruler_c\runs\<단계>\<name>\`, git 제외)

| 파일 | 내용 |
|---|---|
| `drape_input.json` | 패널 메시, 봉제 쌍, 몸 메시, 변환 기록, 입력 sha256, 설정 기록 |
| `drape.blend` | 착장 장면 |
| `garment_draped.obj` | 착장된 옷 (Z 위, 6자리 반올림) |
| `garment_draped_co.npy` | 착장된 옷 정점 좌표 (float64 원값, 재계산·결정성 비교용) |
| `drape_trace.json` | 프레임별 이동량 중앙값, 최종 면 중심 부호 거리 |
| `drape_metrics.json` | 착장 검사 결과 + `error_code`, 설정 기록, 프레임·시간 |
| `analysis.json` | Blender 없이 다시 계산한 지표, 일치 여부, 패널·봉제선별 요약 |
| `front.png` | 착장 확인용 정면 이미지 (Workbench). **명세서 6장 렌더 클립이 아니다** |
| `run_summary.json`, `*_log.txt` | 단계별 시간·종료 코드, 상태, 오류 코드 |

오류 코드(명세서 12장): export 실패 `GARMENT_NOT_READY`, 검사 실패·착장 10분 초과 `DRAPE_INVALID`.

## 알려진 문제

- **신장 초과 / 진동 봉제선**: 기준 실행(해상도 2 cm, 봉제 80프레임)에서 최대 신장 1.838 > 1.5로 `DRAPE_INVALID`.
  봉제선 남은 거리 최대 9.41 mm (중앙 0.47 mm). 1.5 초과 변 6개는 모두 왼쪽 앞 소매(최대 1.838)와
  왼쪽 앞판(1.787)에 있고, 최악 변은 Z≈1.32 m(진동 높이)다. 벌어짐 상위 봉제선도 왼쪽 소매 옆선·진동
  (stitch 8–11)이다. 좌우 대칭 패턴인데 왼쪽만 나빠 원인 미확인
  (`analysis.json`의 `stretch_by_panel`, `seam_gap_by_stitch`).
- 침투 판정은 면 중심의 최근접점 법선 부호를 쓴다. 몸 메시가 닫혀 있지 않으면 '검증 불가'로 둔다.
  면 중심만 보므로 면 일부만 들어간 경우는 놓칠 수 있다.
- 초기 배치 침투는 기록만 하고(`initial_penetration_area_ratio`), 오류로 막는 기준은 아직 없다.
- 천 값은 Blender Cotton 계열 값이며 면 저지 물성이 아니다.
- 기준 몸은 GarmentCode `mean_all`이며 D의 실제 몸(T07)이 아니다. SMPL 계열 몸은 쓰지 않는다(R19 확인 전).
- GarmentCode 2.0.2: 해상도 > 1.0 cm에서 `Edge.name` 없음 예외 → `export_panels.py`에서 `Edge.name = 'Edge'`로 우회.
