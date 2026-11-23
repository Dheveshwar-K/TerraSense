import numpy as np
from scipy import stats
from typing import Any, Optional

# Standard SPC constants for subgroup sizes n=2..10
SPC_CONSTANTS = {
    2: {"A2": 1.880, "A3": 2.659, "D3": 0.000, "D4": 3.267, "B3": 0.000, "B4": 3.267, "d2": 1.128, "c4": 0.7979},
    3: {"A2": 1.023, "A3": 1.954, "D3": 0.000, "D4": 2.574, "B3": 0.000, "B4": 2.568, "d2": 1.693, "c4": 0.8862},
    4: {"A2": 0.729, "A3": 1.628, "D3": 0.000, "D4": 2.282, "B3": 0.000, "B4": 2.266, "d2": 2.059, "c4": 0.9213},
    5: {"A2": 0.577, "A3": 1.427, "D3": 0.000, "D4": 2.114, "B3": 0.000, "B4": 2.089, "d2": 2.326, "c4": 0.9400},
    6: {"A2": 0.483, "A3": 1.287, "D3": 0.000, "D4": 2.004, "B3": 0.030, "B4": 1.970, "d2": 2.534, "c4": 0.9515},
    7: {"A2": 0.419, "A3": 1.182, "D3": 0.076, "D4": 1.924, "B3": 0.118, "B4": 1.882, "d2": 2.704, "c4": 0.9594},
    8: {"A2": 0.373, "A3": 1.099, "D3": 0.136, "D4": 1.864, "B3": 0.185, "B4": 1.815, "d2": 2.847, "c4": 0.9650},
    9: {"A2": 0.337, "A3": 1.032, "D3": 0.184, "D4": 1.816, "B3": 0.239, "B4": 1.761, "d2": 2.970, "c4": 0.9693},
    10: {"A2": 0.308, "A3": 0.975, "D3": 0.223, "D4": 1.777, "B3": 0.284, "B4": 1.716, "d2": 3.078, "c4": 0.9727},
}

class SPCEngine:
    """
    Dedicated Statistical Process Control (SPC) calculation engine.
    Supports Individuals & Moving Range (I-MR), X-bar & R, X-bar & S,
    Attribute charts (P, NP, C, U), Nelson 8 rules, and Process Capability (Cp, Cpk, Pp, Ppk).
    """

    @staticmethod
    def calculate_imr(values: list[float], timestamps: list[str] = None, lsl: Optional[float] = None, usl: Optional[float] = None) -> dict[str, Any]:
        """
        Calculates Individuals and Moving Range (I-MR) control chart.
        Used for single hourly observations.
        """
        if not values or len(values) < 2:
            return {"error": "At least 2 observations required for I-MR chart", "data": []}

        arr = np.array(values, dtype=float)
        n = len(arr)
        
        # Moving ranges (MR_i = |X_i - X_{i-1}| for i >= 1)
        mr = np.abs(np.diff(arr))
        mean_x = float(np.mean(arr))
        mean_mr = float(np.mean(mr)) if len(mr) > 0 else 0.0

        # Constants for n=2
        d2 = 1.128379
        sigma_within = mean_mr / d2 if d2 > 0 else 0.0
        sigma_overall = float(np.std(arr, ddof=1)) if n > 1 else 0.0

        # Control limits for Individuals chart
        ucl_i = mean_x + 3.0 * sigma_within
        lcl_i = mean_x - 3.0 * sigma_within
        cl_i = mean_x

        # Control limits for Moving Range chart
        d4 = 3.267
        d3 = 0.0
        ucl_mr = d4 * mean_mr
        lcl_mr = d3 * mean_mr
        cl_mr = mean_mr

        # Sigma zones for Nelson rules
        zone_1s_upper = mean_x + 1.0 * sigma_within
        zone_2s_upper = mean_x + 2.0 * sigma_within
        zone_1s_lower = mean_x - 1.0 * sigma_within
        zone_2s_lower = mean_x - 2.0 * sigma_within

        # Evaluate Nelson rules on Individuals
        violations = SPCEngine.evaluate_nelson_rules(arr, mean_x, sigma_within)

        # Build point details
        points = []
        for i in range(n):
            val = float(arr[i])
            mr_val = float(mr[i-1]) if i > 0 else None
            mr_ooc = (mr_val > ucl_mr) if (mr_val is not None) else False
            
            point_violations = [v["rule_name"] for v in violations if v["index"] == i]
            is_ooc = len(point_violations) > 0
            
            # Spec status
            spec_status = "OK"
            if usl is not None and val > usl:
                spec_status = "OUT_OF_SPEC_HIGH"
            elif lsl is not None and val < lsl:
                spec_status = "OUT_OF_SPEC_LOW"
            elif usl is not None and val > (usl - 0.1 * (usl - (lsl if lsl is not None else mean_x))):
                spec_status = "WARNING_HIGH"
            elif lsl is not None and val < (lsl + 0.1 * ((usl if usl is not None else mean_x) - lsl)):
                spec_status = "WARNING_LOW"

            points.append({
                "index": i + 1,
                "timestamp": timestamps[i] if timestamps and i < len(timestamps) else f"T{i+1}",
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
                "spec_status": spec_status
            })

        return {
            "chart_type": "I-MR",
            "sample_size": n,
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
            "is_stable": len(violations) == 0,
            "points": points
        }

    @staticmethod
    def calculate_xbar_r(subgroups: list[list[float]], labels: list[str] = None) -> dict[str, Any]:
        """
        Calculates X-bar and R chart for subgrouped data.
        """
        if not subgroups or len(subgroups) < 2:
            return {"error": "At least 2 subgroups required", "points": []}

        subgroup_sizes = [len(sg) for sg in subgroups if len(sg) > 0]
        if not subgroup_sizes:
            return {"error": "Subgroups cannot be empty", "points": []}

        n_size = int(np.round(np.mean(subgroup_sizes)))
        if n_size not in SPC_CONSTANTS:
            n_size = min(max(n_size, 2), 10)

        consts = SPC_CONSTANTS[n_size]
        a2 = consts["A2"]
        d3 = consts["D3"]
        d4 = consts["D4"]
        d2 = consts["d2"]

        x_bars = [float(np.mean(sg)) for sg in subgroups]
        ranges = [float(np.ptp(sg)) for sg in subgroups]

        grand_mean = float(np.mean(x_bars))
        mean_range = float(np.mean(ranges))

        ucl_x = grand_mean + a2 * mean_range
        lcl_x = grand_mean - a2 * mean_range
        ucl_r = d4 * mean_range
        lcl_r = d3 * mean_range
        sigma_within = mean_range / d2

        points = []
        for i in range(len(subgroups)):
            x_bar = x_bars[i]
            r_val = ranges[i]
            is_x_ooc = x_bar > ucl_x or x_bar < lcl_x
            is_r_ooc = r_val > ucl_r or r_val < lcl_r

            points.append({
                "subgroup": i + 1,
                "label": labels[i] if labels and i < len(labels) else f"SG{i+1}",
                "size": len(subgroups[i]),
                "x_bar": round(x_bar, 4),
                "range": round(r_val, 4),
                "ucl_x": round(ucl_x, 4),
                "lcl_x": round(lcl_x, 4),
                "cl_x": round(grand_mean, 4),
                "ucl_r": round(ucl_r, 4),
                "lcl_r": round(lcl_r, 4),
                "cl_r": round(mean_range, 4),
                "is_out_of_control": is_x_ooc or is_r_ooc
            })

        return {
            "chart_type": "X-bar & R",
            "subgroups_count": len(subgroups),
            "subgroup_size": n_size,
            "grand_mean": round(grand_mean, 4),
            "mean_range": round(mean_range, 4),
            "sigma_within": round(sigma_within, 4),
            "ucl_x": round(ucl_x, 4),
            "lcl_x": round(lcl_x, 4),
            "ucl_r": round(ucl_r, 4),
            "lcl_r": round(lcl_r, 4),
            "points": points
        }

    @staticmethod
    def calculate_p_chart(defective_counts: list[int], sample_sizes: list[int], labels: list[str] = None) -> dict[str, Any]:
        """
        Calculates P-chart (Proportion defective) with variable/fixed control limits.
        """
        if not defective_counts or not sample_sizes or len(defective_counts) != len(sample_sizes):
            return {"error": "Invalid inputs for P-chart", "points": []}

        total_defective = sum(defective_counts)
        total_inspected = sum(sample_sizes)
        if total_inspected == 0:
            return {"error": "Total inspected cannot be 0", "points": []}

        p_bar = total_defective / total_inspected

        points = []
        for i in range(len(defective_counts)):
            d = defective_counts[i]
            n = sample_sizes[i]
            p = d / n if n > 0 else 0.0
            
            # Subgroup standard error
            se = np.sqrt(p_bar * (1.0 - p_bar) / n) if n > 0 and (p_bar * (1.0 - p_bar) >= 0) else 0.0
            ucl = min(1.0, p_bar + 3.0 * se)
            lcl = max(0.0, p_bar - 3.0 * se)
            is_ooc = (p > ucl) or (p < lcl)

            points.append({
                "index": i + 1,
                "label": labels[i] if labels and i < len(labels) else f"Lot-{i+1}",
                "defective": d,
                "sample_size": n,
                "p": round(p, 4),
                "p_percentage": round(p * 100, 2),
                "cl": round(p_bar, 4),
                "ucl": round(ucl, 4),
                "lcl": round(lcl, 4),
                "is_out_of_control": is_ooc
            })

        return {
            "chart_type": "P-Chart",
            "p_bar": round(p_bar, 4),
            "p_bar_percentage": round(p_bar * 100, 2),
            "total_defective": total_defective,
            "total_inspected": total_inspected,
            "points": points
        }

    @staticmethod
    def evaluate_nelson_rules(arr: np.ndarray, mean: float, sigma: float) -> list[dict[str, Any]]:
        """
        Evaluates Nelson 8 Rules for statistical control.
        Rule 1: 1 point > 3 sigma.
        Rule 2: 9 points in a row on same side of center line.
        Rule 3: 6 points in a row continuously increasing or decreasing.
        Rule 4: 14 points alternating up and down.
        Rule 5: 2 out of 3 points > 2 sigma on same side.
        Rule 6: 4 out of 5 points > 1 sigma on same side.
        Rule 7: 15 points in a row within 1 sigma (stratification).
        Rule 8: 8 points in a row with none within 1 sigma (mixture).
        """
        violations = []
        n = len(arr)
        if sigma <= 0 or n < 1:
            return violations

        # Rule 1: 1 point beyond 3 sigma
        for i in range(n):
            if abs(arr[i] - mean) > 3.0 * sigma:
                violations.append({
                    "rule": 1,
                    "rule_name": "Rule 1: Beyond 3 Sigma",
                    "index": i,
                    "description": f"Point {i+1} value ({arr[i]:.2f}) exceeds 3 standard deviations ({3*sigma:.2f}) from center line"
                })

        # Rule 2: 9 points in a row on same side of center line
        if n >= 9:
            for i in range(8, n):
                window = arr[i-8:i+1]
                if all(x > mean for x in window) or all(x < mean for x in window):
                    violations.append({
                        "rule": 2,
                        "rule_name": "Rule 2: Nine Points on Same Side",
                        "index": i,
                        "description": f"Point {i+1} is part of 9 consecutive points on the same side of the center line"
                    })

        # Rule 3: 6 points in a row strictly increasing or strictly decreasing
        if n >= 6:
            for i in range(5, n):
                window = arr[i-5:i+1]
                diffs = np.diff(window)
                if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                    direction = "increasing" if diffs[0] > 0 else "decreasing"
                    violations.append({
                        "rule": 3,
                        "rule_name": "Rule 3: Six Point Trend",
                        "index": i,
                        "description": f"Point {i+1} terminates 6 consecutive points continuously {direction}"
                    })

        # Rule 4: 14 points in a row alternating up and down
        if n >= 14:
            for i in range(13, n):
                window = arr[i-13:i+1]
                diffs = np.diff(window)
                alternating = True
                for k in range(len(diffs) - 1):
                    if (diffs[k] > 0 and diffs[k+1] >= 0) or (diffs[k] < 0 and diffs[k+1] <= 0):
                        alternating = False
                        break
                if alternating:
                    violations.append({
                        "rule": 4,
                        "rule_name": "Rule 4: Fourteen Alternating Points",
                        "index": i,
                        "description": f"Point {i+1} completes 14 consecutive points alternating direction"
                    })

        # Rule 5: 2 out of 3 consecutive points beyond 2 sigma on same side
        if n >= 3:
            for i in range(2, n):
                window = arr[i-2:i+1]
                upper_count = sum(1 for x in window if (x - mean) > 2.0 * sigma)
                lower_count = sum(1 for x in window if (mean - x) > 2.0 * sigma)
                if upper_count >= 2 or lower_count >= 2:
                    violations.append({
                        "rule": 5,
                        "rule_name": "Rule 5: 2 of 3 Beyond 2 Sigma",
                        "index": i,
                        "description": f"Point {i+1}: 2 out of 3 consecutive points are beyond 2 sigma"
                    })

        # Rule 6: 4 out of 5 consecutive points beyond 1 sigma on same side
        if n >= 5:
            for i in range(4, n):
                window = arr[i-4:i+1]
                upper_count = sum(1 for x in window if (x - mean) > 1.0 * sigma)
                lower_count = sum(1 for x in window if (mean - x) > 1.0 * sigma)
                if upper_count >= 4 or lower_count >= 4:
                    violations.append({
                        "rule": 6,
                        "rule_name": "Rule 6: 4 of 5 Beyond 1 Sigma",
                        "index": i,
                        "description": f"Point {i+1}: 4 out of 5 consecutive points are beyond 1 sigma on the same side"
                    })

        return violations

    @staticmethod
    def calculate_capability(values: list[float], lsl: Optional[float], usl: Optional[float], target: Optional[float] = None) -> dict[str, Any]:
        """
        Calculates Process Capability indices (Cp, Cpk, Pp, Ppk).
        Uses correct within-subgroup sigma estimation via Moving Range (d2=1.12838)
        and overall sample standard deviation (s).
        """
        if lsl is None and usl is None:
            return {
                "can_calculate": False,
                "reason": "Specification limits (LSL and/or USL) are missing. Capability cannot be calculated."
            }

        if not values or len(values) < 2:
            return {
                "can_calculate": False,
                "reason": "Insufficient observations (N < 2). At least 2 values required."
            }

        arr = np.array(values, dtype=float)
        n = len(arr)
        mean_val = float(np.mean(arr))
        sigma_overall = float(np.std(arr, ddof=1)) if n > 1 else 0.0

        # Estimate within-process sigma via moving range (I-MR method)
        mr = np.abs(np.diff(arr))
        mean_mr = float(np.mean(mr)) if len(mr) > 0 else 0.0
        d2 = 1.128379
        sigma_within = mean_mr / d2 if d2 > 0 and mean_mr > 0 else sigma_overall

        # Evaluate process stability
        violations = SPCEngine.evaluate_nelson_rules(arr, mean_val, sigma_within)
        is_stable = len(violations) == 0

        # Calculations
        cp = None
        cpk = None
        pp = None
        ppk = None
        cpu = None
        cpl = None
        ppu = None
        ppl = None

        if lsl is not None and usl is not None and (usl > lsl):
            if sigma_within > 0:
                cp = (usl - lsl) / (6.0 * sigma_within)
            if sigma_overall > 0:
                pp = (usl - lsl) / (6.0 * sigma_overall)

        if usl is not None and sigma_within > 0:
            cpu = (usl - mean_val) / (3.0 * sigma_within)
        if lsl is not None and sigma_within > 0:
            cpl = (mean_val - lsl) / (3.0 * sigma_within)

        if cpu is not None and cpl is not None:
            cpk = min(cpu, cpl)
        elif cpu is not None:
            cpk = cpu
        elif cpl is not None:
            cpk = cpl

        if usl is not None and sigma_overall > 0:
            ppu = (usl - mean_val) / (3.0 * sigma_overall)
        if lsl is not None and sigma_overall > 0:
            ppl = (mean_val - lsl) / (3.0 * sigma_overall)

        if ppu is not None and ppl is not None:
            ppk = min(ppu, ppl)
        elif ppu is not None:
            ppk = ppu
        elif ppl is not None:
            ppk = ppl

        # Expected ppm defective under normal distribution
        ppm_below = 0.0
        ppm_above = 0.0
        if sigma_overall > 0:
            if lsl is not None:
                ppm_below = float(stats.norm.cdf((lsl - mean_val) / sigma_overall)) * 1_000_000
            if usl is not None:
                ppm_above = float(1.0 - stats.norm.cdf((usl - mean_val) / sigma_overall)) * 1_000_000
        total_ppm = ppm_below + ppm_above

        # Capability assessment
        assessment = "EXCELLENT" if (cpk and cpk >= 1.67) else \
                     "ADEQUATE" if (cpk and cpk >= 1.33) else \
                     "BORDERLINE" if (cpk and cpk >= 1.0) else "INADEQUATE"

        warnings = []
        if n < 20:
            warnings.append(f"Sample size (N={n}) is smaller than recommended (N>=20). Capability figures carry statistical uncertainty.")
        if not is_stable:
            warnings.append("Process is statistically out of control (Nelson rule violations detected). Capability indices assume a stable process and may be misleading.")

        # Normality test
        normality_p = None
        is_normal = True
        if n >= 8:
            try:
                _, p_val = stats.normaltest(arr)
                normality_p = float(p_val)
                if normality_p < 0.05:
                    is_normal = False
                    warnings.append(f"Data deviates from normal distribution (p={normality_p:.4f}). Standard normal capability estimates may have bias.")
            except Exception:
                pass

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
            "assessment": assessment,
            "is_stable": is_stable,
            "is_normal": is_normal,
            "normality_p_value": round(normality_p, 4) if normality_p is not None else None,
            "warnings": warnings,
            "violations_count": len(violations)
        }
