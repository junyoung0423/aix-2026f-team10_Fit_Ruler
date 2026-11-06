# 협업 가이드

네 명이 한 저장소에서 작업합니다. 이 문서는 명세서 15장(역할과 협업 방식)을 저장소 규칙으로 옮긴 것입니다.

## 개발 환경 시작

Python 3.10 이상이 필요합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest              # 테스트
ruff check .        # 린트
ruff format .       # 포맷
```

## 브랜치

- `main`은 항상 테스트가 통과하는 상태로 유지하고, 직접 푸시하지 않습니다. 모든 변경은 PR로 합칩니다.
- 브랜치 이름은 `종류/작업번호-설명` 형식입니다. 작업 번호는 명세서 15장의 T01~T24입니다.

| 종류 | 예시 |
| --- | --- |
| 기능 | `feat/T05-fit-engine` |
| 수정 | `fix/T05-waist-unknown` |
| 문서 | `docs/T01-measurement-protocol` |
| 정리 | `chore/ci-python-version` |

## 커밋

[Conventional Commits](https://www.conventionalcommits.org/ko/) 형식에 작업 번호를 붙입니다.

```text
feat(fit): T05 가슴 경계 판정을 10진수 차이로 계산
fix(contracts): T01 READY 의류의 필수 실측 검증 추가
docs: T01 측정 프로토콜 문서 추가
```

## Pull Request와 검토

- **한 번의 변경은 하나의 검토 단위**로 올립니다. 여러 작업을 한 PR에 섞지 않습니다.
- 작업의 끝은 코드 작성이 아니라, **다른 담당자가 실행하거나 읽을 수 있는 산출물**이 있는 상태입니다.
- 검토 짝이 확인한 뒤 합칩니다. 최소 1명의 승인이 필요합니다.

| 변경한 사람 | 검토 짝 |
| --- | --- |
| A 화면과 사용성 | B (API와 상태) |
| B 서버와 핏 판정 | A (사용자 동작), D (작업 인수) |
| C 의류와 착장 렌더 | D (몸·축·영상 입력) |
| D 몸과 실사화 검증 | C (형상·시점), B (실행 계약) |

## 계약을 바꿀 때

DTO, 단위, 좌표, 필수 필드, 판정 규칙은 팀 모두가 의존하는 계약입니다. 바꿀 때는 아래 순서를 지킵니다.

1. `backend/src/fit_ruler/contracts/`의 모델을 수정합니다.
2. `python -m fit_ruler.contracts.generate`로 `contracts/schemas/`와 `samples/`를 다시 만들어 **함께 커밋**합니다.
   저장된 파일이 최신이 아니면 CI가 실패합니다.
3. 호환이 깨지는 변경이면 `SCHEMA_VERSION`을 올립니다. 판정 구간을 바꾸면 `fit_rules_v0`의 버전을 올려서 이전 리포트를 소급 변경하지 않고 재현할 수 있게 합니다.
4. 계약 변경은 B가 버전을 관리하고, **같은 날 네 명에게 공유**합니다.
5. 명세서와 README에도 같은 내용을 반영합니다.

## 데이터와 보안

- 로그, 파일 이름, 샘플에 실제 신체 치수나 개인정보를 넣지 않습니다.
- 샘플과 시험용 데이터는 샘플임을 표시하고, 실제 사용자 실행 결과와 섞지 않습니다.
- 선택한 의류의 치수를 사용자 몸에 맞게 늘리거나 줄이지 않습니다.
- fal API 키 같은 비밀값은 저장소에 올리지 않습니다. `.env`는 `.gitignore`에 들어 있습니다.

## 저장소 관리자가 한 번 설정할 것

GitHub 웹에서 저장소 관리자 권한으로 설정합니다. (Settings → Rules 또는 Branches)

1. `main`에 **Branch protection rule**을 만듭니다.
2. **Require a pull request before merging**을 켜고 승인 1명 이상을 요구합니다.
3. **Require status checks to pass**를 켜고 `backend (py3.10)`, `backend (py3.12)`를 필수로 지정합니다. (CI가 한 번 실행된 뒤에 목록에 나타납니다.)
4. 강제 푸시(force push)와 브랜치 삭제를 막습니다.
5. Settings → Collaborators에서 팀원을 초대하고 쓰기 권한을 줍니다.
6. `.github/CODEOWNERS`에 팀원의 GitHub 아이디를 채웁니다.
