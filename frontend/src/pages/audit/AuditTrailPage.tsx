import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, FileText, History, RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api } from '../../services/api';
import { AuditLog, AuditVerificationResult } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

function safePrettyJson(raw?: string): string {
  if (!raw) return '(None)';
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export const AuditTrailPage: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [entityFilter, setEntityFilter] = useState<string>('ALL');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verification, setVerification] = useState<AuditVerificationResult | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const canVerify = Boolean(user && ['quality_engineer', 'quality_manager', 'admin'].includes(user.role));

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs(
        entityFilter !== 'ALL' ? entityFilter : undefined,
        actionFilter !== 'ALL' ? actionFilter : undefined,
        startDate || undefined,
        endDate || undefined
      );
      setLogs(data);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load audit logs', 'error');
    } finally {
      setLoading(false);
    }
  }, [actionFilter, endDate, entityFilter, showToast, startDate]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyAuditChain();
      setVerification(res);
      showToast(
        res.valid
          ? `Hash chain verified across ${res.verified_records} records.`
          : `Integrity check detected ${res.broken_links.length} broken link(s).`,
        res.valid ? 'success' : 'error'
      );
      await loadLogs();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Verification failed', 'error');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-blue-600" />
            DIGITAL AUDIT TRAIL (IATF 16949 COMPLIANT)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Append-only SHA-256 hash-chained log of user authentication, test entries, specification changes, and alert workflows.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <select
            aria-label="Filter by entity"
            value={entityFilter}
            onChange={e => setEntityFilter(e.target.value)}
            className="text-xs font-bold bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          >
            <option value="ALL">All Entities</option>
            <option value="User">Users &amp; Auth</option>
            <option value="SandTestRecord">Sand Test Records</option>
            <option value="SandTestValue">Sand Test Corrections</option>
            <option value="ParameterSpecification">Specifications</option>
            <option value="QualityAlert">Quality Alerts</option>
            <option value="CustomerComplaint">Complaints &amp; 8D</option>
            <option value="RejectionRecord">Rejections</option>
            <option value="RootCauseInvestigation">Investigations</option>
            <option value="Report">Report Exports</option>
          </select>

          <select
            aria-label="Filter by action"
            value={actionFilter}
            onChange={e => setActionFilter(e.target.value)}
            className="text-xs font-bold bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          >
            <option value="ALL">All Actions</option>
            <option value="LOGIN">LOGIN</option>
            <option value="LOGIN_FAILED">LOGIN FAILED</option>
            <option value="CREATE">CREATE</option>
            <option value="UPDATE">UPDATE</option>
            <option value="ACKNOWLEDGE">ACKNOWLEDGE</option>
            <option value="RESOLVE">RESOLVE</option>
            <option value="EXPORT">EXPORT</option>
          </select>

          <input
            type="date"
            aria-label="Audit start date"
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />
          <input
            type="date"
            aria-label="Audit end date"
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />

          <button
            type="button"
            onClick={() => loadLogs()}
            aria-label="Refresh audit logs"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {canVerify && (
            <button
              type="button"
              onClick={handleVerifyChain}
              disabled={verifying}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-xs disabled:opacity-60"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              {verifying ? 'Verifying...' : 'Verify Hash Chain'}
            </button>
          )}
        </div>
      </div>

      {verification && (
        <div
          className={`p-4 rounded-xl border text-xs space-y-1 ${
            verification.valid
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-rose-50 border-rose-300 text-rose-900'
          }`}
        >
          <div className="font-bold flex items-center gap-2">
            {verification.valid ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-rose-600" />
            )}
            <span>
              {verification.valid
                ? `Hash-Chain Verified: ${verification.verified_records} / ${verification.total_records} records intact.`
                : `Hash-Chain Mismatch Detected: ${verification.broken_links.length} broken link(s).`}
            </span>
          </div>
          {verification.head_hash && (
            <div className="font-mono text-[10px] opacity-80">Head SHA-256: {verification.head_hash}</div>
          )}
          <div className="text-[11px] opacity-85">{verification.threat_model_note}</div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Audit Events ({logs.length})</h2>
          <span className="text-xs text-slate-500">SHA-256 Hash-Chained Ledger</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">Seq</th>
                <th className="px-4 py-3 font-bold">Timestamp (UTC)</th>
                <th className="px-4 py-3 font-bold">Actor</th>
                <th className="px-4 py-3 font-bold">Role</th>
                <th className="px-4 py-3 font-bold">Action</th>
                <th className="px-4 py-3 font-bold">Entity</th>
                <th className="px-4 py-3 font-bold">Outcome</th>
                <th className="px-4 py-3 font-bold">Hash</th>
                <th className="px-4 py-3 font-bold">Reason</th>
                <th className="px-4 py-3 font-bold text-right">Diff</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500 tabular-nums">#{log.sequence_no ?? log.id}</td>
                  <td className="px-4 py-3 font-mono text-slate-500 whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-800">{log.user_name}</td>
                  <td className="px-4 py-3">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                      {log.user_role}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-bold text-blue-700">{log.action}</td>
                  <td className="px-4 py-3 font-semibold text-slate-700">
                    {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ''}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={log.outcome || 'SUCCESS'} size="sm" />
                  </td>
                  <td className="px-4 py-3 font-mono text-[10px] text-slate-400" title={log.record_hash || ''}>
                    {log.record_hash ? `${log.record_hash.slice(0, 10)}...` : '-'}
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs truncate" title={log.reason || ''}>
                    {log.reason || '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {(log.old_value || log.new_value) && (
                      <button
                        type="button"
                        onClick={() => setSelectedLog(log)}
                        className="px-2 py-1 text-[11px] font-bold text-blue-600 hover:text-blue-800 bg-blue-50 rounded border border-blue-200"
                      >
                        Inspect
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedLog && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                Audit Record Diff: Event #{selectedLog.sequence_no ?? selectedLog.id}
              </h3>
              <button type="button" onClick={() => setSelectedLog(null)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                Actor: <b>{selectedLog.user_name}</b> ({selectedLog.user_role})
              </div>
              <div>
                Action: <b>{selectedLog.action}</b> on <b>{selectedLog.entity_type} #{selectedLog.entity_id}</b>
              </div>
              <div>
                Reason: <i>&ldquo;{selectedLog.reason}&rdquo;</i>
              </div>
              {selectedLog.record_hash && (
                <div className="font-mono text-[10px] text-slate-500 pt-1">
                  SHA-256: {selectedLog.record_hash}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block font-bold text-rose-700 uppercase mb-1">Previous State (Old Value)</label>
                <pre className="p-3 bg-slate-950 text-slate-200 rounded-lg text-[10px] overflow-auto max-h-60 font-mono">
                  {selectedLog.old_value ? safePrettyJson(selectedLog.old_value) : '(None - Created)'}
                </pre>
              </div>

              <div>
                <label className="block font-bold text-emerald-700 uppercase mb-1">New State (Modified Value)</label>
                <pre className="p-3 bg-slate-950 text-slate-200 rounded-lg text-[10px] overflow-auto max-h-60 font-mono">
                  {selectedLog.new_value ? safePrettyJson(selectedLog.new_value) : '(None - Deleted)'}
                </pre>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
