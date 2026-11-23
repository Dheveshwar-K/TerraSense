import pytest
from app.services.correlation_engine import CorrelationEngine

def test_correlation_positive_association():
    # Create synthetic sand data and rejection data showing positive relationship
    sand_points = [
        {"timestamp": f"2026-03-01T{h:02d}:00:00Z", "value": 3.0 + h * 0.1, "is_out_of_spec": False}
        for h in range(1, 20)
    ]
    rejection_points = [
        {"timestamp": f"2026-03-01T{h+6:02d}:00:00Z", "rejection_rate": 1.5 + h * 0.2, "rejected_qty": 5, "inspected_qty": 200}
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
        lsl=3.1
    )

    assert res["has_sufficient_data"] is True
    assert res["sample_size"] > 5
    assert res["pearson_r"] > 0.5  # Positive correlation
    assert res["relationship_strength"] in ["STRONG", "VERY_STRONG"]
    # Check that causation disclaimer is present
    assert "correlation does not prove causation" in res["insight"].lower()
