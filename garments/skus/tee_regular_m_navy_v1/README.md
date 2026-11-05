# tee_regular_m_navy_v1 — 고정 패턴 (초안, FIT_FAILED)

GarmentCode 기본 티셔츠 패턴을 `samples/garment_v1.json` 목표 실측에 맞춰 고정한 파일이다(T02, 명세서 6장 패턴 최적화).

- **목표 실측은 PLACEHOLDER(명세서 4장 예시값)다.** 실물 실측이 오면 `samples/garment_v1.json` 값만 바꾸고
  아래 "다시 만들기"를 돌린 뒤 새 `pattern_version`으로 저장한다.
- **이 패턴은 사용자마다 다시 생성하지 않는다**(R06, C0 규칙 1). 다른 몸에는 이 `pattern_specification.json`을
  그대로 다시 배치하고 착장한다. 의류 치수를 사용자 몸에 맞게 늘리거나 줄이지 않는다.
- 패턴 생성용 몸은 GarmentCode `mean_all`(`body_mean_all.yaml`)로 고정한다. 사용자 몸도, D의 실제 몸(T07)도 아니다.
- 상태: **FIT_FAILED** — 어깨너비 34.457 cm, 목표 46.0 cm, 오차 −11.543 cm (기준 ±1.0 cm).
  GarmentCode 티셔츠의 어깨점은 몸의 `shoulder_w`로만 정해지고(`sleeves.py`: `(shoulder_w − 2)/2`)
  바꿀 수 있는 디자인 파라미터가 없다. 가슴·소매·기장은 오차 0.0 cm.

| 파일 | 내용 |
|---|---|
| `pattern_version.json` | 버전 이름, 상태, 파일별 sha256, 정규형 sha256, GarmentCode 버전, 맞춘 파라미터, 측정값·오차 |
| `design.yaml` | 맞춘 디자인 파라미터 (GarmentCode `t-shirt.yaml`에서 `shirt.width`, `shirt.length`, `sleeve.length`만 바뀜) |
| `body_mean_all.yaml` | 패턴 생성용 몸 (GarmentCode `assets/bodies/mean_all.yaml` 사본) |
| `pattern_specification.json` | 고정 패턴 (착장 입력) |
| `pattern_pattern.svg` | 패턴 그림 |

GarmentCode(MIT, 커밋 d449629) 파일과 그 출력이다. 라이선스 전문: `pipelines/garment/fixtures/tee_gc_default/SOURCE.md`.
`.gitattributes`로 줄바꿈 변환을 막아 sha256이 체크아웃마다 같다.

## 다시 만들기 (실측이 바뀌었을 때)

```powershell
cd C:\dev\GarmentCode; $env:PYTHONPATH='C:\dev\GarmentCode'
C:\dev\venvs\garmentcode\Scripts\python.exe C:\dev\FIT_RULER-c\pipelines\garment\pattern_fit.py fit C:\dev\FIT_RULER-c\pipelines\garment\configs\pattern_fit_v0.json C:\dev\fitruler_c\runs\C3\fit_new
C:\dev\venvs\garmentcode\Scripts\python.exe C:\dev\FIT_RULER-c\pipelines\garment\pattern_fit.py generate C:\dev\fitruler_c\runs\C3\fit_new\design_fitted.yaml C:\dev\GarmentCode\assets\bodies\mean_all.yaml C:\dev\fitruler_c\runs\C3\gen_new
```

`fit`은 디자인 yaml을, `generate`는 새 프로세스에서 패턴 파일을 만든다. GarmentCode는 같은 입력에서도
패널·봉제선 저장 순서가 바뀔 수 있으므로 파일 sha256 대신 `pattern_canonical_sha256`으로 같은 패턴인지 확인한다.
