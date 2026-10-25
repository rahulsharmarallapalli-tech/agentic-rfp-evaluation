import json
from pathlib import Path
import pymupdf
import pytest
from rfp.db import connect, get_run, init_db, list_runs, load_criteria, save_criteria
from rfp.document import extract_pdf
from rfp.evaluator import FixtureEvaluator, ProviderError
from rfp.models import Supplier
from rfp.orchestrator import evaluate_batch

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    manifest = json.loads((ROOT / "samples/manifest.json").read_text())
    return [(Supplier(**{k:m[k] for k in ("supplier_name","submission_date","experience_rating")}),
             (ROOT / "samples/proposals" / m["pdf_file"]).read_bytes()) for m in manifest]


def test_demo_persistence_and_reproducibility(db):
    evaluator = FixtureEvaluator(ROOT / "samples")
    run = evaluate_batch(inputs(),db,evaluator)
    assert run["status"] == "completed"
    assert [s["supplier_name"] for s in run["suppliers"]] == ["NexaWorks","Apex Systems","Orbit Digital","BrightPath Tech"]
    assert [s["absolute_score"] for s in run["suppliers"]] == [83,79,66,58]
    assert all(s["document"]["page_count"] == 3 for s in run["suppliers"])
    assert get_run(db,run["rfp_run_id"]) == run
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM supplier_results").fetchone()[0] == 4
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    again = evaluate_batch(inputs(),db,evaluator)
    assert run["suppliers"] == again["suppliers"]
    assert len(list_runs(db)) == 2


def test_criteria_edit_is_atomic_and_history_snapshot_immutable(db):
    run = evaluate_batch(inputs(),db,FixtureEvaluator(ROOT / "samples"))
    rows = [c.model_dump() for c in load_criteria(db)]
    rows[0]["weight"] = 99
    with pytest.raises(ValueError):
        save_criteria(db,rows)
    assert load_criteria(db)[0].weight == 30
    rows[0]["weight"],rows[1]["weight"] = 40,10
    save_criteria(db,rows)
    new = evaluate_batch(inputs(),db,FixtureEvaluator(ROOT / "samples"))
    assert new["criteria_snapshot"][0]["weight"] == 40
    assert get_run(db,run["rfp_run_id"])["criteria_snapshot"][0]["weight"] == 30
    init_db(db)
    assert load_criteria(db)[0].weight == 40


def test_criteria_activation(db):
    rows = [c.model_dump() for c in load_criteria(db)]
    rows[-1]["is_active"] = False
    rows[0]["weight"] += 10
    save_criteria(db,rows)
    assert len(load_criteria(db)) == 4


class BrokenEvaluator:
    mode, model = "test", "test"
    def __init__(self, response="bad json", error=None):
        self.calls,self.response,self.error = 0,response,error
    def evaluate(self,*args):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


def test_malformed_json_bounded_retries(db):
    evaluator = BrokenEvaluator()
    sleeps=[]
    run = evaluate_batch(inputs()[:2],db,evaluator,sleep=sleeps.append)
    assert evaluator.calls == 6
    assert sleeps == [1,2,1,2]
    assert run["status"] == "failed" and not run["suppliers"]
    assert len(run["failures"]) == 2
    assert get_run(db,run["rfp_run_id"])["status"] == "failed"


def test_provider_auth_not_retried(db):
    evaluator=BrokenEvaluator(error=ProviderError("HTTP 401",False))
    evaluate_batch(inputs()[:2],db,evaluator,sleep=lambda _:None)
    assert evaluator.calls == 2


def test_retry_recovers(db, raw):
    class Recover(BrokenEvaluator):
        def evaluate(self,*args):
            self.calls+=1
            return "broken" if self.calls == 1 else json.dumps(raw)
    evaluator=Recover()
    run=evaluate_batch(inputs()[:2],db,evaluator,sleep=lambda _:None)
    assert run["status"] == "completed"
    assert run["trace"][0]["attempts"] == 2


def test_failed_pdf_excluded_partial_run(db):
    items=inputs()[:2]
    items[1]=(items[1][0],b"not a PDF")
    run=evaluate_batch(items,db,FixtureEvaluator(ROOT / "samples"))
    assert run["status"] == "partial" and len(run["suppliers"]) == 1
    assert run["suppliers"][0]["ppi"] == 100


def test_duplicate_supplier_rejected(db):
    items=inputs()
    with pytest.raises(ValueError,match="unique"):
        evaluate_batch([items[0],items[0]],db,FixtureEvaluator(ROOT / "samples"))
    assert not list_runs(db)


@pytest.mark.parametrize("content", [b"", b"not pdf", b"%PDF-broken", b"x"*(10*1024*1024+1)])
def test_invalid_pdf(content):
    with pytest.raises(ValueError):
        extract_pdf(content)


def test_blank_pdf():
    with pymupdf.open() as doc:
        doc.new_page()
        content=doc.tobytes()
    with pytest.raises(ValueError,match="selectable"):
        extract_pdf(content)


def test_encrypted_pdf(proposal):
    with pymupdf.open(stream=proposal,filetype="pdf") as doc:
        content=doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256,owner_pw="owner",user_pw="secret")
    with pytest.raises(ValueError,match="Password"):
        extract_pdf(content)
