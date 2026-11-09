"""GET /api/v1/fittings/{id} 작업 상태 응답 (명세서 11장).

핏 경로(`report`)와 영상 경로(`visual`)는 서로 독립이다. 한 경로의 예외가 다른 경로의
상태를 덮어쓰지 않는다. 응답 필드는 명세서의 예시를 따르고, `stages`와 `error_code`는
화면의 진행 표시(S02)를 위해 이 구현에서 더한 [제안] 필드다.
"""

from pydantic import BaseModel, ConfigDict, Field

from fit_ruler.contracts.enums import (
    ErrorCode,
    JobStatus,
    QualityStatus,
    ReviewStatus,
    Stage,
    StageStatus,
)
from fit_ruler.contracts.report import RegionResult
from fit_ruler.contracts.versions import SCHEMA_VERSION


class StageProgress(BaseModel):
    """[제안] 단계별 진행. 화면이 단계명과 대기 여부를 표시하는 데 쓴다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Stage
    status: StageStatus
    attempt_no: int = Field(ge=1)


class ReportPart(BaseModel):
    """핏 경로 상태. 완료하면 리포트의 부위별 결과를 함께 돌려준다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: StageStatus
    rules_version: str | None = None
    regions: list[RegionResult] | None = None
    error_code: ErrorCode | None = None


class VisualPart(BaseModel):
    """영상 경로 상태. report_only 작업은 status가 SKIPPED다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: StageStatus
    stage: Stage | None = None
    quality_status: QualityStatus = QualityStatus.PENDING
    review_status: ReviewStatus = ReviewStatus.NOT_READY
    render_artifact_id: str | None = None
    published_video_artifact_id: str | None = None
    error_code: ErrorCode | None = None


class FittingStatus(BaseModel):
    """작업 전체 상태와 두 경로의 상태."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    job_id: str
    status: JobStatus
    report: ReportPart
    visual: VisualPart
    stages: list[StageProgress] = Field(default_factory=list)
