# 측정 프로토콜 measure_v1

사용자 신체 입력과 의류 실측의 정의입니다. 명세서 3장의 내용을 구현 계약(`backend/src/fit_ruler/contracts/`)과 맞춰 정리했습니다. 화면의 측정 안내와 3D 측정 기준점은 같은 `measurement_protocol_version`으로 관리합니다.

> 지원 범위는 초기 UI와 모델의 지원 범위를 정하기 위한 제안값입니다. 신체의 정상 범위를 정의하지 않습니다.

## 공통 규칙

- 길이 단위는 **cm**이고 소수점 한 자리를 기준으로 합니다. (3D 내부 처리에서 m로 바꾸는 것은 C·D 어댑터의 책임입니다.)
- API는 유한한 숫자만 받습니다. 문자열, `NaN`, 무한대, 불리언, 음수, 단위가 섞인 값(`"175 cm"`)은 거절합니다.
- 범위 경계 값은 **포함**합니다. 범위 밖 값은 "현재 지원 범위 밖"으로 안내합니다.
- 값이 없으면 `0`으로 채우지 않고 `null`과 사유를 저장합니다.
- `measurement_protocol_version`은 현재 `measure_v1`입니다. 명세서에는 이 값이 `measure_v1`(API 예시)과 `measurement_protocol_v1`(5장)로 두 가지 적혀 있어서, 이 구현은 API 예시의 `measure_v1`을 씁니다. 팀에서 이름을 정하면 `SUPPORTED_PROTOCOL_VERSIONS`를 함께 바꿉니다.

## 사용자 신체 입력

| 필드 | 측정 정의 | 지원 범위 (cm) |
| --- | --- | --- |
| `height_cm` | 맨발로 선 상태의 바닥부터 정수리까지 수직 높이 | 140.0 ~ 210.0 |
| `chest_cm` | 가슴이 가장 돌출된 수평 위치의 둘레. 줄자를 당기지 않음 | 60.0 ~ 160.0 |
| `waist_cm` | 자연 허리 위치의 수평 둘레. 배꼽 둘레와 구분 | 50.0 ~ 160.0 |
| `shoulder_cm` | 좌우 어깨끝 기준점 사이의 직선 거리. 몸 표면을 따른 곡선 길이와 구분 | 28.0 ~ 60.0 |
| `arm_length_cm` | 오른쪽 어깨끝에서 팔꿈치를 거쳐 손목 기준점까지. 약하게 굽힌 표준 측정 자세 | 40.0 ~ 85.0 |

## 의류 실측

| 필드 | 정의와 입력 규칙 |
| --- | --- |
| `chest_girth_cm` | 의류 가슴 측정선의 **전체 둘레**. 단면 너비만 있으면 2배로 바꾸고 `chest_from_flat_width`에 기록 |
| `waist_girth_cm` | 신체 자연 허리와 대응하는 의류 위치의 전체 둘레. 위치 대응이 확인된 경우에만 핏 계산에 사용 |
| `shoulder_width_cm` | 좌우 어깨 봉제선 끝 기준점 사이 거리 |
| `sleeve_length_cm` | 어깨 봉제선부터 소매 끝까지. 사람의 전체 팔길이와 직접 차감하지 않음 |
| `body_length_cm` | 목 옆 높은 어깨점(HPS)부터 앞 밑단까지. 몸통 길이 입력이 없어 적정 기장은 판정하지 않음 |

의류 실측은 모든 필드가 **0 초과 300 이하**(cm)여야 합니다. 상한 300 cm는 가장 큰 신체 입력(가슴 160 cm)에 여유를 더한 둘레도 담으면서 비현실적인 값(예: `1e30`)을 입력 단계에서 거절하기 위한 제안값입니다. 경계값은 포함하며, 모델과 JSON 스키마가 같은 범위를 씁니다(`MAX_GARMENT_CM`).

`measurement_meta`에는 측정 위치와 방법, 단면·둘레 구분, 원출처, **실측 여부**(`is_measured`), **허리 위치 대응 여부**(`waist_position_matched`), 측정자·날짜·프로토콜 버전을 기록합니다. 실제 의류와 대조되지 않은 값(`is_measured: false`)은 화면에 "시연용 의류"로 표시합니다.

단면과 둘레, 밑단과 허리, 소매 길이와 팔길이를 서로 대체하지 않습니다. `READY` 의류에는 **가슴·어깨 실측이 필수**입니다.

## 판정 구간 (fit_rules_v0)

여유량은 반올림하지 않은 값으로 계산해 구간에 대응시키고, 표시할 때만 소수점 한 자리로 반올림합니다. 가슴·허리는 `의류 둘레 − 신체 둘레`, 어깨는 `의류 어깨너비 − 신체 어깨너비`입니다.

| 부위 | 구간 (cm) | 판정 |
| --- | --- | --- |
| 가슴 | 0 미만 / 0 이상 6 미만 / 6 이상 14 이하 / 14 초과 | `INSUFFICIENT` / `SNUG` / `REGULAR` / `LOOSE` |
| 허리 | 0 미만 / 0 이상 4 미만 / 4 이상 12 이하 / 12 초과 | 같은 네 단계. 위치 대응이 확인된 의류만 적용 |
| 어깨 | −1 미만 / −1 이상 2 이하 / 2 초과 | `NARROW` / `REGULAR` / `DROPPED` |
| 소매·기장 | 직접 대응하는 신체 치수 없음 | 의류 실측만 표시, `NOT_EVALUATED` |

구간은 기본 반팔 티셔츠용 **초기 검증값**입니다. 신축성과 착용 취향을 반영한 정답이 아닙니다.
`INSUFFICIENT`는 "착용 불가"를 뜻하지 않습니다. 어깨 여유는 양쪽을 합한 값이며 한쪽 어깨당 값이 아닙니다.

## 포트 DTO 검증 규칙

- `PortResult`의 네 필드(`schema_version`, `output_artifact_ids`, `metrics`, `tool_versions`)는 모두 **필수**입니다. 빈 응답(`{}`)이나 일부만 담은 응답은 거절합니다. `output_artifact_ids`는 키는 필수이고 값은 빈 목록일 수 있으며, 각 ID는 빈 문자열이 아니어야 합니다.
- 산출물을 만드는 단계(`BODY_FIT`, `DRAPE`, `RENDER`, `REALIZE`)의 결과는 `output_artifact_ids`가 비어 있지 않아야 하고, 도메인 상태를 바꾸기 전에 `require_output_artifacts`로 확인합니다. 이 단계 목록은 명세서에 없어 정한 **제안**입니다.
- `timeout_seconds`, `retryable`, `metrics` 값은 `strict`로 받아 `"30"`, `true`, `1`처럼 형을 바꿔 받는 입력을 거절합니다. 모델과 스키마가 같은 판정을 합니다.

## 이 구현에서 정한 이름 (명세서에 없던 것)

명세서에 이름이 있는 값은 그대로 쓰고, 아래는 구현을 위해 정한 **제안**입니다. 팀이 다른 이름을 정하면 `contracts/enums.py`와 이 문서를 같이 바꿉니다.

| 구분 | 이름 |
| --- | --- |
| 판정 | `INSUFFICIENT`, `SNUG`, `LOOSE`, `NARROW`, `DROPPED`, `NOT_EVALUATED` (`REGULAR`, `UNKNOWN`은 명세서 예시) |
| 판정하지 않은 이유 | `MEASUREMENT_MISSING`, `NO_DIRECT_BODY_COUNTERPART`, `BODY_INPUT_NOT_PROVIDED` (`MEASUREMENT_NOT_COMPARABLE`은 명세서) |
| 리포트·상태 필드 | `FitReport.summary`, `GarmentVariant.garment_family`, `FittingStatus.stages` |
| 검수 상태 | `PENDING_REVIEW`, `APPROVED`, `REJECTED` (`NOT_READY`는 명세서 예시) |

## 파일

- 스키마: [`contracts/schemas/`](../contracts/schemas/) (모델에서 자동 생성). 입력 범위, `READY` 의류의 필수 실측, 지원하는 프로토콜 버전까지 모델과 같은 판정을 하도록 테스트(`backend/tests/test_schemas.py`)로 검증합니다.
- 공통 샘플: [`samples/`](../samples/) — 모두 시연용이며 실제 의류·사용자 결과가 아닙니다.
