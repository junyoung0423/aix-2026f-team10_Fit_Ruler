# pipelines/garment — 의류 준비·착장 (C 담당, 초안)

GarmentCode 패턴을 패널 + 봉제선 쌍으로 내보내고, Blender cloth로 기준 몸에 착장한 뒤
명세서 6장 검사(안정·침투·신장·NaN)를 한다. 상태: **초안(C3)**. 기본 설정은 `configs/drape_v1.json`(status draft).
SKU 고정 패턴은 `garments/skus/<sku>/`에 있다(C3, `pattern_fit.py`).

> **drape_v1 주의**: 용접 뒤 질량이 면밀도 기준(옷 전체 약 0.10 kg)이라 천 강성 대비 매우 가볍다.
> 중력이 켜진 뒤 움직임이 거의 없어(이동량 중앙값 0.9 mm, 밑단 −0.5 mm) **중력 처짐·실루엣은 검증 전**이다.
> 질량·강성 조정은 C3 범위가 아니어서 바꾸지 않았다. 모든 수치 기준은 명세서의
**초기 검증값**이며 검증된 성능이 아니다.

## 빠른 시작 (처음 실행하는 사람용)

1. 환경: 아래 "환경" 표의 Python 3.9 가상환경 `C:\dev\venvs\garmentcode`, GarmentCode `C:\dev\GarmentCode`, Blender 5.2가 있어야 한다. 레포 루트로 이동한다: `cd C:\dev\FIT_RULER-c`
2. 테스트(1분 안쪽): `C:\dev\venvs\garmentcode\Scripts\python.exe -m pytest pipelines\garment\tests -q`
3. 착장 1회(약 2~6분, 결과는 `C:\dev\fitruler_c\runs\quick\try1\`): `C:\dev\venvs\garmentcode\Scripts\python.exe pipelines\garment\run_drape.py --spec pipelines\garment\fixtures\tee_gc_default\t-shirt__261103-16-24-09_specification.json --body C:\dev\GarmentCode\assets\bodies\mean_all.obj --config pipelines\garment\configs\drape_v1.json --name try1 --out-root C:\dev\fitruler_c\runs\quick`
4. 결과 확인: 같은 폴더의 `drape_metrics.json`(`drape_ok`, `failed_checks`)과 `front.png`. 흐름과 한계는 [docs/spike-garmentcode-blender.md](docs/spike-garmentcode-blender.md).

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
  --config pipelines\garment\configs\drape_v1.json --name tee_v1
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
| `pattern_measure.py` | 패턴 JSON에서 가슴·어깨·소매·기장 측정 (svgpathtools, GarmentCode 불필요), 정규형 sha256 |
| `pattern_fit.py` | 디자인 파라미터를 목표 실측에 맞춤(`fit`), 민감도(`sensitivity`), 고정 패턴 생성(`generate`). GarmentCode 필요 |
| `configs/pattern_fit_v0.json` | 패턴 최적화 설정(몸 mean_all 고정, 맞출 파라미터, 허용 오차 1.0 cm) |
| `drape_measure.py` | 패턴 측정선을 착장 메시에서 다시 잼(진단용) |
| `weld.py` | 봉제 쌍 용접 대응표, 패턴 길이 이완 형상, 휴지 길이 편차 (순수 numpy) |
| `run_drape.py` | 위 셋을 묶는 실행 래퍼, `run_summary.json` |
| `tools/make_config.py` | 기존 설정에서 값 하나만 바꾼 실험 설정 만들기 |
| `configs/drape_v1.json` | **C2 통과 설정**: quality 12, 자기 충돌 1.5 mm, 2단계 용접, 용접 뒤 면밀도 질량 |
| `configs/drape_v0.json` | C1 설정(시험 스크립트 값 그대로). 비교·재현용으로 남긴다 |
| `configs/experiments/C2/` | C2 실험 설정 e01~e08 |
| `fixtures/tee_gc_default/` | 시험 패턴: GarmentCode 기본 `t-shirt.yaml`, 몸 mean_all로 만든 specification |
| `tests/` | pytest |

설정 값을 바꿀 때는 파일을 고치지 말고 새 버전 파일(`drape_v1.json` …)을 만든다. 한 번에 한 값만 바꾼다.
모든 지표 JSON에 설정 파일 이름·버전·sha256이 들어간다 (`.gitattributes`로 LF 고정 → 체크아웃마다 같은 해시).

## 착장 절차 (drape_v1)

1. 프레임 1–80: 중력 0, 봉제 스프링(loose edge)으로 패널을 모은다. 질량은 정점당 0.3 kg(수치 안정용).
2. 프레임 80: 봉제 쌍 최대 거리가 `seam_gap_preweld_max_m`(10 mm, [C 제안]) 이하이면 쌍을 한 정점으로 용접한다.
   넘으면 용접하지 않고 멈춰 `DRAPE_INVALID`(용접으로 감추지 않는다).
   - 용접 메시의 시작 형상 = 용접 시점 좌표(쌍 평균).
   - 휴지 형상(`rest_shape_key`) = 원래 패턴 변 길이에 맞춘 3D 이완 형상. 용접 시점 형상을 휴지로 쓰면
     그때의 늘어남(변 길이 비 0.67–1.43)이 옷 치수에 들어가므로 쓰지 않는다. 이완 형상의 패턴 대비 편차는
     `drape_metrics.json`의 `weld.rest_length_ratio_used`에 남는다(기준 실행: 0.966–1.026, p01–p99 0.996–1.004).
   - 용접 뒤 질량 = 면밀도 0.18 kg/m² ([C 제안], 측정값 아님) × 패턴 면적 / 정점 수 (옷 전체 약 0.10 kg).
3. 프레임 80–85에 중력을 1로 올리고, 110프레임 이후 안정 판정(최대 300).
4. 지표는 용접 메시 좌표를 원래 정점(2001개)으로 되돌려 **원래 패턴 길이 대비**로 계산한다.
   봉제선 닫힘은 용접 전 최대 거리로 판정한다(`seam_closure_mode: weld`).

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
| `garment_ref_co.npy` | 중력 반응 기준 프레임(용접 직후) 좌표 |
| `drape_trace.json` | 프레임별 이동량 중앙값, 최종 면 중심 부호 거리 |
| `drape_metrics.json` | 착장 검사 결과 + `error_code`, 설정 기록, 프레임·시간 |
| `analysis.json` | Blender 없이 다시 계산한 지표, 일치 여부, 패널·봉제선별 요약 |
| `front.png` | 착장 확인용 정면 이미지 (Workbench). **명세서 6장 렌더 클립이 아니다** |
| `run_summary.json`, `*_log.txt` | 단계별 시간·종료 코드, 상태, 오류 코드 |

오류 코드(명세서 12장): export 실패 `GARMENT_NOT_READY`, 검사 실패·착장 10분 초과 `DRAPE_INVALID`.

## 알려진 문제

- (C3) SKU 고정 패턴(기장 70 cm)은 drape_v1에서 프레임 80의 용접 전 벌어짐이 12.59 mm(기준 10 mm)라 용접하지 않고 `DRAPE_INVALID`.
  봉제 구간의 벌어짐이 6.5–13 mm로 흔들려 고정 프레임(80) 용접이 운에 좌우된다.
- (C3) SKU 패턴은 어깨너비를 맞추지 못했다(34.46 vs 목표 46.0 cm). GarmentCode 티셔츠 어깨점이 몸 shoulder_w로만 정해진다.
- (C3) GarmentCode는 같은 입력에서도 패턴 JSON의 패널·봉제선 저장 순서가 바뀔 수 있다. 같은 패턴인지는 `canonical_sha256`으로 본다.
- 착장 후 기장의 높이(Z) 차는 어깨를 넘어가는 경로 때문에 평면 기장보다 짧다(기본 패턴 −8.7 cm). 천 위 길이는 패턴과 같다(+0.3 cm).

- drape_v1 최대 신장 1.454로 기준 1.5에 여유가 작다. 최대 변은 어깨 꼭대기의 짧은 변(휴지 6.1 mm, 봉제선 3·10번 0.6 cm).
  Blender 천 스프링 강성은 변 길이로 보정되지 않아 짧은 변이 같은 힘에 더 크게(비율로) 늘어난다.
- drape_v1에서는 옷이 가벼워(0.10 kg) 중력에 의한 처짐이 작다. 천 강성 값은 면 저지 물성으로 맞춘 값이 아니다.
- 용접 휴지 형상은 3D 이완 형상이라 굽힘 휴지 각도도 그 형상을 따른다(패널이 평평한 상태가 휴지가 아님).
- 시뮬레이션 시간이 같은 설정에서도 크게 흔들린다(v0: 24–79 s, v1: 76–90 s). 결과는 비트 단위로 같다.
- (C1, drape_v0) **신장 초과 / 진동 봉제선**: 기준 실행(해상도 2 cm, 봉제 80프레임)에서 최대 신장 1.838 > 1.5로 `DRAPE_INVALID`.
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
