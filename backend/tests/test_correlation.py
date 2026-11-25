import pytest

from app.services.correlation_engine import CorrelationEngine, apply_benjamini_hochberg


def test_correlation_positive_association():
    sand_points = [
        {"timestamp": f"2026-03-01T{h:02d}:00:00Z", "value": 3.0 + h * 0.1, "is_out_of_spec": False}
        for h in range(1, 20)
    ]
    rejection_points = [
        {"timestamp": f"2026-03-01T{h + 6:02d}:00:00Z", "rejection_rate": 1.5 + h * 0.2, "rejected_qty": 5, "inspected_qty": 200}
        for h in range(1, 14)
    ]

    res = CorrelationEngine.analyze_pair(
        parameter_name="Moisture Content",
        defect_name="Porosity",
        line_code="D2",
        sand_points=sand_points,
        rejection_points=rejection_points,
        lag_hours=6,
        usl=3.7,
        lsl=3.1,
    )

    assert res["has_sufficient_data"] is True
    assert res["sample_size"] > 5
    assert res["pearson_r"] > 0.9
    assert res["spearman_rho"] > 0.9
    assert res["pearson_ci_95"] is not None
    assert "correlation does not prove causation" in res["insight"].lower()


def test_correlation_negative_association_wording():
    sand_points = [
        {"timestamp": f"2026-03-01T{h:02d}:00:00Z", "value": 140.0 - h * 2.0, "is_out_of_spec": False}
        for h in range(1, 15)
    ]
    rejection_points = [
        {"timestamp": f"2026-03-01T{h:02d}:00:00Z", "rejection_rate": 1.0 + h * 0.3, "rejected_qty": 5, "inspected_qty": 200}
        for h in range(1, 15)
    ]
    res = CorrelationEngine.analyze_pair(
        parameter_name="Permeability",
        defect_name="Blowholes",
        line_code="D3",
        sand_points=sand_points,
        rejection_points=rejection_points,
        lag_hours=0,
        usl=160.0,
        lsl=115.0,
    )
    assert res["pearson_r"] < -0.5
    assert "negative (inverse)" in res["insight"].lower() or "association" in res["insight"].lower()
    assert "positive association" not in res["insight"].lower()


def test_no_future_data_leakage_at_zero_lag():
    # Rejections occur at 08:00..13:00; sand tests ONLY occur at 10:00..15:00 AFTER each earlier rejection
    sand_points = [
        {"timestamp": "2026-03-01T14:00:00Z", "value": 4.2, "is_out_of_spec": True},
    ]
    rejection_points = [
        {"timestamp": f"2026-03-01T{h:02d}:00:00Z", "rejection_rate": 2.0, "rejected_qty": 4, "inspected_qty": 200}
        for h in range(11, 14)  # 11:00, 12:00, 13:00 (all BEFORE 14:00 sand point)
    ]
    res = CorrelationEngine.analyze_pair(
        parameter_name="Moisture",
        defect_name="Porosity",
        line_code="D1",
        sand_points=sand_points,
        rejection_points=rejection_points,
        lag_hours=0,
    )
    # 14:00 sand point is within 3h of 12:00/13:00, but MUST NOT match because s_time > rej_time!
    assert res["sample_size"] == 0
    assert res["has_sufficient_data"] is False


def test_benjamini_hochberg_fdr():
    raw = [0.001, 0.01, 0.04, 0.50]
    adj = apply_benjamini_hochberg(raw)
    assert adj == [0.004, 0.02, 0.0533, 0.5]
