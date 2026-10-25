import pytest
from rfp.models import Criterion
from rfp.ranking import rank_suppliers


def criteria():
    return [Criterion(criterion_id=1,name="A",description="A",weight=60,max_score=10),
            Criterion(criterion_id=2,name="B",description="B",weight=40,max_score=20)]


def supplier(name, scores, day="2026-01-01", experience=5):
    return {"supplier_name":name,"submission_date":day,"experience_rating":experience,
            "evaluation":{"criteria":[{"criterion_id":i+1,"score":s} for i,s in enumerate(scores)]}}


def test_independent_hand_calculated_values():
    ranked = rank_suppliers([supplier("A",[8,10]),supplier("B",[4,20])],criteria())
    a,b = ranked
    assert a["supplier_name"] == "A"
    assert a["absolute_score"] == pytest.approx(68)  # 8/10*60 + 10/20*40
    assert b["absolute_score"] == pytest.approx(64)
    assert a["ppi"] == pytest.approx(80)  # 100*.6 + 50*.4
    assert b["ppi"] == pytest.approx(70)
    assert a["metrics"][1]["benchmark"] == 20
    assert a["metrics"][1]["gap"] == -10
    assert a["metrics"][1]["relative_percent"] == 50


def test_zero_benchmark_retains_weight():
    ranked = rank_suppliers([supplier("A",[5,0]),supplier("B",[0,0])],criteria())
    assert ranked[0]["ppi"] == 60
    assert ranked[0]["metrics"][1]["relative_percent"] == 0
    assert ranked[1]["ppi"] == 0


def test_all_tie_break_levels_and_sequential_ranks():
    inputs = [supplier("Zulu",[8,10],"2026-01-02",10),
              supplier("beta",[8,10],"2026-01-01",7),
              supplier("Alpha",[8,10],"2026-01-01",7),
              supplier("Experienced",[8,10],"2026-01-01",9),
              supplier("Winner",[9,20],"2026-01-03",0)]
    ranked = rank_suppliers(inputs,criteria())
    assert [s["supplier_name"] for s in ranked] == ["Winner","Experienced","Alpha","beta","Zulu"]
    assert [s["final_rank"] for s in ranked] == [1,2,3,4,5]
    assert "higher PPI" in ranked[1]["rank_explanation"]
    assert "higher historical experience" in ranked[2]["rank_explanation"]
    assert "supplier name" in ranked[3]["rank_explanation"]
    assert "earlier submission" in ranked[4]["rank_explanation"]
    assert ranked == rank_suppliers(list(reversed(inputs)),criteria())


def test_unrounded_ppi_controls_order():
    ranked = rank_suppliers([supplier("A",[8,10]),supplier("Z",[8.00001,10])],criteria())
    assert round(ranked[0]["ppi"],2) == round(ranked[1]["ppi"],2)
    assert ranked[0]["supplier_name"] == "Z"


def test_empty_cohort():
    assert rank_suppliers([],criteria()) == []
