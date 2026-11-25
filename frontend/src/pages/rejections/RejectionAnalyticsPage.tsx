import React, { useCallback, useEffect, useState } from 'react';
import { Plus, RefreshCw, TrendingDown } from 'lucide-react';
import { api } from '../../services/api';
import { CastingProduct, DefectCategory, RejectionRecord } from '../../types';
import { StatusBadge } from '../../components/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const RejectionAnalyticsPage: React.FC = () => {
  const { selectedLine, user } = useAuth();
  const { showToast } = useToast();
  const [lineCode, setLineCode] = useState<string>(selectedLine);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [rejections, setRejections] = useState<RejectionRecord[]>([]);
  const [defects, setDefects] = useState<DefectCategory[]>([]);
  const [products, setProducts] = useState<CastingProduct[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalLine, setModalLine] = useState<string>('D1');
  const [modalShift, setModalShift] = useState<number>(1);
  const [modalDate, setModalDate] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [modalProductId, setModalProductId] = useState<number>(0);
  const [modalDefectId, setModalDefectId] = useState<number>(0);
  const [inspectedQty, setInspectedQty] = useState<number>(400);
  const [rejectedQty, setRejectedQty] = useState<number>(8);
  const [detectionStage, setDetectionStage] = useState<string>('Visual Shakeout');
  const [submitting, setSubmitting] = useState<boolean>(false);

  const canCreate = Boolean(user && ['quality_engineer', 'supervisor', 'quality_manager', 'admin'].includes(user.role));

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [rData, dData, pData] = await Promise.all([
        api.getRejections({
          line_code: lineCode !== 'ALL' ? lineCode : undefined,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        }),
        api.getDefects(),
        api.getProducts(),
      ]);
      setRejections(rData);
      setDefects(dData);
      setProducts(pData);
      if (pData.length > 0) setModalProductId(prev => prev || pData[0].id);
      if (dData.length > 0) setModalDefectId(prev => prev || dData[0].id);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load rejection records', 'error');
    } finally {
      setLoading(false);
    }
  }, [endDate, lineCode, showToast, startDate]);

  useEffect(() => {
    setLineCode(selectedLine);
  }, [selectedLine]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const liveRate = inspectedQty > 0 ? ((rejectedQty / inspectedQty) * 100).toFixed(2) : '0.00';

  const handleCreateRejection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    if (inspectedQty <= 0) {
      showToast('Inspected quantity must be greater than zero.', 'error');
      return;
    }
    if (rejectedQty < 0 || rejectedQty > inspectedQty) {
      showToast('Rejected quantity must be between 0 and inspected quantity.', 'error');
      return;
    }
    setSubmitting(true);
    try {
      await api.createRejection({
        production_date: modalDate,
        line_code: modalLine,
        shift: modalShift,
        product_id: modalProductId,
        defect_category_id: modalDefectId,
        rejected_qty: rejectedQty,
        inspected_qty: inspectedQty,
        detection_stage: detectionStage,
        severity: Number(liveRate) > 4.0 ? 'CRITICAL' : Number(liveRate) > 2.5 ? 'MAJOR' : 'MINOR',
        root_cause_candidate: 'Recorded at inspection station',
      });
      showToast('Rejection record registered successfully.', 'success');
      setShowModal(false);
      await loadData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Error creating rejection record', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-blue-600" />
            CASTING REJECTION &amp; DEFECT TRACKING MODULE
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Shift-wise scrap rate recording, defect classifications, and correlation linkages to upstream sand parameters.
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
            aria-label="Start date"
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />
          <input
            type="date"
            aria-label="End date"
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />

          <button
            type="button"
            onClick={() => loadData()}
            aria-label="Refresh rejections"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {canCreate && (
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Record Rejection
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Rejection History Logs ({rejections.length} records)
          </h2>
          <span className="text-xs text-slate-500">Filtered by Line: {lineCode}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">Rejection No</th>
                <th className="px-4 py-3 font-bold">Line</th>
                <th className="px-4 py-3 font-bold">Date &amp; Shift</th>
                <th className="px-4 py-3 font-bold">Casting Product</th>
                <th className="px-4 py-3 font-bold">Defect Category</th>
                <th className="px-4 py-3 font-bold text-right">Rejected</th>
                <th className="px-4 py-3 font-bold text-right">Inspected</th>
                <th className="px-4 py-3 font-bold text-right">Scrap Rate</th>
                <th className="px-4 py-3 font-bold">Severity</th>
                <th className="px-4 py-3 font-bold">Detection Stage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rejections.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-10 text-center text-slate-400">
                    No rejection records match the selected filters.
                  </td>
                </tr>
              ) : (
                rejections.map(r => (
                  <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-blue-600">{r.rejection_number}</td>
                    <td className="px-4 py-3">
                      <span className="w-6 h-6 rounded bg-slate-900 text-white text-[10px] font-black flex items-center justify-center">
                        {r.line_code}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-800">{r.production_date}</div>
                      <div className="text-[10px] text-slate-400">Shift {r.shift}</div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-800">{r.product_name}</td>
                    <td className="px-4 py-3 font-bold text-slate-700">{r.defect_name}</td>
                    <td className="px-4 py-3 text-right font-black text-rose-600 tabular-nums">{r.rejected_qty}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-600 tabular-nums">{r.inspected_qty}</td>
                    <td className="px-4 py-3 text-right font-black text-slate-900 tabular-nums">
                      <span className={`px-2 py-0.5 rounded ${r.rejection_rate > 3.0 ? 'bg-rose-50 text-rose-700 font-black' : 'text-slate-800'}`}>
                        {r.rejection_rate.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.severity} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-slate-500">{r.detection_stage}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase flex items-center gap-1.5">
                <TrendingDown className="w-4 h-4 text-blue-600" />
                Record Casting Rejection / Scrap
              </h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateRejection} className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Line</label>
                  <select
                    value={modalLine}
                    onChange={e => setModalLine(e.target.value)}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                  >
                    <option value="D1">Line D1</option>
                    <option value="D2">Line D2</option>
                    <option value="D3">Line D3</option>
                    <option value="D4">Line D4</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Shift</label>
                  <select
                    value={modalShift}
                    onChange={e => setModalShift(Number(e.target.value))}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                  >
                    <option value={1}>Shift 1</option>
                    <option value={2}>Shift 2</option>
                    <option value={3}>Shift 3</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Date</label>
                  <input
                    type="date"
                    required
                    value={modalDate}
                    onChange={e => setModalDate(e.target.value)}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Casting Product</label>
                  <select
                    value={modalProductId}
                    onChange={e => setModalProductId(Number(e.target.value))}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                  >
                    {products.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.part_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Defect Category</label>
                  <select
                    value={modalDefectId}
                    onChange={e => setModalDefectId(Number(e.target.value))}
                    className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                  >
                    {defects.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Inspected Qty</label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={inspectedQty}
                    onChange={e => setInspectedQty(Number(e.target.value))}
                    className="w-full text-sm font-bold bg-white border border-slate-300 rounded p-1.5 text-right tabular-nums"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Rejected Qty</label>
                  <input
                    type="number"
                    min={0}
                    max={inspectedQty}
                    required
                    value={rejectedQty}
                    onChange={e => setRejectedQty(Number(e.target.value))}
                    className="w-full text-sm font-bold bg-white border border-slate-300 rounded p-1.5 text-right text-rose-600 tabular-nums"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Scrap Rate (%)</label>
                  <div className="text-lg font-black text-slate-900 pt-1 text-right tabular-nums">{liveRate}%</div>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Detection Stage</label>
                <select
                  value={detectionStage}
                  onChange={e => setDetectionStage(e.target.value)}
                  className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2"
                >
                  <option value="Visual Shakeout">Visual Shakeout</option>
                  <option value="Shotblast Inspection">Shotblast Inspection</option>
                  <option value="Bore Machining">Bore Machining</option>
                  <option value="Hydrostatic Pressure Test">Hydrostatic Pressure Test</option>
                  <option value="Final Dispatch QC">Final Dispatch QC</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button type="button" onClick={() => setShowModal(false)} className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg"
                >
                  {submitting ? 'Recording...' : 'Register Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
