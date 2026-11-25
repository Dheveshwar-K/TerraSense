import math
import numpy as np
import pytest

from app.services.spc_engine import D2_MR2, SPCEngine


def test_imr_calculation_manual_verification():
    data = [3.4, 3.5, 3.3, 3.6, 3.4, 3.5, 3.7, 3.4, 3.3, 3.5]
    res = SPCEngine.calculate_imr(data, lsl=3.1, usl=3.7)

    assert res["chart_type"] == "I-MR"
    assert res["sample_size"] == 10
    expected_mean = sum(data) / len(data)
    mr = [abs(data[i] - data[i - 1]) for i in range(1, len(data))]
    expected_mean_mr = sum(mr) / len(mr)
    expected_sigma_within = expected_mean_mr / D2_MR2

    assert abs(res["mean"] - expected_mean) < 1e-4
    assert abs(res["mean_mr"] - expected_mean_mr) < 1e-4
    assert abs(res["sigma_within"] - expected_sigma_within) < 1e-4
    assert abs(res["i_chart"]["ucl"] - (expected_mean + 3.0 * expected_sigma_within)) < 1e-3
    assert abs(res["i_chart"]["lcl"] - (expected_mean - 3.0 * expected_sigma_within)) < 1e-3
    assert abs(res["mr_chart"]["ucl"] - (3.26653 * expected_mean_mr)) < 1e-3
    assert res["mr_chart"]["lcl"] == 0.0


def test_imr_edge_cases():
    # Single point -> insufficient
    res1 = SPCEngine.calculate_imr([3.4])
    assert "error" in res1

    # Exactly 2 observations -> valid
    res2 = SPCEngine.calculate_imr([3.4, 3.6])
    assert res2["sample_size"] == 2
    assert abs(res2["mean_mr"] - 0.2) < 1e-4

    # Constant data -> zero variance handled cleanly
    res_const = SPCEngine.calculate_imr([3.5, 3.5, 3.5, 3.5, 3.5])
    assert res_const["is_constant"] is True
    assert res_const["sigma_within"] == 0.0
    assert res_const["i_chart"]["ucl"] == 3.5
    assert res_const["i_chart"]["lcl"] == 3.5
    assert res_const["is_stable"] is True

    # Missing/NaN filtered + negative physically valid values
    res_nan = SPCEngine.calculate_imr([-2.0, float("nan"), -1.5, -2.5, -1.0])
    assert res_nan["sample_size"] == 4
    assert res_nan["dropped_missing"] == 1

    # Out-of-order ISO timestamps get sorted chronologically before MR diff
    vals = [10.0, 20.0, 11.0]
    ts = ["2026-11-25T10:00:00Z", "2026-11-25T12:00:00Z", "2026-11-25T11:00:00Z"]
    res_sorted = SPCEngine.calculate_imr(vals, timestamps=ts)
    # Sorted order: 10.0 (10:00), 11.0 (11:00), 20.0 (12:00) -> MR = [1.0, 9.0] -> mean_mr = 5.0
    assert abs(res_sorted["mean_mr"] - 5.0) < 1e-4


def test_xbar_r_constant_and_variable_subgroups():
    # Constant subgroup size n=4
    subgroups = [
        [3.3, 3.4, 3.5, 3.4],
        [3.4, 3.5, 3.5, 3.6],
        [3.2, 3.3, 3.4, 3.3],
    ]
    res = SPCEngine.calculate_xbar_r(subgroups)
    assert res["variable_subgroup_sizes"] is False
    assert res["subgroup_size"] == 4
    x_bars = [np.mean(s) for s in subgroups]
    ranges = [np.ptp(s) for s in subgroups]
    expected_gm = float(np.mean(x_bars))
    expected_mr = float(np.mean(ranges))
    assert abs(res["grand_mean"] - expected_gm) < 1e-4
    assert abs(res["mean_range"] - expected_mr) < 1e-4
    assert abs(res["ucl_x"] - (expected_gm + 0.729 * expected_mr)) < 1e-3
    assert abs(res["ucl_r"] - (2.282 * expected_mr)) < 1e-3

    # Variable subgroup sizes (n=2 and n=4) -> per-subgroup limits + warning
    var_subgroups = [[3.3, 3.5], [3.4, 3.5, 3.6, 3.5]]
    res_var = SPCEngine.calculate_xbar_r(var_subgroups)
    assert res_var["variable_subgroup_sizes"] is True
    assert len(res_var["warnings"]) >= 1
    assert res_var["points"][0]["ucl_x"] != res_var["points"][1]["ucl_x"]


def test_all_8_nelson_rules_trigger_and_non_trigger():
    mean, sigma = 10.0, 1.0

    # Rule 1: 1 point > 3 sigma
    v1 = SPCEngine.evaluate_nelson_rules([10.0, 10.0, 13.5], mean, sigma)
    assert any(v["rule"] == 1 and v["index"] == 2 for v in v1)
    assert not any(v["rule"] == 1 for v in SPCEngine.evaluate_nelson_rules([10.0, 12.9, 7.1], mean, sigma))

    # Rule 2: 9 consecutive points on same side
    r2_trig = [10.5] * 9
    assert any(v["rule"] == 2 for v in SPCEngine.evaluate_nelson_rules(r2_trig, mean, sigma))
    r2_non = [10.5] * 8 + [10.0] + [10.5] * 8  # point on mean breaks run
    assert not any(v["rule"] == 2 for v in SPCEngine.evaluate_nelson_rules(r2_non, mean, sigma))

    # Rule 3: 6 consecutive strictly increasing/decreasing
    r3_trig = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert any(v["rule"] == 3 for v in SPCEngine.evaluate_nelson_rules(r3_trig, 3.5, 2.0))
    r3_non = [1.0, 2.0, 3.0, 3.0, 4.0, 5.0]  # flat step breaks strict trend
    assert not any(v["rule"] == 3 for v in SPCEngine.evaluate_nelson_rules(r3_non, 3.5, 2.0))

    # Rule 4: 14 alternating points (including flat step non-trigger regression)
    r4_trig = [10.5, 9.5] * 7
    assert any(v["rule"] == 4 for v in SPCEngine.evaluate_nelson_rules(r4_trig, mean, sigma))
    r4_flat = [10.0, 10.0, 10.5, 9.5, 10.5, 9.5, 10.5, 9.5, 10.5, 9.5, 10.5, 9.5, 10.5, 9.5]
    assert not any(v["rule"] == 4 for v in SPCEngine.evaluate_nelson_rules(r4_flat, mean, sigma))

    # Rule 5: 2 of 3 beyond 2 sigma on same side
    r5_trig = [12.5, 10.2, 12.2]
    assert any(v["rule"] == 5 for v in SPCEngine.evaluate_nelson_rules(r5_trig, mean, sigma))
    r5_non = [12.5, 10.2, 7.5]  # opposite sides -> should NOT trigger Rule 5
    assert not any(v["rule"] == 5 for v in SPCEngine.evaluate_nelson_rules(r5_non, mean, sigma))

    # Rule 6: 4 of 5 beyond 1 sigma on same side
    r6_trig = [11.2, 11.3, 10.1, 11.4, 11.5]
    assert any(v["rule"] == 6 for v in SPCEngine.evaluate_nelson_rules(r6_trig, mean, sigma))
    r6_non = [11.2, 11.3, 10.1, 10.2, 11.5]
    assert not any(v["rule"] == 6 for v in SPCEngine.evaluate_nelson_rules(r6_non, mean, sigma))

    # Rule 7: 15 consecutive within +/-1 sigma
    r7_trig = [10.4, 9.6] * 7 + [10.2]
    assert len(r7_trig) == 15
    assert any(v["rule"] == 7 for v in SPCEngine.evaluate_nelson_rules(r7_trig, mean, sigma))
    r7_non = [10.4] * 14 + [11.2]
    assert not any(v["rule"] == 7 for v in SPCEngine.evaluate_nelson_rules(r7_non, mean, sigma))

    # Rule 8: 8 consecutive outside +/-1 sigma on both sides
    r8_trig = [11.5, 8.5, 11.6, 8.4, 11.3, 8.7, 11.2, 8.8]
    assert any(v["rule"] == 8 for v in SPCEngine.evaluate_nelson_rules(r8_trig, mean, sigma))
    r8_same_side = [11.5] * 8
    assert not any(v["rule"] == 8 for v in SPCEngine.evaluate_nelson_rules(r8_same_side, mean, sigma))
    r8_with_zone_c = [11.5, 8.5, 10.2, 8.4, 11.3, 8.7, 11.2, 8.8]
    assert not any(v["rule"] == 8 for v in SPCEngine.evaluate_nelson_rules(r8_with_zone_c, mean, sigma))


def test_process_capability_and_stability_gates():
    # Exact manual check on centered in-control sample (seed 42 produces zero Nelson violations)
    rng = np.random.default_rng(42)
    data = list(rng.normal(loc=10.0, scale=0.5, size=30))
    cap = SPCEngine.calculate_capability(data, lsl=8.0, usl=12.0, target=10.0)
    assert cap["can_calculate"] is True
    assert cap["stability_status"] == "STABLE"
    assert cap["capability_status"] == "ASSESSABLE"

    # Manual check of Pp, Ppk
    s_overall = float(np.std(data, ddof=1))
    mean_val = float(np.mean(data))
    expected_pp = (12.0 - 8.0) / (6.0 * s_overall)
    expected_ppk = min((12.0 - mean_val) / (3.0 * s_overall), (mean_val - 8.0) / (3.0 * s_overall))
    assert abs(cap["pp"] - round(expected_pp, 3)) < 1e-3
    assert abs(cap["ppk"] - round(expected_ppk, 3)) < 1e-3
    assert "does not prove normality" in cap["normality_note"].lower()

    # Zero variance -> NOT_ASSESSABLE, never infinite or fake 0
    cap_const = SPCEngine.calculate_capability([10.0] * 25, lsl=8.0, usl=12.0, target=10.0)
    assert cap_const["capability_status"] == "NOT_ASSESSABLE"
    assert cap_const["assessment"] == "NOT_ASSESSABLE"
    assert cap_const["cp"] is None
    assert cap_const["ppm_total"] == 0.0

    # Unstable process -> EXPLORATORY_UNSTABLE warning
    unstable_data = [10.0] * 10 + [15.0] + [10.0] * 10
    cap_unstable = SPCEngine.calculate_capability(unstable_data, lsl=8.0, usl=12.0)
    assert cap_unstable["is_stable"] is False
    assert cap_unstable["capability_status"] == "EXPLORATORY_UNSTABLE"

    # One-sided spec (LSL only)
    cap_one = SPCEngine.calculate_capability(data, lsl=8.0, usl=None)
    assert cap_one["cp"] is None
    assert cap_one["cpk"] == cap_one["cpl"]

    # Invalid spec (USL <= LSL)
    cap_bad = SPCEngine.calculate_capability(data, lsl=12.0, usl=8.0)
    assert cap_bad["can_calculate"] is False

    # Missing specs
    cap_missing = SPCEngine.calculate_capability([1.0, 2.0, 3.0], lsl=None, usl=None)
    assert cap_missing["can_calculate"] is False


def test_p_chart():
    res = SPCEngine.calculate_p_chart([4, 6, 5, 5], [200, 200, 200, 200])
    assert abs(res["p_bar"] - 0.025) < 1e-4
    assert len(res["points"]) == 4

    bad = SPCEngine.calculate_p_chart([10], [5])
    assert "error" in bad
