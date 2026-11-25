import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  LineChart as LineChartIcon,
  RefreshCw,
} from 'lucide-react';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../../services/api';
import { IMRChartData, Parameter, XBarRChartData } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

export const SPCAnalyticsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedLine } = useAuth();
  const { showToast } = useToast();

  const [lineCode, setLineCode] = useState<string>(
    searchParams.get('line') || (selectedLine !== 'ALL' ? selectedLine : 'D1')
  );
  const [parameterCode, setParameterCode] = useState<string>('MOISTURE');
  const [chartMode, setChartMode] = useState<'IMR' | 'XBAR_R'>('IMR');
  const [subgroupBy, setSubgroupBy] = useState<'shift' | 'date'>('shift');
  const [parameters, setParameters] = useState<Parameter[]>([]);
  const [chartData, setChartData] = useState<IMRChartData | null>(null);
  const [xbarData, setXbarData] = useState<XBarRChartData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadParams = async () => {
      try {
        const data = await api.getParameters('PHYSICAL');
        setParameters(data);
        if (data.length > 0 && !data.some(p => p.code === parameterCode)) {
          setParameterCode(data[0].code);
        }
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : 'Failed to load parameters', 'error');
      }
    };
    loadParams();
  }, [parameterCode, showToast]);

  const loadChart = useCallback(async () => {
    if (!parameterCode) return;
    setLoading(true);
    try {
      if (chartMode === 'IMR') {
        const data = await api.getIMRChart(lineCode, parameterCode);
        setChartData(data);
      } else {
        const data = await api.getXBarRChart(lineCode, parameterCode, undefined, undefined, subgroupBy);
        setXbarData(data);
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load SPC chart data', 'error');
    } finally {
      setLoading(false);
    }
  }, [chartMode, lineCode, parameterCode, subgroupBy, showToast]);

  useEffect(() => {
    loadChart();
  }, [loadChart]);

  const violationPoints = chartData?.points?.filter(p => p.is_out_of_control || p.violations.length > 0) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <LineChartIcon className="w-5 h-5 text-blue-600" />
            AUTOMATED STATISTICAL PROCESS CONTROL (SPC) ENGINE
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Individuals &amp; Moving Range (I-MR) and Subgrouped X-bar &amp; R control charts with Nelson 8-Rule detection.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
            <button
              type="button"
              onClick={() => setChartMode('IMR')}
              className={`px-3 py-1 text-xs font-bold rounded transition-colors ${
                chartMode === 'IMR' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              I-MR
            </button>
            <button
              type="button"
              onClick={() => setChartMode('XBAR_R')}
              className={`px-3 py-1 text-xs font-bold rounded transition-colors ${
                chartMode === 'XBAR_R' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              X-bar &amp; R
            </button>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
            {['D1', 'D2', 'D3', 'D4'].map(code => (
              <button
                key={code}
                type="button"
                onClick={() => setLineCode(code)}
                className={`px-2.5 py-1 text-xs font-bold rounded transition-colors ${
                  lineCode === code ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {code}
              </button>
            ))}
          </div>

          <select
            aria-label="Select sand parameter"
            value={parameterCode}
            onChange={e => setParameterCode(e.target.value)}
            className="text-xs font-bold bg-white border border-slate-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500"
          >
            {parameters.map(p => (
              <option key={p.code} value={p.code}>
                {p.name} ({p.unit})
              </option>
            ))}
          </select>

          {chartMode === 'XBAR_R' && (
            <select
              aria-label="Subgroup grouping"
              value={subgroupBy}
              onChange={e => setSubgroupBy(e.target.value as 'shift' | 'date')}
              className="text-xs font-bold bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
            >
              <option value="shift">By Shift</option>
              <option value="date">By Date</option>
            </select>
          )}

          <button
            type="button"
            onClick={() => loadChart()}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
            title="Refresh SPC"
            aria-label="Refresh SPC"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {chartMode === 'IMR' && (
        <>
          {chartData?.warnings && chartData.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 space-y-1">
              {chartData.warnings.map((w, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {chartData && chartData.points && chartData.points.length >= 2 ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Center Line (X&#772;)</div>
                  <div className="text-lg font-black text-slate-800 tabular-nums">
                    {chartData.mean} <span className="text-xs font-normal text-slate-500">{chartData.unit}</span>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Upper Control Limit (UCL)</div>
                  <div className="text-lg font-black text-rose-700 tabular-nums">{chartData.i_chart?.ucl}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Lower Control Limit (LCL)</div>
                  <div className="text-lg font-black text-rose-700 tabular-nums">{chartData.i_chart?.lcl}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Sigma Within (&sigma;&#770;w = MR&#772;/d2)</div>
                  <div className="text-lg font-black text-blue-700 tabular-nums">{chartData.sigma_within}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Statistical Stability</div>
                  <div className="mt-0.5">
                    <StatusBadge status={chartData.is_stable ? 'STABLE' : 'UNSTABLE'} size="sm" />
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Nelson Violations</div>
                  <div className={`text-lg font-black tabular-nums ${chartData.violations_count > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {chartData.violations_count} points
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                      Individuals (I) Chart — {chartData.parameter_name} ({lineCode})
                    </h2>
                    <p className="text-xs text-slate-400">
                      UCL/LCL calculated from moving range (d2 = 1.1284). Nelson rule violations flagged in red.
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-medium">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <span className="w-3 h-0.5 bg-blue-600"></span> Value
                    </span>
                    <span className="flex items-center gap-1.5 text-rose-600">
                      <span className="w-3 h-0.5 bg-rose-500"></span> UCL/LCL
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-800">
                      <span className="w-3 h-0.5 bg-slate-900"></span> USL/LSL
                    </span>
                  </div>
                </div>

                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData.points} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                      <YAxis
                        tick={{ fontSize: 10 }}
                        domain={[
                          (dataMin: number) => Math.min(dataMin, chartData.i_chart.lcl, chartData.lsl ?? dataMin) - 0.1,
                          (dataMax: number) => Math.max(dataMax, chartData.i_chart.ucl, chartData.usl ?? dataMax) + 0.1,
                        ]}
                      />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const p = payload[0].payload;
                            return (
                              <div className="bg-slate-900 text-white p-3 rounded-lg text-xs shadow-xl border border-slate-800 space-y-1">
                                <div className="font-bold text-blue-400">
                                  Point #{p.index} ({p.timestamp})
                                </div>
                                <div>
                                  Value: <b>{p.value} {chartData.unit}</b>
                                </div>
                                <div>
                                  Mean (CL): {p.cl} | UCL: {p.ucl} | LCL: {p.lcl}
                                </div>
                                {p.usl !== undefined && p.lsl !== undefined && (
                                  <div>
                                    Spec: {p.lsl} to {p.usl}
                                  </div>
                                )}
                                {p.violations && p.violations.length > 0 && (
                                  <div className="text-rose-400 font-bold border-t border-slate-800 pt-1 mt-1">
                                    Violations: {p.violations.join(', ')}
                                  </div>
                                )}
                              </div>
                            );
                          }
                          return null;
                        }}
                      />

                      <ReferenceLine y={chartData.i_chart.ucl} stroke="#e11d48" strokeDasharray="4 4" label={{ value: `UCL ${chartData.i_chart.ucl}`, fill: '#e11d48', fontSize: 10 }} />
                      <ReferenceLine y={chartData.i_chart.cl} stroke="#059669" label={{ value: `CL ${chartData.i_chart.cl}`, fill: '#059669', fontSize: 10 }} />
                      <ReferenceLine y={chartData.i_chart.lcl} stroke="#e11d48" strokeDasharray="4 4" label={{ value: `LCL ${chartData.i_chart.lcl}`, fill: '#e11d48', fontSize: 10 }} />

                      {chartData.usl !== undefined && (
                        <ReferenceLine y={chartData.usl} stroke="#0f172a" strokeWidth={1.5} strokeDasharray="2 2" label={{ value: `USL ${chartData.usl}`, fill: '#0f172a', fontSize: 10 }} />
                      )}
                      {chartData.lsl !== undefined && (
                        <ReferenceLine y={chartData.lsl} stroke="#0f172a" strokeWidth={1.5} strokeDasharray="2 2" label={{ value: `LSL ${chartData.lsl}`, fill: '#0f172a', fontSize: 10 }} />
                      )}

                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#2563eb"
                        strokeWidth={2}
                        dot={(props: any) => {
                          const { cx, cy, payload } = props;
                          if (payload.is_out_of_control) {
                            return <circle key={`dot-${payload.index}`} cx={cx} cy={cy} r={5} fill="#e11d48" stroke="#ffffff" strokeWidth={2} />;
                          }
                          return <circle key={`dot-${payload.index}`} cx={cx} cy={cy} r={3} fill="#2563eb" />;
                        }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                      Moving Range (MR) Chart — Short-Term Process Variation
                    </h2>
                    <p className="text-xs text-slate-400">MR = |Xi - Xi-1| (n=2). UCL = 3.267 &times; MR&#772;. LCL = 0.</p>
                  </div>
                  <div className="text-xs text-slate-600 font-semibold tabular-nums">
                    Average Moving Range (MR&#772;): <b>{chartData.mean_mr}</b>
                  </div>
                </div>

                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData.points.slice(1)} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} domain={[0, 'auto']} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const p = payload[0].payload;
                            return (
                              <div className="bg-slate-900 text-white p-2.5 rounded-lg text-xs">
                                <div>Moving Range: <b>{p.mr}</b></div>
                                <div>MR UCL: {chartData.mr_chart.ucl}</div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <ReferenceLine y={chartData.mr_chart.ucl} stroke="#e11d48" strokeDasharray="4 4" label={{ value: `MR UCL ${chartData.mr_chart.ucl}`, fill: '#e11d48', fontSize: 10 }} />
                      <ReferenceLine y={chartData.mr_chart.cl} stroke="#059669" label={{ value: `MR̄ ${chartData.mr_chart.cl}`, fill: '#059669', fontSize: 10 }} />
                      <Line type="monotone" dataKey="mr" stroke="#64748b" strokeWidth={1.5} dot={{ r: 2 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
                <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    Detected Statistical Rule Violations ({violationPoints.length})
                  </h3>
                  <span className="text-[11px] text-slate-500">Nelson 8-Rule Standard</span>
                </div>

                {violationPoints.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Zero statistical rule violations detected. Process is in statistical control.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
                        <tr>
                          <th className="px-4 py-2.5 font-bold">Point #</th>
                          <th className="px-4 py-2.5 font-bold">Timestamp</th>
                          <th className="px-4 py-2.5 font-bold">Measured Value</th>
                          <th className="px-4 py-2.5 font-bold">Tolerance Deviation</th>
                          <th className="px-4 py-2.5 font-bold">Triggered Nelson Rule</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {violationPoints.map((p, idx) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="px-4 py-2 font-mono font-bold text-slate-800">#{p.index}</td>
                            <td className="px-4 py-2 text-slate-600">{p.timestamp}</td>
                            <td className="px-4 py-2 font-black text-rose-700 tabular-nums">
                              {p.value} {chartData.unit}
                            </td>
                            <td className="px-4 py-2">
                              <StatusBadge status={p.spec_status} size="sm" />
                            </td>
                            <td className="px-4 py-2 font-semibold text-rose-700">
                              {p.violations.join(', ') || 'Statistical excursion'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-xs text-slate-500">
              {chartData?.message || chartData?.error || 'Insufficient observations for I-MR chart calculation.'}
            </div>
          )}
        </>
      )}

      {chartMode === 'XBAR_R' && (
        <div className="space-y-6">
          {xbarData?.warnings && xbarData.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 space-y-1">
              {xbarData.warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
            </div>
          )}

          {xbarData?.points && xbarData.points.length >= 2 ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Subgroups</div>
                  <div className="text-lg font-black text-slate-800 tabular-nums">{xbarData.subgroups_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Grand Mean (X&#772;&#772;)</div>
                  <div className="text-lg font-black text-slate-800 tabular-nums">
                    {xbarData.grand_mean} {xbarData.unit}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Mean Range (R&#772;)</div>
                  <div className="text-lg font-black text-blue-700 tabular-nums">{xbarData.mean_range}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Sigma Within</div>
                  <div className="text-lg font-black text-slate-800 tabular-nums">{xbarData.sigma_within}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Subgroup Mode</div>
                  <div className="text-xs font-bold text-slate-700 mt-1">
                    {xbarData.variable_subgroup_sizes ? 'Variable n (Exact Limits)' : `Fixed n=${xbarData.subgroup_size}`}
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  X-bar Chart (Subgroup Means) — {xbarData.parameter_name} ({lineCode})
                </h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={xbarData.points} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                      <Tooltip />
                      <Line type="monotone" dataKey="ucl_x" stroke="#e11d48" strokeDasharray="4 4" dot={false} name="UCL X-bar" />
                      <Line type="monotone" dataKey="lcl_x" stroke="#e11d48" strokeDasharray="4 4" dot={false} name="LCL X-bar" />
                      <Line type="monotone" dataKey="cl_x" stroke="#059669" dot={false} name="Grand Mean" />
                      <Line type="monotone" dataKey="x_bar" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} name="Subgroup Mean" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  R Chart (Subgroup Ranges)
                </h2>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={xbarData.points} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} domain={[0, 'auto']} />
                      <Tooltip />
                      <Line type="monotone" dataKey="ucl_r" stroke="#e11d48" strokeDasharray="4 4" dot={false} name="UCL R" />
                      <Line type="monotone" dataKey="cl_r" stroke="#059669" dot={false} name="R-bar" />
                      <Line type="monotone" dataKey="range" stroke="#475569" strokeWidth={2} dot={{ r: 3 }} name="Range" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-xs text-slate-500">
              {xbarData?.error || 'Insufficient subgroup data (at least 2 subgroups with 2–15 samples each required).'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
