import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, Info, RefreshCw } from 'lucide-react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../../services/api';
import { Parameter, ProcessCapabilityData } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

export const ProcessCapabilityPage: React.FC = () => {
  const { selectedLine } = useAuth();
  const { showToast } = useToast();
  const [lineCode, setLineCode] = useState<string>(selectedLine !== 'ALL' ? selectedLine : 'D1');
  const [parameterCode, setParameterCode] = useState<string>('MOISTURE');
  const [parameters, setParameters] = useState<Parameter[]>([]);
  const [capability, setCapability] = useState<ProcessCapabilityData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadParams = async () => {
      try {
        const data = await api.getParameters('PHYSICAL');
        setParameters(data);
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : 'Failed to load parameters', 'error');
      }
    };
    loadParams();
  }, [showToast]);

  const loadCapability = useCallback(async () => {
    if (!parameterCode) return;
    setLoading(true);
    try {
      const data = await api.getProcessCapability(lineCode, parameterCode);
      setCapability(data);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load process capability', 'error');
    } finally {
      setLoading(false);
    }
  }, [lineCode, parameterCode, showToast]);

  useEffect(() => {
    loadCapability();
  }, [loadCapability]);

  const generateNormalCurve = () => {
    if (!capability || capability.mean === undefined || !capability.sigma_overall || capability.sigma_overall <= 0) {
      return [];
    }
    const mean = capability.mean;
    const sigma = capability.sigma_overall;
    const lsl = capability.lsl ?? mean - 3 * sigma;
    const usl = capability.usl ?? mean + 3 * sigma;

    const minX = Math.min(mean - 4 * sigma, lsl - 0.5 * sigma);
    const maxX = Math.max(mean + 4 * sigma, usl + 0.5 * sigma);
    const step = (maxX - minX) / 60;
    if (step <= 0) return [];

    const pts = [];
    for (let x = minX; x <= maxX; x += step) {
      const z = (x - mean) / sigma;
      const pdf = (1 / (sigma * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * z * z);
      pts.push({
        x: Number(x.toFixed(3)),
        density: Number(pdf.toFixed(4)),
      });
    }
    return pts;
  };

  const curveData = generateNormalCurve();

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            PROCESS CAPABILITY ANALYSIS (Cp, Cpk, Pp, Ppk)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Stability-gated capability analysis comparing within-subgroup variation (&sigma;&#770;w) and overall sample deviation (s) against tolerances.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200">
            {['D1', 'D2', 'D3', 'D4'].map(code => (
              <button
                key={code}
                type="button"
                onClick={() => setLineCode(code)}
                className={`px-3 py-1 text-xs font-bold rounded transition-colors ${
                  lineCode === code
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Line {code}
              </button>
            ))}
          </div>

          <select
            aria-label="Select parameter"
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

          <button
            type="button"
            onClick={() => loadCapability()}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
            title="Refresh Capability"
            aria-label="Refresh Capability"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stability & Capability Gate Status */}
      {capability && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-500 uppercase text-[10px]">Process Stability:</span>
              <StatusBadge status={capability.stability_status || (capability.is_stable ? 'STABLE' : 'UNSTABLE')} size="sm" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-500 uppercase text-[10px]">Capability Validity:</span>
              <StatusBadge status={capability.capability_status || 'ASSESSABLE'} size="sm" />
            </div>
            {capability.normality_test_used && (
              <div className="text-slate-600 tabular-nums">
                Normality ({capability.normality_test_used}): <b>p = {capability.normality_p_value}</b>
              </div>
            )}
          </div>
          <div className="text-slate-500 tabular-nums">
            N = <b>{capability.sample_size ?? 0}</b> | Expected Yield: <b>{capability.yield_percentage ?? '--'}%</b>
          </div>
        </div>
      )}

      {/* Warnings & Assumptions Alert Box */}
      {capability?.warnings && capability.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs space-y-1 text-amber-900">
          <div className="font-bold flex items-center gap-1.5 text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Statistical Stability &amp; Distributional Assumptions Notice
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-800 pl-2">
            {capability.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {capability && !capability.can_calculate && (
        <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-xs text-slate-500">
          {capability.reason || 'Capability cannot be calculated for this selection.'}
        </div>
      )}

      {capability && capability.can_calculate && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase flex items-center justify-between">
              <span>Cpk {capability.is_stable ? '' : '(Exploratory)'}</span>
              <span
                className={`text-[10px] font-black px-1.5 py-0.5 rounded ${
                  capability.cpk !== null && capability.cpk !== undefined && capability.cpk >= 1.33
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-rose-100 text-rose-800'
                }`}
              >
                {capability.assessment}
              </span>
            </div>
            <div className="text-3xl font-black text-blue-700 mt-1 tabular-nums">{capability.cpk ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">Min(Cpu, Cpl) using &sigma;&#770;w</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Cp (Potential)</div>
            <div className="text-3xl font-black text-slate-800 mt-1 tabular-nums">{capability.cp ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">(USL - LSL) / 6&sigma;&#770;w</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Ppk (Overall)</div>
            <div className="text-3xl font-black text-indigo-700 mt-1 tabular-nums">{capability.ppk ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">Uses overall sample std s</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Pp (Performance)</div>
            <div className="text-3xl font-black text-slate-800 mt-1 tabular-nums">{capability.pp ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">(USL - LSL) / 6s</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Sigma Within (&sigma;&#770;w)</div>
            <div className="text-2xl font-black text-slate-800 mt-1 tabular-nums">{capability.sigma_within}</div>
            <div className="text-[10px] text-slate-400 mt-1">Short-term MR&#772;/d2</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Projected PPM</div>
            <div
              className={`text-2xl font-black mt-1 tabular-nums ${
                capability.ppm_total && capability.ppm_total > 500 ? 'text-rose-600' : 'text-emerald-600'
              }`}
            >
              {capability.ppm_total?.toLocaleString() ?? 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Normal-model defective PPM</div>
          </div>
        </div>
      )}

      {/* Bell Curve Visualization */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Normal Reference Curve &amp; Process Centering vs. Specification Tolerances
            </h2>
            <p className="text-xs text-slate-400">
              Theoretical Normal(&mu;, s) curve relative to LSL ({capability?.lsl}) and USL ({capability?.usl}).
            </p>
          </div>
          <div className="text-xs font-semibold text-slate-600 tabular-nums">
            Mean (&mu;): <b>{capability?.mean} {capability?.unit}</b> | Target: <b>{capability?.target}</b>
          </div>
        </div>

        <div className="h-72">
          {curveData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              Normal curve unavailable (insufficient variation or observations).
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={curveData} margin={{ top: 10, right: 30, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="x" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                  formatter={(val: any) => [val, 'Normal Density']}
                  labelFormatter={lbl => `Value: ${lbl} ${capability?.unit}`}
                />

                {capability?.lsl !== undefined && (
                  <ReferenceLine x={capability.lsl} stroke="#e11d48" strokeWidth={2} label={{ value: `LSL ${capability.lsl}`, fill: '#e11d48', fontSize: 10 }} />
                )}
                {capability?.target !== undefined && (
                  <ReferenceLine x={capability.target} stroke="#059669" strokeWidth={2} strokeDasharray="3 3" label={{ value: `Target ${capability.target}`, fill: '#059669', fontSize: 10 }} />
                )}
                {capability?.usl !== undefined && (
                  <ReferenceLine x={capability.usl} stroke="#e11d48" strokeWidth={2} label={{ value: `USL ${capability.usl}`, fill: '#e11d48', fontSize: 10 }} />
                )}

                <Area type="monotone" dataKey="density" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        {capability?.normality_note && (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-[11px] text-slate-600 flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <div>{capability.normality_note}</div>
              {capability.ppm_assumptions && <div className="text-slate-500 mt-0.5">{capability.ppm_assumptions}</div>}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="p-2.5 rounded bg-emerald-50 border border-emerald-200">
            <span className="font-bold text-emerald-800">Cpk &ge; 1.67: Excellent</span>
            <p className="text-[10px] text-emerald-700 mt-0.5">Six Sigma quality benchmark under stable normal process.</p>
          </div>
          <div className="p-2.5 rounded bg-blue-50 border border-blue-200">
            <span className="font-bold text-blue-800">1.33 &le; Cpk &lt; 1.67: Adequate</span>
            <p className="text-[10px] text-blue-700 mt-0.5">Automotive IATF 16949 benchmark. Process is capable and centered.</p>
          </div>
          <div className="p-2.5 rounded bg-amber-50 border border-amber-200">
            <span className="font-bold text-amber-800">1.00 &le; Cpk &lt; 1.33: Borderline</span>
            <p className="text-[10px] text-amber-700 mt-0.5">Marginal capability. Close monitoring and SPC tracking required.</p>
          </div>
          <div className="p-2.5 rounded bg-rose-50 border border-rose-200">
            <span className="font-bold text-rose-800">Cpk &lt; 1.00: Inadequate</span>
            <p className="text-[10px] text-rose-700 mt-0.5">High nonconformance risk. Process centering/variation action required.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
