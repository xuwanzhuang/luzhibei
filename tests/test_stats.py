from app import stats


def _d(label, conf=0.9):
    return {"category": stats.category_of(label), "label": label, "confidence": conf}


def test_category_mapping():
    assert stats.category_of("fire") == "fire"
    assert stats.category_of("smoke") == "smoke"
    assert stats.category_of("person") == "other"


def test_single_counts_and_risk_high():
    res = stats.compute_single([_d("fire"), _d("smoke")])
    assert res["counts"]["fire"] == 1
    assert res["counts"]["smoke"] == 1
    assert res["risk"] == "high"


def test_risk_medium_when_only_smoke():
    res = stats.compute_single([_d("smoke")])
    assert res["risk"] == "medium"


def test_risk_normal_when_empty():
    res = stats.compute_single([])
    assert res["risk"] == "normal"
    assert res["counts"]["total"] == 0


def test_task_stats_accumulate_and_peak():
    ts = stats.TaskStats()
    ts.accumulate([_d("fire"), _d("fire")])
    ts.accumulate([_d("smoke")])
    snap = ts.snapshot()
    assert snap["frames"] == 2
    assert snap["total"]["fire"] == 2
    assert snap["peak"]["fire"] == 2
    assert snap["total"]["smoke"] == 1
    assert snap["risk"] == "high"
