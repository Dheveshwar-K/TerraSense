import pytest
import numpy as np
from app.services.spc_engine import SPCEngine

def test_imr_calculation():
    # Known dataset: 10 observations
    data = [3.4, 3.5, 3.3, 3.6, 3.4, 3.5, 3.7, 3.4, 3.3, 3.5]
    res = SPCEngine.calculate_imr(data, lsl=3.1, usl=3.7)
    
    assert res["chart_type"] == "I-MR"
    assert res["sample_size"] == 10
    assert abs(res["mean"] - 3.46) < 0.05
    
    # Moving ranges
    mr = np.abs(np.diff(data))
    expected_mean_mr = float(np.mean(mr))
    assert abs(res["mean_mr"] - expected_mean_mr) < 1e-4

    # Control limits
    expected_sigma_within = expected_mean_mr / 1.128379
    assert abs(res["sigma_within"] - expected_sigma_within) < 1e-4
    assert res["i_chart"]["ucl"] > res["mean"]
    assert res["i_chart"]["lcl"] < res["mean"]
    assert len(res["points"]) == 10

def test_nelson_rule_1_violation():
    # Mean around 10, sigma=1, single extreme outlier at index 4 (value 20)
    data = [10.0, 10.1, 9.9, 10.0, 20.0, 10.0, 9.8, 10.2]
    res = SPCEngine.calculate_imr(data)
    
    # Point 5 (index 4) should trigger Rule 1 (> 3 sigma)
    p5 = res["points"][4]
    assert p5["is_out_of_control"] is True
    assert any("Rule 1" in v for v in p5["violations"])

def test_process_capability_calculation():
    # Standard normal distribution centered at target 10.0 with std 1.0
    # Spec limits: LSL = 7.0, USL = 13.0
    # Expected Cp = (13 - 7) / (6 * 1.0) = 1.0, Cpk = (13 - 10) / (3 * 1.0) = 1.0
    np.random.seed(42)
    data = list(np.random.normal(loc=10.0, scale=1.0, size=50))
    
    cap = SPCEngine.calculate_capability(data, lsl=7.0, usl=13.0, target=10.0)
    assert cap["can_calculate"] is True
    assert cap["sample_size"] == 50
    assert abs(cap["cp"] - 1.0) < 0.25
    assert abs(cap["cpk"] - 1.0) < 0.25
    assert cap["is_stable"] is True

def test_capability_missing_specs():
    data = [1.0, 2.0, 3.0, 4.0]
    cap = SPCEngine.calculate_capability(data, lsl=None, usl=None)
    assert cap["can_calculate"] is False
    assert "missing" in cap["reason"].lower()
