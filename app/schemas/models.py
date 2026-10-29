"""Request bodies. Length limits here are the first line of defence; the
service layer re-validates everything (it is also called from tests and
scripts, not just HTTP)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CapabilityClaim(BaseModel):
    capability_id: str = Field(..., max_length=64)
    level: str = Field("Beginner", max_length=20)


class YouthCreate(BaseModel):
    name: str = Field(..., max_length=120)
    location: str = Field(..., max_length=120)
    goal: str = Field(..., max_length=200)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)
    passion: Optional[str] = Field(None, max_length=300)
    availability: Optional[str] = Field(None, max_length=100)
    equipment: Optional[str] = Field(None, max_length=300)
    intake: Optional[dict] = None
    capabilities: Optional[List[CapabilityClaim]] = None


class YouthLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class BusinessCreate(BaseModel):
    name: str = Field(..., max_length=150)
    owner: str = Field(..., max_length=120)
    sector: str = Field(..., max_length=100)
    location: str = Field(..., max_length=120)
    main_problem: str = Field(..., max_length=1000)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=30)
    password: Optional[str] = Field(None, max_length=128)


class BusinessLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class BizJobCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=4000)
    department: Optional[str] = Field(None, max_length=100)
    budget: float = 0


class PaymentSubmit(BaseModel):
    method: str = Field(..., max_length=20)
    provider_ref: Optional[str] = Field(None, max_length=80)
    amount: Optional[float] = None
    note: Optional[str] = Field(None, max_length=300)


class BizApprove(BaseModel):
    score: float = Field(..., ge=0, le=100)
    note: Optional[str] = Field(None, max_length=500)


class ResolveUnmatched(BaseModel):
    resolution: str = Field(..., max_length=300)


class PaymentReject(BaseModel):
    note: Optional[str] = Field(None, max_length=300)


class PayoutPaid(BaseModel):
    provider_ref: str = Field(..., max_length=80)


class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=500)
    location: str = Field(..., max_length=120)
    availability: Optional[str] = Field(None, max_length=100)
    equipment: Optional[str] = Field(None, max_length=300)
    passion: Optional[str] = Field(None, max_length=300)
    public_profile: bool = False


class PayoutAccountSet(BaseModel):
    method: str = Field(..., max_length=20)
    account_name: str = Field(..., max_length=120)
    account_ref: str = Field(..., max_length=60)


class ApprovalDecision(BaseModel):
    approved: bool
    note: Optional[str] = Field(None, max_length=300)


class AuditStatusUpdate(BaseModel):
    status: str = Field(..., max_length=20)


class OpportunityCreate(BaseModel):
    business_id: str = Field(..., max_length=64)
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=4000)
    department: Optional[str] = Field(None, max_length=100)
    budget: float = 0


class CapabilityCreate(BaseModel):
    name: str = Field(..., max_length=100)
    category: str = Field(..., max_length=60)
    description: Optional[str] = Field(None, max_length=500)


class CapabilityAssign(BaseModel):
    capability_id: str = Field(..., max_length=64)
    level: str = Field("Beginner", max_length=20)


class CapabilityVerify(BaseModel):
    verified: bool = True


class EvidenceSubmit(BaseModel):
    youth_id: str = Field(..., max_length=64)
    kind: str = Field(..., max_length=30)
    trial_id: Optional[str] = Field(None, max_length=64)
    capability_id: Optional[str] = Field(None, max_length=64)
    url: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=2000)


class MyEvidenceSubmit(BaseModel):
    kind: str = Field(..., max_length=30)
    trial_id: Optional[str] = Field(None, max_length=64)
    capability_id: Optional[str] = Field(None, max_length=64)
    url: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=2000)


class MatchCreate(BaseModel):
    youth_id: str = Field(..., max_length=64)
    opportunity_id: str = Field(..., max_length=64)
    match_score: float = 0
    reason: Optional[dict] = None


class AssignmentCreate(BaseModel):
    youth_id: str = Field(..., max_length=64)
    opportunity_id: str = Field(..., max_length=64)
    match_id: Optional[str] = Field(None, max_length=64)


class TrialCreate(BaseModel):
    assignment_id: str = Field(..., max_length=64)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)


class TrialSubmission(BaseModel):
    submission: Optional[dict] = None


class TrialReview(BaseModel):
    review: Optional[dict] = None


class TrialCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class FieldAuditCreate(BaseModel):
    business_id: Optional[str] = Field(None, max_length=64)
    business_name: str = Field(..., max_length=150)
    location: str = Field(..., max_length=120)
    ratings: Optional[dict] = None
    rooms: Optional[List[int]] = None
    insight: Optional[str] = Field(None, max_length=1000)
    score: int = 5


class StaffLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class StaffCreate(BaseModel):
    name: str = Field(..., max_length=120)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)
    role: str = Field(..., max_length=20)


class StaffActive(BaseModel):
    active: bool


class ResetIssue(BaseModel):
    account_type: str = Field(..., max_length=20)
    email: str = Field(..., max_length=254)


class ResetRedeem(BaseModel):
    account_type: str = Field(..., max_length=20)
    email: str = Field(..., max_length=254)
    code: str = Field(..., max_length=20)
    new_password: str = Field(..., max_length=128)


class VoidInvoice(BaseModel):
    reason: str = Field(..., max_length=300)


class DeleteAccount(BaseModel):
    password: str = Field(..., max_length=128)


class OwnerDelete(BaseModel):
    kind: str = Field(..., max_length=20)
    ids: list
    confirm: str = Field(..., max_length=10)


class OwnerEdit(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=120)
    goal: Optional[str] = Field(None, max_length=300)
    passion: Optional[str] = Field(None, max_length=300)
    availability: Optional[str] = Field(None, max_length=100)
    equipment: Optional[str] = Field(None, max_length=300)
    bio: Optional[str] = Field(None, max_length=500)
    email: Optional[str] = Field(None, max_length=254)
    owner: Optional[str] = Field(None, max_length=120)
    sector: Optional[str] = Field(None, max_length=60)
    main_problem: Optional[str] = Field(None, max_length=500)
    budget: Optional[float] = None
    status: Optional[str] = Field(None, max_length=20)


class StaffSignup(BaseModel):
    name: str = Field(..., max_length=120)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class StaffApprove(BaseModel):
    role: str = Field(..., max_length=20)
