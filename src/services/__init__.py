"""Services package for Data-to-Dirt."""

from .carbon_calculator import (
    CarbonCalculator,
    CarbonProfile,
    calculate_energy_kwh,
    calculate_carbon_grams,
    calculate_avoided_offset_kg,
    calculate_tree_equivalent,
)
from .scanner import (
    FileScanner,
    ScanState,
    ScannedFileMetadata,
    ConfidentialFileError,
    PermissionRequiredError,
)
from .cloud_storage import (
    ICloudStorageProvider,
    MockCloudProvider,
    GoogleDriveProvider,
    CloudFileItem,
    CloudQuotaInfo,
)
from .ledger import (
    AuditLedger,
    LedgerBlock,
    VALID_TRANSACTION_TYPES,
)
from .tree_nation import (
    TreeNationClient,
    TreeNationError,
    TreeNationAPIError,
)
from .eco_fund import (
    EcoFundManager,
    DEFAULT_THRESHOLD_BYTES,
    DEFAULT_COST_PER_TREE_CENTS,
)
from .auth import (
    AuthService,
    AuthSession,
    AuthenticationError,
    AuthorizationError,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLE_ADMIN,
    default_auth_service,
)
from .teacher_queue import (
    TeacherQueue,
    DeletionRequest,
    default_teacher_queue,
)
from .analytics import (
    AnalyticsService,
    ClassroomStats,
)

__all__ = [
    "CarbonCalculator",
    "CarbonProfile",
    "calculate_energy_kwh",
    "calculate_carbon_grams",
    "calculate_avoided_offset_kg",
    "calculate_tree_equivalent",
    "FileScanner",
    "ScanState",
    "ScannedFileMetadata",
    "ConfidentialFileError",
    "PermissionRequiredError",
    "ICloudStorageProvider",
    "MockCloudProvider",
    "GoogleDriveProvider",
    "CloudFileItem",
    "CloudQuotaInfo",
    "AuditLedger",
    "LedgerBlock",
    "VALID_TRANSACTION_TYPES",
    "TreeNationClient",
    "TreeNationError",
    "TreeNationAPIError",
    "EcoFundManager",
    "DEFAULT_THRESHOLD_BYTES",
    "DEFAULT_COST_PER_TREE_CENTS",
    "AuthService",
    "AuthSession",
    "AuthenticationError",
    "AuthorizationError",
    "ROLE_STUDENT",
    "ROLE_TEACHER",
    "ROLE_ADMIN",
    "default_auth_service",
    "TeacherQueue",
    "DeletionRequest",
    "default_teacher_queue",
    "AnalyticsService",
    "ClassroomStats",
]

