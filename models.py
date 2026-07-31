# Data validation models
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    full_name: str
    password: str = Field(..., min_length=6)
    role: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectCreate(BaseModel):
    name: str
    code: str
    location: Optional[str] = None
    opening_balance: Decimal = Field(default=0)

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

class TransactionCreate(BaseModel):
    category_id: int
    particulars_raw: str
    qty: Optional[Decimal] = Field(default=0)
    unit: Optional[str] = None
    rate: Optional[Decimal] = Field(default=0)
    amount: Optional[Decimal] = Field(default=0)
    remarks: Optional[str] = None
    sr_no: int
    is_lump_sum: bool = False

class RequisitionCreate(BaseModel):
    project_id: int
    period_start: datetime
    period_end: datetime
    transactions: List[TransactionCreate]

class RequisitionUpdate(BaseModel):
    status: Optional[str] = None
    verifier_comments: Optional[str] = None
    approver_comments: Optional[str] = None
    rejection_reason: Optional[str] = None

class ItemMasterCreate(BaseModel):
    canonical_name: str
    category_id: int
    unit: Optional[str] = None
    aliases: Optional[List[str]] = []

class ApprovalAction(BaseModel):
    action: str  # approve, reject, return
    comments: Optional[str] = None