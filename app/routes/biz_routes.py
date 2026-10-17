"""Business portal routes. Authenticated by the business's own JWT
(role=business); the business id comes from the token, never the URL."""

from fastapi import APIRouter, Header, Request

from app.api.service import (
    biz_accept_applicant,
    biz_approve_work,
    biz_close_job,
    biz_decline_applicant,
    get_biz_invoices,
    get_biz_jobs,
    get_biz_notifications,
    get_biz_people,
    get_biz_profile,
    post_biz_job,
    read_biz_notifications,
    submit_biz_payment,
)
from app.routes.common import service_call
from app.schemas.models import BizApprove, BizJobCreate, PaymentSubmit

router = APIRouter(prefix="/biz", tags=["business"])


def _bid(request):
    return request.state.business_id


@router.get("")
def me(request: Request):
    return service_call(get_biz_profile, _bid(request))


@router.get("/opportunities")
def jobs(request: Request):
    return service_call(get_biz_jobs, _bid(request))


@router.post("/opportunities", status_code=201)
def post_job(payload: BizJobCreate, request: Request):
    return service_call(post_biz_job, _bid(request), payload.dict())


@router.get("/opportunities/{opportunity_id}/people")
def people(opportunity_id: str, request: Request):
    return service_call(get_biz_people, _bid(request), opportunity_id)


@router.get("/invoices")
def invoices(request: Request):
    return service_call(get_biz_invoices, _bid(request))


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def pay(invoice_id: str, payload: PaymentSubmit, request: Request,
        idempotency_key: str = Header(None, alias="Idempotency-Key")):
    return service_call(submit_biz_payment, _bid(request), invoice_id, payload.dict(), idempotency_key)


@router.get("/notifications")
def notifications(request: Request):
    return service_call(get_biz_notifications, _bid(request))


@router.post("/notifications/read")
def read_notifications(request: Request):
    return service_call(read_biz_notifications, _bid(request))


@router.post("/assignments/{assignment_id}/accept")
def accept_applicant_route(assignment_id: str, request: Request):
    return service_call(biz_accept_applicant, _bid(request), assignment_id)


@router.post("/assignments/{assignment_id}/decline")
def decline_applicant_route(assignment_id: str, request: Request):
    return service_call(biz_decline_applicant, _bid(request), assignment_id)


@router.post("/trials/{trial_id}/approve")
def approve_work_route(trial_id: str, payload: BizApprove, request: Request):
    return service_call(biz_approve_work, _bid(request), trial_id, payload.dict())


@router.post("/opportunities/{opportunity_id}/close")
def close_job_route(opportunity_id: str, request: Request):
    return service_call(biz_close_job, _bid(request), opportunity_id)
