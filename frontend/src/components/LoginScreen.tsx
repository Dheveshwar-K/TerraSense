import React, { useState } from 'react';
import { AlertCircle, ArrowRight, Lock, ShieldCheck, User as UserIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

const ROLE_OPTIONS: Array<{ role: UserRole; label: string; defaultUserId: string }> = [
  { role: 'quality_manager', label: 'Quality Manager / Admin', defaultUserId: 'admin' },
  { role: 'quality_engineer', label: 'Quality Engineer (Lead)', defaultUserId: 'quality_engineer' },
  { role: 'supervisor', label: 'Production Supervisor', defaultUserId: 'supervisor' },
  { role: 'operator', label: 'Operator (Shop Floor)', defaultUserId: 'operator' },
];

export const LoginScreen: React.FC = () => {
  const { login, demoMode, switchRole } = useAuth();
  const [selectedRole, setSelectedRole] = useState<UserRole>('quality_manager');
  const [userId, setUserId] = useState('admin');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRoleChange = (role: UserRole) => {
    setSelectedRole(role);
    const match = ROLE_OPTIONS.find(r => r.role === role);
    if (match) {
      setUserId(match.defaultUserId);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedId = userId.trim();
    if (!trimmedId) {
      setError('Please enter a User ID.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (demoMode && !password) {
        // Quick dev/demo entry by Role + User ID without strict password prompt
        await switchRole(selectedRole, trimmedId);
      } else if (demoMode && password) {
        // In dev/demo, try credential login first; if password doesn't match, allow quick demo entry if user chose demo role
        try {
          await login(trimmedId, password);
        } catch {
          await switchRole(selectedRole, trimmedId);
        }
      } else {
        if (!password) {
          setError('Password is required in strict/production mode.');
          return;
        }
        await login(trimmedId, password);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="bg-slate-900 px-6 py-6 text-white border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center font-black text-xl tracking-wider shadow-lg">
              4.0
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight">TERRASENSE PS-010</h1>
              <p className="text-xs text-blue-300 font-medium">
                Digital Sand Quality &amp; Rejection Analytics (Lines D1–D4)
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {error && (
            <div
              role="alert"
              className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-role" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Role
              </label>
              <div className="relative">
                <ShieldCheck className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
                <select
                  id="login-role"
                  value={selectedRole}
                  onChange={e => handleRoleChange(e.target.value as UserRole)}
                  className="w-full pl-9 pr-3 py-2 text-sm font-semibold bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  {ROLE_OPTIONS.map(r => (
                    <option key={r.role} value={r.role}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="login-userid" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                User ID
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="login-userid"
                  type="text"
                  autoComplete="username"
                  required
                  value={userId}
                  onChange={e => setUserId(e.target.value)}
                  placeholder="e.g. operator, quality_engineer, supervisor, admin"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="login-password" className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                Password {demoMode ? <span className="text-slate-400 font-normal">(Optional in local/demo mode)</span> : null}
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required={!demoMode}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={demoMode ? 'Leave blank or enter any password to enter' : 'Enter password'}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-bold text-xs uppercase tracking-wider rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              <span>{submitting ? 'Entering...' : 'Enter Workspace'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
          <span>{demoMode ? 'Quick Local / Demo Entry' : 'Strict Production Auth'}</span>
          <span>PS-010 Quality 4.0</span>
        </div>
      </div>
    </div>
  );
};
