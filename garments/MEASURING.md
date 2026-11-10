# 의류 실측 가이드 — C 세부 위치와 패턴·착장 측정 (measure_v1 보충)

- `measurement_protocol_version`: **`measure_v1`**
- 필드 정의, 단위·범위, `null` 규칙, `measurement_meta` 필드는 [docs/measurement-protocol-v1.md](../docs/measurement-protocol-v1.md)를 따릅니다.
  이 문서에서는 다시 쓰지 않습니다. 둘이 어긋나면 프로토콜 문서가 우선합니다.
- 이 문서에는 C가 정한 두 가지만 둡니다. 프로토콜에 없는 실물 측정 세부 위치(**[C 제안]**)와, 같은 정의를 패턴·착장 메시에서 재는 방법입니다.
- [C 제안]은 B(T01)와 합의하기 전까지 초안입니다. 합의가 끝나면 프로토콜 문서로 옮기고 여기서는 지웁니다.

## 1. 실물 측정 세부 위치 [C 제안]

티셔츠는 뒤집지 않고 앞판이 위로 오게 평평한 곳에 펼칩니다. 주름만 손으로 펴고 당기지 않습니다.
줄자는 늘어나지 않는 cm 줄자를 씁니다.

| 필드 | [C 제안] 위치 | 직접 재는 값 |
| --- | --- | --- |
| `chest_girth_cm` | 겨드랑이 봉제점에서 옆선을 따라 **1 cm 아래**, 좌우 옆선 사이 | 단면 너비. 둘레로 바꾸면 `chest_from_flat_width: true` |
| `shoulder_width_cm` | 좌우 어깨 봉제선과 소매 봉제선이 만나는 점 사이 | 펼친 상태의 **직선** |
| `sleeve_length_cm` | 어깨 봉제선 끝점에서 소매 바깥선(윗선)을 따라 소매 끝단까지 | 바깥선을 따른 길이 |
| `body_length_cm` | HPS(목 옆 어깨 봉제선 시작점)에서 앞 중심선과 평행하게 앞 밑단까지 | 직선 |
| `waist_girth_cm` | 위치 미정 → 팀 합의 필요(리뷰 Csync.md) | 위치 대응을 확인하지 못하면 `null`, `waist_position_matched: false` |

- 프로토콜의 `measurement_meta`에는 필드별 원래 값(단면 너비 등)을 담을 칸이 없습니다.
  [C 제안] 원래 값과 위치·사진은 SKU 폴더(`garments/skus/<id>/`)에 측정 기록으로 두고, `notes`에 그 파일을 적습니다.
- 사진에는 의류만 나오게 하고 사람·개인정보가 나오지 않게 합니다.

## 2. 패턴에서 재는 방법 (GarmentCode 반소매 티셔츠, `pipelines/garment/pattern_measure.py`)

전제와 기준점은 리뷰 기록 C3.md "측정 정의"와 같습니다. 패널 구조가 다르면 `PatternMeasureError`를 냅니다. 값을 0이나 기본값으로 채우지 않습니다.

| 필드 | 패턴 측정 |
| --- | --- |
| `chest_girth_cm` | 4개 몸판에서 겨드랑이점 A로부터 옆선 곡선을 따라 1.0 cm 아래 점의 반폭(중심선까지 수직 거리)을 더합니다. 단면 × 2가 아니라 실제 둘레입니다. |
| `shoulder_width_cm` | 펼친 앞판에서 좌우 중심선을 겹쳤을 때, 좌우 어깨점 SP 사이 직선 |
| `sleeve_length_cm` | 소매 윗선(바깥선) 곡선 길이. 앞·뒤 평균을 낸 뒤 좌우 평균 |
| `body_length_cm` | HPS에서 중심선과 평행하게 밑단 곡선까지의 거리. 좌우 평균 |
| `waist_girth_cm` | 아직 재지 않습니다. 위치 정의가 정해지면 C3b에서 추가합니다. |

## 3. 착장 메시에서 재는 방법 (진단용, `pipelines/garment/drape_measure.py`)

패턴 측정선을 착장 메시 위로 옮겨 다시 잽니다. **진단 기록용**이며, 의류 실측값을 대신하지 않습니다.

- 가슴: 천을 따라 잰 둘레
- 어깨: 3D 직선
- 기장: 천을 따라 잰 길이
  - HPS–밑단 높이 차이는 어깨를 넘어가는 경로 때문에 평면 기장보다 짧게 나옵니다.
  - 그래서 평면 기장과 비교하지 않습니다(C3 [C 제안] P3).

## 4. 결과 파일

- 목표 실측은 공통 샘플 [samples/garment_v1.json](../samples/garment_v1.json)에서 읽습니다.
  이 파일은 B가 계약 모델에서 만들므로 **C는 고치지 않습니다**(CONTRIBUTING.md "계약을 바꿀 때").
  실측 값이 생기면 B에게 전달합니다.
- 실측 여부는 `measurement_meta.is_measured`와 `source_ref`로 판단합니다. `false`이면 시연용 값입니다.
  C의 패턴 기록(`pattern_version.json`)에도 그대로 옮겨 적습니다.
