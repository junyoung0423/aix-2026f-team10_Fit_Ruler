"""공통 샘플과 JSON 스키마가 계약 모델과 어긋나지 않는지 확인한다."""

import json

import pytest

from fit_ruler.contracts import FitReport, FittingRequest, FittingStatus, GarmentVariant
from fit_ruler.contracts.generate import SCHEMA_MODELS, build_artifacts, main

from .conftest import REPO_ROOT, SAMPLES


def _read(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_hand_written_samples_validate():
    request = FittingRequest.model_validate_json(_read("sample_input_v1.json"))
    garment = GarmentVariant.model_validate_json(_read("garment_v1.json"))
    assert request.garment_variant_id == garment.id


def test_samples_are_marked_as_samples():
    garment = GarmentVariant.model_validate_json(_read("garment_v1.json"))
    assert garment.is_demo
    assert garment.source_ref.startswith("SAMPLE")
    assert "SAMPLE" in (garment.measurement_meta.notes or "")


def test_generated_samples_validate():
    report = FitReport.model_validate_json(_read("fit_report_v1.json"))
    status = FittingStatus.model_validate_json(_read("job_status_v1.json"))
    assert report.job_id == status.job_id
    # 작업 상태 샘플의 리포트 부분은 리포트 샘플과 같은 부위 결과를 담는다.
    assert status.report.regions == report.regions


def test_committed_schemas_and_samples_are_up_to_date():
    """계약 모델을 바꿨다면 `python -m fit_ruler.contracts.generate`로 다시 만들어야 한다."""
    stale = [
        str(path.relative_to(REPO_ROOT))
        for path, content in build_artifacts(REPO_ROOT).items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    assert not stale, f"최신이 아닌 파일: {stale}"


def test_generate_check_command_passes():
    assert main(["--check", "--root", str(REPO_ROOT)]) == 0


@pytest.mark.parametrize("name", list(SCHEMA_MODELS))
def test_schema_file_is_valid_json_schema_document(name):
    path = REPO_ROOT / "contracts" / "schemas" / f"{name}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["title"] == SCHEMA_MODELS[name].__name__
    assert schema["type"] == "object"
