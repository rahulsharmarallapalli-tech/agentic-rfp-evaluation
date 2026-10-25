import argparse
import json
from pathlib import Path
from rfp.db import init_db
from rfp.models import Supplier
from rfp.evaluator import FixtureEvaluator
from rfp.orchestrator import evaluate_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/demo.sqlite")
    parser.add_argument("--output", default="samples/completed_run.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "samples"
    manifest = json.loads((root / "manifest.json").read_text())
    inputs = [(Supplier(**{k:m[k] for k in ("supplier_name","submission_date","experience_rating")}),
               (root / "proposals" / m["pdf_file"]).read_bytes()) for m in manifest]
    init_db(args.db)
    run = evaluate_batch(inputs, args.db, FixtureEvaluator(root))
    Path(args.output).write_text(json.dumps(run,indent=2))
    print(f"Run {run['rfp_run_id']}: {run['status']} (OFFLINE FIXTURES)")
    for s in run["suppliers"]:
        print(f"{s['final_rank']}. {s['supplier_name']}: absolute={s['absolute_score']:.2f}, PPI={s['ppi']:.2f}")
    if run["failures"]:
        raise RuntimeError(run["failures"])


if __name__ == "__main__":
    main()
