"""Admin routes: guarded by the X-API-Key header (middleware)."""

from fastapi import APIRouter, Header, Query, Request

from app.api.service import (
    agent_person,
    owner_delete,
    owner_edit,
    owner_records,
    add_staff,
    get_attention,
    staff_set_role,
    youth_profile_for_staff,
    staff_approve,
    staff_delete,
    get_open_resets,
    agent_people,
    agent_register,
    get_report,
    get_scorecard,
    get_staff,
    issue_reset_code,
    set_staff_active,
    void_invoice,
    reissue_invoice,
    whoami,
    get_migration_status,
    run_migrations,
    get_unmatched,
    resolve_unmatched_payment,
    staff_submit_payment,
    confirm_payment,
    decide_opportunity,
    fail_payout,
    get_invoices,
    get_payments,
    get_payouts,
    pay_out,
    reject_payment,
    close_business_opportunity,
    get_activity,
    get_opportunity_candidates,
    get_business_diagnosis,
    get_field_audits,
    get_review_queue,
    record_field_audit,
    accept_opportunity_assignment,
    assign_opportunity,
    assign_youth_capability,
    cancel_opportunity_assignment,
    cancel_opportunity_trial,
    complete_opportunity_assignment,
    complete_opportunity_trial,
    create_assignment_trial,
    create_business_opportunity,
    create_youth_capability,
    decline_opportunity_assignment,
    find_youth_opportunities,
    get_business_opportunity,
    get_business_profile,
    get_dashboard,
    get_opportunity_assignment,
    get_opportunity_trial,
    get_youth_profile,
    list_assignment_opportunity_trials,
    list_business_opportunities,
    list_businesses,
    list_capability_records,
    list_opportunity_assignment_records,
    list_trial_evidence_records,
    list_youth,
    list_youth_capability_records,
    list_youth_evidence_records,
    list_youth_opportunity_assignments,
    list_youth_opportunity_matches,
    list_youth_opportunity_trials,
    match_youth_opportunity,
    review_opportunity_trial,
    start_opportunity_trial,
    submit_opportunity_trial,
    submit_youth_evidence,
    update_business_audit_status,
    verify_youth_capability,
)
from app.routes.common import service_call
from app.schemas.models import (
    OwnerDelete,
    OwnerEdit,
    ResetIssue,
    StaffActive,
    StaffApprove,
    StaffCreate,
    VoidInvoice,
    ReissueInvoice,
    ApprovalDecision,
    PaymentReject,
    PaymentSubmit,
    PayoutPaid,
    ResolveUnmatched,
    FieldAuditCreate,
    AssignmentCreate,
    AuditStatusUpdate,
    CapabilityAssign,
    CapabilityCreate,
    CapabilityVerify,
    EvidenceSubmit,
    MatchCreate,
    OpportunityCreate,
    TrialCancel,
    TrialCreate,
    TrialReview,
    AgentRegister,
    MyEvidenceSubmit,
    TrialSubmission,
)

router = APIRouter(tags=["admin"])


def _actor(request):
    """Who is acting: a staff member's name, or "admin-key" for the shared key."""
    return getattr(request.state, "actor", None) or "staff"


@router.get("/admin/stats")
def stats():
    return service_call(get_dashboard)


@router.get("/admin/queue")
def queue():
    return service_call(get_review_queue)


@router.get("/admin/activity")
def activity(limit: int = Query(50, ge=1, le=200)):
    return service_call(get_activity, limit)


@router.get("/opportunities/{opportunity_id}/candidates")
def opportunity_candidates(opportunity_id: str):
    return service_call(get_opportunity_candidates, opportunity_id)


@router.post("/opportunities/{opportunity_id}/close")
def opportunity_close(opportunity_id: str):
    return service_call(close_business_opportunity, opportunity_id)


@router.post("/audits", status_code=201)
def audit_create(payload: FieldAuditCreate):
    return service_call(record_field_audit, payload.dict())


@router.get("/audits")
def audit_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(get_field_audits, limit, offset)


@router.get("/businesses/{business_id}/diagnosis")
def business_diagnosis(business_id: str):
    return service_call(get_business_diagnosis, business_id)


# ----- youth -----

@router.get("/youth")
def youth_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(list_youth, limit, offset)


@router.get("/youth/{youth_id}")
def youth_get(youth_id: str, request: Request):
    return service_call(youth_profile_for_staff, youth_id, getattr(request.state, "staff_role", "owner"))


@router.get("/youth/{youth_id}/capabilities")
def youth_capabilities(youth_id: str):
    return service_call(list_youth_capability_records, youth_id)


@router.post("/youth/{youth_id}/capabilities", status_code=201)
def youth_capability_assign(youth_id: str, payload: CapabilityAssign):
    body = payload.dict()
    body["youth_id"] = youth_id
    return service_call(assign_youth_capability, body)


@router.get("/youth/{youth_id}/opportunities/discover")
def youth_discover(youth_id: str):
    return service_call(find_youth_opportunities, youth_id)


@router.get("/youth/{youth_id}/matches")
def youth_matches(youth_id: str):
    return service_call(list_youth_opportunity_matches, youth_id)


@router.get("/youth/{youth_id}/assignments")
def youth_assignments(youth_id: str):
    return service_call(list_youth_opportunity_assignments, youth_id)


@router.get("/youth/{youth_id}/trials")
def youth_trials(youth_id: str):
    return service_call(list_youth_opportunity_trials, youth_id)


@router.get("/youth/{youth_id}/evidence")
def youth_evidence(youth_id: str):
    return service_call(list_youth_evidence_records, youth_id)


# ----- capabilities -----

@router.post("/capabilities", status_code=201)
def capability_create(payload: CapabilityCreate):
    return service_call(create_youth_capability, payload.dict())


@router.get("/capabilities")
def capability_list():
    return service_call(list_capability_records)


@router.post("/youth-capabilities/{youth_capability_id}/verify")
def capability_verify(youth_capability_id: str, payload: CapabilityVerify):
    return service_call(verify_youth_capability, youth_capability_id, payload.verified)


# ----- businesses -----

@router.get("/businesses")
def business_list(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return service_call(list_businesses, limit, offset)


@router.get("/businesses/{business_id}")
def business_get(business_id: str):
    return service_call(get_business_profile, business_id)


@router.post("/businesses/{business_id}/audit-status")
def business_audit_status(business_id: str, payload: AuditStatusUpdate):
    return service_call(update_business_audit_status, business_id, payload.status)


# ----- opportunities -----

@router.post("/opportunities", status_code=201)
def opportunity_create(payload: OpportunityCreate):
    return service_call(create_business_opportunity, payload.dict())


@router.get("/opportunities")
def opportunity_list(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None, max_length=20),
    approval: str = Query(None, max_length=20),
):
    return service_call(list_business_opportunities, limit, offset, status, approval)


@router.get("/opportunities/{opportunity_id}")
def opportunity_get(opportunity_id: str):
    return service_call(get_business_opportunity, opportunity_id)


@router.get("/opportunities/{opportunity_id}/assignments")
def opportunity_assignments(opportunity_id: str):
    return service_call(list_opportunity_assignment_records, opportunity_id)


# ----- matches / assignments -----

@router.post("/matches", status_code=201)
def match_create(payload: MatchCreate):
    return service_call(match_youth_opportunity, payload.dict())


@router.post("/assignments", status_code=201)
def assignment_create(payload: AssignmentCreate):
    return service_call(assign_opportunity, payload.dict())


@router.get("/assignments/{assignment_id}")
def assignment_get(assignment_id: str):
    return service_call(get_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/accept")
def assignment_accept(assignment_id: str):
    return service_call(accept_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/decline")
def assignment_decline(assignment_id: str):
    return service_call(decline_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/cancel")
def assignment_cancel(assignment_id: str):
    return service_call(cancel_opportunity_assignment, assignment_id)


@router.post("/assignments/{assignment_id}/complete")
def assignment_complete(assignment_id: str):
    return service_call(complete_opportunity_assignment, assignment_id)


@router.get("/assignments/{assignment_id}/trials")
def assignment_trials(assignment_id: str):
    return service_call(list_assignment_opportunity_trials, assignment_id)


# ----- trials -----

@router.post("/trials", status_code=201)
def trial_create(payload: TrialCreate):
    return service_call(create_assignment_trial, payload.dict())


@router.get("/trials/{trial_id}")
def trial_get(trial_id: str):
    return service_call(get_opportunity_trial, trial_id)


@router.post("/trials/{trial_id}/start")
def trial_start(trial_id: str):
    return service_call(start_opportunity_trial, trial_id)


@router.post("/trials/{trial_id}/submit")
def trial_submit(trial_id: str, payload: TrialSubmission):
    return service_call(submit_opportunity_trial, trial_id, payload.submission)


@router.post("/trials/{trial_id}/review")
def trial_review(trial_id: str, payload: TrialReview):
    return service_call(review_opportunity_trial, trial_id, payload.review)


@router.post("/trials/{trial_id}/complete")
def trial_complete(trial_id: str, payload: TrialReview):
    return service_call(complete_opportunity_trial, trial_id, payload.review)


@router.post("/trials/{trial_id}/cancel")
def trial_cancel(trial_id: str, payload: TrialCancel):
    return service_call(cancel_opportunity_trial, trial_id, payload.reason)


@router.get("/trials/{trial_id}/evidence")
def trial_evidence(trial_id: str):
    return service_call(list_trial_evidence_records, trial_id)


# ----- evidence -----

@router.post("/evidence", status_code=201)
def evidence_submit(payload: EvidenceSubmit):
    return service_call(submit_youth_evidence, payload.dict())


# ----- approvals and finance -----

@router.post("/opportunities/{opportunity_id}/approval")
def opportunity_approval(opportunity_id: str, payload: ApprovalDecision, request: Request):
    return service_call(decide_opportunity, opportunity_id, payload.dict(), _actor(request))


@router.get("/invoices")
def invoice_list(
    status: str = Query(None, max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return service_call(get_invoices, status, limit, offset)


@router.get("/payments")
def payment_list(
    status: str = Query(None, max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return service_call(get_payments, status, limit, offset)


@router.post("/payments/{payment_id}/confirm")
def payment_confirm(payment_id: str, request: Request):
    return service_call(confirm_payment, payment_id, _actor(request))


@router.post("/payments/{payment_id}/reject")
def payment_reject(payment_id: str, payload: PaymentReject, request: Request):
    return service_call(reject_payment, payment_id, payload.dict(), _actor(request))


@router.get("/payouts")
def payout_list(
    status: str = Query(None, max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return service_call(get_payouts, status, limit, offset)


@router.post("/payouts/{payout_id}/paid")
def payout_paid(payout_id: str, payload: PayoutPaid, request: Request):
    return service_call(pay_out, payout_id, payload.dict(), _actor(request))


@router.post("/payouts/{payout_id}/fail")
def payout_fail(payout_id: str, payload: PaymentReject):
    return service_call(fail_payout, payout_id, payload.dict())


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def invoice_payment(invoice_id: str, payload: PaymentSubmit,
                    idempotency_key: str = Header(None, alias="Idempotency-Key")):
    """Staff record a payment received outside the app (cash, EFT)."""
    return service_call(staff_submit_payment, invoice_id, payload.dict(), idempotency_key)


@router.get("/unmatched-payments")
def unmatched_list(status: str = Query("Open", max_length=20)):
    return service_call(get_unmatched, status)


@router.post("/unmatched-payments/{unmatched_id}/resolve")
def unmatched_resolve(unmatched_id: str, payload: ResolveUnmatched):
    return service_call(resolve_unmatched_payment, unmatched_id, payload.dict())


@router.get("/admin/migrations")
def migrations_status():
    return service_call(get_migration_status)


@router.post("/admin/migrations/apply")
def migrations_apply():
    """Applies the SQL files bundled with this release. Admin key only."""
    return service_call(run_migrations)


# ----- staff accounts, resets, system check -----

@router.get("/admin/me")
def admin_me(request: Request):
    return {"name": _actor(request), "role": getattr(request.state, "staff_role", "admin")}


@router.get("/admin/staff")
def staff_list():
    return service_call(get_staff)


@router.post("/admin/staff", status_code=201)
def staff_add(payload: StaffCreate):
    return service_call(add_staff, payload.dict())


@router.post("/admin/staff/{staff_id}/active")
def staff_active(staff_id: str, payload: StaffActive, request: Request):
    return service_call(set_staff_active, staff_id, payload.active, getattr(request.state, "staff_id", None))


@router.post("/admin/staff/{staff_id}/approve")
def staff_approve_route(staff_id: str, payload: StaffApprove):
    return service_call(staff_approve, staff_id, payload.dict())


@router.post("/admin/staff/{staff_id}/role")
def staff_role_route(staff_id: str, payload: StaffApprove):
    return service_call(staff_set_role, staff_id, payload.dict())


@router.get("/admin/attention")
def attention(request: Request):
    return service_call(get_attention, getattr(request.state, "staff_role", "owner"))


@router.delete("/admin/staff/{staff_id}")
def staff_delete_route(staff_id: str):
    return service_call(staff_delete, staff_id)


@router.get("/admin/resets")
def resets_list():
    return service_call(get_open_resets)


@router.post("/admin/resets", status_code=201)
def reset_issue(payload: ResetIssue, request: Request):
    return service_call(issue_reset_code, payload.dict(), _actor(request))


@router.get("/admin/report")
def report(month: str = ""):
    return service_call(get_report, month or None)


@router.get("/admin/scorecard")
def scorecard():
    return service_call(get_scorecard)


@router.post("/invoices/{invoice_id}/reissue", status_code=201)
def invoice_reissue(invoice_id: str, payload: ReissueInvoice, request: Request):
    return service_call(reissue_invoice, invoice_id, payload.dict(), _actor(request))


@router.post("/invoices/{invoice_id}/void")
def invoice_void(invoice_id: str, payload: VoidInvoice, request: Request):
    return service_call(void_invoice, invoice_id, payload.dict(), _actor(request))


# ----- owner only (see app.core.permissions: /admin/owner and /admin/staff) -----

@router.get("/admin/owner/records")
def owner_list(kind: str = Query(..., max_length=20)):
    return service_call(owner_records, kind)


@router.post("/admin/owner/delete")
def owner_remove(payload: OwnerDelete, request: Request):
    return service_call(owner_delete, payload.dict(), _actor(request))


@router.put("/admin/owner/{kind}/{record_id}")
def owner_update(kind: str, record_id: str, payload: OwnerEdit, request: Request):
    return service_call(owner_edit, kind, record_id, payload.dict(), _actor(request))


@router.post("/admin/agent/register", status_code=201)
def agent_register_route(payload: AgentRegister, request: Request):
    key = getattr(request.state, "staff_id", None) or "admin-key"
    return service_call(agent_register, key, _actor(request), payload.dict())


@router.get("/admin/agent/people")
def agent_people_route(request: Request):
    role = getattr(request.state, "staff_role", None)
    key = getattr(request.state, "staff_id", None) if role == "agent" else None
    return service_call(agent_people, key)


def _agent_key(request):
    role = getattr(request.state, "staff_role", None)
    return getattr(request.state, "staff_id", None) if role == "agent" else None


@router.get("/admin/agent/people/{youth_id}/jobs")
def agent_person_jobs(youth_id: str, request: Request):
    return service_call(agent_person, "jobs", _agent_key(request), _actor(request), youth_id)


@router.get("/admin/agent/people/{youth_id}/work")
def agent_person_work(youth_id: str, request: Request):
    return service_call(agent_person, "work", _agent_key(request), _actor(request), youth_id)


@router.post("/admin/agent/people/{youth_id}/apply/{opportunity_id}", status_code=201)
def agent_person_apply(youth_id: str, opportunity_id: str, request: Request):
    return service_call(agent_person, "apply", _agent_key(request), _actor(request), youth_id, opportunity_id)


@router.post("/admin/agent/people/{youth_id}/evidence", status_code=201)
def agent_person_evidence(youth_id: str, payload: MyEvidenceSubmit, request: Request):
    return service_call(agent_person, "evidence", _agent_key(request), _actor(request), youth_id, payload.dict())


@router.get("/admin/report/csv")
def report_csv_route(month: str = ""):
    from fastapi.responses import Response
    from app.services.report_service import monthly_report, report_csv
    csv = service_call(lambda m: report_csv(monthly_report(m)), month or None)
    return Response(csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bstm-report.csv"})


@router.get("/admin/agent/people/{youth_id}/trials")
def agent_person_trials(youth_id: str, request: Request):
    return service_call(agent_person, "trials", _agent_key(request), _actor(request), youth_id)


@router.post("/admin/agent/people/{youth_id}/work/{assignment_id}/start", status_code=201)
def agent_person_start(youth_id: str, assignment_id: str, request: Request):
    return service_call(agent_person, "start", _agent_key(request), _actor(request), youth_id, assignment_id)


@router.post("/admin/agent/people/{youth_id}/trials/{trial_id}/submit")
def agent_person_submit(youth_id: str, trial_id: str, payload: TrialSubmission, request: Request):
    return service_call(agent_person, "submit", _agent_key(request), _actor(request), youth_id, trial_id, payload.submission)
