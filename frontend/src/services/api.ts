import {
  AuthConfig,
  AuditLog,
  AuditVerificationResult,
  CastingProduct,
  CorrelationAnalysis,
  CorrectionRequest,
  CustomerComplaint,
  DashboardMetrics,
  DefectCategory,
  IMRChartData,
  LineCardInfo,
  Parameter,
  ParetoResponse,
  ProcessCapabilityData,
  ProductionLine,
  QualityAlert,
  RejectionRecord,
  RootCauseInvestigation,
  SandBatch,
  SandTestRecord,
  SpecificationRevision,
  User,
  UserRole,
  XBarRChartData,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const REQUEST_TIMEOUT_MS = 15000;

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('ps010_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshSession(): Promise<boolean> {
  const refreshToken = localStorage.getItem('ps010_refresh_token');
  if (!refreshToken) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        if (data?.access_token) {
          localStorage.setItem('ps010_token', data.access_token);
          if (data.refresh_token) {
            localStorage.setItem('ps010_refresh_token', data.refresh_token);
          }
          return true;
        }
        return false;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function request<T>(endpoint: string, options: RequestInit = {}, allowRefresh = true): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers as Record<string, string> | undefined),
  };

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (response.status === 401 && allowRefresh && !endpoint.startsWith('/auth/')) {
      const refreshed = await tryRefreshSession();
      if (refreshed) {
        return request<T>(endpoint, options, false);
      }
    }

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errData = await response.json();
        if (errData && errData.detail) {
          errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
        }
      } catch {
        // ignore parse failure
      }
      throw new Error(errorMsg);
    }

    return response.json();
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out. Verify backend service connectivity.');
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  // Auth
  async getAuthConfig(): Promise<AuthConfig> {
    return request('/auth/config', {}, false);
  },

  async login(
    username: string,
    password: string
  ): Promise<{ access_token: string; refresh_token?: string; user: User }> {
    return request(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      },
      false
    );
  },

  async demoSwitch(
    role: UserRole,
    userId?: string
  ): Promise<{ access_token: string; refresh_token?: string; user: User }> {
    return request(
      '/auth/demo-switch',
      {
        method: 'POST',
        body: JSON.stringify({ role, user_id: userId }),
      },
      false
    );
  },

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('ps010_refresh_token');
    const q = refreshToken ? `?refresh_token=${encodeURIComponent(refreshToken)}` : '';
    await request(`/auth/logout${q}`, { method: 'POST' }, false);
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  async getMe(): Promise<User> {
    return request('/auth/me');
  },

  // Users (Admin / Quality Manager)
  async getUsers(): Promise<User[]> {
    return request('/users');
  },

  async createUser(data: {
    username: string;
    email: string;
    full_name: string;
    role: UserRole;
    password: string;
    is_active?: boolean;
  }): Promise<User> {
    return request('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateUser(
    userId: number,
    data: { full_name?: string; email?: string; role?: UserRole; is_active?: boolean }
  ): Promise<User> {
    return request(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Lines
  async getLines(): Promise<ProductionLine[]> {
    return request('/lines');
  },

  // Parameters
  async getParameters(category?: string, frequency?: string): Promise<Parameter[]> {
    const q = new URLSearchParams();
    if (category) q.set('category', category);
    if (frequency) q.set('frequency', frequency);
    return request(`/parameters?${q.toString()}`);
  },

  async updateSpecification(
    paramId: number,
    data: {
      target_value?: number;
      lsl?: number;
      usl?: number;
      revision_reason?: string;
      expected_version?: number;
    }
  ): Promise<Parameter> {
    return request(`/parameters/${paramId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async getParameterRevisions(paramId: number): Promise<SpecificationRevision[]> {
    return request(`/parameters/${paramId}/revisions`);
  },

  // Sand Tests
  async getSandTests(
    params: {
      line_code?: string;
      test_type?: string;
      test_date?: string;
      start_date?: string;
      end_date?: string;
      shift?: number;
      status?: string;
      limit?: number;
    } = {}
  ): Promise<SandTestRecord[]> {
    const q = new URLSearchParams();
    if (params.line_code) q.set('line_code', params.line_code);
    if (params.test_type) q.set('test_type', params.test_type);
    if (params.test_date) {
      q.set('start_date', params.test_date);
      q.set('end_date', params.test_date);
    }
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.shift) q.set('shift', params.shift.toString());
    if (params.status) q.set('status', params.status);
    if (params.limit) q.set('limit', params.limit.toString());
    return request(`/sand-tests?${q.toString()}`);
  },

  async createSandTest(data: {
    line_code: string;
    test_type: string;
    test_date: string;
    shift: number;
    test_hour: number;
    batch_number?: string;
    notes?: string;
    values: Array<{ parameter_id: number; measured_value: number }>;
  }): Promise<SandTestRecord> {
    return request('/sand-tests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getCorrectionRequests(status: string = 'ALL'): Promise<CorrectionRequest[]> {
    return request(`/sand-tests/corrections?status=${encodeURIComponent(status)}`);
  },

  async requestCorrection(data: {
    value_id: number;
    requested_value: number;
    reason: string;
  }): Promise<{ message: string; request_id: number }> {
    return request('/sand-tests/corrections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async approveCorrection(requestId: number, reviewNotes?: string): Promise<{ message: string }> {
    return request(`/sand-tests/corrections/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },

  async rejectCorrection(requestId: number, reviewNotes?: string): Promise<{ message: string }> {
    return request(`/sand-tests/corrections/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },

  // Sand Batches
  async getSandBatches(lineCode?: string): Promise<SandBatch[]> {
    const q = new URLSearchParams();
    if (lineCode) q.set('line_code', lineCode);
    return request(`/sand-batches?${q.toString()}`);
  },

  async createSandBatch(data: {
    line_code: string;
    muller_id: string;
    batch_weight_kg: number;
    bentonite_addition_kg: number;
    coal_dust_addition_kg: number;
    new_sand_addition_kg: number;
    return_sand_kg: number;
    water_addition_liters: number;
    cycle_time_seconds: number;
    notes?: string;
  }): Promise<SandBatch> {
    return request('/sand-batches', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // SPC
  async getIMRChart(
    lineCode: string,
    parameterCode: string,
    startDate?: string,
    endDate?: string,
    shift?: number
  ): Promise<IMRChartData> {
    const q = new URLSearchParams({ line_code: lineCode, parameter_code: parameterCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    if (shift) q.set('shift', shift.toString());
    return request(`/spc/imr?${q.toString()}`);
  },

  async getXBarRChart(
    lineCode: string,
    parameterCode: string,
    startDate?: string,
    endDate?: string,
    subgroupBy: 'shift' | 'date' = 'shift'
  ): Promise<XBarRChartData> {
    const q = new URLSearchParams({
      line_code: lineCode,
      parameter_code: parameterCode,
      subgroup_by: subgroupBy,
    });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/spc/xbar-r?${q.toString()}`);
  },

  async getPChart(lineCode: string = 'ALL'): Promise<any> {
    return request(`/spc/p-chart?line_code=${encodeURIComponent(lineCode)}`);
  },

  async getProcessCapability(
    lineCode: string,
    parameterCode: string,
    startDate?: string,
    endDate?: string
  ): Promise<ProcessCapabilityData> {
    const q = new URLSearchParams({ line_code: lineCode, parameter_code: parameterCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/spc/capability?${q.toString()}`);
  },

  // Rejections
  async getRejections(
    params: {
      line_code?: string;
      product_id?: number;
      defect_category_id?: number;
      start_date?: string;
      end_date?: string;
      shift?: number;
    } = {}
  ): Promise<RejectionRecord[]> {
    const q = new URLSearchParams();
    if (params.line_code) q.set('line_code', params.line_code);
    if (params.product_id) q.set('product_id', params.product_id.toString());
    if (params.defect_category_id) q.set('defect_category_id', params.defect_category_id.toString());
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.shift) q.set('shift', params.shift.toString());
    return request(`/rejections?${q.toString()}`);
  },

  async createRejection(data: any): Promise<RejectionRecord> {
    return request('/rejections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getDefects(): Promise<DefectCategory[]> {
    return request('/rejections/defects');
  },

  async getProducts(): Promise<CastingProduct[]> {
    return request('/rejections/products');
  },

  async getPareto(lineCode: string = 'ALL', startDate?: string, endDate?: string): Promise<ParetoResponse> {
    const q = new URLSearchParams({ line_code: lineCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/rejections/pareto?${q.toString()}`);
  },

  // Analytics
  async getDashboardSummary(
    lineCode?: string
  ): Promise<{ metrics: DashboardMetrics; lines: LineCardInfo[]; rejection_trends: any[] }> {
    const q = lineCode && lineCode !== 'ALL' ? `?line_code=${encodeURIComponent(lineCode)}` : '';
    return request(`/analytics/dashboard${q}`);
  },

  // Correlations
  async getCorrelationPair(
    lineCode: string,
    parameterCode: string,
    defectCode: string,
    lagHours: number = 12
  ): Promise<CorrelationAnalysis> {
    const q = new URLSearchParams({
      line_code: lineCode,
      parameter_code: parameterCode,
      defect_code: defectCode,
      lag_hours: lagHours.toString(),
    });
    return request(`/correlations/pair?${q.toString()}`);
  },

  async getCandidateRootCauses(lineCode: string = 'D2', lagHours: number = 12): Promise<any> {
    return request(
      `/correlations/candidate-root-causes?line_code=${encodeURIComponent(lineCode)}&lag_hours=${lagHours}`
    );
  },

  // Root Cause Investigations
  async getInvestigations(lineCode?: string): Promise<RootCauseInvestigation[]> {
    const q = lineCode && lineCode !== 'ALL' ? `?line_code=${encodeURIComponent(lineCode)}` : '';
    return request(`/investigations${q}`);
  },

  async createInvestigation(data: {
    title: string;
    line_code: string;
    lag_hours?: number;
    five_why_analysis: string[];
    fishbone_factors: Record<string, string>;
    findings?: string;
    conclusion?: string;
  }): Promise<RootCauseInvestigation> {
    return request('/investigations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateInvestigation(
    id: number,
    data: {
      title?: string;
      five_why_analysis?: string[];
      fishbone_factors?: Record<string, string>;
      findings?: string;
      conclusion?: string;
      status?: 'IN_PROGRESS' | 'VALIDATED' | 'CLOSED';
      expected_version?: number;
    }
  ): Promise<RootCauseInvestigation> {
    return request(`/investigations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Customer Complaints
  async getComplaints(status?: string, customerName?: string, lineCode?: string): Promise<CustomerComplaint[]> {
    const q = new URLSearchParams();
    if (status) q.set('status', status);
    if (customerName) q.set('customer_name', customerName);
    if (lineCode) q.set('line_code', lineCode);
    return request(`/complaints?${q.toString()}`);
  },

  async createComplaint(data: {
    customer_name: string;
    received_date: string;
    product_id: number;
    defect_category_id: number;
    batch_number?: string;
    line_code: string;
    affected_qty: number;
    severity: string;
    description: string;
  }): Promise<CustomerComplaint> {
    return request('/complaints', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateComplaint8D(id: number, data: any): Promise<CustomerComplaint> {
    return request(`/complaints/${id}/8d`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Quality Alerts
  async getAlerts(lineCode?: string, status?: string, severity?: string): Promise<QualityAlert[]> {
    const q = new URLSearchParams();
    if (lineCode) q.set('line_code', lineCode);
    if (status) q.set('status', status);
    if (severity) q.set('severity', severity);
    return request(`/alerts?${q.toString()}`);
  },

  async acknowledgeAlert(alertId: number, notes?: string, expectedVersion?: number): Promise<any> {
    return request(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ notes, expected_version: expectedVersion }),
    });
  },

  async resolveAlert(alertId: number, notes: string, expectedVersion?: number): Promise<any> {
    return request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ notes, expected_version: expectedVersion }),
    });
  },

  // Audit Logs
  async getAuditLogs(
    entityType?: string,
    action?: string,
    startDate?: string,
    endDate?: string
  ): Promise<AuditLog[]> {
    const q = new URLSearchParams();
    if (entityType) q.set('entity_type', entityType);
    if (action) q.set('action', action);
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/audit-logs?${q.toString()}`);
  },

  async verifyAuditChain(): Promise<AuditVerificationResult> {
    return request('/audit-logs/verify');
  },

  // Secure Authenticated Report Download (never passes JWT in URL query string)
  async downloadReport(
    reportType: string,
    format: 'pdf' | 'excel' | 'csv',
    lineCode: string = 'ALL',
    startDate?: string,
    endDate?: string
  ): Promise<void> {
    const q = new URLSearchParams({
      report_type: reportType,
      format,
      line_code: lineCode,
    });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);

    const response = await fetch(`${API_BASE}/reports/export?${q.toString()}`, {
      method: 'GET',
      headers: {
        ...getAuthHeader(),
      },
    });

    if (!response.ok) {
      let msg = `Export failed (HTTP ${response.status})`;
      try {
        const err = await response.json();
        if (err?.detail) msg = err.detail;
      } catch {
        // ignore
      }
      throw new Error(msg);
    }

    const blob = await response.blob();
    const ext = format === 'excel' ? 'xlsx' : format;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${reportType}_${lineCode}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  // System
  async seedData(force: boolean = false): Promise<any> {
    return request('/system/seed', {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
  },
};
