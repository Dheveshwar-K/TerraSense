import React, { useCallback, useEffect, useState } from 'react';
import { Check, Plus, RefreshCw, Users, X } from 'lucide-react';
import { api } from '../../services/api';
import { User, UserRole } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { StatusBadge } from '../../components/StatusBadge';

export const UserManagementPage: React.FC = () => {
  const { user: currentUser, demoMode, switchRole } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<UserRole>('operator');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load user directory', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await api.createUser({
        username: username.trim(),
        email: email.trim(),
        full_name: fullName.trim(),
        role,
        password,
      });
      showToast(`Provisioned user '${username.trim()}' (${role}).`, 'success');
      setShowCreateModal(false);
      setUsername('');
      setEmail('');
      setFullName('');
      setPassword('');
      await loadUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to create user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (target: User) => {
    try {
      await api.updateUser(target.id, { is_active: !target.is_active });
      showToast(
        `${target.username} ${!target.is_active ? 'reactivated' : 'deactivated'}.`,
        'success'
      );
      await loadUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to update user status', 'error');
    }
  };

  const permissionsMatrix = [
    { feature: 'Enter Hourly & Chemical Sand Test Results', operator: true, qe: true, super: true, admin: true },
    { feature: 'Request Test Measurement Correction', operator: true, qe: true, super: true, admin: true },
    { feature: 'Approve / Reject Data Corrections', operator: false, qe: true, super: false, admin: true },
    { feature: 'Configure Parameter Specifications (USL/LSL)', operator: false, qe: true, super: false, admin: true },
    { feature: 'Analyze Real-Time SPC Charts & Correlation Engine', operator: true, qe: true, super: true, admin: true },
    { feature: 'Log Casting Rejection Lots & Scrap Records', operator: false, qe: true, super: true, admin: true },
    { feature: 'Create & Update 5-Why / Ishikawa Investigations', operator: false, qe: true, super: true, admin: true },
    { feature: 'Update 8D Customer Complaint CAPA Dossiers', operator: false, qe: true, super: false, admin: true },
    { feature: 'Acknowledge Process Deviation Alerts', operator: true, qe: true, super: true, admin: true },
    { feature: 'Resolve & Close Quality Alerts', operator: false, qe: true, super: false, admin: true },
    { feature: 'Generate & Export Official PDF/Excel/CSV Reports', operator: false, qe: true, super: true, admin: true },
    { feature: 'Inspect & Verify IATF 16949 Hash-Chained Audit Trail', operator: false, qe: true, super: true, admin: true },
    { feature: 'Provision & Manage User Accounts / Roles', operator: false, qe: false, super: false, admin: true },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            ROLE-BASED ACCESS CONTROL (RBAC) &amp; USER DIRECTORY
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Backend-enforced foundry operational permissions and user lifecycle governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => loadUsers()}
            aria-label="Refresh users"
            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            Provision User
          </button>
        </div>
      </div>

      {/* Live Database User Accounts Directory */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {users.map(u => {
          const isCurrent = currentUser?.username === u.username;
          return (
            <div
              key={u.id}
              className={`p-4 rounded-xl border transition-all shadow-xs ${
                isCurrent ? 'bg-blue-50/50 border-blue-400 ring-2 ring-blue-100' : 'bg-white border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-black text-xs flex items-center justify-center">
                  {u.full_name.charAt(0)}
                </span>
                <div className="flex items-center gap-1.5">
                  <StatusBadge status={u.is_active ? 'OK' : 'CRITICAL'} size="sm" />
                  {isCurrent && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-600 text-white">YOU</span>
                  )}
                </div>
              </div>
              <div className="font-bold text-slate-800 text-xs">{u.full_name}</div>
              <div className="text-[11px] font-mono text-blue-600 font-semibold">
                @{u.username} &bull; {u.role}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">{u.email}</div>

              <div className="mt-4 pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                {!isCurrent && (
                  <button
                    type="button"
                    onClick={() => handleToggleActive(u)}
                    className={`px-2.5 py-1 text-[11px] font-bold rounded transition-colors ${
                      u.is_active
                        ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                        : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200'
                    }`}
                  >
                    {u.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                )}
                {demoMode && !isCurrent && (
                  <button
                    type="button"
                    onClick={() => switchRole(u.role)}
                    className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 font-bold text-[11px] rounded transition-colors ml-auto"
                  >
                    Demo Switch
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Permissions Matrix */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Operational Role Permissions Matrix</h2>
          <span className="text-xs text-slate-500">Backend-Enforced RBAC Policy</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-bold">System Capability / Operation</th>
                <th className="px-4 py-3 font-bold text-center">Operator</th>
                <th className="px-4 py-3 font-bold text-center">Quality Engineer</th>
                <th className="px-4 py-3 font-bold text-center">Supervisor</th>
                <th className="px-4 py-3 font-bold text-center">Quality Manager / Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {permissionsMatrix.map((p, idx) => (
                <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-4 py-2.5 text-slate-800 font-semibold">{p.feature}</td>
                  <td className="px-4 py-2.5 text-center">
                    {p.operator ? <Check className="w-4 h-4 text-emerald-600 mx-auto" /> : <X className="w-4 h-4 text-slate-300 mx-auto" />}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {p.qe ? <Check className="w-4 h-4 text-emerald-600 mx-auto" /> : <X className="w-4 h-4 text-slate-300 mx-auto" />}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {p.super ? <Check className="w-4 h-4 text-emerald-600 mx-auto" /> : <X className="w-4 h-4 text-slate-300 mx-auto" />}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {p.admin ? <Check className="w-4 h-4 text-emerald-600 mx-auto" /> : <X className="w-4 h-4 text-slate-300 mx-auto" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision User Modal */}
      {showCreateModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase">Provision New User Account</h3>
              <button type="button" onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  minLength={2}
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Username</label>
                  <input
                    type="text"
                    required
                    minLength={3}
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-600 uppercase mb-1">Role</label>
                  <select value={role} onChange={e => setRole(e.target.value as UserRole)} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2">
                    <option value="operator">Operator</option>
                    <option value="quality_engineer">Quality Engineer</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="quality_manager">Quality Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-600 uppercase mb-1">
                  Initial Password (min 8 chars, letters + numbers)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-3 py-1.5 text-slate-600">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-blue-600 text-white font-bold rounded-lg disabled:opacity-60"
                >
                  {submitting ? 'Provisioning...' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
