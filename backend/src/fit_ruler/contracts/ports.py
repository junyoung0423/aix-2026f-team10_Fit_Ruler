"""외부 기능 포트의 공통 요청·결과·오류 (명세서 10장).

어댑터의 반환값을 검증한 뒤 도메인 상태를 바꾼다. 화면에는 safe_message만 보이고,
내부 파일 경로와 외부 서비스 응답 원문은 internal_details_ref가 가리키는 운영 기록에만 둔다.
"""

from pydantic import BaseModel, ConfigDict, Field

from fit_ruler.contracts.enums import ErrorCode, Stage
from fit_ruler.contracts.versions import SCHEMA_VERSION


class PortRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    job_id: str
    attempt_id: str
    input_artifact_ids: list[str] = Field(default_factory=list)
    config_version: str
    timeout_seconds: int = Field(gt=0)
    trace_id: str


class PortError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ErrorCode
    stage: Stage | None = None
    retryable: bool
    safe_message: str
    internal_details_ref: str | None = None


class PortResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    output_artifact_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    tool_versions: dict[str, str] = Field(default_factory=dict)
