"""Two people pressing the same button at the same moment (real Postgres locks)."""
import threading

from app.core.errors import Conflict
from app.services import assignment_service, payment_service
from tests.test_ledger_flows import _completed_job


def _race(fns):
    """Run each callable in its own thread, released together. Returns (ok, errors)."""
    gate, ok, errs = threading.Barrier(len(fns)), [], []

    def run(fn):
        gate.wait()
        try:
            ok.append(fn())
        except Exception as exc:  # noqa: BLE001
            errs.append(exc)

    threads = [threading.Thread(target=run, args=(f,)) for f in fns]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    return ok, errs


def test_two_staff_confirming_one_payment_pay_out_once(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "Race Shop")
    payment_service.set_payout_account(yid, "MyZaka", "Worker", "71234567")
    pid = payment_service.submit_payment(invoice["id"], "MyZaka", provider_ref="MZRACE0001", submitted_by="business", business_id=bid)

    ok, errs = _race([lambda: payment_service.confirm_payment(pid, "staff-a"), lambda: payment_service.confirm_payment(pid, "staff-b")])
    assert len(ok) == 1 and len(errs) == 1 and isinstance(errs[0], Conflict)
    payouts = payment_service.list_payouts(status="Pending")
    assert len(payouts) == 1 and float(payouts[0]["amount"]) == 700.0


def test_two_staff_marking_one_payout_paid_records_one(test_database):
    bid, yid, aid, invoice = _completed_job(1000, "Race Payout")
    payment_service.set_payout_account(yid, "MyZaka", "Worker", "71234567")
    pid = payment_service.submit_payment(invoice["id"], "MyZaka", provider_ref="MZRACE0002", submitted_by="business", business_id=bid)
    payment_service.confirm_payment(pid)
    payout = payment_service.list_payouts(status="Pending")[0]["id"]

    ok, errs = _race([lambda: payment_service.mark_payout_paid(payout, "OUT-A"), lambda: payment_service.mark_payout_paid(payout, "OUT-B")])
    assert len(ok) == 1 and len(errs) == 1 and isinstance(errs[0], Conflict)
    assert float(payment_service.youth_earnings(yid)["totals"]["paid_out"]) == 700.0   # counted once, not twice
