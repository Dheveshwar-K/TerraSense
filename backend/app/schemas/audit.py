from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    sequence_no: Optional[int] = None
    timestamp: datetime
    user_name: str
    user_role: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    outcome: str = "SUCCESS"
    prev_hash: Optional[str] = None
    record_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
