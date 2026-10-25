import time
import uuid
from datetime import datetime, timezone

from .db import load_criteria, save_run
from .document import extract_pdf
from .evaluator import ProviderError
from .ranking import rank_suppliers
from .validation import InvalidResponse, validate_response


def evaluate_batch(inputs, db_path, evaluator, progress=None, sleep=time.sleep):
    """Explicit tool routing, bounded repair retries, failure isolation and atomic final save."""
    if not 2 <= len(inputs) <= 10:
        raise ValueError("Evaluate 2-10 suppliers in one batch.")
    names = [s.supplier_name.casefold() for s, _ in inputs]
    if len(set(names)) != len(names):
        raise ValueError("Supplier names must be unique (case-insensitive).")
    criteria = load_criteria(db_path)  # Fresh snapshot at evaluation time.
    run = {"schema_version": "1.0", "rfp_run_id": str(uuid.uuid4()),
           "created_at": datetime.now(timezone.utc).isoformat(), "status": "running",
           "mode": evaluator.mode, "model": evaluator.model,
           "criteria_snapshot": [c.model_dump() for c in criteria], "suppliers": [], "failures": [], "trace": [],
           "rules": {"zero_benchmark": "relative_percent=0; weight retained in PPI denominator",
                     "tie_break": ["PPI descending (unrounded)", "submission_date ascending", "experience_rating descending", "supplier_name ascending (case-insensitive)"],
                     "missing_or_unsupported_evidence": "score=0 with warning", "maximum_attempts_per_supplier": 3}}
    save_run(db_path, run)
    successful = []
    for i, (supplier, content) in enumerate(inputs):
        if progress:
            progress(i / len(inputs), f"Evaluating {supplier.supplier_name}")
        trace = {"supplier_name": supplier.supplier_name, "steps": [], "attempts": 0}
        run["trace"].append(trace)
        try:
            document = extract_pdf(content)
            trace["steps"].append("document_extracted")
            for attempt in range(1, 4):
                trace["attempts"] = attempt
                try:
                    raw = evaluator.evaluate(supplier, criteria, document)
                    trace["steps"].append(f"evaluation_received_attempt_{attempt}")
                    evaluation = validate_response(raw, criteria, supplier.supplier_name, document["pages"])
                    trace["steps"].append("validated")
                    break
                except (InvalidResponse, ProviderError) as exc:
                    trace["steps"].append(f"attempt_{attempt}: {exc}")
                    if attempt == 3 or (isinstance(exc, ProviderError) and not exc.retryable):
                        raise
                    sleep(min(2 ** (attempt - 1), 4))
            successful.append({**supplier.model_dump(mode="json"),
                "document": {k: v for k, v in document.items() if k != "text"},
                "evaluation": evaluation.model_dump()})
        except (ValueError, ProviderError) as exc:
            trace["steps"].append("failed_excluded_from_ranking")
            run["failures"].append({**supplier.model_dump(mode="json"), "error": str(exc)})
    run["suppliers"] = rank_suppliers(successful, criteria)
    run["status"] = "failed" if not successful else "partial" if run["failures"] else "completed"
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    run["trace"].append({"steps": ["deterministic_scoring", "peer_benchmarking", "stable_ranking", "persisted"]})
    save_run(db_path, run)
    if progress:
        progress(1.0, "Evaluation saved")
    return run
