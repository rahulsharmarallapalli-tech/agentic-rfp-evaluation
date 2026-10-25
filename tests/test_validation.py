import json
import pytest
from rfp.document import extract_pdf
from rfp.validation import InvalidResponse, parse_json, validate_response


@pytest.mark.parametrize("raw", ["{broken", "[]", "null", '{"criteria":null}', '{"criteria":[],"score":NaN}', '{"criteria":[],"score":Infinity}'])
def test_malformed_json_rejected(raw):
    with pytest.raises(InvalidResponse):
        parse_json(raw)


def test_code_fences_accepted():
    assert parse_json('```json\n{"criteria":[]}\n```') == {"criteria": []}


def test_valid_evidence(criteria, proposal, raw):
    result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    assert [c.score for c in result.criteria] == [9,7,6,9,8]
    assert all(c.evidence_verified and not c.warnings for c in result.criteria)


def test_missing_and_clipped(criteria, proposal, raw):
    raw["criteria"] = raw["criteria"][:2]
    raw["criteria"][0]["score"] = 200
    raw["criteria"][1]["score"] = -5
    result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    assert [c.score for c in result.criteria] == [10,0,0,0,0]
    assert all(c.warnings for c in result.criteria)


@pytest.mark.parametrize("score", ["9", True, None, {}, [], 1e309])
def test_invalid_scores_zero(criteria, proposal, raw, score):
    raw["criteria"][0]["score"] = score
    if score == float("inf"):
        with pytest.raises(InvalidResponse):
            validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    else:
        result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
        assert result.criteria[0].score == 0


def test_duplicate_unknown_id_name_max_and_page(criteria, proposal, raw):
    raw["supplier_name"] = "Impostor"
    raw["criteria"][0]["max_score"] = 999
    raw["criteria"][0]["evidence_page"] = 99
    raw["criteria"].extend([raw["criteria"][0], {"criterion_id":999}, {"criterion_id":[]}])
    result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    assert result.supplier_name == "Apex Systems"
    assert result.criteria[0].max_score == 10
    assert result.criteria[0].evidence_page == 1
    assert len(result.criteria) == 5
    assert len(result.warnings) == 4


def test_invented_evidence_zero(criteria, proposal, raw):
    raw["criteria"][0]["evidence"] = "Invented certification XYZ 987"
    result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    assert result.criteria[0].score == 0
    assert not result.criteria[0].evidence_verified


def test_malformed_optional_fields(criteria, proposal, raw):
    raw.update(risks={},overall_summary=42)
    raw["criteria"][0].update(justification=None,evidence={})
    result = validate_response(json.dumps(raw), criteria, "Apex Systems", extract_pdf(proposal)["pages"])
    assert result.criteria[0].score == 0
    assert len(result.warnings) == 2
