import React, { useCallback, useEffect, useState } from 'react';
import { FileText, Plus, RefreshCw, ShieldAlert } from 'lucide-react';
import { api } from '../../services/api';
import { CastingProduct, CustomerComplaint, DefectCategory } from '../../types';
import { StatusBadge } from '../../components/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const ComplaintsPage: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [complaints, setComplaints] = useState<CustomerComplaint[]>([]);
  const [defects, setDefects] = useState<DefectCategory[]>([]);
  const [products, setProducts] = useState<CastingProduct[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Create Complaint Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newCustomer, setNewCustomer] = useState<string>('');
  const [newDate, setNewDate] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [newLine, setNewLine] = useState<string>('D1');
  const [newProductId, setNewProductId] = useState<number>(0);
  const [newDefectId, setNewDefectId] = useState<number>(0);
  const [newQty, setNewQty] = useState<number>(10);
  const [newSeverity, setNewSeverity] = useState<string>('HIGH');
  const [newDesc, setNewDesc] = useState<string>('');
  const [creating, setCreating] = useState<boolean>(false);

  // 8D Editor Modal
  const [selectedComplaint, setSelectedComplaint] = useState<CustomerComplaint | null>(null);
  const [d1Team, setD1Team] = useState<string>('');
  const [d2Problem, setD2Problem] = useState<string>('');
  const [d3Containment, setD3Containment] = useState<string>('');
  const [d4RootCause, setD4RootCause] = useState<string>('');
  const [d5Corrective, setD5Corrective] = useState<string>('');
  const [d6Validation, setD6Validation] = useState<string>('');
  const [d7Preventive, setD7Preventive] = useState<string>('');
  const [d8Closure, setD8Closure] = useState<string>('');
  const [statusVal, setStatusVal] = useState<string>('OPEN');
  const [saving8D, setSaving8D] = useState<boolean>(false);

  const canEdit = Boolean(user && ['quality_engineer', 'quality_manager', 'admin'].includes(user.role));

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [cData, dData, pData] = await Promise.all([
        api.getComplaints(),
        api.getDefects(),
        api.getProducts(),
      ]);
      setComplaints(cData);
      setDefects(dData);
      setProducts(pData);
      if (pData.length > 0) setNewProductId(prev => prev || pData[0].id);
      if (dData.length > 0) setNewDefectId(prev => prev || dData[0].id);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load complaints', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const open8DModal = (c: CustomerComplaint) => {
    setSelectedComplaint(c);
    setD1Team(c.d1_team || '');
    setD2Problem(c.d2_problem || c.description);
    setD3Containment(c.d3_containment || '');
    setD4RootCause(c.d4_root_cause || '');
    setD5Corrective(c.d5_corrective_action || '');
    setD6Validation(c.d6_validation || '');
    setD7Preventive(c.d7_preventive_action || '');
    setD8Closure(c.d8_closure || '');
    setStatusVal(c.status);
  };

  const handleCreateComplaint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (creating) return;
    setCreating(true);
    try {
      await api.createComplaint({
        customer_name: newCustomer.trim(),
        received_date: newDate,
        line_code: newLine,
        product_id: newProductId,
        defect_category_id: newDefectId,
        affected_qty: newQty,
        severity: newSeverity,
        description: newDesc.trim(),
      });
      showToast('Customer complaint registered.', 'success');
      setShowCreateModal(false);
      setNewCustomer('');
      setNewDesc('');
      await loadData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Error creating complaint', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleSave8D = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || saving8D) return;
    setSaving8D(true);
    try {
      await api.updateComplaint8D(selectedComplaint.id, {
        d1_team: d1Team,
        d2_problem: d2Problem,
        d3_containment: d3Containment,
        d4_root_cause: d4RootCause,
        d5_corrective_action: d5Corrective,
        d6_validation: d6Validation,
        d7_preventive_action: d7Preventive,
        d8_closure: d8Closure,
        status: statusVal,
        expected_version: selectedComplaint.version,
      });
      showToast(`8D CAPA updated for complaint ${selectedComplaint.complaint_number}.`, 'success');
      setSelectedComplaint(null);
      await loadData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Error updating 8D', 'error');
    } finally {
      setSaving8D(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-blue-600" />
            CUSTOMER COMPLAINT &amp; 8D CAPA MANAGEMENT
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            IATF 16949 compliant customer quality resolution workflow: Containment, Root Cause, Corrective &amp; Preventive Action (D1–D8).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => loadData()}
            aria-label="Refresh complaints"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {canEdit && (
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Log Complaint
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Customer Complaints Register ({complaints.length})
          </h2>
          <span className="text-xs text-slate-500">Linked to Sand Batches &amp; Rejection Lots</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">Complaint No</th>
                <th className="px-4 py-3 font-bold">Customer Name</th>
                <th className="px-4 py-3 font-bold">Received Date</th>
                <th className="px-4 py-3 font-bold">Casting Part</th>
                <th className="px-4 py-3 font-bold">Defect Category</th>
                <th className="px-4 py-3 font-bold text-center">Affected Qty</th>
                <th className="px-4 py-3 font-bold">Severity</th>
                <th className="px-4 py-3 font-bold">Status</th>
                <th className="px-4 py-3 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {complaints.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-slate-400">
                    No customer complaints logged.
                  </td>
                </tr>
              ) : (
                complaints.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-blue-600">{c.complaint_number}</td>
                    <td className="px-4 py-3 font-bold text-slate-800">{c.customer_name}</td>
                    <td className="px-4 py-3 text-slate-600">{c.received_date}</td>
                    <td className="px-4 py-3 font-semibold text-slate-700">{c.product_name}</td>
                    <td className="px-4 py-3 text-slate-800 font-medium">{c.defect_name}</td>
                    <td className="px-4 py-3 text-center font-black text-rose-600 tabular-nums">{c.affected_qty} pcs</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.severity} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => open8DModal(c)}
                        className="px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold rounded text-xs border border-blue-200 inline-flex items-center gap-1"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        8D CAPA
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Complaint Modal */}
      {showCreateModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase">Register Customer Quality Complaint</h3>
              <button type="button" onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateComplaint} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Customer Name</label>
                  <input
                    type="text"
                    required
                    minLength={2}
                    value={newCustomer}
                    onChange={e => setNewCustomer(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Received Date</label>
                  <input
                    type="date"
                    required
                    value={newDate}
                    onChange={e => setNewDate(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Line</label>
                  <select value={newLine} onChange={e => setNewLine(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2">
                    <option value="D1">D1</option>
                    <option value="D2">D2</option>
                    <option value="D3">D3</option>
                    <option value="D4">D4</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Affected Qty</label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={newQty}
                    onChange={e => setNewQty(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Severity</label>
                  <select value={newSeverity} onChange={e => setNewSeverity(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2">
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Product</label>
                  <select value={newProductId} onChange={e => setNewProductId(Number(e.target.value))} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2">
                    {products.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.part_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Defect</label>
                  <select value={newDefectId} onChange={e => setNewDefectId(Number(e.target.value))} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2">
                    {defects.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">Complaint Description</label>
                <textarea
                  rows={3}
                  required
                  minLength={5}
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-3 py-1.5 text-slate-600">
                  Cancel
                </button>
                <button type="submit" disabled={creating} className="px-4 py-1.5 bg-blue-600 text-white font-bold rounded-lg disabled:opacity-60">
                  {creating ? 'Registering...' : 'Register Complaint'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 8D CAPA Modal */}
      {selectedComplaint && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-3xl w-full p-6 shadow-xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-800 uppercase flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-blue-600" />
                  8D Problem Solving Dossier: {selectedComplaint.complaint_number}
                </h3>
                <p className="text-xs text-slate-500">
                  Customer: {selectedComplaint.customer_name} | Part: {selectedComplaint.product_name}
                </p>
              </div>
              <button type="button" onClick={() => setSelectedComplaint(null)} className="text-slate-400 hover:text-slate-600 text-xl font-bold">
                &times;
              </button>
            </div>

            <form onSubmit={handleSave8D} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">D1. Team Members</label>
                  <input
                    type="text"
                    disabled={!canEdit}
                    value={d1Team}
                    onChange={e => setD1Team(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded p-2"
                    placeholder="e.g. Lead QE, Metallurgist, Foundry Incharge"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">Investigation Status</label>
                  <select
                    disabled={!canEdit}
                    value={statusVal}
                    onChange={e => setStatusVal(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded p-2 font-bold"
                  >
                    <option value="OPEN">OPEN</option>
                    <option value="UNDER_INVESTIGATION">UNDER INVESTIGATION</option>
                    <option value="CAPA_PENDING">CAPA PENDING</option>
                    <option value="CLOSED">CLOSED (APPROVED)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase mb-1">D2. Problem Description</label>
                <textarea rows={2} disabled={!canEdit} value={d2Problem} onChange={e => setD2Problem(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase mb-1">D3. Immediate Containment Action</label>
                <textarea rows={2} disabled={!canEdit} value={d3Containment} onChange={e => setD3Containment(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase mb-1">D4. Verified Root Cause (Sand &amp; Molding)</label>
                <textarea rows={2} disabled={!canEdit} value={d4RootCause} onChange={e => setD4RootCause(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">D5. Permanent Corrective Action (PCA)</label>
                  <textarea rows={2} disabled={!canEdit} value={d5Corrective} onChange={e => setD5Corrective(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">D6. Validation of Effectiveness</label>
                  <textarea rows={2} disabled={!canEdit} value={d6Validation} onChange={e => setD6Validation(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">D7. Preventive Action (FMEA / Control Plan)</label>
                  <textarea rows={2} disabled={!canEdit} value={d7Preventive} onChange={e => setD7Preventive(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 uppercase mb-1">D8. Team Recognition &amp; Closure</label>
                  <textarea rows={2} disabled={!canEdit} value={d8Closure} onChange={e => setD8Closure(e.target.value)} className="w-full bg-slate-50 border border-slate-300 rounded p-2" />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setSelectedComplaint(null)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-semibold">
                  Close
                </button>
                {canEdit && (
                  <button type="submit" disabled={saving8D} className="px-6 py-2 text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg font-bold shadow-xs">
                    {saving8D ? 'Saving...' : 'Save 8D Report'}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
