from pydantic import Field
from sas.cosmosdb.sql import EntityBase, RepositoryBase, RootEntityBase
from config import RAITestConfig
from datetime import UTC, datetime, timezone

def _get_utc_timestamp() -> str:
    """Get current UTC timestamp in human-readable format"""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

class AgentActivityHistory(EntityBase):
    """Historical record of agent activity"""

    timestamp: str = Field(default_factory=_get_utc_timestamp)
    action: str
    message_preview: str = ""
    step: str = ""
    tool_used: str = ""


class AgentActivity(EntityBase):
    """Current activity status of an agent"""

    name: str
    current_action: str = "idle"
    last_message_preview: str = ""
    last_full_message: str = ""
    current_speaking_content: str = ""
    last_update_time: str = Field(default_factory=_get_utc_timestamp)
    is_active: bool = False
    is_currently_speaking: bool = False
    is_currently_thinking: bool = False
    thinking_about: str = ""
    current_reasoning: str = ""
    last_reasoning: str = ""
    reasoning_steps: list[str] = Field(default_factory=list)
    participation_status: str = "ready"
    last_activity_summary: str = ""
    message_word_count: int = 0
    activity_history: list[AgentActivityHistory] = Field(default_factory=list)
    step_reset_count: int = 0

class ProcessStatus(RootEntityBase["ProcessStatus", str]):
    """Overall process status for user visibility"""

    id: str  # Primary key (process_id)
    phase: str = ""
    step: str = ""
    status: str = "running"  # running, completed, failed, qa_review
    agents: dict[str, AgentActivity] = Field(default_factory=dict)
    last_update_time: str = Field(default_factory=_get_utc_timestamp)
    started_at_time: str = Field(default_factory=_get_utc_timestamp)

    # Failure information fields
    failure_reason: str = ""
    failure_details: str = ""
    failure_step: str = ""
    failure_agent: str = ""
    failure_timestamp: str = ""
    stack_trace: str = ""

    # Final Results Storage - capturing outcomes from each step
    step_results: dict[str, dict] = Field(
        default_factory=dict
    )  # Store results from each step
    final_outcome: dict | None = Field(default=None)  # Overall migration outcome
    generated_files: list[dict] = Field(default_factory=list)  # List of generated files
    conversion_metrics: dict = Field(
        default_factory=dict
    )  # Success rates, accuracy, etc.

    # UI-Optimized Telemetry Data for Frontend Consumption
    ui_telemetry_data: dict = Field(
        default_factory=dict,
        description="Comprehensive UI data including file manifests, dashboard metrics, and downloadable artifacts",
    )
   

class AgentActivityRepository(RepositoryBase[ProcessStatus, str]):
    def __init__(self, config: RAITestConfig):
        if not config:
            raise ValueError("RAITestConfig is required")

        super().__init__(
            connection_string=f"AccountEndpoint={config.COSMOS_DB_ENDPOINT};AccountKey={config.COSMOS_DB_KEY};",
            database_name=config.COSMOS_DB_NAME,
            container_name=config.COSMOS_DB_CONTAINER,
        )

class Process(RootEntityBase["Process", str]):
    user_id: str
    source_file_count: int = 0
    result_file_count: int = 0
    status: str = "initialized"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProcessRepository(RepositoryBase[Process, str]):
    def __init__(self, config: RAITestConfig):
        if not config:
            raise ValueError("RAITestConfig is required")

        super().__init__(
            connection_string=f"AccountEndpoint={config.COSMOS_DB_ENDPOINT};AccountKey={config.COSMOS_DB_KEY};",
            database_name=config.COSMOS_DB_NAME,
            container_name=config.COSMOS_DB_CONTAINER,
        )