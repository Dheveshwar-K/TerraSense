import math
from datetime import datetime
from typing import Any, Optional

import numpy as np
from scipy import stats

# Standard ASTM E2587 / ISO 7870 SPC constants for subgroup sizes n=2..15
SPC_CONSTANTS = {
    2: {"A2": 1.880, "A3": 2.659, "D3": 0.000, "D4": 3.267, "B3": 0.000, "B4": 3.267, "d2": 1.128379, "c4": 0.7979},
    3: {"A2": 1.023, "A3": 1.954, "D3": 0.000, "D4": 2.574, "B3": 0.000, "B4": 2.568, "d2": 1.692569, "c4": 0.8862},
    4: {"A2": 0.729, "A3": 1.628, "D3": 0.000, "D4": 2.282, "B3": 0.000, "B4": 2.266, "d2": 2.058751, "c4": 0.9213},
    5: {"A2": 0.577, "A3": 1.427, "D3": 0.000, "D4": 2.114, "B3": 0.000, "B4": 2.089, "d2": 2.325929, "c4": 0.9400},
    6: {"A2": 0.483, "A3": 1.287, "D3": 0.000, "D4": 2.004, "B3": 0.030, "B4": 1.970, "d2": 2.534413, "c4": 0.9515},
    7: {"A2": 0.419, "A3": 1.182, "D3": 0.076, "D4": 1.924, "B3": 0.118, "B4": 1.882, "d2": 2.704357, "c4": 0.9594},
    8: {"A2": 0.373, "A3": 1.099, "D3": 0.136, "D4": 1.864, "B3": 0.185, "B4": 1.815, "d2": 2.847201, "c4": 0.9650},
    9: {"A2": 0.337, "A3": 1.032, "D3": 0.184, "D4": 1.816, "B3": 0.239, "B4": 1.761, "d2": 2.970026, "c4": 0.9693},
    10: {"A2": 0.308, "A3": 0.975, "D3": 0.223, "D4": 1.777, "B3": 0.284, "B4": 1.716, "d2": 3.077505, "c4": 0.9727},
    11: {"A2": 0.285, "A3": 0.927, "D3": 0.256, "D4": 1.744, "B3": 0.321, "B4": 1.679, "d2": 3.172873, "c4": 0.9754},
    12: {"A2": 0.266, "A3": 0.886, "D3": 0.283, "D4": 1.717, "B3": 0.354, "B4": 1.646, "d2": 3.258455, "c4": 0.9776},
    13: {"A2": 0.249, "A3": 0.850, "D3": 0.307, "D4": 1.693, "B3": 0.382, "B4": 1.618, "d2": 3.335980, "c4": 0.9794},
    14: {"A2": 0.235, "A3": 0.817, "D3": 0.328, "D4": 1.672, "B3": 0.406, "B4": 1.594, "d2": 3.406763, "c4": 0.9810},
    15: {"A2": 0.223, "A3": 0.789, "D3": 0.347, "D4": 1.653, "B3": 0.428, "B4": 1.572, "d2": 3.471827, "c4": 0.9823},
}

D2_MR2 = 1.1283791670955126  # 2 / sqrt(pi) for moving range span n=2
D4_MR2 = 3.26653
D3_MR2 = 0.0


def _clean_finite_series(
    values: list[float],
    timestamps: Optional[list[str]] = None,
) -> tuple[np.ndarray, list[str], int]:
    """
    Filters out None/NaN/Inf entries while keeping paired timestamps aligned.
    If all timestamps are ISO-8601 parseable, sorts chronologically.
    """
    cleaned: list[tuple[int, float, str, Optional[datetime]]] = []
    parseable_iso = bool(timestamps and len(timestamps) == len(values))

    for idx, val in enumerate(values):
        if val is None:
            continue
        try:
            fval = float(val)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(fval):
            continue

        ts_str = timestamps[idx] if timestamps and idx < len(timestamps) else f"T{idx + 1}"
        parsed_dt: Optional[datetime] = None
        if parseable_iso:
            try:
                parsed_dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                if parsed_dt.tzinfo is not None:
                    parsed_dt = parsed_dt.astimezone().replace(tzinfo=None)
            except Exception:
                parseable_iso = False
        cleaned.append((idx, fval, str(ts_str), parsed_dt))

    if parseable_iso and cleaned:
        cleaned.sort(key=lambda item: (item[3], item[0]))

    dropped = len(values) - len(cleaned)
    arr = np.array([c[1] for c in cleaned], dtype=float)
    out_ts = [c[2] for c in cleaned]
    return arr, out_ts, dropped


class SPCEngine:
    """
    Statistical Process Control (SPC) calculation engine following ASTM E2587 / ISO 7870.
    Supports I-MR, X-bar & R, P-Chart, Nelson 8 Rules, and Process Capability (Cp, Cpk, Pp, Ppk).
    """

    @staticmethod
    def calculate_imr(
        values: list[float],
        timestamps: Optional[list[str]] = None,
        lsl: Optional[float] = None,
        usl: Optional[float] = None,
    ) -> dict[str, Any]:
        if not values:
            return {"error": "At least 2 observations required for I-MR chart", "points": [], "data": []}

        arr, ordered_ts, dropped = _clean_finite_series(values, timestamps)
        n = len(arr)
        if n < 2:
            return {
                "error": "At least 2 finite observations required for I-MR chart",
                "sample_size": n,
                "dropped_missing": dropped,
                "points": [],
                "data": [],
            }

        mr = np.abs(np.diff(arr))
        mean_x = float(np.mean(arr))
        mean_mr = float(np.mean(mr))
        sigma_within = mean_mr / D2_MR2
        sigma_overall = float(np.std(arr, ddof=1))

        ucl_i = mean_x + 3.0 * sigma_within
        lcl_i = mean_x - 3.0 * sigma_within
        cl_i = mean_x

        ucl_mr = D4_MR2 * mean_mr
        lcl_mr = D3_MR2 * mean_mr
        cl_mr = mean_mr

        zone_1s_upper = mean_x + 1.0 * sigma_within
        zone_2s_upper = mean_x + 2.0 * sigma_within
        zone_1s_lower = mean_x - 1.0 * sigma_within
        zone_2s_lower = mean_x - 2.0 * sigma_within

        violations = SPCEngine.evaluate_nelson_rules(arr, mean_x, sigma_within)
        is_constant = sigma_within == 0.0

        warnings: list[str] = []
        if dropped > 0:
            warnings.append(f"{dropped} missing or non-finite observation(s) excluded prior to calculation.")
        if is_constant:
            warnings.append("All observations are identical (zero moving range). Control limits collapse to the center line.")
        if n < 20:
            warnings.append(f"Sample size N={n} (<20); control limits are preliminary until 20-25+ observations are collected.")

        has_two_sided_spec = lsl is not None and usl is not None and usl > lsl
        spec_band = (usl - lsl) if has_two_sided_spec else None

        points = []
        for i in range(n):
            val = float(arr[i])
            mr_val = float(mr[i - 1]) if i > 0 else None
            mr_ooc = (mr_val > ucl_mr) if (mr_val is not None and ucl_mr > 0) else False

            point_violations = [v["rule_name"] for v in violations if v["index"] == i]
            is_ooc = len(point_violations) > 0

            spec_status = "OK"
            if usl is not None and val > usl:
                spec_status = "OUT_OF_SPEC_HIGH"
            elif lsl is not None and val < lsl:
                spec_status = "OUT_OF_SPEC_LOW"
            elif spec_band is not None:
                if val > (usl - 0.1 * spec_band):
                    spec_status = "WARNING_HIGH"
                elif val < (lsl + 0.1 * spec_band):
                    spec_status = "WARNING_LOW"

            points.append({
                "index": i + 1,
                "timestamp": ordered_ts[i],
                "value": round(val, 4),
                "mr": round(mr_val, 4) if mr_val is not None else None,
                "cl": round(cl_i, 4),
                "ucl": round(ucl_i, 4),
                "lcl": round(lcl_i, 4),
                "mr_cl": round(cl_mr, 4),
                "mr_ucl": round(ucl_mr, 4),
                "mr_lcl": round(lcl_mr, 4),
                "lsl": lsl,
                "usl": usl,
                "is_out_of_control": is_ooc,
                "is_mr_out_of_control": mr_ooc,
                "violations": point_violations,
                "spec_status": spec_status,
            })

        return {
            "chart_type": "I-MR",
            "sample_size": n,
            "dropped_missing": dropped,
            "is_constant": is_constant,
            "mean": round(mean_x, 4),
            "mean_mr": round(mean_mr, 4),
            "sigma_within": round(sigma_within, 4),
            "sigma_overall": round(sigma_overall, 4),
            "i_chart": {
                "cl": round(cl_i, 4),
                "ucl": round(ucl_i, 4),
                "lcl": round(lcl_i, 4),
                "zone_1s_upper": round(zone_1s_upper, 4),
                "zone_2s_upper": round(zone_2s_upper, 4),
                "zone_1s_lower": round(zone_1s_lower, 4),
                "zone_2s_lower": round(zone_2s_lower, 4),
            },
            "mr_chart": {
                "cl": round(cl_mr, 4),
                "ucl": round(ucl_mr, 4),
                "lcl": round(lcl_mr, 4),
            },
            "violations_count": len([p for p in points if p["is_out_of_control"] or p["is_mr_out_of_control"]]),
            "is_stable": len(violations) == 0 and not any(p["is_mr_out_of_control"] for p in points),
            "warnings": warnings,
            "points": points,
        }

    @staticmethod
    def calculate_xbar_r(subgroups: list[list[float]], labels: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Calculates X-bar and R chart for subgrouped data.
        Supports constant subgroup sizes (n=2..15) and variable subgroup sizes with exact per-subgroup limits.
        """
        if not subgroups or len(subgroups) < 2:
            return {"error": "At least 2 subgroups required for X-bar & R chart", "points": []}

        valid_subgroups: list[list[float]] = []
        valid_labels: list[str] = []
        skipped = 0

        for idx, sg in enumerate(subgroups):
            clean_sg = [float(v) for v in sg if v is not None and math.isfinite(float(v))]
            if len(clean_sg) < 2 or len(clean_sg) > 15:
                skipped += 1
                continue
            valid_subgroups.append(clean_sg)
            valid_labels.append(labels[idx] if labels and idx < len(labels) else f"SG{idx + 1}")

        if len(valid_subgroups) < 2:
            return {
                "error": "At least 2 valid subgroups with size 2..15 required for X-bar & R chart",
                "skipped_subgroups": skipped,
                "points": [],
            }

        sizes = [len(sg) for sg in valid_subgroups]
        unique_sizes = sorted(set(sizes))
        variable_sizes = len(unique_sizes) > 1

        x_bars = [float(np.mean(sg)) for sg in valid_subgroups]
        ranges = [float(np.ptp(sg)) for sg in valid_subgroups]

        warnings: list[str] = []
        if skipped > 0:
            warnings.append(f"{skipped} subgroup(s) excluded because size was outside valid range [2, 15].")

        if not variable_sizes:
            n_size = unique_sizes[0]
            consts = SPC_CONSTANTS[n_size]
            grand_mean = float(np.mean(x_bars))
            mean_range = float(np.mean(ranges))
            sigma_within = mean_range / consts["d2"]

            ucl_x = grand_mean + consts["A2"] * mean_range
            lcl_x = grand_mean - consts["A2"] * mean_range
            ucl_r = consts["D4"] * mean_range
            lcl_r = consts["D3"] * mean_range

            points = []
            for i, sg in enumerate(valid_subgroups):
                x_bar = x_bars[i]
                r_val = ranges[i]
                is_x_ooc = x_bar > ucl_x or x_bar < lcl_x
                is_r_ooc = r_val > ucl_r or r_val < lcl_r
                points.append({
                    "subgroup": i + 1,
                    "label": valid_labels[i],
                    "size": len(sg),
                    "x_bar": round(x_bar, 4),
                    "range": round(r_val, 4),
                    "ucl_x": round(ucl_x, 4),
                    "lcl_x": round(lcl_x, 4),
                    "cl_x": round(grand_mean, 4),
                    "ucl_r": round(ucl_r, 4),
                    "lcl_r": round(lcl_r, 4),
                    "cl_r": round(mean_range, 4),
                    "is_out_of_control": is_x_ooc or is_r_ooc,
                })

            return {
                "chart_type": "X-bar & R",
                "subgroups_count": len(valid_subgroups),
                "subgroup_size": n_size,
                "variable_subgroup_sizes": False,
                "grand_mean": round(grand_mean, 4),
                "mean_range": round(mean_range, 4),
                "sigma_within": round(sigma_within, 4),
                "ucl_x": round(ucl_x, 4),
                "lcl_x": round(lcl_x, 4),
                "ucl_r": round(ucl_r, 4),
                "lcl_r": round(lcl_r, 4),
                "warnings": warnings,
                "points": points,
            }

        # Variable subgroup sizes: use weighted grand mean & pooled R/d2(n_i) sigma estimate,
        # then compute exact subgroup-specific limits.
        warnings.append(
            f"Subgroup sizes vary ({min(sizes)} to {max(sizes)}). Control limits are computed individually per subgroup size."
        )
        total_n = sum(sizes)
        grand_mean = sum(x_bars[i] * sizes[i] for i in range(len(valid_subgroups))) / total_n
        mean_range = float(np.mean(ranges))
        sigma_estimates = [ranges[i] / SPC_CONSTANTS[sizes[i]]["d2"] for i in range(len(valid_subgroups))]
        sigma_within = float(np.mean(sigma_estimates))

        points = []
        for i, sg in enumerate(valid_subgroups):
            n_i = sizes[i]
            c_i = SPC_CONSTANTS[n_i]
            expected_r_i = c_i["d2"] * sigma_within
            ucl_x_i = grand_mean + 3.0 * sigma_within / math.sqrt(n_i)
            lcl_x_i = grand_mean - 3.0 * sigma_within / math.sqrt(n_i)
            ucl_r_i = c_i["D4"] * expected_r_i
            lcl_r_i = c_i["D3"] * expected_r_i
            x_bar = x_bars[i]
            r_val = ranges[i]
            is_x_ooc = x_bar > ucl_x_i or x_bar < lcl_x_i
            is_r_ooc = r_val > ucl_r_i or r_val < lcl_r_i

            points.append({
                "subgroup": i + 1,
                "label": valid_labels[i],
                "size": n_i,
                "x_bar": round(x_bar, 4),
                "range": round(r_val, 4),
                "ucl_x": round(ucl_x_i, 4),
                "lcl_x": round(lcl_x_i, 4),
                "cl_x": round(grand_mean, 4),
                "ucl_r": round(ucl_r_i, 4),
                "lcl_r": round(lcl_r_i, 4),
                "cl_r": round(expected_r_i, 4),
                "is_out_of_control": is_x_ooc or is_r_ooc,
            })

        return {
            "chart_type": "X-bar & R",
            "subgroups_count": len(valid_subgroups),
            "subgroup_size": int(round(float(np.mean(sizes)))),
            "variable_subgroup_sizes": True,
            "grand_mean": round(grand_mean, 4),
            "mean_range": round(mean_range, 4),
            "sigma_within": round(sigma_within, 4),
            "ucl_x": points[-1]["ucl_x"],
            "lcl_x": points[-1]["lcl_x"],
            "ucl_r": points[-1]["ucl_r"],
            "lcl_r": points[-1]["lcl_r"],
            "warnings": warnings,
            "points": points,
        }

    @staticmethod
    def calculate_p_chart(
        defective_counts: list[int],
        sample_sizes: list[int],
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        if not defective_counts or not sample_sizes or len(defective_counts) != len(sample_sizes):
            return {"error": "Invalid inputs for P-chart", "points": []}

        for d, n in zip(defective_counts, sample_sizes):
            if n <= 0 or d < 0 or d > n:
                return {"error": "Each P-chart subgroup requires sample_size > 0 and 0 <= defective <= sample_size", "points": []}

        total_defective = sum(defective_counts)
        total_inspected = sum(sample_sizes)
        p_bar = total_defective / total_inspected

        points = []
        for i in range(len(defective_counts)):
            d = defective_counts[i]
            n = sample_sizes[i]
            p = d / n
            se = math.sqrt(max(0.0, p_bar * (1.0 - p_bar) / n))
            ucl = min(1.0, p_bar + 3.0 * se)
            lcl = max(0.0, p_bar - 3.0 * se)
            is_ooc = (p > ucl) or (p < lcl)

            points.append({
                "index": i + 1,
                "label": labels[i] if labels and i < len(labels) else f"Lot-{i + 1}",
                "defective": d,
                "sample_size": n,
                "p": round(p, 4),
                "p_percentage": round(p * 100, 2),
                "cl": round(p_bar, 4),
                "ucl": round(ucl, 4),
                "lcl": round(lcl, 4),
                "is_out_of_control": is_ooc,
            })

        return {
            "chart_type": "P-Chart",
            "p_bar": round(p_bar, 4),
            "p_bar_percentage": round(p_bar * 100, 2),
            "total_defective": total_defective,
            "total_inspected": total_inspected,
            "points": points,
        }

    @staticmethod
    def evaluate_nelson_rules(arr: np.ndarray | list[float], mean: float, sigma: float) -> list[dict[str, Any]]:
        """
        Evaluates all 8 Nelson Rules for special-cause variation:
        Rule 1: 1 point beyond 3 sigma.
        Rule 2: 9 consecutive points on the same side of center line.
        Rule 3: 6 consecutive points strictly increasing or decreasing.
        Rule 4: 14 consecutive points strictly alternating up and down.
        Rule 5: 2 of 3 consecutive points beyond 2 sigma on the same side.
        Rule 6: 4 of 5 consecutive points beyond 1 sigma on the same side.
        Rule 7: 15 consecutive points within +/-1 sigma (stratification).
        Rule 8: 8 consecutive points outside +/-1 sigma on both sides (mixture).
        """
        arr_np = np.asarray(arr, dtype=float)
        violations: list[dict[str, Any]] = []
        n = len(arr_np)
        if not math.isfinite(mean) or not math.isfinite(sigma) or sigma <= 0 or n < 1:
            return violations

        # Rule 1: 1 point beyond 3 sigma
        for i in range(n):
            if abs(arr_np[i] - mean) > 3.0 * sigma:
                violations.append({
                    "rule": 1,
                    "rule_name": "Rule 1: Beyond 3 Sigma",
                    "index": i,
                    "description": f"Point {i + 1} value ({arr_np[i]:.4g}) exceeds 3 sigma ({3 * sigma:.4g}) from center line",
                })

        # Rule 2: 9 consecutive points strictly on same side of center line
        if n >= 9:
            for i in range(8, n):
                window = arr_np[i - 8 : i + 1]
                if all(x > mean for x in window) or all(x < mean for x in window):
                    violations.append({
                        "rule": 2,
                        "rule_name": "Rule 2: Nine Points on Same Side",
                        "index": i,
                        "description": f"Point {i + 1} completes 9 consecutive points on the same side of the center line",
                    })

        # Rule 3: 6 consecutive points strictly increasing or decreasing
        if n >= 6:
            for i in range(5, n):
                window = arr_np[i - 5 : i + 1]
                diffs = np.diff(window)
                if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                    direction = "increasing" if diffs[0] > 0 else "decreasing"
                    violations.append({
                        "rule": 3,
                        "rule_name": "Rule 3: Six Point Trend",
                        "index": i,
                        "description": f"Point {i + 1} terminates 6 consecutive points continuously {direction}",
                    })

        # Rule 4: 14 consecutive points alternating up and down (no flat/zero step allowed)
        if n >= 14:
            for i in range(13, n):
                window = arr_np[i - 13 : i + 1]
                diffs = np.diff(window)
                alternating = all(
                    diffs[k] != 0 and diffs[k + 1] != 0 and (diffs[k] * diffs[k + 1] < 0)
                    for k in range(len(diffs) - 1)
                )
                if alternating:
                    violations.append({
                        "rule": 4,
                        "rule_name": "Rule 4: Fourteen Alternating Points",
                        "index": i,
                        "description": f"Point {i + 1} completes 14 consecutive points alternating direction",
                    })

        # Rule 5: 2 out of 3 consecutive points beyond 2 sigma on same side
        if n >= 3:
            for i in range(2, n):
                window = arr_np[i - 2 : i + 1]
                upper_count = sum(1 for x in window if (x - mean) > 2.0 * sigma)
                lower_count = sum(1 for x in window if (mean - x) > 2.0 * sigma)
                if upper_count >= 2 or lower_count >= 2:
                    violations.append({
                        "rule": 5,
                        "rule_name": "Rule 5: 2 of 3 Beyond 2 Sigma",
                        "index": i,
                        "description": f"Point {i + 1}: 2 out of 3 consecutive points are beyond 2 sigma on the same side",
                    })

        # Rule 6: 4 out of 5 consecutive points beyond 1 sigma on same side
        if n >= 5:
            for i in range(4, n):
                window = arr_np[i - 4 : i + 1]
                upper_count = sum(1 for x in window if (x - mean) > 1.0 * sigma)
                lower_count = sum(1 for x in window if (mean - x) > 1.0 * sigma)
                if upper_count >= 4 or lower_count >= 4:
                    violations.append({
                        "rule": 6,
                        "rule_name": "Rule 6: 4 of 5 Beyond 1 Sigma",
                        "index": i,
                        "description": f"Point {i + 1}: 4 out of 5 consecutive points are beyond 1 sigma on the same side",
                    })

        # Rule 7: 15 consecutive points within +/-1 sigma (stratification)
        if n >= 15:
            for i in range(14, n):
                window = arr_np[i - 14 : i + 1]
                if all(abs(x - mean) < 1.0 * sigma for x in window):
                    violations.append({
                        "rule": 7,
                        "rule_name": "Rule 7: Fifteen Within 1 Sigma",
                        "index": i,
                        "description": f"Point {i + 1} completes 15 consecutive points within +/-1 sigma (possible stratification)",
                    })

        # Rule 8: 8 consecutive points outside +/-1 sigma on both sides (mixture)
        if n >= 8:
            for i in range(7, n):
                window = arr_np[i - 7 : i + 1]
                if (
                    all(abs(x - mean) > 1.0 * sigma for x in window)
                    and any(x > mean for x in window)
                    and any(x < mean for x in window)
                ):
                    violations.append({
                        "rule": 8,
                        "rule_name": "Rule 8: Eight Outside 1 Sigma Both Sides",
                        "index": i,
                        "description": f"Point {i + 1} completes 8 consecutive points outside +/-1 sigma on both sides (mixture pattern)",
                    })

        return violations

    @staticmethod
    def calculate_capability(
        values: list[float],
        lsl: Optional[float],
        usl: Optional[float],
        target: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Calculates Process Capability indices (Cp, Cpk, Pp, Ppk) with explicit stability,
        zero-variance, sample-size, normality, and PPM assumption reporting.
        """
        if lsl is None and usl is None:
            return {
                "can_calculate": False,
                "stability_status": "NOT_ASSESSABLE",
                "capability_status": "NOT_ASSESSABLE",
                "reason": "Specification limits (LSL and/or USL) are missing. Capability cannot be calculated.",
            }

        if lsl is not None and usl is not None and usl <= lsl:
            return {
                "can_calculate": False,
                "stability_status": "INVALID_SPEC",
                "capability_status": "NOT_ASSESSABLE",
                "reason": f"Invalid specification limits: USL ({usl}) must be strictly greater than LSL ({lsl}).",
            }

        arr, _, dropped = _clean_finite_series(values)
        n = len(arr)
        if n < 2:
            return {
                "can_calculate": False,
                "stability_status": "INSUFFICIENT_DATA",
                "capability_status": "NOT_ASSESSABLE",
                "reason": "Insufficient observations (N < 2). At least 2 finite values required.",
            }

        mean_val = float(np.mean(arr))
        sigma_overall = float(np.std(arr, ddof=1))
        mr = np.abs(np.diff(arr))
        mean_mr = float(np.mean(mr))
        sigma_within = mean_mr / D2_MR2

        warnings: list[str] = []
        if dropped > 0:
            warnings.append(f"{dropped} missing or non-finite value(s) excluded from capability analysis.")

        # Zero-variance / constant-data handling
        if sigma_within <= 0 or sigma_overall <= 0:
            in_spec = True
            if lsl is not None and mean_val < lsl:
                in_spec = False
            if usl is not None and mean_val > usl:
                in_spec = False
            warnings.append(
                "Zero process variation observed (all measurements identical). "
                "Capability indices Cp/Cpk/Pp/Ppk are undefined when sigma = 0 and are not reported as infinite."
            )
            return {
                "can_calculate": True,
                "sample_size": n,
                "mean": round(mean_val, 4),
                "target": target,
                "lsl": lsl,
                "usl": usl,
                "sigma_within": 0.0,
                "sigma_overall": 0.0,
                "cp": None,
                "cpk": None,
                "cpu": None,
                "cpl": None,
                "pp": None,
                "ppk": None,
                "ppu": None,
                "ppl": None,
                "ppm_total": 0.0 if in_spec else 1_000_000.0,
                "ppm_below_lsl": 1_000_000.0 if (lsl is not None and mean_val < lsl) else 0.0,
                "ppm_above_usl": 1_000_000.0 if (usl is not None and mean_val > usl) else 0.0,
                "yield_percentage": 100.0 if in_spec else 0.0,
                "assessment": "NOT_ASSESSABLE",
                "stability_status": "CONSTANT_DATA",
                "capability_status": "NOT_ASSESSABLE",
                "is_stable": True,
                "is_normal": False,
                "normality_rejected": None,
                "normality_test_used": None,
                "normality_p_value": None,
                "normality_note": "Normality test is undefined for zero-variance constant data.",
                "ppm_assumptions": "Empirical constant-value evaluation (zero variance).",
                "warnings": warnings,
                "violations_count": 0,
            }

        # Stability assessment BEFORE capability interpretation
        violations = SPCEngine.evaluate_nelson_rules(arr, mean_val, sigma_within)
        is_stable = len(violations) == 0
        stability_status = "STABLE" if is_stable else "UNSTABLE"

        cp = None
        cpk = None
        pp = None
        ppk = None
        cpu = None
        cpl = None
        ppu = None
        ppl = None

        if lsl is not None and usl is not None:
            cp = (usl - lsl) / (6.0 * sigma_within)
            pp = (usl - lsl) / (6.0 * sigma_overall)

        if usl is not None:
            cpu = (usl - mean_val) / (3.0 * sigma_within)
            ppu = (usl - mean_val) / (3.0 * sigma_overall)
        if lsl is not None:
            cpl = (mean_val - lsl) / (3.0 * sigma_within)
            ppl = (mean_val - lsl) / (3.0 * sigma_overall)

        if cpu is not None and cpl is not None:
            cpk = min(cpu, cpl)
        elif cpu is not None:
            cpk = cpu
        elif cpl is not None:
            cpk = cpl

        if ppu is not None and ppl is not None:
            ppk = min(ppu, ppl)
        elif ppu is not None:
            ppk = ppu
        elif ppl is not None:
            ppk = ppl

        # Expected PPM defective assuming Normal(mean_val, sigma_overall)
        ppm_below = 0.0
        ppm_above = 0.0
        if lsl is not None:
            ppm_below = float(stats.norm.cdf((lsl - mean_val) / sigma_overall)) * 1_000_000.0
        if usl is not None:
            ppm_above = float(1.0 - stats.norm.cdf((usl - mean_val) / sigma_overall)) * 1_000_000.0
        total_ppm = min(1_000_000.0, ppm_below + ppm_above)
        yield_pct = max(0.0, (1.0 - total_ppm / 1_000_000.0) * 100.0)

        if not is_stable:
            capability_status = "EXPLORATORY_UNSTABLE"
            warnings.append(
                "Process is statistically UNSTABLE (Nelson rule violations detected). "
                "Displayed capability indices are exploratory only and do NOT guarantee future predictability."
            )
        elif n < 20:
            capability_status = "EXPLORATORY_SMALL_SAMPLE"
            warnings.append(
                f"Sample size (N={n}) is smaller than recommended (N>=20). "
                "Capability figures carry wide statistical uncertainty."
            )
        else:
            capability_status = "ASSESSABLE"

        # Assessment label (guarding cpk=0.0 and None properly)
        if cpk is None:
            assessment = "NOT_ASSESSABLE"
        elif cpk >= 1.67:
            assessment = "EXCELLENT"
        elif cpk >= 1.33:
            assessment = "ADEQUATE"
        elif cpk >= 1.0:
            assessment = "BORDERLINE"
        else:
            assessment = "INADEQUATE"

        # Normality assessment (Shapiro-Wilk for 3 <= N <= 5000, D'Agostino-Pearson for N > 5000)
        normality_p: Optional[float] = None
        normality_test_used: Optional[str] = None
        normality_rejected: Optional[bool] = None
        is_normal = True
        normality_note = "Sample size N < 3 is too small for normality hypothesis testing."

        if 3 <= n <= 5000:
            try:
                _, p_val = stats.shapiro(arr)
                normality_p = float(p_val)
                normality_test_used = "Shapiro-Wilk"
            except Exception:
                normality_p = None
        elif n > 5000:
            try:
                _, p_val = stats.normaltest(arr)
                normality_p = float(p_val)
                normality_test_used = "D'Agostino-Pearson"
            except Exception:
                normality_p = None

        if normality_p is not None and math.isfinite(normality_p):
            normality_rejected = normality_p < 0.05
            is_normal = not normality_rejected
            if normality_rejected:
                normality_note = (
                    f"{normality_test_used} rejected normality (p={normality_p:.4f} < 0.05). "
                    "Normal-theory Cp/Cpk and PPM projections may be biased."
                )
                warnings.append(normality_note)
            else:
                normality_note = (
                    f"{normality_test_used} did not reject normality (p={normality_p:.4f} >= 0.05). "
                    "Note: failing to reject the null hypothesis does not prove normality."
                )
        elif n < 3:
            warnings.append(normality_note)

        ppm_assumptions = (
            "Projected PPM and yield assume a statistically stable, normally distributed process "
            "using overall sample mean and standard deviation s."
        )

        return {
            "can_calculate": True,
            "sample_size": n,
            "mean": round(mean_val, 4),
            "target": target,
            "lsl": lsl,
            "usl": usl,
            "sigma_within": round(sigma_within, 4),
            "sigma_overall": round(sigma_overall, 4),
            "cp": round(cp, 3) if cp is not None else None,
            "cpk": round(cpk, 3) if cpk is not None else None,
            "cpu": round(cpu, 3) if cpu is not None else None,
            "cpl": round(cpl, 3) if cpl is not None else None,
            "pp": round(pp, 3) if pp is not None else None,
            "ppk": round(ppk, 3) if ppk is not None else None,
            "ppu": round(ppu, 3) if ppu is not None else None,
            "ppl": round(ppl, 3) if ppl is not None else None,
            "ppm_total": round(total_ppm, 1),
            "ppm_below_lsl": round(ppm_below, 1),
            "ppm_above_usl": round(ppm_above, 1),
            "yield_percentage": round(yield_pct, 4),
            "assessment": assessment,
            "stability_status": stability_status,
            "capability_status": capability_status,
            "is_stable": is_stable,
            "is_normal": is_normal,
            "normality_rejected": normality_rejected,
            "normality_test_used": normality_test_used,
            "normality_p_value": round(normality_p, 4) if normality_p is not None else None,
            "normality_note": normality_note,
            "ppm_assumptions": ppm_assumptions,
            "warnings": warnings,
            "violations_count": len(violations),
        }
