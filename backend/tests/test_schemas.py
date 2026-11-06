"""JSON 스키마 검증.

`contracts/schemas/`의 스키마는 A(TypeScript 화면)처럼 Python 모델을 쓰지 않는 쪽이 계약으로
읽는 파일이다. 그래서 스키마가 (1) 올바른 JSON Schema이고, (2) 공통 샘플을 통과시키고,
(3) 모델이 거절하는 입력을 똑같이 거절하는지 확인한다.
"""

import copy
import json

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError

from fit_ruler.contracts import FittingRequest, GarmentVariant
from fit_ruler.contracts.generate import SCHEMA_MODELS

from .conftest import REPO_ROOT, SAMPLES

SCHEMA_DIR = REPO_ROOT / "contracts" / "schemas"

# 샘플 파일 -> 그 파일이 따라야 하는 스키마
SAMPLE_SCHEMA = {
    "sample_input_v1.json": "fitting_request",
    "garment_v1.json": "garment_variant",
    "fit_report_v1.json": "fit_report",
    "job_status_v1.json": "fitting_status",
}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def load_sample(filename: str) -> dict:
    return json.loads((SAMPLES / filename).read_text(encoding="utf-8"))


def schema_accepts(name: str, payload: dict) -> bool:
    return Draft202012Validator(load_schema(name)).is_valid(payload)


def model_accepts(model: type[BaseModel], payload: dict) -> bool:
    try:
        model.model_validate(payload)
    except ValidationError:
        return False
    return True


def modified(payload: dict, path: list[str], value) -> dict:
    """payload를 복사해 path가 가리키는 값만 바꾼다. value가 KeyError면 그 키를 지운다."""
    result = copy.deepcopy(payload)
    target = result
    for key in path[:-1]:
        target = target[key]
    if value is KeyError:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return result


@pytest.mark.parametrize("name", list(SCHEMA_MODELS))
def test_schema_is_a_valid_json_schema(name):
    Draft202012Validator.check_schema(load_schema(name))


@pytest.mark.parametrize(("filename", "schema_name"), list(SAMPLE_SCHEMA.items()))
def test_samples_pass_their_schema(filename, schema_name):
    errors = list(Draft202012Validator(load_schema(schema_name)).iter_errors(load_sample(filename)))
    assert not errors, [e.message for e in errors]


# --- 모델이 거절하는 입력은 스키마도 거절한다 ---------------------------------------------------

REQUEST = load_sample("sample_input_v1.json")
GARMENT = load_sample("garment_v1.json")

INVALID_REQUESTS = {
    "키가 범위 아래": modified(REQUEST, ["measurements", "height_cm"], 139.9),
    "키가 범위 위": modified(REQUEST, ["measurements", "height_cm"], 210.1),
    "가슴이 범위 아래": modified(REQUEST, ["measurements", "chest_cm"], 59.9),
    "허리가 범위 위": modified(REQUEST, ["measurements", "waist_cm"], 160.1),
    "어깨가 범위 아래": modified(REQUEST, ["measurements", "shoulder_cm"], 27.9),
    "팔길이가 범위 위": modified(REQUEST, ["measurements", "arm_length_cm"], 85.1),
    "음수": modified(REQUEST, ["measurements", "height_cm"], -175.0),
    "문자열 숫자": modified(REQUEST, ["measurements", "height_cm"], "175.0"),
    "단위가 붙은 문자열": modified(REQUEST, ["measurements", "height_cm"], "175 cm"),
    "null": modified(REQUEST, ["measurements", "height_cm"], None),
    "불리언": modified(REQUEST, ["measurements", "height_cm"], True),
    "필수 치수 누락": modified(REQUEST, ["measurements", "waist_cm"], KeyError),
    "모르는 신체 필드": modified(REQUEST, ["measurements", "height_in"], 68.9),
    "모르는 최상위 필드": modified(REQUEST, ["note"], "x"),
    "실행 방식 오류": modified(REQUEST, ["mode"], "fast"),
    "의류 id 비어 있음": modified(REQUEST, ["garment_variant_id"], ""),
    "지원하지 않는 프로토콜": modified(REQUEST, ["measurement_protocol_version"], "measure_v0"),
    "프로토콜 누락": modified(REQUEST, ["measurement_protocol_version"], KeyError),
}

VALID_REQUESTS = {
    "샘플 그대로": REQUEST,
    "범위 경계(최솟값)": {
        **REQUEST,
        "measurements": {
            "height_cm": 140.0,
            "chest_cm": 60.0,
            "waist_cm": 50.0,
            "shoulder_cm": 28.0,
            "arm_length_cm": 40.0,
        },
    },
    "범위 경계(최댓값)": {
        **REQUEST,
        "measurements": {
            "height_cm": 210.0,
            "chest_cm": 160.0,
            "waist_cm": 160.0,
            "shoulder_cm": 60.0,
            "arm_length_cm": 85.0,
        },
    },
    "정수 입력": modified(REQUEST, ["measurements", "height_cm"], 175),
    "report_only": modified(REQUEST, ["mode"], "report_only"),
    "mode 생략(기본값 full)": modified(REQUEST, ["mode"], KeyError),
}


@pytest.mark.parametrize("case", list(INVALID_REQUESTS))
def test_schema_rejects_what_the_model_rejects_for_requests(case):
    payload = INVALID_REQUESTS[case]
    assert not model_accepts(FittingRequest, payload), "모델이 거절해야 하는 케이스"
    assert not schema_accepts("fitting_request", payload)


@pytest.mark.parametrize("case", list(VALID_REQUESTS))
def test_schema_accepts_what_the_model_accepts_for_requests(case):
    payload = VALID_REQUESTS[case]
    assert model_accepts(FittingRequest, payload), "모델이 받아들여야 하는 케이스"
    assert schema_accepts("fitting_request", payload)


INVALID_GARMENTS = {
    "READY인데 가슴 실측 null": modified(GARMENT, ["measurements", "chest_girth_cm"], None),
    "READY인데 어깨 실측 null": modified(GARMENT, ["measurements", "shoulder_width_cm"], None),
    "READY인데 가슴 실측 키 없음": modified(GARMENT, ["measurements", "chest_girth_cm"], KeyError),
    "실측 0": modified(GARMENT, ["measurements", "waist_girth_cm"], 0),
    "실측 음수": modified(GARMENT, ["measurements", "sleeve_length_cm"], -1.0),
    "실측 문자열": modified(GARMENT, ["measurements", "chest_girth_cm"], "108"),
    "상태 오류": modified(GARMENT, ["status"], "DONE"),
    "모르는 실측 필드": modified(GARMENT, ["measurements", "hem_cm"], 50.0),
    "meta 실측 여부 누락": modified(GARMENT, ["measurement_meta", "is_measured"], KeyError),
    "id 비어 있음": modified(GARMENT, ["id"], ""),
}

VALID_GARMENTS = {
    "샘플 그대로": GARMENT,
    "DRAFT는 가슴·어깨 없어도 됨": modified(
        modified(modified(GARMENT, ["status"], "DRAFT"), ["measurements", "chest_girth_cm"], None),
        ["measurements", "shoulder_width_cm"],
        None,
    ),
    "READY도 허리·소매·기장은 null 가능": modified(
        modified(
            modified(GARMENT, ["measurements", "waist_girth_cm"], None),
            ["measurements", "sleeve_length_cm"],
            None,
        ),
        ["measurements", "body_length_cm"],
        None,
    ),
    "다른 프로토콜 버전의 의류(차단은 엔진이 한다)": modified(
        GARMENT, ["measurement_meta", "measurement_protocol_version"], "measure_v0"
    ),
}


@pytest.mark.parametrize("case", list(INVALID_GARMENTS))
def test_schema_rejects_what_the_model_rejects_for_garments(case):
    payload = INVALID_GARMENTS[case]
    assert not model_accepts(GarmentVariant, payload), "모델이 거절해야 하는 케이스"
    assert not schema_accepts("garment_variant", payload)


@pytest.mark.parametrize("case", list(VALID_GARMENTS))
def test_schema_accepts_what_the_model_accepts_for_garments(case):
    payload = VALID_GARMENTS[case]
    assert model_accepts(GarmentVariant, payload), "모델이 받아들여야 하는 케이스"
    assert schema_accepts("garment_variant", payload)


def test_body_input_schema_rejects_unsupported_protocol():
    body = {**REQUEST["measurements"], "measurement_protocol_version": "measure_v1"}
    assert schema_accepts("body_input", body)
    assert not schema_accepts("body_input", {**body, "measurement_protocol_version": "x"})


# --- 열거형과 상태 응답 ------------------------------------------------------------------------


def test_report_schema_enums_match_python_enums():
    from fit_ruler.contracts import FitLabel, ReasonCode, Region

    defs = load_schema("fit_report")["$defs"]
    assert set(defs["FitLabel"]["enum"]) == {e.value for e in FitLabel}
    assert set(defs["ReasonCode"]["enum"]) == {e.value for e in ReasonCode}
    assert set(defs["Region"]["enum"]) == {e.value for e in Region}


def test_status_schema_rejects_unknown_enum_values():
    status = load_sample("job_status_v1.json")
    assert schema_accepts("fitting_status", status)
    assert not schema_accepts("fitting_status", modified(status, ["status"], "DONE"))
    assert not schema_accepts("fitting_status", modified(status, ["visual", "status"], "BUSY"))
    assert not schema_accepts(
        "fitting_status", modified(status, ["visual", "quality_status"], "MAYBE")
    )


def test_report_schema_rejects_unknown_label():
    report = load_sample("fit_report_v1.json")
    assert schema_accepts("fit_report", report)
    assert not schema_accepts("fit_report", modified(report, ["regions", 0, "label"], "FINE"))
