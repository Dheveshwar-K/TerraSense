import {
  User, ProductionLine, Parameter, SandTestRecord,
  IMRChartData, ProcessCapabilityData, RejectionRecord,
  DefectCategory, CastingProduct, ParetoResponse,
  CorrelationAnalysis, CustomerComplaint, QualityAlert,
  AuditLog, DashboardMetrics, LineCardInfo, SpecificationRevision
} from '../types';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('ps010_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(username: string, password: string): Promise<{ access_token: string; user: User }> {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  },

  async getMe(): Promise<User> {
    return request('/auth/me');
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

  async updateSpecification(paramId: number, data: { target_value?: number; lsl?: number; usl?: number; revision_reason?: string }): Promise<Parameter> {
    return request(`/parameters/${paramId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async getParameterRevisions(paramId: number): Promise<SpecificationRevision[]> {
    return request(`/parameters/${paramId}/revisions`);
  },

  // Sand Tests
  async getSandTests(params: { line_code?: string; test_type?: string; test_date?: string; start_date?: string; end_date?: string; shift?: number; status?: string; limit?: number } = {}): Promise<SandTestRecord[]> {
    const q = new URLSearchParams();
    if (params.line_code) q.set('line_code', params.line_code);
    if (params.test_type) q.set('test_type', params.test_type);
    if (params.test_date) q.set('start_date', params.test_date);
    if (params.test_date) q.set('end_date', params.test_date);
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
      body: JSON.stringify(data)
    });
  },

  async requestCorrection(data: { value_id: number; requested_value: number; reason: string }): Promise<{ message: string; request_id: number }> {
    return request('/sand-tests/corrections', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async approveCorrection(requestId: number): Promise<{ message: string }> {
    return request(`/sand-tests/corrections/${requestId}/approve`, {
      method: 'POST'
    });
  },

  // SPC
  async getIMRChart(lineCode: string, parameterCode: string, startDate?: string, endDate?: string, shift?: number): Promise<IMRChartData> {
    const q = new URLSearchParams({ line_code: lineCode, parameter_code: parameterCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    if (shift) q.set('shift', shift.toString());
    return request(`/spc/imr?${q.toString()}`);
  },

  async getXBarRChart(lineCode: string, parameterCode: string, startDate?: string, endDate?: string): Promise<any> {
    const q = new URLSearchParams({ line_code: lineCode, parameter_code: parameterCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/spc/xbar-r?${q.toString()}`);
  },

  async getPChart(lineCode: string = 'ALL'): Promise<any> {
    return request(`/spc/p-chart?line_code=${lineCode}`);
  },

  async getProcessCapability(lineCode: string, parameterCode: string, startDate?: string, endDate?: string): Promise<ProcessCapabilityData> {
    const q = new URLSearchParams({ line_code: lineCode, parameter_code: parameterCode });
    if (startDate) q.set('start_date', startDate);
    if (endDate) q.set('end_date', endDate);
    return request(`/spc/capability?${q.toString()}`);
  },

  // Rejections
  async getRejections(params: { line_code?: string; product_id?: number; defect_category_id?: number; start_date?: string; end_date?: string; shift?: number } = {}): Promise<RejectionRecord[]> {
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
      body: JSON.stringify(data)
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
  async getDashboardSummary(): Promise<{ metrics: DashboardMetrics; lines: LineCardInfo[]; rejection_trends: any[] }> {
    return request('/analytics/dashboard');
  },

  // Correlations
  async getCorrelationPair(lineCode: string, parameterCode: string, defectCode: string, lagHours: number = 12): Promise<CorrelationAnalysis> {
    const q = new URLSearchParams({
      line_code: lineCode,
      parameter_code: parameterCode,
      defect_code: defectCode,
      lag_hours: lagHours.toString()
    });
    return request(`/correlations/pair?${q.toString()}`);
  },

  async getCandidateRootCauses(lineCode: string = 'D2', lagHours: number = 12): Promise<any> {
    return request(`/correlations/candidate-root-causes?line_code=${lineCode}&lag_hours=${lagHours}`);
  },

  // Customer Complaints
  async getComplaints(status?: string, customerName?: string, lineCode?: string): Promise<CustomerComplaint[]> {
    const q = new URLSearchParams();
    if (status) q.set('status', status);
    if (customerName) q.set('customer_name', customerName);
    if (lineCode) q.set('line_code', lineCode);
    return request(`/complaints?${q.toString()}`);
  },

  async createComplaint(data: any): Promise<CustomerComplaint> {
    return request('/complaints', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async updateComplaint8D(id: number, data: any): Promise<CustomerComplaint> {
    return request(`/complaints/${id}/8d`, {
      method: 'PUT',
      body: JSON.stringify(data)
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

  async acknowledgeAlert(alertId: number, notes?: string): Promise<any> {
    return request(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  },

  async resolveAlert(alertId: number, notes: string): Promise<any> {
    return request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  },

  // Audit Logs
  async getAuditLogs(entityType?: string, action?: string): Promise<AuditLog[]> {
    const q = new URLSearchParams();
    if (entityType) q.set('entity_type', entityType);
    if (action) q.set('action', action);
    return request(`/audit-logs?${q.toString()}`);
  },

  // Report Export
  getExportUrl(reportType: string, format: string, lineCode: string = 'ALL'): string {
    const token = localStorage.getItem('ps010_token');
    return `/api/reports/export?report_type=${reportType}&format=${format}&line_code=${lineCode}&token=${token || ''}`;
  },

  // System
  async seedData(force: boolean = false): Promise<any> {
    return request('/system/seed', {
      method: 'POST',
      body: JSON.stringify({ force })
    });
  }
};
