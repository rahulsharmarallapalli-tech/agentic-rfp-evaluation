"""All arithmetic and final ordering are Python-owned, with exact Decimal math."""
from decimal import Decimal, localcontext

from .models import active_criteria


def rank_suppliers(suppliers: list[dict], criteria: list) -> list[dict]:
    criteria = active_criteria(criteria)
    if not suppliers:
        return []
    D = lambda x: Decimal(str(x))
    with localcontext() as ctx:
        ctx.prec = 40
        benchmark = {c.criterion_id: max(D(next(r["score"] for r in s["evaluation"]["criteria"]
                     if r["criterion_id"] == c.criterion_id)) for s in suppliers) for c in criteria}
        out = []
        for s in suppliers:
            metrics, absolute, ppi = [], Decimal(0), Decimal(0)
            by_id = {r["criterion_id"]: r for r in s["evaluation"]["criteria"]}
            for c in criteria:
                score, bench = D(by_id[c.criterion_id]["score"]), benchmark[c.criterion_id]
                relative = score / bench * 100 if bench else Decimal(0)
                weighted = score / D(c.max_score) * D(c.weight)
                absolute += weighted
                ppi += relative * D(c.weight) / 100
                metrics.append({**by_id[c.criterion_id], "criterion_name": c.name, "weight": c.weight,
                    "weighted_score": float(weighted), "benchmark": float(bench), "gap": float(score-bench),
                    "relative_percent": float(relative)})
            out.append({**s, "metrics": metrics, "absolute_score": float(absolute),
                        "ppi": float(ppi), "_ppi": ppi})
        out.sort(key=lambda s: (-s["_ppi"], s["submission_date"], -D(s["experience_rating"]),
                              s["supplier_name"].casefold(), s["supplier_name"]))
        for i, s in enumerate(out):
            s["final_rank"] = i + 1
            if i == 0:
                s["rank_explanation"] = "First after sorting by PPI, submission date, experience and name."
            else:
                prev = out[i - 1]
                reason = ("higher PPI" if prev["_ppi"] != s["_ppi"] else
                          "earlier submission date" if prev["submission_date"] != s["submission_date"] else
                          "higher historical experience" if prev["experience_rating"] != s["experience_rating"] else
                          "supplier name ascending (case-insensitive)")
                s["rank_explanation"] = f"{prev['supplier_name']} precedes this supplier by {reason}."
        for s in out:
            del s["_ppi"]
        return out
