"""Bond settlement — the arithmetic that decides who is paid what.

One function, and one invariant: `assessor + treasury == attached`, for every
input and every outcome. The contract holds exactly the value an assessor
posted, so a settlement that did not conserve value would either strand GEN in
the contract or pay out more than it took in. `conserved` exists so the
property is asserted in tests rather than assumed.

No genlayer imports.
"""

TRIGGER_CONFIRMED = "TRIGGER_CONFIRMED"


def settle(decision, attached, fee_amount):
    """Split an incident's attached value for one verdict.

    A non-confirming verdict refunds everything: the bond is returned in full
    and nothing is charged, because the assessor did the work and the charter
    simply was not tripped. A confirmed verdict returns the assessor's bond in
    full and routes the disclosed fee to the treasury. In both cases the split
    sums to exactly `attached`.
    """
    attached = int(attached)
    fee_amount = int(fee_amount)
    if fee_amount < 0:
        fee_amount = 0
    fee = fee_amount if fee_amount <= attached else attached
    bond = attached - fee
    if decision == TRIGGER_CONFIRMED:
        return {"assessor": bond, "treasury": fee, "total": attached}
    return {"assessor": attached, "treasury": 0, "total": attached}


def conserved(settlement):
    return settlement["assessor"] + settlement["treasury"] == settlement["total"]
