"""Bond settlement conserves value for every input and every verdict."""

import pytest
from circuitlib.accounting import conserved, settle

NON_CONFIRMING = [
    "NOT_CONFIRMED",
    "INSUFFICIENT",
    "CONFLICTING",
    "STALE",
    "TAMPERED",
]


def test_confirmed_returns_bond_and_routes_fee():
    s = settle("TRIGGER_CONFIRMED", 110, 10)
    assert s == {"assessor": 100, "treasury": 10, "total": 110}
    assert conserved(s)


@pytest.mark.parametrize("decision", NON_CONFIRMING)
def test_non_confirming_refunds_everything(decision):
    s = settle(decision, 110, 10)
    assert s == {"assessor": 110, "treasury": 0, "total": 110}
    assert conserved(s)


@pytest.mark.parametrize("attached,fee", [(0, 0), (5, 0), (5, 5), (5, 9), (0, 7), (123456, 456)])
def test_conservation_holds(attached, fee):
    for decision in ("TRIGGER_CONFIRMED", "INSUFFICIENT", "NOT_CONFIRMED"):
        assert conserved(settle(decision, attached, fee))


def test_negative_fee_is_clamped():
    assert settle("TRIGGER_CONFIRMED", 50, -5) == {
        "assessor": 50,
        "treasury": 0,
        "total": 50,
    }


def test_fee_cannot_exceed_attached():
    s = settle("TRIGGER_CONFIRMED", 5, 9)
    assert s["treasury"] == 5 and s["assessor"] == 0
    assert conserved(s)
