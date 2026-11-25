import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  RotateCcw,
  Save,
} from 'lucide-react';
import { api } from '../../services/api';
import { Parameter } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const SandTestEntryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedLine, selectedShift, refreshAlertsCount } = useAuth();
  const { showToast } = useToast();

  const [lineCode, setLineCode] = useState<string>(
    searchParams.get('line') || (selectedLine !== 'ALL' ? selectedLine : 'D1')
  );
  const [shift, setShift] = useState<number>(selectedShift || 1);
  const [testDate, setTestDate] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [testHour, setTestHour] = useState<number>(() => Math.max(1, Math.min(24, new Date().getHours() || 1)));
  const [batchNumber, setBatchNumber] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  const [parameters, setParameters] = useState<Parameter[]>([]);
  const [values, setValues] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    const loadParams = async () => {
      setLoading(true);
      try {
        const data = await api.getParameters('PHYSICAL', 'HOURLY');
        if (!active) return;
        setParameters(data);
        const initial: Record<number, string> = {};
        data.forEach(p => {
          initial[p.id] = p.target_value.toString();
        });
        setValues(initial);
      } catch (err: unknown) {
        if (active) {
          showToast(err instanceof Error ? err.message : 'Failed to load parameters', 'error');
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    loadParams();
    return () => {
      active = false;
    };
  }, [showToast]);

  useEffect(() => {
    setBatchNumber(`BAT-${lineCode}-${testDate.replace(/-/g, '')}-S${shift}`);
  }, [lineCode, testDate, shift]);

  const handleValueChange = (paramId: number, val: string) => {
    setValues(prev => ({ ...prev, [paramId]: val }));
  };

  const getValidationState = (param: Parameter, valStr: string) => {
    if (!valStr.trim() || isNaN(Number(valStr))) {
      return { status: 'EMPTY', text: 'Required', color: 'text-slate-600 bg-slate-100 border-slate-200' };
    }
    const num = Number(valStr);
    if (
      (param.data_validation_min !== undefined && num < param.data_validation_min) ||
      (param.data_validation_max !== undefined && num > param.data_validation_max)
    ) {
      return {
        status: 'INVALID_SENSOR',
        text: `Sensor Range (${param.data_validation_min}–${param.data_validation_max})`,
        color: 'text-rose-700 bg-rose-100 border-rose-400',
      };
    }
    if (param.usl !== undefined && num > param.usl) {
      return { status: 'OUT_OF_SPEC', text: `Exceeds USL (${param.usl})`, color: 'text-rose-600 bg-rose-50 border-rose-300' };
    }
    if (param.lsl !== undefined && num < param.lsl) {
      return { status: 'OUT_OF_SPEC', text: `Below LSL (${param.lsl})`, color: 'text-rose-600 bg-rose-50 border-rose-300' };
    }
    if (
      (param.usl !== undefined && num > param.usl - 0.15 * (param.usl - param.lsl)) ||
      (param.lsl !== undefined && num < param.lsl + 0.15 * (param.usl - param.lsl))
    ) {
      return { status: 'WARNING', text: 'Near Spec Margin', color: 'text-amber-600 bg-amber-50 border-amber-300' };
    }
    return { status: 'OK', text: 'In Spec', color: 'text-emerald-600 bg-emerald-50 border-emerald-300' };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setFeedback(null);

    for (const p of parameters) {
      const raw = values[p.id];
      const num = Number(raw);
      if (raw === undefined || raw.trim() === '' || !Number.isFinite(num)) {
        setFeedback({ type: 'error', message: `Please enter a valid numeric value for ${p.name}.` });
        return;
      }
      if (p.data_validation_min !== undefined && num < p.data_validation_min) {
        setFeedback({
          type: 'error',
          message: `${p.name} value (${num}) is below physical sensor limit (${p.data_validation_min}).`,
        });
        return;
      }
      if (p.data_validation_max !== undefined && num > p.data_validation_max) {
        setFeedback({
          type: 'error',
          message: `${p.name} value (${num}) exceeds physical sensor limit (${p.data_validation_max}).`,
        });
        return;
      }
    }

    setSubmitting(true);
    try {
      const payloadValues = parameters.map(p => ({
        parameter_id: p.id,
        measured_value: Number(values[p.id]),
      }));

      const res = await api.createSandTest({
        line_code: lineCode,
        test_type: 'HOURLY_PHYSICAL',
        test_date: testDate,
        shift,
        test_hour: testHour,
        batch_number: batchNumber,
        notes,
        values: payloadValues,
      });

      const msg = `Sand test #${res.test_number} saved (${res.status}). SPC rules evaluated.`;
      setFeedback({ type: 'success', message: msg });
      showToast(msg, 'success');
      await refreshAlertsCount();
      setTestHour(h => (h >= 24 ? 1 : h + 1));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit test entry.';
      setFeedback({ type: 'error', message: msg });
      showToast(msg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-blue-600" />
            DIGITAL SAND TEST ENTRY (SHOP FLOOR TABLET)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Hourly physical green sand parameter verification with instant tolerance limit validation and duplicate prevention.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 rounded text-slate-600 border border-slate-200 flex items-center gap-1.5 tabular-nums">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            Hour {testHour}:00
          </span>
        </div>
      </div>

      {feedback && (
        <div
          role={feedback.type === 'error' ? 'alert' : 'status'}
          className={`p-4 rounded-xl border flex items-start gap-3 ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
              : 'bg-rose-50 border-rose-300 text-rose-800'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          )}
          <div className="text-xs font-medium">{feedback.message}</div>
        </div>
      )}

      {/* Main Entry Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label htmlFor="entry-line" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Molding Line
            </label>
            <select
              id="entry-line"
              value={lineCode}
              onChange={e => setLineCode(e.target.value)}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
            >
              <option value="D1">Line D1 (Automotive Engine Blocks)</option>
              <option value="D2">Line D2 (Transmission Housings)</option>
              <option value="D3">Line D3 (Hydraulic Pumps)</option>
              <option value="D4">Line D4 (Valve Bodies)</option>
            </select>
          </div>

          <div>
            <label htmlFor="entry-shift" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Shift
            </label>
            <select
              id="entry-shift"
              value={shift}
              onChange={e => setShift(Number(e.target.value))}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Shift 1 (06:00 - 14:00)</option>
              <option value={2}>Shift 2 (14:00 - 22:00)</option>
              <option value={3}>Shift 3 (22:00 - 06:00)</option>
            </select>
          </div>

          <div>
            <label htmlFor="entry-date" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Test Date
            </label>
            <input
              id="entry-date"
              type="date"
              required
              value={testDate}
              onChange={e => setTestDate(e.target.value)}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="entry-hour" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Test Hour (1–24)
            </label>
            <input
              id="entry-hour"
              type="number"
              min={1}
              max={24}
              required
              value={testHour}
              onChange={e => setTestHour(Number(e.target.value))}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 tabular-nums"
            />
          </div>

          <div>
            <label htmlFor="entry-batch" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
              Sand Batch / Muller No.
            </label>
            <input
              id="entry-batch"
              type="text"
              value={batchNumber}
              onChange={e => setBatchNumber(e.target.value)}
              placeholder="e.g. BAT-D1-01"
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Parameters Input Grid */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-800 tracking-wider uppercase">
              Physical Sand Measurements
            </h2>
            <span className="text-xs text-slate-500">Values are compared to engineering specifications (LSL &amp; USL)</span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-slate-400">Loading active test parameters...</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {parameters.map(param => {
                const val = values[param.id] || '';
                const validation = getValidationState(param, val);
                const inputId = `param-input-${param.id}`;

                return (
                  <div
                    key={param.id}
                    className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <label htmlFor={inputId} className="cursor-pointer">
                        <span className="text-xs font-bold text-slate-800 block">{param.name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {param.code} ({param.unit})
                        </span>
                      </label>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${validation.color}`}>
                        {validation.text}
                      </span>
                    </div>

                    <div className="relative">
                      <input
                        id={inputId}
                        type="number"
                        step="any"
                        value={val}
                        onChange={e => handleValueChange(param.id, e.target.value)}
                        required
                        className="w-full text-lg font-black text-slate-900 bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-right tracking-tight focus:ring-2 focus:ring-blue-500 focus:outline-none tabular-nums"
                      />
                      <span className="absolute left-3 top-3 text-xs font-semibold text-slate-400 pointer-events-none">
                        {param.unit}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium pt-1 tabular-nums">
                      <span>
                        LSL: <b className="text-slate-700">{param.lsl}</b>
                      </span>
                      <span>
                        Target: <b className="text-blue-600">{param.target_value}</b>
                      </span>
                      <span>
                        USL: <b className="text-slate-700">{param.usl}</b>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="pt-2">
            <label htmlFor="entry-notes" className="block text-xs font-bold text-slate-600 uppercase mb-1">
              Shop Floor Notes / Observations
            </label>
            <textarea
              id="entry-notes"
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="e.g. Added 5L temper water at muller. Ambient temp high (38°C)."
              className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => {
              const resetVals: Record<number, string> = {};
              parameters.forEach(p => {
                resetVals[p.id] = p.target_value.toString();
              });
              setValues(resetVals);
            }}
            className="px-4 py-2.5 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition-colors flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Targets
          </button>

          <button
            type="submit"
            disabled={submitting || loading}
            className="px-6 py-2.5 text-xs font-black uppercase tracking-wider text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {submitting ? 'Submitting Test...' : 'Save & Evaluate SPC'}
          </button>
        </div>
      </form>
    </div>
  );
};
