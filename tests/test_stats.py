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


def test_by_label_counts_real_categories():
    res = stats.compute_single([_d("fire"), _d("person"), _d("person"), _d("car")])
    assert res["by_label"]["person"] == 2
    assert res["by_label"]["car"] == 1
    assert res["by_label"]["fire"] == 1


def test_alerts_fire_is_alarm_and_risk_high():
    res = stats.compute_single([_d("fire")])
    assert res["alerts"] == [{"label": "fire", "level": "alarm"}]
    assert res["risk"] == "high"


def test_alerts_smoke_only_is_warn_and_risk_medium():
    res = stats.compute_single([_d("smoke")])
    assert res["alerts"] == [{"label": "smoke", "level": "warn"}]
    assert res["risk"] == "medium"


def test_alerts_ignore_labels_without_rules():
    res = stats.compute_single([_d("person"), _d("car")])
    assert res["alerts"] == []
    assert res["risk"] == "normal"


def test_task_stats_tracks_by_label_and_peak():
    ts = stats.TaskStats()
    ts.accumulate([_d("person"), _d("person")])
    ts.accumulate([_d("person"), _d("smoke")])
    snap = ts.snapshot()
    assert snap["by_label"]["person"] == 3
    assert snap["peak"]["person"] == 2
    assert snap["peak"]["total"] == 2
    assert snap["alerts"] == [{"label": "smoke", "level": "warn"}]
    assert snap["risk"] == "medium"


def test_task_stats_current_is_latest_frame():
    ts = stats.TaskStats()
    ts.accumulate([_d("person"), _d("person")])
    ts.accumulate([_d("smoke")])
    snap = ts.snapshot()
    assert snap["current"]["counts"]["total"] == 1
    assert snap["current"]["by_label"] == {"smoke": 1}
    assert snap["current"]["alerts"] == [{"label": "smoke", "level": "warn"}]
    assert snap["by_label"]["person"] == 2
