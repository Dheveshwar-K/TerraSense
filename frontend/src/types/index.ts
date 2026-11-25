export type UserRole = 'operator' | 'quality_engineer' | 'supervisor' | 'quality_manager' | 'admin';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  must_change_password?: boolean;
  created_at?: string;
}

export interface AuthConfig {
  demo_mode: boolean;
  environment: string;
  access_token_expire_minutes: number;
}

export interface ProductionLine {
  id: number;
  code: 'D1' | 'D2' | 'D3' | 'D4';
  name: string;
  description?: string;
  molding_type: string;
  capacity_tph: number;
  is_active: boolean;
}

export interface Parameter {
  id: number;
  code: string;
  name: string;
  description?: string;
  category: 'PHYSICAL' | 'CHEMICAL';
  unit: string;
  frequency: 'HOURLY' | 'SHIFT' | 'DAILY';
  applicable_lines: string;
  target_value: number;
  lsl: number;
  usl: number;
  lcl_historical?: number;
  ucl_historical?: number;
  current_revision: number;
  version?: number;
  testing_method?: string;
  data_validation_min?: number;
  data_validation_max?: number;
  is_active: boolean;
}

export interface SpecificationRevision {
  id: number;
  parameter_id: number;
  revision_number: number;
  effective_date: string;
  target_value: number;
  lsl: number;
  usl: number;
  change_reason: string;
  approved_by_id?: number;
}

export interface SandTestValue {
  id: number;
  parameter_id: number;
  parameter_name: string;
  parameter_code: string;
  measured_value: number;
  unit: string;
  status: 'OK' | 'WARNING' | 'OUT_OF_SPEC';
  is_corrected: boolean;
  original_value?: number;
  correction_reason?: string;
}

export interface SandTestRecord {
  id: number;
  test_number: string;
  line_code: string;
  test_type: 'HOURLY_PHYSICAL' | 'SHIFT_CHEMICAL';
  test_date: string;
  shift: number;
  test_hour: number;
  timestamp: string;
  batch_number?: string;
  status: 'CONFORMING' | 'WARNING' | 'OUT_OF_SPEC';
  notes?: string;
  operator_name?: string;
  values: SandTestValue[];
}

export interface CorrectionRequest {
  id: number;
  value_id: number;
  test_number?: string;
  line_code?: string;
  parameter_name?: string;
  current_value?: number;
  requested_value: number;
  unit?: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requested_by_name?: string;
  reviewed_by_name?: string;
  review_notes?: string;
  created_at: string;
}

export interface SandBatch {
  id: number;
  batch_number: string;
  line_code: string;
  muller_id: string;
  batch_weight_kg: number;
  bentonite_addition_kg: number;
  coal_dust_addition_kg: number;
  new_sand_addition_kg: number;
  return_sand_kg: number;
  water_addition_liters: number;
  cycle_time_seconds: number;
  operator_id?: number;
  timestamp: string;
  notes?: string;
}

export interface SPCPoint {
  index: number;
  timestamp: string;
  value: number;
  mr?: number;
  cl: number;
  ucl: number;
  lcl: number;
  mr_cl?: number;
  mr_ucl?: number;
  mr_lcl?: number;
  lsl?: number;
  usl?: number;
  is_out_of_control: boolean;
  is_mr_out_of_control?: boolean;
  violations: string[];
  spec_status: string;
}

export interface IMRChartData {
  chart_type: string;
  parameter_name: string;
  parameter_code: string;
  unit: string;
  line_code: string;
  sample_size: number;
  is_constant?: boolean;
  mean: number;
  mean_mr: number;
  sigma_within: number;
  sigma_overall: number;
  target?: number;
  lsl?: number;
  usl?: number;
  i_chart: {
    cl: number;
    ucl: number;
    lcl: number;
    zone_1s_upper: number;
    zone_2s_upper: number;
    zone_1s_lower: number;
    zone_2s_lower: number;
  };
  mr_chart: {
    cl: number;
    ucl: number;
    lcl: number;
  };
  violations_count: number;
  is_stable: boolean;
  warnings?: string[];
  message?: string;
  error?: string;
  points: SPCPoint[];
}

export interface XBarRPoint {
  subgroup: number;
  label: string;
  size: number;
  x_bar: number;
  range: number;
  ucl_x: number;
  lcl_x: number;
  cl_x: number;
  ucl_r: number;
  lcl_r: number;
  cl_r: number;
  is_out_of_control: boolean;
}

export interface XBarRChartData {
  chart_type: string;
  parameter_name: string;
  parameter_code: string;
  unit: string;
  line_code: string;
  subgroups_count?: number;
  subgroup_size?: number;
  variable_subgroup_sizes?: boolean;
  grand_mean?: number;
  mean_range?: number;
  sigma_within?: number;
  ucl_x?: number;
  lcl_x?: number;
  ucl_r?: number;
  lcl_r?: number;
  target?: number;
  lsl?: number;
  usl?: number;
  warnings?: string[];
  error?: string;
  points: XBarRPoint[];
}

export interface ProcessCapabilityData {
  can_calculate: boolean;
  reason?: string;
  sample_size?: number;
  parameter_name?: string;
  parameter_code?: string;
  unit?: string;
  line_code?: string;
  mean?: number;
  target?: number;
  lsl?: number;
  usl?: number;
  sigma_within?: number;
  sigma_overall?: number;
  cp?: number | null;
  cpk?: number | null;
  cpu?: number | null;
  cpl?: number | null;
  pp?: number | null;
  ppk?: number | null;
  ppu?: number | null;
  ppl?: number | null;
  ppm_total?: number;
  ppm_below_lsl?: number;
  ppm_above_usl?: number;
  yield_percentage?: number;
  assessment?: string;
  stability_status?: string;
  capability_status?: string;
  is_stable?: boolean;
  is_normal?: boolean;
  normality_rejected?: boolean | null;
  normality_test_used?: string | null;
  normality_p_value?: number | null;
  normality_note?: string;
  ppm_assumptions?: string;
  warnings?: string[];
  violations_count?: number;
}

export interface DefectCategory {
  id: number;
  code: string;
  name: string;
  description?: string;
  potential_sand_causes?: string;
}

export interface CastingProduct {
  id: number;
  part_number: string;
  part_name: string;
  customer_name: string;
  material_grade: string;
}

export interface RejectionRecord {
  id: number;
  rejection_number: string;
  production_date: string;
  line_code: string;
  shift: number;
  product_name: string;
  defect_name: string;
  defect_code: string;
  rejected_qty: number;
  inspected_qty: number;
  rejection_rate: number;
  batch_number?: string;
  detection_stage: string;
  severity: string;
  root_cause_candidate?: string;
  corrective_action?: string;
  responsible_person?: string;
  inspector_name?: string;
  status: string;
}

export interface ParetoItem {
  defect_id: number;
  defect_name: string;
  defect_code: string;
  rejected_qty: number;
  percentage: number;
  cumulative_percentage: number;
}

export interface ParetoResponse {
  line_code: string;
  total_rejected: number;
  defects_count: number;
  items: ParetoItem[];
}

export interface CorrelationAnalysis {
  parameter_code: string;
  parameter_name: string;
  defect_code: string;
  defect_name: string;
  parameter_unit: string;
  line_code: string;
  lag_hours: number;
  lag_convention?: string;
  sample_size: number;
  has_sufficient_data: boolean;
  message?: string;
  pearson_r: number;
  pearson_p_value: number;
  pearson_ci_95?: [number, number] | null;
  spearman_rho: number;
  spearman_p_value: number;
  relationship_strength: string;
  is_statistically_significant: boolean;
  group_comparison: {
    high_or_ooc_count: number;
    normal_count: number;
    mean_rejection_high_group?: number;
    mean_rejection_normal_group?: number;
    rejection_ratio?: number;
    group_p_value?: number;
  };
  insight: string;
  limitations?: string[];
  usl?: number;
  lsl?: number;
  scatter_points: Array<{
    x_sand: number;
    y_rejection: number;
    is_out_of_spec: boolean;
    timestamp?: string;
  }>;
}

export interface RootCauseInvestigation {
  id: number;
  investigation_number: string;
  title: string;
  line_code: string;
  parameter_id?: number;
  defect_category_id?: number;
  lag_hours: number;
  correlation_stat?: number;
  p_value?: number;
  five_why_analysis: string[];
  fishbone_factors: Record<string, string>;
  findings?: string;
  conclusion?: string;
  status: 'IN_PROGRESS' | 'VALIDATED' | 'CLOSED';
  version: number;
  investigator_name?: string;
  created_at: string;
  updated_at?: string;
}

export interface CustomerComplaint {
  id: number;
  complaint_number: string;
  customer_name: string;
  received_date: string;
  product_name: string;
  defect_name: string;
  batch_number?: string;
  line_code: string;
  affected_qty: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  status: 'OPEN' | 'UNDER_INVESTIGATION' | 'CAPA_PENDING' | 'CLOSED';
  version?: number;
  d1_team?: string;
  d2_problem?: string;
  d3_containment?: string;
  d4_root_cause?: string;
  d5_corrective_action?: string;
  d6_validation?: string;
  d7_preventive_action?: string;
  d8_closure?: string;
  responsible_person?: string;
  due_date?: string;
}

export interface QualityAlert {
  id: number;
  alert_code: string;
  line_code: string;
  parameter_name?: string;
  parameter_code?: string;
  alert_type: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  description: string;
  nelson_rule_triggered?: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  version?: number;
  timestamp: string;
  acknowledged_by_name?: string;
  resolved_by_name?: string;
  resolution_notes?: string;
}

export interface AuditLog {
  id: number;
  sequence_no?: number;
  timestamp: string;
  user_name: string;
  user_role: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  old_value?: string;
  new_value?: string;
  reason?: string;
  ip_address?: string;
  outcome?: string;
  prev_hash?: string;
  record_hash?: string;
}

export interface AuditVerificationResult {
  valid: boolean;
  total_records: number;
  verified_records: number;
  broken_links: Array<{ audit_id: number; sequence_no: number; issues: string[] }>;
  head_hash?: string | null;
  threat_model_note: string;
}

export interface DashboardMetrics {
  total_tests_today: number;
  total_tests_week: number;
  conforming_percentage: number;
  open_alerts: number;
  total_rejected_qty: number;
  total_inspected_qty: number;
  overall_rejection_rate: number;
  active_complaints: number;
}

export interface LineCardInfo {
  line_code: 'D1' | 'D2' | 'D3' | 'D4';
  health: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  latest_test_number: string;
  latest_test_status: string;
  latest_test_time?: string;
  open_alerts: number;
  rejection_rate: number;
  molding_line: string;
}
