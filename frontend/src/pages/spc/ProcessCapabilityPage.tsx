import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  Info,
  HelpCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { api } from '../../services/api';
import { ProcessCapabilityData, Parameter } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { StatusBadge } from '../../components/StatusBadge';

export const ProcessCapabilityPage: React.FC = () => {
  const { selectedLine } = useAuth();
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
      } catch (err) {
        console.error('Failed to load parameters', err);
      }
    };
    loadParams();
  }, []);

  const loadCapability = async () => {
    if (!parameterCode) return;
    setLoading(true);
    try {
      const data = await api.getProcessCapability(lineCode, parameterCode);
      setCapability(data);
    } catch (err) {
      console.error('Failed to load capability', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCapability();
  }, [lineCode, parameterCode]);

  // Generate normal bell curve points for visualization
  const generateNormalCurve = () => {
    if (!capability || !capability.mean || !capability.sigma_overall) return [];
    const mean = capability.mean;
    const sigma = capability.sigma_overall;
    const lsl = capability.lsl ?? mean - 3 * sigma;
    const usl = capability.usl ?? mean + 3 * sigma;

    const minX = Math.min(mean - 4 * sigma, lsl - 0.5 * sigma);
    const maxX = Math.max(mean + 4 * sigma, usl + 0.5 * sigma);
    const step = (maxX - minX) / 60;

    const pts = [];
    for (let x = minX; x <= maxX; x += step) {
      const z = (x - mean) / sigma;
      const pdf = (1 / (sigma * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * z * z);
      pts.push({
        x: Number(x.toFixed(3)),
        density: Number(pdf.toFixed(4)),
        isBelowLsl: capability.lsl !== undefined && x < capability.lsl,
        isAboveUsl: capability.usl !== undefined && x > capability.usl,
      });
    }
    return pts;
  };

  const curveData = generateNormalCurve();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            PROCESS CAPABILITY ANALYSIS (Cp, Cpk, Pp, Ppk)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Statistical capability indices comparing inherent within-subgroup variation (σ̂w) and overall sample deviation (s) against tolerance limits.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200">
            {['D1', 'D2', 'D3', 'D4'].map(code => (
              <button
                key={code}
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
            onClick={() => loadCapability()}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
            title="Refresh Capability"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Warnings & Assumptions Alert Box */}
      {capability?.warnings && capability.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs space-y-1 text-amber-900">
          <div className="font-bold flex items-center gap-1.5 text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            SPC Capability Statistical Assumptions Warning
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-800 pl-2">
            {capability.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Capability Indices Cards */}
      {capability && capability.can_calculate && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {/* Cpk Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase flex items-center justify-between">
              <span>Cpk (Within)</span>
              <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${
                (capability.cpk || 0) >= 1.33 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
              }`}>
                {capability.assessment}
              </span>
            </div>
            <div className="text-3xl font-black text-blue-700 mt-1">{capability.cpk ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">Min(Cpu, Cpl) using σ̂w</div>
          </div>

          {/* Cp Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Cp (Potential)</div>
            <div className="text-3xl font-black text-slate-800 mt-1">{capability.cp ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">(USL - LSL) / 6σ̂w</div>
          </div>

          {/* Ppk Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Ppk (Overall)</div>
            <div className="text-3xl font-black text-indigo-700 mt-1">{capability.ppk ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">Uses overall sample std s</div>
          </div>

          {/* Pp Card */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Pp (Performance)</div>
            <div className="text-3xl font-black text-slate-800 mt-1">{capability.pp ?? 'N/A'}</div>
            <div className="text-[10px] text-slate-400 mt-1">(USL - LSL) / 6s</div>
          </div>

          {/* Sigmas */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Sigma Within (σ̂w)</div>
            <div className="text-2xl font-black text-slate-800 mt-1">{capability.sigma_within}</div>
            <div className="text-[10px] text-slate-400 mt-1">Short-term MR̄/d2</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-bold text-slate-500 uppercase">Total Expected PPM</div>
            <div className={`text-2xl font-black mt-1 ${capability.ppm_total && capability.ppm_total > 500 ? 'text-rose-600' : 'text-emerald-600'}`}>
              {capability.ppm_total?.toLocaleString() ?? 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Defects Per Million Parts</div>
          </div>
        </div>
      )}

      {/* Bell Curve Normal Distribution Visualization */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Normal Distribution & Process Centering vs. Specification Tolerances
            </h2>
            <p className="text-xs text-slate-400">
              Superimposed theoretical distribution curve showing process spread relative to engineering LSL ({capability?.lsl}) and USL ({capability?.usl}).
            </p>
          </div>
          <div className="text-xs font-semibold text-slate-600">
            Mean (μ): <b>{capability?.mean} {capability?.unit}</b> | Target: <b>{capability?.target}</b>
          </div>
        </div>

        <div className="h-72">
          {curveData.length > 0 && (
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

                {/* Specification & Target Markers */}
                {capability?.lsl !== undefined && (
                  <ReferenceLine x={capability.lsl} stroke="#e11d48" strokeWidth={2} label={{ value: `LSL ${capability.lsl}`, fill: '#e11d48', fontSize: 10 }} />
                )}
                {capability?.target !== undefined && (
                  <ReferenceLine x={capability.target} stroke="#059669" strokeWidth={2} strokeDasharray="3 3" label={{ value: `Target ${capability.target}`, fill: '#059669', fontSize: 10 }} />
                )}
                {capability?.usl !== undefined && (
                  <ReferenceLine x={capability.usl} stroke="#e11d48" strokeWidth={2} label={{ value: `USL ${capability.usl}`, fill: '#e11d48', fontSize: 10 }} />
                )}

                {/* Bell Curve Area */}
                <Area type="monotone" dataKey="density" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Capability Assessment Guide Table */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="p-2.5 rounded bg-emerald-50 border border-emerald-200">
            <span className="font-bold text-emerald-800">Cpk ≥ 1.67: Excellent</span>
            <p className="text-[10px] text-emerald-700 mt-0.5">Six Sigma quality. Extremely low risk of defects (PPM &lt; 1).</p>
          </div>
          <div className="p-2.5 rounded bg-blue-50 border border-blue-200">
            <span className="font-bold text-blue-800">1.33 ≤ Cpk &lt; 1.67: Adequate</span>
            <p className="text-[10px] text-blue-700 mt-0.5">Automotive IATF benchmark. Process is capable and centered.</p>
          </div>
          <div className="p-2.5 rounded bg-amber-50 border border-amber-200">
            <span className="font-bold text-amber-800">1.00 ≤ Cpk &lt; 1.33: Borderline</span>
            <p className="text-[10px] text-amber-700 mt-0.5">Marginal capability. Close monitoring and SPC alert tracking required.</p>
          </div>
          <div className="p-2.5 rounded bg-rose-50 border border-rose-200">
            <span className="font-bold text-rose-800">Cpk &lt; 1.00: Inadequate</span>
            <p className="text-[10px] text-rose-700 mt-0.5">High defect generation risk. Immediate process adjustment necessary.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
