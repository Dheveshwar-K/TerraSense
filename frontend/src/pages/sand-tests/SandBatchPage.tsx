import React, { useCallback, useEffect, useState } from 'react';
import { Layers, Plus, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { SandBatch } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const SandBatchPage: React.FC = () => {
  const { selectedLine } = useAuth();
  const { showToast } = useToast();
  const [lineCode, setLineCode] = useState<string>(selectedLine !== 'ALL' ? selectedLine : 'D1');
  const [batches, setBatches] = useState<SandBatch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [showModal, setShowModal] = useState<boolean>(false);
  const [mullerId, setMullerId] = useState<string>('Muller-A (Simpson 2G)');
  const [batchWeight, setBatchWeight] = useState<number>(2000);
  const [bentoniteKg, setBentoniteKg] = useState<number>(25.0);
  const [coalDustKg, setCoalDustKg] = useState<number>(12.0);
  const [waterLiters, setWaterLiters] = useState<number>(34.5);
  const [cycleSeconds, setCycleSeconds] = useState<number>(120);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const loadBatches = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getSandBatches(lineCode);
      setBatches(data);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load sand batches', 'error');
    } finally {
      setLoading(false);
    }
  }, [lineCode, showToast]);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await api.createSandBatch({
        line_code: lineCode,
        muller_id: mullerId,
        batch_weight_kg: batchWeight,
        bentonite_addition_kg: bentoniteKg,
        coal_dust_addition_kg: coalDustKg,
        new_sand_addition_kg: 100,
        return_sand_kg: Math.max(0, batchWeight - bentoniteKg - coalDustKg - 100),
        water_addition_liters: waterLiters,
        cycle_time_seconds: cycleSeconds,
      });
      showToast('Muller sand batch logged to database.', 'success');
      setShowModal(false);
      await loadBatches();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to log sand batch', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const avgWeight = batches.length > 0 ? (batches.reduce((s, b) => s + b.batch_weight_kg, 0) / batches.length).toFixed(0) : '0';
  const avgBent = batches.length > 0 ? (batches.reduce((s, b) => s + b.bentonite_addition_kg, 0) / batches.length).toFixed(1) : '0.0';
  const avgCoal = batches.length > 0 ? (batches.reduce((s, b) => s + b.coal_dust_addition_kg, 0) / batches.length).toFixed(1) : '0.0';
  const avgCycle = batches.length > 0 ? Math.round(batches.reduce((s, b) => s + b.cycle_time_seconds, 0) / batches.length) : 0;

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            SAND BATCH &amp; MULLER PREPARATION MANAGEMENT
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Database-backed muller batch tracking: Bentonite bonding additions, lustrous coal dust dosing, water temper additions, and mix durations.
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

          <button
            type="button"
            onClick={() => loadBatches()}
            aria-label="Refresh batches"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            type="button"
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Log Muller Batch
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase">Avg Batch Weight</div>
          <div className="text-2xl font-black text-slate-800 mt-1 tabular-nums">
            {Number(avgWeight).toLocaleString()} <span className="text-xs font-normal">kg</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">From {batches.length} logged batches</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase">Avg Bentonite Dosing</div>
          <div className="text-2xl font-black text-slate-800 mt-1 tabular-nums">
            {avgBent} <span className="text-xs font-normal">kg/batch</span>
          </div>
          <div className="text-[11px] text-emerald-600 font-semibold mt-0.5">Active Clay Target 7.2%</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase">Avg Coal Dust</div>
          <div className="text-2xl font-black text-slate-800 mt-1 tabular-nums">
            {avgCoal} <span className="text-xs font-normal">kg/batch</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Volatiles Target 2.4%</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase">Avg Mix Duration</div>
          <div className="text-2xl font-black text-slate-800 mt-1 tabular-nums">
            {avgCycle} <span className="text-xs font-normal">sec</span>
          </div>
          <div className="text-[11px] text-emerald-600 font-semibold mt-0.5">Optimal Shear Bond</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Recent Muller Mix Batches (Line {lineCode})
          </h2>
          <span className="text-xs text-slate-500">{batches.length} persisted records</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">Batch Number</th>
                <th className="px-4 py-3 font-bold">Muller Equipment</th>
                <th className="px-4 py-3 font-bold">Batch Mass</th>
                <th className="px-4 py-3 font-bold">Bentonite</th>
                <th className="px-4 py-3 font-bold">Coal Dust</th>
                <th className="px-4 py-3 font-bold">Water Addition</th>
                <th className="px-4 py-3 font-bold">Cycle Time</th>
                <th className="px-4 py-3 font-bold">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {batches.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-slate-400">
                    No muller batches logged yet for Line {lineCode}. Click &ldquo;Log Muller Batch&rdquo; to record one.
                  </td>
                </tr>
              ) : (
                batches.map(b => (
                  <tr key={b.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-blue-600">{b.batch_number}</td>
                    <td className="px-4 py-3 text-slate-700">{b.muller_id}</td>
                    <td className="px-4 py-3 font-bold text-slate-800 tabular-nums">{b.batch_weight_kg} kg</td>
                    <td className="px-4 py-3 text-slate-800 tabular-nums">{b.bentonite_addition_kg} kg</td>
                    <td className="px-4 py-3 text-slate-800 tabular-nums">{b.coal_dust_addition_kg} kg</td>
                    <td className="px-4 py-3 text-blue-700 font-bold tabular-nums">{b.water_addition_liters} L</td>
                    <td className="px-4 py-3 text-emerald-700 font-bold tabular-nums">{b.cycle_time_seconds} s</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(b.timestamp).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase">Log Muller Sand Batch (Line {lineCode})</h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateBatch} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">Muller Equipment</label>
                <input
                  type="text"
                  required
                  value={mullerId}
                  onChange={e => setMullerId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Batch Weight (kg)</label>
                  <input
                    type="number"
                    min={100}
                    step="any"
                    required
                    value={batchWeight}
                    onChange={e => setBatchWeight(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Bentonite (kg)</label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    required
                    value={bentoniteKg}
                    onChange={e => setBentoniteKg(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Coal Dust (kg)</label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    required
                    value={coalDustKg}
                    onChange={e => setCoalDustKg(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Water Added (L)</label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    required
                    value={waterLiters}
                    onChange={e => setWaterLiters(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">Mix Cycle Time (seconds)</label>
                <input
                  type="number"
                  min={10}
                  max={3600}
                  required
                  value={cycleSeconds}
                  onChange={e => setCycleSeconds(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-3 py-1.5 text-slate-600">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-blue-600 text-white font-bold rounded-lg disabled:opacity-60"
                >
                  {submitting ? 'Saving...' : 'Save Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
