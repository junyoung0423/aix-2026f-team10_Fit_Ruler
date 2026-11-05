# 의류 실측 가이드 (초안 garment_measure_v0)

T02(1 SKU 실측과 패턴)용 작업 문서입니다. 필드 정의는 명세서 3장 "의류 실측 필드"를 따르고, 측정 위치처럼 명세서에 없는 세부 사항은 **[C 제안]**으로 표시합니다. [C 제안] 항목은 B와 측정 프로토콜(T01)을 합의할 때 확정합니다.

## 준비물

- 줄자(cm, 늘어나지 않는 것), 평평한 바닥 또는 책상
- 티셔츠는 뒤집지 않고 앞판이 위로 오게 펼치고, 주름만 손으로 펴며 당기지 않습니다.
- 각 값은 cm 소수점 한 자리로 기록합니다.

## 측정 항목

| 필드 | 명세서 정의 | 측정 방법 | 필수 |
| --- | --- | --- | --- |
| `chest_girth_cm` | 의류 가슴 측정선의 전체 둘레. 단면 너비만 있으면 2배 변환을 기록 | [C 제안] 겨드랑이 봉제점 아래 1 cm에서 좌우 옆선 사이 단면 너비를 재고 2배 | ✅ |
| `shoulder_width_cm` | 좌우 어깨 봉제선 끝 기준점 사이 거리 | 좌우 어깨 봉제선과 소매 봉제선이 만나는 점 사이 직선 | ✅ |
| `sleeve_length_cm` | 어깨 봉제선부터 소매 끝까지 길이 | 어깨 끝점에서 소매 바깥선을 따라 끝단까지 | |
| `body_length_cm` | HPS(목옆점)부터 앞 밑단까지 길이 | 목 옆 어깨 봉제선 시작점에서 수직으로 앞판 밑단까지 | |
| `waist_girth_cm` | 신체 자연 허리와 대응하는 의류 위치의 전체 둘레 | 대응 위치를 확인한 경우에만 기록. 모르면 `null`, `matches_body_waist: false` | |

- 값이 없으면 0이 아니라 `null`로 둡니다 (명세서 3장).
- 가슴·어깨가 비어 있으면 이 의류는 READY가 될 수 없습니다 (명세서 6장).

## 기록할 메타데이터 (`measurement_meta`)

- `raw_kind`: `flat_width`(단면) / `girth`(둘레) / `straight`(직선)
- `raw_value_cm`와 `conversion`: 단면을 둘레로 바꿨다면 원래 값과 변환식을 함께 남깁니다.
- `source`: 실물 측정인지, 판매처 상세 페이지인지, 패턴에서 잰 값인지 적습니다.
- `is_measured`: 실물을 직접 쟀으면 `true`
- `measured_by`, `measured_at`, `protocol_version`

## 결과 파일

측정이 끝나면 [samples/garment_v1.json](../samples/garment_v1.json)의 `measurements`와 `measurement_meta`를 실측값으로 바꾸고, `source`에서 `PLACEHOLDER` 표시를 지웁니다. 사진은 개인정보 없이 의류만 나오게 찍어 같은 SKU 폴더에 둡니다.
