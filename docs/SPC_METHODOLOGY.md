# Statistical Process Control (SPC) & Correlation Methodology

## 1. Individuals and Moving Range (I-MR) Charts

Used for continuous hourly green sand testing where each sampling interval produces an individual observation $X_i$ (ordered chronologically, missing/non-finite observations excluded and reported).

1. **Center Line**: $\overline{X} = \frac{1}{N} \sum_{i=1}^N X_i$ ($N \ge 2$).
2. **Moving Range (span $n=2$)**: $MR_i = |X_i - X_{i-1}|$, $\overline{MR} = \frac{1}{N-1} \sum_{i=2}^N MR_i$.
3. **Within-Process Sigma**: $\hat{\sigma}_{\text{within}} = \frac{\overline{MR}}{d_2}$, where $d_2 = 2/\sqrt{\pi} \approx 1.12837917$.
4. **Individuals Control Limits**: $UCL_I = \overline{X} + 3\hat{\sigma}_{\text{within}}$, $LCL_I = \overline{X} - 3\hat{\sigma}_{\text{within}}$.
5. **Moving Range Control Limits**: $UCL_{MR} = D_4 \cdot \overline{MR} = 3.26653 \cdot \overline{MR}$, $LCL_{MR} = 0$.

---

## 2. X-bar and R Charts

- **Constant Subgroup Sizes ($2 \le n \le 15$)**: Uses standard ASTM E2587 / ISO 7870 constants ($A_2, D_3, D_4, d_2$).
- **Variable Subgroup Sizes**: Estimates $\hat{\sigma}_{\text{within}} = \frac{1}{k}\sum_{i=1}^k \frac{R_i}{d_2(n_i)}$ and computes exact per-subgroup control limits $UCL_{X,i} = \overline{\overline{X}} + \frac{3\hat{\sigma}_{\text{within}}}{\sqrt{n_i}}$ rather than rounding average subgroup sizes.

---

## 3. Nelson 8 Rules

All 8 Nelson (1984) rules are evaluated when $\hat{\sigma}_{\text{within}} > 0$:

| Rule | Criterion | Interpretation |
|---|---|---|
| **Rule 1** | 1 point $> 3\sigma$ from center line | Gross process shock or measurement excursion |
| **Rule 2** | 9 consecutive points strictly on same side of center line | Sustained process mean shift |
| **Rule 3** | 6 consecutive points strictly increasing or decreasing | Progressive drift / wear / additive depletion |
| **Rule 4** | 14 consecutive points strictly alternating up and down | Over-adjustment or alternating sand/muller streams |
| **Rule 5** | 2 of 3 consecutive points $> 2\sigma$ on same side | Early warning of mean shift |
| **Rule 6** | 4 of 5 consecutive points $> 1\sigma$ on same side | Moderate sustained shift |
| **Rule 7** | 15 consecutive points strictly within $\pm 1\sigma$ | Stratification / mixed sampling or stale limits |
| **Rule 8** | 8 consecutive points $> 1\sigma$ on both sides (none within $\pm 1\sigma$) | Bimodal mixture / two distinct material sources |

---

## 4. Stability-Gated Process Capability & Normality

- **Stability First**: `stability_status` (`STABLE`, `UNSTABLE`, `CONSTANT_DATA`, `INSUFFICIENT_DATA`) is evaluated before capability. When unstable, `capability_status = "EXPLORATORY_UNSTABLE"` warns that indices do not imply future predictability.
- **Zero Variance**: When $\hat{\sigma}_{\text{within}} = 0$ or $s = 0$, indices are reported as `None` (`NOT_ASSESSABLE`) rather than `0` or infinity.
- **Formulas**:
  - $C_p = \frac{USL - LSL}{6\hat{\sigma}_{\text{within}}}$, $C_{pk} = \min\!\left(\frac{USL - \overline{X}}{3\hat{\sigma}_{\text{within}}}, \frac{\overline{X} - LSL}{3\hat{\sigma}_{\text{within}}}\right)$ (supports one-sided limits).
  - $P_p = \frac{USL - LSL}{6s}$, $P_{pk} = \min\!\left(\frac{USL - \overline{X}}{3s}, \frac{\overline{X} - LSL}{3s}\right)$.
- **Normality Testing**: Uses Shapiro-Wilk ($3 \le N \le 5000$) or D'Agostino-Pearson ($N > 5000$). Failing to reject ($p \ge 0.05$) does **not** prove normality.
- **PPM & Yield**: Normal-theory projections assume stability and normality using $\overline{X}$ and $s$.

---

## 5. Time-Lagged Correlation & Multiple Testing

- For each rejection at time $T$, upstream sand values are averaged within $[T - \Delta t \pm w]$, strictly enforcing $t_{\text{sand}} \le T$ to prevent future data leakage.
- Reports Pearson $r$ with Fisher $z$ 95% confidence interval, Spearman $\rho$, and Benjamini-Hochberg FDR adjusted $q$-values across multi-factor scans.
- Observational associations are explicitly framed as candidate factors for 8D/5-Why engineering investigation, never causal proof.
