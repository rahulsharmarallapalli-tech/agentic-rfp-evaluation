"""Never trust proposal instructions, model IDs, score ranges or evidence claims."""
import json
import math
import re

from .models import Criterion, CriterionResult, Evaluation


class InvalidResponse(ValueError):
    pass


def parse_json(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 200_000:
        raise InvalidResponse("Missing or oversized JSON response.")
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        def reject_constant(value):
            raise ValueError(value)
        value = json.loads(raw, parse_constant=reject_constant)
    except (ValueError, TypeError) as exc:
        raise InvalidResponse("Model returned malformed JSON.") from exc
    if not isinstance(value, dict) or not isinstance(value.get("criteria"), list):
        raise InvalidResponse("Response must be an object with a criteria array.")
    return value


def _normalize(text):
    return " ".join(text.split()).casefold()


def validate_response(raw: str, criteria: list[Criterion], supplier_name: str, pages: list[dict]) -> Evaluation:
    data = parse_json(raw)
    warnings, by_id = [], {}
    ids = {c.criterion_id for c in criteria}
    if data.get("supplier_name") != supplier_name:
        warnings.append("Model supplier name missing or mismatched; trusted input metadata used.")
    for item in data["criteria"]:
        if not isinstance(item, dict):
            warnings.append("Non-object criterion ignored.")
            continue
        cid = item.get("criterion_id")
        if type(cid) is not int or cid not in ids:
            warnings.append("Unknown or malformed criterion ID ignored.")
            continue
        if cid in by_id:
            warnings.append(f"Duplicate criterion {cid}; first occurrence retained.")
            continue
        by_id[cid] = item
    results = []
    for c in criteria:
        w = []
        item = by_id.get(c.criterion_id, {})
        if not item:
            w.append("Missing criterion; score set to zero.")
        score = item.get("score", 0)
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            score = 0
            w.append("Non-numeric or non-finite score; set to zero.")
        if score < 0 or score > c.max_score:
            score = min(max(score, 0), c.max_score)
            w.append("Score clipped to the configured range.")
        if item and item.get("max_score") != c.max_score:
            w.append("Model maximum replaced with the database maximum.")
        evidence = item.get("evidence", "")
        evidence = evidence.strip() if isinstance(evidence, str) else ""
        page = item.get("evidence_page")
        matched = [p["page"] for p in pages if evidence and _normalize(evidence) in _normalize(p["text"])]
        verified = bool(matched)
        if not verified:
            if score:
                w.append("Evidence absent or not found in PDF; unsupported score set to zero.")
            else:
                w.append("No verified evidence for this criterion.")
            score, page = 0, None
        elif type(page) is not int or page not in matched:
            page = matched[0]
            w.append("Evidence page located from the extracted PDF text.")
        justification = item.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            justification = "No justification supplied; manual review recommended."
            w.append("Missing justification.")
        results.append(CriterionResult(criterion_id=c.criterion_id, score=score, max_score=c.max_score,
                       evidence=evidence, evidence_page=page, evidence_verified=verified,
                       justification=justification, warnings=w))
    risks = data.get("risks", [])
    if not isinstance(risks, list) or not all(isinstance(r, str) for r in risks):
        risks = ["Malformed risk list; manual review needed."]
        warnings.append("Invalid risk list normalized.")
    summary = data.get("overall_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Summary unavailable; inspect the criterion evidence."
        warnings.append("Missing summary.")
    return Evaluation(supplier_name=supplier_name, criteria=results, risks=risks,
                      overall_summary=summary, warnings=warnings)
