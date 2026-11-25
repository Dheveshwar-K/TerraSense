import React, { useCallback, useEffect, useState } from 'react';
import { Check, Edit2, Grid3X3, RefreshCw, X } from 'lucide-react';
import { api } from '../../services/api';
import { CorrectionRequest, Parameter, SandTestRecord } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

export const HourlyMonitoringPage: React.FC = () => {
  const { selectedLine, user } = useAuth();
  const { showToast } = useToast();
  const [lineCode, setLineCode] = useState<string>(selectedLine !== 'ALL' ? selectedLine : 'D1');
  const [testDate, setTestDate] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [records, setRecords] = useState<SandTestRecord[]>([]);
  const [parameters, setParameters] = useState<Parameter[]>([]);
  const [corrections, setCorrections] = useState<CorrectionRequest[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Correction Modal State
  const [selectedCell, setSelectedCell] = useState<{
    valueId: number;
    paramName: string;
    currentValue: number;
    unit: string;
  } | null>(null);
  const [correctionValue, setCorrectionValue] = useState<string>('');
  const [correctionReason, setCorrectionReason] = useState<string>('');
  const [submittingCorrection, setSubmittingCorrection] = useState<boolean>(false);

  const canReviewCorrections = Boolean(user && ['quality_engineer', 'quality_manager', 'admin'].includes(user.role));

  const loadMatrixData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [paramsData, testsData, corrData] = await Promise.all([
        api.getParameters('PHYSICAL', 'HOURLY'),
        api.getSandTests({ line_code: lineCode, test_date: testDate, test_type: 'HOURLY_PHYSICAL', limit: 100 }),
        api.getCorrectionRequests('PENDING'),
      ]);
      setParameters(paramsData);
      setRecords(testsData);
      setCorrections(corrData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load hourly monitoring matrix');
    } finally {
      setLoading(false);
    }
  }, [lineCode, testDate]);

  useEffect(() => {
    loadMatrixData();
  }, [loadMatrixData]);

  const hourMap: Record<number, SandTestRecord> = {};
  records.forEach(r => {
    hourMap[r.test_hour] = r;
  });

  const hours = Array.from({ length: 24 }, (_, i) => i + 1);

  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCell || !correctionReason.trim() || submittingCorrection) return;
    setSubmittingCorrection(true);
    try {
      await api.requestCorrection({
        value_id: selectedCell.valueId,
        requested_value: Number(correctionValue),
        reason: correctionReason.trim(),
      });
      showToast('Correction request submitted for Quality Engineer review.', 'success');
      setSelectedCell(null);
      setCorrectionValue('');
      setCorrectionReason('');
      await loadMatrixData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Error submitting correction', 'error');
    } finally {
      setSubmittingCorrection(false);
    }
  };

  const handleReview = async (id: number, action: 'approve' | 'reject') => {
    try {
      if (action === 'approve') {
        await api.approveCorrection(id, 'Approved via Hourly Matrix QA review');
        showToast('Correction approved and audit trail updated.', 'success');
      } else {
        await api.rejectCorrection(id, 'Rejected during QA review');
        showToast('Correction request rejected.', 'info');
      }
      await loadMatrixData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to process review', 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <Grid3X3 className="w-5 h-5 text-blue-600" />
            HOURLY SAND PARAMETER MONITORING MATRIX
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            24-Hour continuous green sand physical testing grid for tracking process consistency and shift handovers.
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

          <input
            type="date"
            aria-label="Monitoring test date"
            value={testDate}
            onChange={e => setTestDate(e.target.value)}
            className="text-xs font-semibold bg-white border border-slate-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500"
          />

          <button
            type="button"
            onClick={() => loadMatrixData()}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200 transition-colors"
            title="Refresh Grid"
            aria-label="Refresh Grid"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-800">
          {error}
        </div>
      )}

      {/* 24-Hour Matrix Grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <span className="font-bold text-slate-700">Status Legend:</span>
            <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> In Spec
            </span>
            <span className="flex items-center gap-1.5 text-amber-700 font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Warning Margin
            </span>
            <span className="flex items-center gap-1.5 text-rose-700 font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> Out of Spec
            </span>
            <span className="flex items-center gap-1.5 text-slate-400 font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-200"></span> No Test
            </span>
          </div>

          <div className="text-xs text-slate-500 tabular-nums">
            Total Logged Tests: <b>{records.length}</b> / 24 hrs
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/80 text-slate-700 border-b border-slate-200">
                <th className="sticky left-0 bg-slate-100 z-10 px-4 py-3 text-left font-bold border-r border-slate-200 min-w-[200px]">
                  Sand Parameter
                </th>
                <th className="px-2 py-3 text-center font-bold border-r border-slate-200 text-[10px] text-slate-500">
                  Target
                </th>
                <th className="px-2 py-3 text-center font-bold border-r border-slate-200 text-[10px] text-slate-500">
                  Spec Range
                </th>
                {hours.map(h => (
                  <th
                    key={h}
                    className={`px-2 py-2 text-center font-bold border-r border-slate-200 min-w-[50px] ${
                      hourMap[h] ? 'bg-blue-50/50 text-blue-900' : 'text-slate-400'
                    }`}
                  >
                    H{h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {parameters.map(param => (
                <tr key={param.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="sticky left-0 bg-white z-10 px-4 py-2.5 font-semibold text-slate-800 border-r border-slate-200">
                    <div>{param.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      {param.code} ({param.unit})
                    </div>
                  </td>
                  <td className="px-2 py-2 text-center font-bold text-blue-600 border-r border-slate-200 tabular-nums">
                    {param.target_value}
                  </td>
                  <td className="px-2 py-2 text-center text-[10px] text-slate-500 border-r border-slate-200 whitespace-nowrap font-mono tabular-nums">
                    {param.lsl} - {param.usl}
                  </td>

                  {hours.map(h => {
                    const record = hourMap[h];
                    const valObj = record?.values.find(v => v.parameter_id === param.id);

                    if (!valObj) {
                      return (
                        <td key={h} className="px-2 py-2 text-center border-r border-slate-100 text-slate-300">
                          -
                        </td>
                      );
                    }

                    const val = valObj.measured_value;
                    let cellBg = 'bg-emerald-50 text-emerald-800 border-emerald-200';
                    if (valObj.status === 'OUT_OF_SPEC') {
                      cellBg = 'bg-rose-50 text-rose-800 border-rose-300 font-bold';
                    } else if (valObj.status === 'WARNING') {
                      cellBg = 'bg-amber-50 text-amber-800 border-amber-300';
                    }

                    return (
                      <td
                        key={h}
                        onClick={() => {
                          setSelectedCell({
                            valueId: valObj.id,
                            paramName: param.name,
                            currentValue: val,
                            unit: param.unit,
                          });
                          setCorrectionValue(String(val));
                        }}
                        className={`px-1 py-1.5 text-center border-r border-slate-100 cursor-pointer hover:ring-1 hover:ring-blue-400 tabular-nums ${cellBg}`}
                        title={`H${h}: ${val} ${param.unit} (${valObj.status}). Click to request correction.`}
                      >
                        <div className="text-[11px] font-semibold">{val}</div>
                        {valObj.is_corrected && (
                          <div className="text-[8px] text-blue-600 font-bold">REV</div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Data Correction Requests Queue */}
      {corrections.length > 0 && (
        <div className="bg-white rounded-xl border border-amber-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-amber-200 bg-amber-50/60 flex items-center justify-between">
            <h2 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
              Pending Measurement Correction Requests ({corrections.length})
            </h2>
            <span className="text-[11px] text-amber-700">IATF 16949 Dual-Control Approval</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5 font-bold">Test / Line</th>
                  <th className="px-4 py-2.5 font-bold">Parameter</th>
                  <th className="px-4 py-2.5 font-bold text-right">Current</th>
                  <th className="px-4 py-2.5 font-bold text-right">Requested</th>
                  <th className="px-4 py-2.5 font-bold">Reason</th>
                  <th className="px-4 py-2.5 font-bold">Requested By</th>
                  <th className="px-4 py-2.5 font-bold">Status</th>
                  {canReviewCorrections && <th className="px-4 py-2.5 font-bold text-right">QA Review</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {corrections.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-mono font-bold text-slate-800">
                      {c.test_number} ({c.line_code})
                    </td>
                    <td className="px-4 py-2.5 font-semibold text-slate-700">{c.parameter_name}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {c.current_value} {c.unit}
                    </td>
                    <td className="px-4 py-2.5 text-right font-bold text-blue-700 tabular-nums">
                      {c.requested_value} {c.unit}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 max-w-xs truncate" title={c.reason}>
                      {c.reason}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">{c.requested_by_name}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                    {canReviewCorrections && (
                      <td className="px-4 py-2.5 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleReview(c.id, 'approve')}
                            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded text-[11px] inline-flex items-center gap-1"
                          >
                            <Check className="w-3 h-3" /> Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => handleReview(c.id, 'reject')}
                            className="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded text-[11px] inline-flex items-center gap-1"
                          >
                            <X className="w-3 h-3" /> Reject
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Correction Request Modal */}
      {selectedCell && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase flex items-center gap-1.5">
                <Edit2 className="w-4 h-4 text-blue-600" />
                Request Test Correction
              </h3>
              <button
                type="button"
                onClick={() => setSelectedCell(null)}
                aria-label="Close modal"
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                Parameter: <b>{selectedCell.paramName}</b>
              </div>
              <div>
                Current Measured Value:{' '}
                <b>
                  {selectedCell.currentValue} {selectedCell.unit}
                </b>
              </div>
              <div className="text-[10px] text-slate-400">
                Note: In compliance with IATF 16949 audit rules, original values are permanently preserved in the audit log.
              </div>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                  Corrected Value ({selectedCell.unit})
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  value={correctionValue}
                  onChange={e => setCorrectionValue(e.target.value)}
                  className="w-full text-sm font-bold bg-white border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                  Reason for Correction (min 5 chars)
                </label>
                <textarea
                  rows={3}
                  required
                  minLength={5}
                  value={correctionReason}
                  onChange={e => setCorrectionReason(e.target.value)}
                  placeholder="e.g. Typographical error during tablet entry. Lab test log sheet shows 3.42%."
                  className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedCell(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCorrection}
                  className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg"
                >
                  {submittingCorrection ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
