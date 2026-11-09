"""팀 전체가 공유하는 데이터 계약 (T01).

이 패키지의 모델이 JSON 스키마(`contracts/schemas/`)와 공통 샘플(`samples/`)의 원본이다.
모델을 바꾸면 `python scripts/generate_contracts.py`로 스키마와 샘플을 다시 만들고,
변경 내용을 팀 전체에 같은 날 공유한다.
"""

from fit_ruler.contracts.enums import (
    ErrorCode,
    FitLabel,
    GarmentStatus,
    JobStatus,
    Mode,
    QualityStatus,
    ReasonCode,
    Region,
    ReviewStatus,
    Stage,
    StageStatus,
)
from fit_ruler.contracts.garment import (
    FAMILY_BASIC_SHORT_SLEEVE_CREW,
    GarmentMeasurements,
    GarmentVariant,
    MeasurementMeta,
)
from fit_ruler.contracts.measurements import (
    SUPPORTED_PROTOCOL_VERSIONS,
    BodyInput,
    FittingRequest,
    Measurements,
)
from fit_ruler.contracts.ports import (
    ARTIFACT_PRODUCING_STAGES,
    PortError,
    PortRequest,
    PortResult,
    PortResultInvalid,
    require_output_artifacts,
)
from fit_ruler.contracts.report import FitReport, RegionResult
from fit_ruler.contracts.status import FittingStatus, ReportPart, StageProgress, VisualPart
from fit_ruler.contracts.versions import SCHEMA_VERSION

__all__ = [
    "ARTIFACT_PRODUCING_STAGES",
    "FAMILY_BASIC_SHORT_SLEEVE_CREW",
    "SCHEMA_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "BodyInput",
    "ErrorCode",
    "FitLabel",
    "FitReport",
    "FittingRequest",
    "FittingStatus",
    "GarmentMeasurements",
    "GarmentStatus",
    "GarmentVariant",
    "JobStatus",
    "MeasurementMeta",
    "Measurements",
    "Mode",
    "PortError",
    "PortRequest",
    "PortResult",
    "PortResultInvalid",
    "QualityStatus",
    "ReasonCode",
    "Region",
    "RegionResult",
    "ReportPart",
    "ReviewStatus",
    "Stage",
    "StageProgress",
    "StageStatus",
    "VisualPart",
    "require_output_artifacts",
]
