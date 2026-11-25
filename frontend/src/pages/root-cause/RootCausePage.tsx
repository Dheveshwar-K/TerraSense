import React, { useCallback, useEffect, useState } from 'react';
import { GitBranch, Plus, RefreshCw, Save, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import { RootCauseInvestigation } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

const DEFAULT_FISHBONE = {
  man: '',
  machine: '',
  material: '',
  method: '',
  measurement: '',
  environment: '',
};

export const RootCausePage: React.FC = () => {
  const { selectedLine, user } = useAuth();
  const { showToast } = useToast();
  const [investigations, setInvestigations] = useState<RootCauseInvestigation[]>([]);
  const [activeInv, setActiveInv] = useState<RootCauseInvestigation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  // Editable form state
  const [title, setTitle] = useState<string>('');
  const [lineCode, setLineCode] = useState<string>(selectedLine !== 'ALL' ? selectedLine : 'D2');
  const [problemStatement, setProblemStatement] = useState<string>('');
  const [whys, setWhys] = useState<string[]>(['Why 1: ', 'Why 2: ', 'Why 3: ', 'Why 4: ', 'Why 5 (Root Cause): ']);
  const [fishbone, setFishbone] = useState<Record<string, string>>(DEFAULT_FISHBONE);
  const [countermeasure, setCountermeasure] = useState<string>('');
  const [statusVal, setStatusVal] = useState<'IN_PROGRESS' | 'VALIDATED' | 'CLOSED'>('IN_PROGRESS');

  const canEdit = Boolean(user && ['quality_engineer', 'supervisor', 'quality_manager', 'admin'].includes(user.role));

  const populateForm = (inv: RootCauseInvestigation) => {
    setActiveInv(inv);
    setTitle(inv.title);
    setLineCode(inv.line_code);
    setProblemStatement(inv.findings || '');
    setWhys(inv.five_why_analysis?.length ? inv.five_why_analysis : ['Why 1: ']);
    setFishbone({ ...DEFAULT_FISHBONE, ...(inv.fishbone_factors || {}) });
    setCountermeasure(inv.conclusion || '');
    setStatusVal(inv.status);
  };

  const loadInvestigations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getInvestigations(selectedLine);
      setInvestigations(data);
      if (data.length > 0) {
        populateForm(data[0]);
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load root cause dossiers', 'error');
    } finally {
      setLoading(false);
    }
  }, [selectedLine, showToast]);

  useEffect(() => {
    loadInvestigations();
  }, [loadInvestigations]);

  const handleNewDraft = () => {
    setActiveInv(null);
    setTitle('New Sand Quality & Defect Investigation');
    setLineCode(selectedLine !== 'ALL' ? selectedLine : 'D2');
    setProblemStatement('');
    setWhys(['Why 1: ', 'Why 2: ', 'Why 3: ', 'Why 4: ', 'Why 5 (Root Cause): ']);
    setFishbone({ ...DEFAULT_FISHBONE });
    setCountermeasure('');
    setStatusVal('IN_PROGRESS');
  };

  const handleSave = async () => {
    if (!title.trim() || saving) {
      showToast('Investigation title is required.', 'error');
      return;
    }
    setSaving(true);
    try {
      if (activeInv) {
        const updated = await api.updateInvestigation(activeInv.id, {
          title: title.trim(),
          five_why_analysis: whys,
          fishbone_factors: fishbone,
          findings: problemStatement,
          conclusion: countermeasure,
          status: statusVal,
          expected_version: activeInv.version,
        });
        showToast(`Investigation ${updated.investigation_number} saved to database.`, 'success');
        await loadInvestigations();
        populateForm(updated);
      } else {
        const created = await api.createInvestigation({
          title: title.trim(),
          line_code: lineCode,
          five_why_analysis: whys,
          fishbone_factors: fishbone,
          findings: problemStatement,
          conclusion: countermeasure,
        });
        showToast(`Created investigation dossier ${created.investigation_number}.`, 'success');
        await loadInvestigations();
        populateForm(created);
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to save investigation', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-blue-600" />
            STRUCTURED ROOT CAUSE INVESTIGATION (5-WHY &amp; ISHIKAWA)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Persistent engineering dossier translating statistical correlation findings into verified root causes and CAPA actions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => loadInvestigations()}
            aria-label="Refresh investigations"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {canEdit && (
            <button
              type="button"
              onClick={handleNewDraft}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg border border-slate-200"
            >
              <Plus className="w-3.5 h-3.5" />
              New Dossier
            </button>
          )}
          <Link
            to="/complaints"
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            8D CAPA Register
          </Link>
        </div>
      </div>

      {/* Saved Dossiers Selector */}
      {investigations.length > 0 && (
        <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center gap-2 overflow-x-auto">
          <span className="text-[11px] font-bold text-slate-500 uppercase px-2 shrink-0">Saved Dossiers:</span>
          {investigations.map(inv => (
            <button
              key={inv.id}
              type="button"
              onClick={() => populateForm(inv)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border shrink-0 flex items-center gap-2 transition-colors ${activeInv?.id === inv.id
                  ? 'bg-blue-50 border-blue-400 text-blue-800'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
            >
              <span className="font-mono font-bold">{inv.investigation_number}</span>
              <StatusBadge status={inv.status} size="sm" />
            </button>
          ))}
        </div>
      )}

      {/* Metadata & Problem Statement */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Dossier Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              disabled={!canEdit}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5"
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Line</label>
            <select
              value={lineCode}
              onChange={e => setLineCode(e.target.value)}
              disabled={!canEdit || Boolean(activeInv)}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5"
            >
              <option value="D1">Line D1</option>
              <option value="D2">Line D2</option>
              <option value="D3">Line D3</option>
              <option value="D4">Line D4</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Status</label>
            <select
              value={statusVal}
              onChange={e => setStatusVal(e.target.value as 'IN_PROGRESS' | 'VALIDATED' | 'CLOSED')}
              disabled={!canEdit}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5"
            >
              <option value="IN_PROGRESS">IN PROGRESS</option>
              <option value="VALIDATED">VALIDATED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
            Problem Description &amp; Findings
          </label>
          <textarea
            rows={2}
            value={problemStatement}
            onChange={e => setProblemStatement(e.target.value)}
            disabled={!canEdit}
            className="w-full text-xs font-medium bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* 5-Why Investigation Tree */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">5-Why Sequential Root Cause Tree</h2>
            <p className="text-xs text-slate-400">Drill down from defect symptom to fundamental system failure</p>
          </div>
          {canEdit && (
            <button
              type="button"
              onClick={() => setWhys([...whys, `Why ${whys.length + 1}: `])}
              className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> Add Step
            </button>
          )}
        </div>

        <div className="space-y-3">
          {whys.map((w, idx) => (
            <div key={idx} className="flex items-start gap-3">
              <span
                className={`w-8 h-8 rounded-lg font-black text-xs flex items-center justify-center shrink-0 ${idx === whys.length - 1 ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-700'
                  }`}
              >
                W{idx + 1}
              </span>
              <input
                type="text"
                value={w}
                disabled={!canEdit}
                onChange={e => {
                  const updated = [...whys];
                  updated[idx] = e.target.value;
                  setWhys(updated);
                }}
                className={`flex-1 text-xs p-2 rounded-lg border font-medium ${idx === whys.length - 1
                    ? 'bg-rose-50 border-rose-300 text-rose-900 font-bold'
                    : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Ishikawa 6M Fishbone Grid */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
            Ishikawa Fishbone (6M Cause-and-Effect Matrix)
          </h2>
          <p className="text-xs text-slate-400">Comprehensive contributing factor analysis across foundry operations</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { key: 'man', label: '1. Man (Operator / Skills)' },
            { key: 'machine', label: '2. Machine (Mullers / Mold Lines)' },
            { key: 'material', label: '3. Material (Sand, Clay, Coal)' },
            { key: 'method', label: '4. Method (Mulling Cycle & SOP)' },
            { key: 'measurement', label: '5. Measurement (Calibration / Sensors)' },
            { key: 'environment', label: '6. Milieu (Ambient Humidity & Temp)' },
          ].map(item => (
            <div key={item.key} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span> {item.label}
              </span>
              <textarea
                rows={3}
                disabled={!canEdit}
                value={fishbone[item.key] || ''}
                onChange={e => setFishbone({ ...fishbone, [item.key]: e.target.value })}
                className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Verified Countermeasure */}
      <div className="bg-emerald-50 border border-emerald-300 rounded-xl p-5 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          Verified Permanent Countermeasure &amp; Preventive Action (D7)
        </h3>
        <textarea
          rows={2}
          disabled={!canEdit}
          value={countermeasure}
          onChange={e => setCountermeasure(e.target.value)}
          className="w-full text-xs font-medium bg-white border border-emerald-300 rounded-lg p-2.5 text-slate-800"
        />
        {canEdit && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-60 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : activeInv ? 'Update Investigation' : 'Save New Investigation'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
