"""JSON 스키마와 공통 샘플을 계약 모델에서 만든다.

    python -m fit_ruler.contracts.generate          # contracts/schemas, samples를 다시 만든다
    python -m fit_ruler.contracts.generate --check  # 저장된 파일이 최신인지만 확인한다

손으로 쓰는 샘플은 `samples/sample_input_v1.json`, `samples/garment_v1.json` 둘뿐이다.
나머지(`fit_report_v1.json`, `job_status_v1.json`, 스키마)는 이 모듈이 만들어서,
계약과 샘플이 서로 어긋나지 않는다. 샘플은 모두 시연용이며 실제 사용자 결과와 섞지 않는다.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from fit_ruler.contracts import (
    BodyInput,
    FitReport,
    FittingRequest,
    FittingStatus,
    GarmentVariant,
    JobStatus,
    PortError,
    PortRequest,
    PortResult,
    ReportPart,
    Stage,
    StageProgress,
    StageStatus,
    VisualPart,
)
from fit_ruler.fit_engine import compute_report

SAMPLE_JOB_ID = "fit_sample_001"
SAMPLE_CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "fitting_request": FittingRequest,
    "body_input": BodyInput,
    "garment_variant": GarmentVariant,
    "fit_report": FitReport,
    "fitting_status": FittingStatus,
    "port_request": PortRequest,
    "port_result": PortResult,
    "port_error": PortError,
}


def default_repo_root() -> Path:
    # <repo>/backend/src/fit_ruler/contracts/generate.py
    return Path(__file__).resolve().parents[4]


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def build_sample_report(root: Path) -> FitReport:
    request = FittingRequest.model_validate_json(
        (root / "samples" / "sample_input_v1.json").read_text(encoding="utf-8")
    )
    garment = GarmentVariant.model_validate_json(
        (root / "samples" / "garment_v1.json").read_text(encoding="utf-8")
    )
    return compute_report(
        request.to_body_input(),
        garment,
        job_id=SAMPLE_JOB_ID,
        created_at=SAMPLE_CREATED_AT,
    )


def build_sample_status(report: FitReport) -> FittingStatus:
    """명세서 11장 예시와 같은 상황: 리포트는 끝났고 영상은 실사화 단계를 실행 중이다."""
    progress = [
        (Stage.FIT_CALCULATE, StageStatus.SUCCEEDED),
        (Stage.FIT_REPORT, StageStatus.SUCCEEDED),
        (Stage.BODY_FIT, StageStatus.SUCCEEDED),
        (Stage.DRAPE, StageStatus.SUCCEEDED),
        (Stage.RENDER, StageStatus.SUCCEEDED),
        (Stage.REALIZE, StageStatus.RUNNING),
        (Stage.VALIDATE, StageStatus.WAITING),
        (Stage.REVIEW, StageStatus.WAITING),
        (Stage.PUBLISH, StageStatus.WAITING),
    ]
    return FittingStatus(
        job_id=SAMPLE_JOB_ID,
        status=JobStatus.RUNNING,
        report=ReportPart(
            status=StageStatus.SUCCEEDED,
            rules_version=report.rules_version,
            regions=report.regions,
        ),
        visual=VisualPart(
            status=StageStatus.RUNNING,
            stage=Stage.REALIZE,
            render_artifact_id="art_render_001",
        ),
        stages=[StageProgress(stage=s, status=st, attempt_no=1) for s, st in progress],
    )


def build_artifacts(root: Path) -> dict[Path, str]:
    """저장소 루트 기준으로 만들어야 하는 파일과 그 내용."""
    files: dict[Path, str] = {}
    for name, model in SCHEMA_MODELS.items():
        files[root / "contracts" / "schemas" / f"{name}.schema.json"] = _dump(
            model.model_json_schema()
        )
    report = build_sample_report(root)
    files[root / "samples" / "fit_report_v1.json"] = _dump(report.model_dump(mode="json"))
    status = build_sample_status(report)
    files[root / "samples" / "job_status_v1.json"] = _dump(status.model_dump(mode="json"))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 최신인지 확인한다")
    parser.add_argument("--root", type=Path, default=None, help="저장소 루트 (기본: 자동 탐지)")
    args = parser.parse_args(argv)

    root = args.root or default_repo_root()
    files = build_artifacts(root)

    stale = [
        path
        for path, content in files.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if args.check:
        if stale:
            print("최신이 아닌 파일이 있습니다. 아래 명령을 실행하세요:")
            print("  python -m fit_ruler.contracts.generate")
            for path in stale:
                print(f"  - {path.relative_to(root)}")
            return 1
        print("계약 스키마와 샘플이 최신입니다.")
        return 0

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")
        print(f"갱신: {path.relative_to(root)}")
    if not stale:
        print("바꿀 파일이 없습니다. 이미 최신입니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
