# Statistical Process Control (SPC) Methodology

## 1. Mathematical Definitions

Statistical Process Control in **PS-010** is implemented strictly according to standard statistical quality engineering standards (ASTM E2587 / ISO 7870 / AIAG SPC Manual).

### 1.1 Individuals and Moving Range (I-MR) Control Charts

Used for continuous hourly sand testing where each sampling interval produces a single individual observation $X_i$.

1. **Center Line (Average)**:
   $$\overline{X} = \frac{1}{N} \sum_{i=1}^N X_i$$

2. **Moving Range**:
   $$MR_i = |X_i - X_{i-1}| \quad \text{for } i = 2, \dots, N$$
   $$\overline{MR} = \frac{1}{N-1} \sum_{i=2}^N MR_i$$

3. **Estimate of Within-Process Standard Deviation ($\hat{\sigma}_{within}$)**:
   $$\hat{\sigma}_{within} = \frac{\overline{MR}}{d_2}$$
   Where for moving range span $n = 2$, $d_2 = 1.12837917$.

4. **Individuals Chart Control Limits**:
   $$UCL_I = \overline{X} + 3 \hat{\sigma}_{within} = \overline{X} + 2.66 \times \overline{MR}$$
   $$CL_I = \overline{X}$$
   $$LCL_I = \overline{X} - 3 \hat{\sigma}_{within} = \overline{X} - 2.66 \times \overline{MR}$$

5. **Moving Range Chart Control Limits**:
   $$UCL_{MR} = D_4 \times \overline{MR} = 3.267 \times \overline{MR}$$
   $$CL_{MR} = \overline{MR}$$
   $$LCL_{MR} = D_3 \times \overline{MR} = 0$$

---

## 2. Nelson 8 Rules for Special Cause Variation

The system evaluates all 8 Nelson rules on the chronologically ordered observation sequence:

| Rule | Description | Statistical Implication |
|------|-------------|-------------------------|
| **Rule 1** | One point beyond 3 sigma from center line ($> UCL$ or $< LCL$) | Gross process shock or measurement error |
| **Rule 2** | Nine consecutive points on the same side of center line | Process mean shift / drift |
| **Rule 3** | Six consecutive points steadily increasing or decreasing | Continuous wear, temperature ramp, or additive depletion |
| **Rule 4** | Fourteen consecutive points alternating up and down | Systematic over-adjustment / two alternated supply sources |
| **Rule 5** | Two out of three consecutive points beyond 2 sigma on the same side | Early warning of impending process shift |
| **Rule 6** | Four out of five consecutive points beyond 1 sigma on the same side | Small sustained mean shift |
| **Rule 7** | Fifteen consecutive points within 1 sigma of center line | Stratification (incorrect limit estimation or mixed subgrouping) |
| **Rule 8** | Eight consecutive points with none within 1 sigma on either side | Mixture of two distinct populations / raw material lots |

---

## 3. Process Capability Indices

Capability calculations measure the relationship between the natural process spread and the engineering specification limits:

### 3.1 Potential Capability (Within-subgroup: $C_p$ and $C_{pk}$)
$$C_p = \frac{USL - LSL}{6 \hat{\sigma}_{within}}$$

$$C_{pu} = \frac{USL - \overline{X}}{3 \hat{\sigma}_{within}}, \quad C_{pl} = \frac{\overline{X} - LSL}{3 \hat{\sigma}_{within}}$$

$$C_{pk} = \min(C_{pu}, C_{pl})$$

### 3.2 Overall Performance ($P_p$ and $P_{pk}$)
Using the overall sample standard deviation $s = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (X_i - \overline{X})^2}$:

$$P_p = \frac{USL - LSL}{6 s}$$

$$P_{pu} = \frac{USL - \overline{X}}{3 s}, \quad P_{pl} = \frac{\overline{X} - LSL}{3 s}$$

$$P_{pk} = \min(P_{pu}, P_{pl})$$

### 3.3 Quality Thresholds
- $C_{pk} \ge 1.67$: **Excellent** (World Class / Six Sigma)
- $1.33 \le C_{pk} < 1.67$: **Adequate** (IATF 16949 Automotive Standard)
- $1.00 \le C_{pk} < 1.33$: **Borderline** (Process requires tightening)
- $C_{pk} < 1.00$: **Inadequate** (Process produces nonconforming material)
