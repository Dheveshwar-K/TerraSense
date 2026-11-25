import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from scipy import stats


def _parse_utc_naive(ts: Any) -> Optional[datetime]:
    if isinstance(ts, datetime):
        if ts.tzinfo is not None:
            return ts.astimezone(timezone.utc).replace(tzinfo=None)
        return ts
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            return None
    return None


def _fisher_ci(r: float, n: int, alpha: float = 0.05) -> Optional[list[float]]:
    """95% confidence interval for Pearson r using Fisher z-transformation."""
    if n < 4 or abs(r) >= 0.999999:
        return None
    z = 0.5 * math.log((1.0 + r) / (1.0 - r))
    se = 1.0 / math.sqrt(n - 3)
    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    lo = math.tanh(z - z_crit * se)
    hi = math.tanh(z + z_crit * se)
    return [round(lo, 3), round(hi, 3)]


def apply_benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR adjusted p-values for multiple hypothesis comparisons."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [1.0] * m
    prev = 1.0
    for rank_desc in range(m - 1, -1, -1):
        orig_idx, p = indexed[rank_desc]
        rank = rank_desc + 1
        val = min(prev, (p * m) / rank)
        adjusted[orig_idx] = round(min(1.0, max(0.0, val)), 4)
        prev = val
    return adjusted


class CorrelationEngine:
    """
    Foundry Sand Quality & Casting Defect Time-Lagged Correlation Engine.
    Pairs upstream sand testing parameters at (T - lag_hours) with downstream casting rejections at T,
    strictly preventing future data leakage (sand_time <= rej_time) and reporting non-causal caveats.
    """

    @staticmethod
    def analyze_pair(
        parameter_name: str,
        defect_name: str,
        line_code: str,
        sand_points: list[dict[str, Any]],
        rejection_points: list[dict[str, Any]],
        lag_hours: int = 12,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> dict[str, Any]:
        if lag_hours < 0:
            raise ValueError("lag_hours must be non-negative to prevent future data leakage")

        if not sand_points or not rejection_points:
            return {
                "parameter_name": parameter_name,
                "defect_name": defect_name,
                "line_code": line_code,
                "lag_hours": lag_hours,
                "sample_size": 0,
                "has_sufficient_data": False,
                "message": "Insufficient data points to compute correlation.",
                "limitations": [
                    "No paired observations available.",
                    "Correlation does not prove causation.",
                ],
            }

        # Normalize & sort sand points chronologically
        parsed_sand: list[tuple[datetime, float]] = []
        for s in sand_points:
            st = _parse_utc_naive(s.get("timestamp"))
            val = s.get("value")
            if st is None or val is None:
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            if math.isfinite(fval):
                parsed_sand.append((st, fval))
        parsed_sand.sort(key=lambda x: x[0])

        # Normalize & sort rejection points chronologically
        parsed_rej: list[tuple[datetime, float]] = []
        for r in rejection_points:
            rt = _parse_utc_naive(r.get("timestamp"))
            rate = r.get("rejection_rate")
            if rt is None or rate is None:
                continue
            try:
                frate = float(rate)
            except (TypeError, ValueError):
                continue
            if math.isfinite(frate):
                parsed_rej.append((rt, frate))
        parsed_rej.sort(key=lambda x: x[0])

        paired_sand: list[float] = []
        paired_rejection: list[float] = []
        is_ooc_group: list[bool] = []
        paired_timestamps: list[str] = []

        window_half = max(3.0, lag_hours * 0.4)

        for rej_time, rate in parsed_rej:
            target_sand_time = rej_time - timedelta(hours=lag_hours)
            matching_vals: list[float] = []

            for s_time, s_val in parsed_sand:
                # Strict causal ordering: never pair future sand tests after rejection timestamp
                if s_time > rej_time:
                    continue
                diff_hours = abs((s_time - target_sand_time).total_seconds()) / 3600.0
                if diff_hours <= window_half:
                    matching_vals.append(s_val)

            if matching_vals:
                avg_sand = float(np.mean(matching_vals))
                paired_sand.append(avg_sand)
                paired_rejection.append(rate)
                paired_timestamps.append(rej_time.isoformat())

                is_ooc = False
                if usl is not None and avg_sand > usl:
                    is_ooc = True
                elif lsl is not None and avg_sand < lsl:
                    is_ooc = True
                is_ooc_group.append(is_ooc)

        n_pairs = len(paired_sand)
        if n_pairs < 5:
            return {
                "parameter_name": parameter_name,
                "defect_name": defect_name,
                "line_code": line_code,
                "lag_hours": lag_hours,
                "sample_size": n_pairs,
                "has_sufficient_data": False,
                "message": f"Only {n_pairs} matched time-lagged pairs found. Minimum 5 required.",
                "limitations": [
                    "Sample size too small (N < 5) for reliable correlation inference.",
                    "Correlation does not prove causation.",
                ],
            }

        sand_arr = np.array(paired_sand, dtype=float)
        rej_arr = np.array(paired_rejection, dtype=float)

        pearson_r, pearson_p = 0.0, 1.0
        spearman_rho, spearman_p = 0.0, 1.0
        zero_variance = float(np.std(sand_arr)) <= 1e-9 or float(np.std(rej_arr)) <= 1e-9

        if not zero_variance:
            r_val, p_val = stats.pearsonr(sand_arr, rej_arr)
            if math.isfinite(float(r_val)) and math.isfinite(float(p_val)):
                pearson_r = float(r_val)
                pearson_p = float(p_val)

            rho_val, sp_p_val = stats.spearmanr(sand_arr, rej_arr)
            if math.isfinite(float(rho_val)) and math.isfinite(float(sp_p_val)):
                spearman_rho = float(rho_val)
                spearman_p = float(sp_p_val)

        pearson_ci = _fisher_ci(pearson_r, n_pairs) if not zero_variance else None

        # Group comparison (Out-of-Spec vs In-Spec sand)
        ooc_mask = np.array(is_ooc_group, dtype=bool)
        high_group = rej_arr[ooc_mask]
        normal_group = rej_arr[~ooc_mask]

        mean_rej_high = float(np.mean(high_group)) if len(high_group) > 0 else None
        mean_rej_normal = float(np.mean(normal_group)) if len(normal_group) > 0 else None
        diff_ratio = None
        group_p_val = None

        if mean_rej_high is not None and mean_rej_normal is not None and mean_rej_normal > 0:
            diff_ratio = mean_rej_high / mean_rej_normal
            if len(high_group) >= 2 and len(normal_group) >= 2:
                try:
                    _, t_p = stats.ttest_ind(high_group, normal_group, equal_var=False)
                    if math.isfinite(float(t_p)):
                        group_p_val = float(t_p)
                except Exception:
                    pass

        abs_r = abs(pearson_r)
        strength = (
            "VERY_STRONG" if abs_r >= 0.7 else
            "STRONG" if abs_r >= 0.5 else
            "MODERATE" if abs_r >= 0.3 else
            "WEAK"
        )

        is_statistically_significant = (not zero_variance) and (pearson_p < 0.05) and (n_pairs >= 5)
        direction_label = "positive" if pearson_r > 0 else "negative (inverse)"

        insight_parts: list[str] = []
        if zero_variance:
            insight_parts.append(
                f"Zero variance in paired {parameter_name} or {defect_name} observations; linear correlation is undefined."
            )
        elif is_statistically_significant and abs_r >= 0.35:
            if diff_ratio and diff_ratio > 1.2:
                insight_parts.append(
                    f"Potential statistical association identified: {parameter_name} out-of-spec runs coincided with a "
                    f"{diff_ratio:.1f}x higher observed {defect_name} rejection rate on line {line_code} at a {lag_hours}-hour lag "
                    f"(Pearson r = {pearson_r:.2f}, p = {pearson_p:.4f}, N = {n_pairs})."
                )
            else:
                insight_parts.append(
                    f"Potential statistical association identified: an observed {direction_label} association exists between "
                    f"{parameter_name} and {defect_name} rejection rates on line {line_code} at {lag_hours}h lag "
                    f"(r = {pearson_r:.2f}, p = {pearson_p:.4f}, N = {n_pairs})."
                )
            insight_parts.append(
                "Candidate contributing factor for structured 8D/Fishbone engineering investigation. "
                "Note: Correlation does not prove causation."
            )
        else:
            insight_parts.append(
                f"No strong statistically significant linear association detected between {parameter_name} and {defect_name} "
                f"at {lag_hours}h lag (r = {pearson_r:.2f}, p = {pearson_p:.4f}, N = {n_pairs}). "
                "Note: Correlation does not prove causation."
            )

        limitations = [
            "Observational time-series correlation does not establish causation.",
            "Confounding variables (pouring temperature, alloy chemistry, mold compaction, tooling wear) are not controlled.",
            "Serial autocorrelation in hourly sand and shift rejection series can inflate apparent significance (smaller effective sample size).",
        ]
        if n_pairs < 15:
            limitations.append(f"Small paired sample size (N={n_pairs}) reduces statistical power and widens confidence intervals.")

        # Return up to 100 chronologically sampled scatter points
        step = max(1, n_pairs // 100)
        scatter_points = []
        for i in range(0, n_pairs, step):
            scatter_points.append({
                "x_sand": round(float(sand_arr[i]), 3),
                "y_rejection": round(float(rej_arr[i]), 3),
                "is_out_of_spec": bool(is_ooc_group[i]),
                "timestamp": paired_timestamps[i],
            })

        return {
            "parameter_name": parameter_name,
            "defect_name": defect_name,
            "line_code": line_code,
            "lag_hours": lag_hours,
            "lag_convention": f"Average sand value in [T - {lag_hours}h +/- {window_half:.1f}h] paired with rejection at T (sand timestamp <= rejection timestamp).",
            "sample_size": n_pairs,
            "has_sufficient_data": n_pairs >= 10,
            "pearson_r": round(pearson_r, 3),
            "pearson_p_value": round(pearson_p, 4),
            "pearson_ci_95": pearson_ci,
            "spearman_rho": round(spearman_rho, 3),
            "spearman_p_value": round(spearman_p, 4),
            "relationship_strength": strength,
            "is_statistically_significant": is_statistically_significant,
            "group_comparison": {
                "high_or_ooc_count": len(high_group),
                "normal_count": len(normal_group),
                "mean_rejection_high_group": round(mean_rej_high, 2) if mean_rej_high is not None else None,
                "mean_rejection_normal_group": round(mean_rej_normal, 2) if mean_rej_normal is not None else None,
                "rejection_ratio": round(diff_ratio, 2) if diff_ratio is not None else None,
                "group_p_value": round(group_p_val, 4) if group_p_val is not None else None,
            },
            "insight": " ".join(insight_parts),
            "limitations": limitations,
            "scatter_points": scatter_points,
        }
