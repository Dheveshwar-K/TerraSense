import numpy as np
from scipy import stats
from typing import Any, Optional
from datetime import datetime, timedelta

class CorrelationEngine:
    """
    Dedicated Foundry Sand Quality & Casting Defect Correlation Engine.
    Analyzes historical sand testing parameters against downstream casting defect rejections
    across configurable time lag windows (0h, 6h, 12h, 24h, 48h, 72h).
    Strictly adheres to statistical reporting standards: correlation != causation.
    """

    @staticmethod
    def analyze_pair(
        parameter_name: str,
        defect_name: str,
        line_code: str,
        sand_points: list[dict[str, Any]],  # [{timestamp, value, is_out_of_spec}]
        rejection_points: list[dict[str, Any]],  # [{timestamp, rejection_rate, rejected_qty, inspected_qty}]
        lag_hours: int = 12,
        usl: Optional[float] = None,
        lsl: Optional[float] = None
    ) -> dict[str, Any]:
        """
        Pairs sand test measurements with rejection records with a specific time lag window.
        Computes Pearson and Spearman correlation, group comparisons (In-Spec vs Out-of-Spec),
        and candidate root-cause insights with responsible non-causal language.
        """
        if not sand_points or not rejection_points:
            return {
                "parameter_name": parameter_name,
                "defect_name": defect_name,
                "line_code": line_code,
                "lag_hours": lag_hours,
                "sample_size": 0,
                "has_sufficient_data": False,
                "message": "Insufficient data points to compute correlation."
            }

        # Pair observations: For each rejection at time T, find average sand value at T - lag_hours (+/- window)
        paired_sand = []
        paired_rejection = []
        is_high_sand_group = []

        window_half = max(3.0, lag_hours * 0.4)  # tolerance window in hours

        for rej in rejection_points:
            rej_time = rej.get("timestamp")
            if isinstance(rej_time, str):
                try:
                    rej_time = datetime.fromisoformat(rej_time.replace("Z", "+00:00"))
                except Exception:
                    continue
            
            target_sand_time = rej_time - timedelta(hours=lag_hours)
            
            # Find sand measurements within target_sand_time +/- window_half
            matching_vals = []
            for s in sand_points:
                s_time = s.get("timestamp")
                if isinstance(s_time, str):
                    try:
                        s_time = datetime.fromisoformat(s_time.replace("Z", "+00:00"))
                    except Exception:
                        continue
                diff_hours = abs((s_time - target_sand_time).total_seconds()) / 3600.0
                if diff_hours <= window_half:
                    matching_vals.append(s.get("value"))

            if matching_vals:
                avg_sand = float(np.mean(matching_vals))
                rate = float(rej.get("rejection_rate", 0.0))
                paired_sand.append(avg_sand)
                paired_rejection.append(rate)

                # Classify into high/out-of-spec or normal
                is_high = False
                if usl is not None and avg_sand > usl:
                    is_high = True
                elif lsl is not None and avg_sand < lsl:
                    is_high = True
                is_high_sand_group.append(is_high)

        n_pairs = len(paired_sand)
        if n_pairs < 5:
            return {
                "parameter_name": parameter_name,
                "defect_name": defect_name,
                "line_code": line_code,
                "lag_hours": lag_hours,
                "sample_size": n_pairs,
                "has_sufficient_data": False,
                "message": f"Only {n_pairs} matched time-lagged pairs found. Minimum 5 required."
            }

        sand_arr = np.array(paired_sand, dtype=float)
        rej_arr = np.array(paired_rejection, dtype=float)

        # Pearson correlation
        pearson_r, pearson_p = 0.0, 1.0
        if np.std(sand_arr) > 1e-6 and np.std(rej_arr) > 1e-6:
            r_val, p_val = stats.pearsonr(sand_arr, rej_arr)
            pearson_r = float(r_val)
            pearson_p = float(p_val)

        # Spearman correlation
        spearman_rho, spearman_p = 0.0, 1.0
        if np.std(sand_arr) > 1e-6 and np.std(rej_arr) > 1e-6:
            rho_val, p_val = stats.spearmanr(sand_arr, rej_arr)
            spearman_rho = float(rho_val)
            spearman_p = float(p_val)

        # Group comparison
        high_group = rej_arr[np.array(is_high_sand_group)]
        normal_group = rej_arr[~np.array(is_high_sand_group)]

        mean_rej_high = float(np.mean(high_group)) if len(high_group) > 0 else None
        mean_rej_normal = float(np.mean(normal_group)) if len(normal_group) > 0 else None
        diff_ratio = None
        group_p_val = None

        if mean_rej_high is not None and mean_rej_normal is not None and mean_rej_normal > 0:
            diff_ratio = mean_rej_high / mean_rej_normal
            if len(high_group) >= 2 and len(normal_group) >= 2:
                try:
                    _, t_p = stats.ttest_ind(high_group, normal_group, equal_var=False)
                    group_p_val = float(t_p)
                except Exception:
                    pass

        # Correlation strength interpretation
        abs_r = abs(pearson_r)
        strength = "VERY_STRONG" if abs_r >= 0.7 else \
                   "STRONG" if abs_r >= 0.5 else \
                   "MODERATE" if abs_r >= 0.3 else "WEAK"

        is_statistically_significant = pearson_p < 0.05

        # Responsible industrial insight formulation
        direction = "higher" if pearson_r > 0 else "lower"
        insight_parts = []
        if is_statistically_significant and abs_r >= 0.35:
            if diff_ratio and diff_ratio > 1.2:
                insight_parts.append(
                    f"{parameter_name} deviations were associated with a {diff_ratio:.1f}x higher observed rate "
                    f"of {defect_name} defects on line {line_code} across a {lag_hours}-hour process lag window "
                    f"(Pearson r = {pearson_r:.2f}, p = {pearson_p:.3f})."
                )
            else:
                insight_parts.append(
                    f"An observed positive association exists between {parameter_name} and {defect_name} "
                    f"rejection rates on line {line_code} at {lag_hours}h lag (r = {pearson_r:.2f}, p = {pearson_p:.3f})."
                )
            insight_parts.append("Candidate root cause identified for structured 8D/Fishbone investigation. Note: Correlation does not prove causation.")
        else:
            insight_parts.append(
                f"No statistically significant linear relationship detected between {parameter_name} and {defect_name} "
                f"at {lag_hours}h lag (r = {pearson_r:.2f}, p = {pearson_p:.3f}). Note: Correlation does not prove causation."
            )

        scatter_points = []
        for i in range(min(50, n_pairs)):
            scatter_points.append({
                "x_sand": round(float(sand_arr[i]), 3),
                "y_rejection": round(float(rej_arr[i]), 3),
                "is_out_of_spec": bool(is_high_sand_group[i])
            })

        return {
            "parameter_name": parameter_name,
            "defect_name": defect_name,
            "line_code": line_code,
            "lag_hours": lag_hours,
            "sample_size": n_pairs,
            "has_sufficient_data": n_pairs >= 10,
            "pearson_r": round(pearson_r, 3),
            "pearson_p_value": round(pearson_p, 4),
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
                "group_p_value": round(group_p_val, 4) if group_p_val is not None else None
            },
            "insight": " ".join(insight_parts),
            "scatter_points": scatter_points
        }
