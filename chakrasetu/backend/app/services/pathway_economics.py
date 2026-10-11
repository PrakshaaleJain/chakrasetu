"""Comparable transaction/NPV calculations with explicit missing-value handling."""

from datetime import datetime
from ..decision_schemas import COMPONENTS


def financial_result(path, finance, timestamp):
    if not finance:
        return {
            "complete": False,
            "missing": ["benefits", *COMPONENTS[path]],
            "net_paise": None,
            "range_paise": None,
            "inputs": {},
            "provisional": True,
        }
    costs, benefits = finance.get("costs", {}), finance.get("benefits", [])
    missing = [k for k in COMPONENTS[path] if k not in costs]
    if not benefits:
        missing.append("benefits")
    values = [*benefits, *costs.values()]
    for v in values:
        if (
            v.get("valid_until") is None
            or datetime.fromisoformat(v["valid_until"]) <= timestamp
        ):
            missing.append("expired_or_undated_input: " + v.get("reference", "unknown"))
        if (
            v.get("recorded_at")
            and datetime.fromisoformat(v["recorded_at"]) > timestamp
        ):
            missing.append("future_dated_input: " + v.get("reference", "unknown"))
    rate = finance.get("discount_rate") or 0

    def weight(v):
        start = v.get("year", 0)
        end = v.get("repeat_through_year")
        return sum(
            1 / ((1 + rate) ** year)
            for year in range(start, (end if end is not None else start) + 1)
        )

    def pv(v):
        return v["amount_paise"] * weight(v)

    net = (
        None
        if missing
        else round(sum(pv(v) for v in benefits) - sum(pv(v) for v in costs.values()))
    )
    uncertainty = round(sum(v.get("uncertainty_paise", 0) * weight(v) for v in values))
    return {
        "complete": not missing,
        "missing": list(dict.fromkeys(missing)),
        "net_paise": net,
        "range_paise": (
            [net - uncertainty, net + uncertainty] if net is not None else None
        ),
        "currency": "INR",
        "basis": finance["basis"],
        "horizon_years": finance["horizon_years"],
        "discount_rate": finance.get("discount_rate"),
        "perspective": finance["perspective"],
        "inputs": finance,
        "provisional": any(v["source"] != "ACTUAL_QUOTE" for v in values),
        "formula": "Present value of explicit benefits minus all required explicit costs; no omitted cost is assumed zero.",
    }
