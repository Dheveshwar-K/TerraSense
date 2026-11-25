import React, { useCallback, useEffect, useState } from 'react';
import { PieChart as PieChartIcon, RefreshCw } from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../../services/api';
import { ParetoResponse } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const DefectParetoPage: React.FC = () => {
  const { selectedLine } = useAuth();
  const { showToast } = useToast();
  const [lineCode, setLineCode] = useState<string>(selectedLine);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [paretoData, setParetoData] = useState<ParetoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadPareto = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getPareto(lineCode, startDate || undefined, endDate || undefined);
      setParetoData(data);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load Pareto chart', 'error');
    } finally {
      setLoading(false);
    }
  }, [endDate, lineCode, showToast, startDate]);

  useEffect(() => {
    setLineCode(selectedLine);
  }, [selectedLine]);

  useEffect(() => {
    loadPareto();
  }, [loadPareto]);

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <PieChartIcon className="w-5 h-5 text-blue-600" />
            DEFECT PARETO ANALYSIS (80/20 RULE)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Prioritizes the &ldquo;vital few&rdquo; casting defects causing 80% of scrap volume over the &ldquo;trivial many&rdquo;.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
            {['ALL', 'D1', 'D2', 'D3', 'D4'].map(code => (
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

          <input
            type="date"
            aria-label="Pareto start date"
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />
          <input
            type="date"
            aria-label="Pareto end date"
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />

          <button
            type="button"
            onClick={() => loadPareto()}
            aria-label="Refresh Pareto"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Defect Volume Frequency &amp; Cumulative Percentage ({lineCode})
            </h2>
            <p className="text-xs text-slate-400">
              Bars indicate scrap piece count (left axis); curve indicates cumulative % (right axis). 80% threshold line highlighted.
            </p>
          </div>
          <div className="text-xs font-semibold text-slate-600 tabular-nums">
            Total Scrap Analyzed: <b>{paretoData?.total_rejected.toLocaleString() || 0} pieces</b>
          </div>
        </div>

        <div className="h-80">
          {!paretoData?.items || paretoData.items.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No rejection records found for Pareto calculation.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={paretoData.items} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="defect_name" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} />
                <YAxis yAxisId="left" tick={{ fontSize: 10 }} label={{ value: 'Scrap Quantity', angle: -90, position: 'insideLeft', fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" label={{ value: 'Cumulative %', angle: 90, position: 'insideRight', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                  formatter={(val: any, name?: any) => [
                    name === 'Cumulative %' ? `${val}%` : `${val} pcs`,
                    name ?? '',
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <ReferenceLine yAxisId="right" y={80} stroke="#e11d48" strokeDasharray="4 4" label={{ value: '80% Cutoff', fill: '#e11d48', fontSize: 10 }} />
                <Bar yAxisId="left" dataKey="rejected_qty" fill="#3b82f6" name="Rejected Quantity" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="cumulative_percentage" stroke="#e11d48" strokeWidth={2.5} dot={{ r: 4 }} name="Cumulative %" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Defect Contribution Breakdown</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">Rank</th>
                <th className="px-4 py-3 font-bold">Defect Name</th>
                <th className="px-4 py-3 font-bold">Defect Code</th>
                <th className="px-4 py-3 font-bold text-right">Rejected Quantity</th>
                <th className="px-4 py-3 font-bold text-right">Individual %</th>
                <th className="px-4 py-3 font-bold text-right">Cumulative %</th>
                <th className="px-4 py-3 font-bold">Category Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paretoData?.items.map((item, idx) => {
                const isVitalFew = item.cumulative_percentage <= 80 || idx === 0;
                return (
                  <tr key={item.defect_id} className={`hover:bg-slate-50/60 ${isVitalFew ? 'bg-amber-50/30' : ''}`}>
                    <td className="px-4 py-2.5 font-bold font-mono text-slate-700">#{idx + 1}</td>
                    <td className="px-4 py-2.5 font-bold text-slate-800">{item.defect_name}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-500">{item.defect_code}</td>
                    <td className="px-4 py-2.5 text-right font-black text-rose-600 tabular-nums">{item.rejected_qty.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right font-semibold text-slate-700 tabular-nums">{item.percentage}%</td>
                    <td className="px-4 py-2.5 text-right font-black text-slate-900 tabular-nums">{item.cumulative_percentage}%</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isVitalFew ? 'bg-rose-100 text-rose-800 border border-rose-200' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {isVitalFew ? 'Vital Few (Top 80%)' : 'Secondary'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
