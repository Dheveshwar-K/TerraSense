import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, KeyRound, LogOut, Menu, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';
import { UserRole } from '../types';

interface HeaderProps {
  onOpenMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenMobileMenu }) => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const {
    user,
    demoMode,
    selectedLine,
    setSelectedLine,
    selectedShift,
    setSelectedShift,
    openAlertsCount,
    switchRole,
    refreshAlertsCount,
    logout,
  } = useAuth();

  const [showPwdModal, setShowPwdModal] = useState(false);
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [savingPwd, setSavingPwd] = useState(false);

  const lines = ['ALL', 'D1', 'D2', 'D3', 'D4'];
  const shifts = [
    { num: 1, label: 'Shift 1 (06:00-14:00)' },
    { num: 2, label: 'Shift 2 (14:00-22:00)' },
    { num: 3, label: 'Shift 3 (22:00-06:00)' },
  ];

  const roles: { role: UserRole; label: string }[] = [
    { role: 'operator', label: 'Operator (Shop Floor)' },
    { role: 'quality_engineer', label: 'Quality Engineer (Lead)' },
    { role: 'supervisor', label: 'Production Supervisor' },
    { role: 'quality_manager', label: 'Quality Manager / Admin' },
  ];

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPwd(true);
    try {
      const res = await api.changePassword(currentPwd, newPwd);
      showToast(res.message, 'success');
      setShowPwdModal(false);
      setCurrentPwd('');
      setNewPwd('');
      await logout();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to change password', 'error');
    } finally {
      setSavingPwd(false);
    }
  };

  return (
    <>
      <header className="min-h-16 bg-white/95 backdrop-blur-xs border-b border-slate-200 px-4 lg:px-6 py-2 flex flex-wrap items-center justify-between gap-3 sticky top-0 z-30 shadow-xs">
        {/* Left: Mobile Menu + Production Line & Shift Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onOpenMobileMenu}
            aria-label="Open navigation menu"
            className="lg:hidden p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100"
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Line Selector Buttons */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200" role="group" aria-label="Production Line Filter">
            <span className="text-[11px] font-bold text-slate-500 px-2 tracking-wider">LINE:</span>
            {lines.map(line => (
              <button
                key={line}
                type="button"
                onClick={() => {
                  setSelectedLine(line);
                  refreshAlertsCount(line);
                }}
                aria-pressed={selectedLine === line}
                className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
                  selectedLine === line
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                {line}
              </button>
            ))}
          </div>

          {/* Shift Selector */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="header-shift-select" className="text-[11px] font-bold text-slate-500 tracking-wider">
              SHIFT:
            </label>
            <select
              id="header-shift-select"
              value={selectedShift}
              onChange={e => setSelectedShift(Number(e.target.value))}
              className="text-xs bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              {shifts.map(s => (
                <option key={s.num} value={s.num}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Demo-only Role Switcher, Alerts & User Profile */}
        <div className="flex items-center gap-3">
          {demoMode && (
            <div className="hidden sm:flex items-center gap-2 bg-amber-50 border border-amber-200 px-3 py-1 rounded-lg">
              <Shield className="w-3.5 h-3.5 text-amber-600" />
              <label htmlFor="demo-role-switcher" className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
                Demo Role:
              </label>
              <select
                id="demo-role-switcher"
                value={user?.role || 'quality_manager'}
                onChange={e => switchRole(e.target.value as UserRole)}
                className="text-xs bg-transparent text-amber-900 font-bold focus:outline-none cursor-pointer"
              >
                {roles.map(r => (
                  <option key={r.role} value={r.role}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Alert Bell */}
          <button
            type="button"
            onClick={() => navigate('/alerts')}
            title="Open Quality Alerts Center"
            aria-label={`Open Quality Alerts Center (${openAlertsCount} open alerts)`}
            className="w-9 h-9 rounded-lg border border-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-50 transition-colors relative"
          >
            <Bell className="w-4 h-4" />
            {openAlertsCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 bg-rose-600 text-white rounded-full text-[10px] font-black flex items-center justify-center border-2 border-white shadow-xs tabular-nums">
                {openAlertsCount}
              </span>
            )}
          </button>

          {/* User Card + Password / Sign Out */}
          <div className="flex items-center gap-2.5 pl-2 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-blue-100 border border-blue-200 text-blue-700 font-bold text-xs flex items-center justify-center">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="hidden md:block text-left">
              <div className="text-xs font-bold text-slate-800 leading-tight">{user?.full_name || 'User'}</div>
              <div className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">
                {user?.role?.replace(/_/g, ' ')}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowPwdModal(true)}
              title="Change Password"
              aria-label="Change Password"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
            >
              <KeyRound className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => logout()}
              title="Sign Out"
              aria-label="Sign Out"
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-700 hover:bg-rose-50 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Change Password Modal */}
      {showPwdModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="change-pwd-title"
          className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4"
        >
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 id="change-pwd-title" className="text-sm font-bold text-slate-800 uppercase flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-blue-600" />
                Change Account Password
              </h3>
              <button
                type="button"
                onClick={() => setShowPwdModal(false)}
                aria-label="Close password dialog"
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>
            <form onSubmit={handlePasswordChange} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">Current Password</label>
                <input
                  type="password"
                  required
                  value={currentPwd}
                  onChange={e => setCurrentPwd(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase mb-1">
                  New Password (min 8 chars, letters + numbers)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPwd}
                  onChange={e => setNewPwd(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowPwdModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingPwd}
                  className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 rounded-lg"
                >
                  {savingPwd ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
