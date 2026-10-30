"""Youth self-service routes. Everything here is authenticated by the
youth's own JWT (middleware) and acts only on that youth's own data:
the id comes from the token, never from the URL."""

from fastapi import APIRouter, Query, Request

from app.api.service import (
    change_my_password,
    delete_my_account,
    export_my_data,
    accept_my_assignment,
    apply_to_opportunity,
    browse_my_opportunities,
    cancel_my_trial,
    claim_my_capability,
    create_my_trial,
    decline_my_assignment,
    get_my_assignments,
    get_my_earnings,
    get_my_notifications,
    get_my_payout_account,
    read_my_notifications,
    set_my_payout_account,
    update_my_profile,
    get_my_brief,
    get_my_capabilities,
    get_my_evidence,
    get_my_matches,
    get_my_profile,
    get_my_trial,
    get_my_trials,
    submit_my_evidence,
    submit_my_trial,
    withdraw_my_assignment,
)
from app.routes.common import service_call, youth_id_of
from app.schemas.models import (
    DeleteAccount,
    CapabilityAssign,
    PayoutAccountSet,
    ProfileUpdate,
    MyEvidenceSubmit,
    TrialCancel,
    PasswordChange,
    TrialSubmission,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def my_profile(request: Request):
    return service_call(get_my_profile, youth_id_of(request))


@router.get("/brief")
def brief(request: Request):
    return service_call(get_my_brief, youth_id_of(request))


@router.get("/capabilities")
def my_capabilities(request: Request):
    return service_call(get_my_capabilities, youth_id_of(request))


@router.post("/capabilities", status_code=201)
def claim_capability(payload: CapabilityAssign, request: Request):
    return service_call(claim_my_capability, youth_id_of(request), payload.dict())


@router.get("/opportunities")
def my_matches(request: Request):
    return service_call(get_my_matches, youth_id_of(request))


@router.get("/opportunities/browse")
def browse_opportunities(
    request: Request,
    q: str = Query(None, max_length=80),
    location: str = Query(None, max_length=120),
    department: str = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return service_call(browse_my_opportunities, youth_id_of(request), q, location, department, limit, offset)


@router.post("/opportunities/{opportunity_id}/apply", status_code=201)
def apply(opportunity_id: str, request: Request):
    return service_call(apply_to_opportunity, youth_id_of(request), opportunity_id)


@router.get("/assignments")
def my_assignments(request: Request):
    return service_call(get_my_assignments, youth_id_of(request))


@router.post("/assignments/{assignment_id}/accept")
def accept_assignment_route(assignment_id: str, request: Request):
    return service_call(accept_my_assignment, youth_id_of(request), assignment_id)


@router.post("/assignments/{assignment_id}/decline")
def decline_assignment_route(assignment_id: str, request: Request):
    return service_call(decline_my_assignment, youth_id_of(request), assignment_id)


@router.post("/assignments/{assignment_id}/withdraw")
def withdraw_assignment_route(assignment_id: str, request: Request):
    return service_call(withdraw_my_assignment, youth_id_of(request), assignment_id)


@router.post("/assignments/{assignment_id}/trial", status_code=201)
def start_my_trial(assignment_id: str, request: Request):
    return service_call(create_my_trial, youth_id_of(request), assignment_id)


@router.get("/trials")
def my_trials(request: Request):
    return service_call(get_my_trials, youth_id_of(request))


@router.get("/trials/{trial_id}")
def my_trial(trial_id: str, request: Request):
    return service_call(get_my_trial, youth_id_of(request), trial_id)


@router.post("/trials/{trial_id}/submit")
def submit_trial_route(trial_id: str, payload: TrialSubmission, request: Request):
    return service_call(submit_my_trial, youth_id_of(request), trial_id, payload.submission)


@router.post("/trials/{trial_id}/cancel")
def cancel_trial_route(trial_id: str, payload: TrialCancel, request: Request):
    return service_call(cancel_my_trial, youth_id_of(request), trial_id, payload.reason)


@router.get("/evidence")
def my_evidence(request: Request):
    return service_call(get_my_evidence, youth_id_of(request))


@router.post("/evidence", status_code=201)
def add_evidence(payload: MyEvidenceSubmit, request: Request):
    return service_call(submit_my_evidence, youth_id_of(request), payload.dict())


@router.put("/profile")
def profile_update(payload: ProfileUpdate, request: Request):
    return service_call(update_my_profile, youth_id_of(request), payload.dict())


@router.get("/payout-account")
def payout_account(request: Request):
    return service_call(get_my_payout_account, youth_id_of(request))


@router.put("/payout-account")
def payout_account_set(payload: PayoutAccountSet, request: Request):
    return service_call(set_my_payout_account, youth_id_of(request), payload.dict())


@router.get("/earnings")
def earnings(request: Request):
    return service_call(get_my_earnings, youth_id_of(request))


@router.get("/notifications")
def notifications(request: Request):
    return service_call(get_my_notifications, youth_id_of(request))


@router.post("/notifications/read")
def notifications_read(request: Request):
    return service_call(read_my_notifications, youth_id_of(request))


@router.get("/export")
def export(request: Request):
    return service_call(export_my_data, youth_id_of(request))


@router.post("/delete")
def delete_account(payload: DeleteAccount, request: Request):
    return service_call(delete_my_account, youth_id_of(request), payload.dict())


@router.put("/password")
def password_change(payload: PasswordChange, request: Request):
    return service_call(change_my_password, youth_id_of(request), payload.dict())
