import React, { useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { LoginScreen } from './components/LoginScreen';

// Pages
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { SandTestEntryPage } from './pages/sand-tests/SandTestEntryPage';
import { HourlyMonitoringPage } from './pages/sand-tests/HourlyMonitoringPage';
import { ChemicalTestsPage } from './pages/sand-tests/ChemicalTestsPage';
import { SandBatchPage } from './pages/sand-tests/SandBatchPage';
import { SpecificationsPage } from './pages/specifications/SpecificationsPage';
import { SPCAnalyticsPage } from './pages/spc/SPCAnalyticsPage';
import { ProcessCapabilityPage } from './pages/spc/ProcessCapabilityPage';
import { RejectionAnalyticsPage } from './pages/rejections/RejectionAnalyticsPage';
import { DefectParetoPage } from './pages/rejections/DefectParetoPage';
import { CorrelationPage } from './pages/correlations/CorrelationPage';
import { RootCausePage } from './pages/root-cause/RootCausePage';
import { ComplaintsPage } from './pages/complaints/ComplaintsPage';
import { AlertsPage } from './pages/alerts/AlertsPage';
import { ReportsPage } from './pages/reports/ReportsPage';
import { AuditTrailPage } from './pages/audit/AuditTrailPage';
import { UserManagementPage } from './pages/users/UserManagementPage';

const RoleGuard: React.FC<{ allowedRoles: string[]; children: React.ReactNode }> = ({
  allowedRoles,
  children,
}) => {
  const { user } = useAuth();
  if (!user || !allowedRoles.includes(user.role)) {
    return (
      <div className="max-w-xl mx-auto mt-12 bg-white rounded-xl border border-rose-200 p-6 shadow-xs text-center space-y-2">
        <ShieldAlert className="w-8 h-8 text-rose-600 mx-auto" />
        <h2 className="text-sm font-bold text-slate-800 uppercase">Access Restricted</h2>
        <p className="text-xs text-slate-600">
          Your current role (<b>{user?.role?.replace(/_/g, ' ')}</b>) does not have permission to access this module.
        </p>
      </div>
    );
  }
  return <>{children}</>;
};

const AppShell: React.FC = () => {
  const { user, loading, demoMode } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="bg-white px-6 py-4 rounded-xl border border-slate-200 shadow-xs text-xs font-bold text-slate-600 tracking-wider uppercase">
          Initializing TerraSense PS-010 Quality 4.0...
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-100/80 font-sans text-slate-900 antialiased">
        <Sidebar mobileOpen={mobileMenuOpen} onCloseMobile={() => setMobileMenuOpen(false)} />

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {demoMode && (
            <div className="bg-amber-500 text-slate-950 text-[11px] font-bold px-4 py-1 text-center tracking-wide">
              DEMO ENVIRONMENT ACTIVE — Simulated foundry dataset for Lines D1–D4. Not for live production sign-off.
            </div>
          )}

          <Header onOpenMobileMenu={() => setMobileMenuOpen(true)} />

          <main className="flex-1 overflow-y-auto p-4 sm:p-6">
            <Routes>
              {/* 1. Dashboard */}
              <Route path="/" element={<DashboardPage />} />

              {/* 2. Sand Quality Lab */}
              <Route path="/sand-tests/entry" element={<SandTestEntryPage />} />
              <Route path="/sand-tests/hourly" element={<HourlyMonitoringPage />} />
              <Route path="/sand-tests/chemical" element={<ChemicalTestsPage />} />
              <Route path="/sand-tests/batches" element={<SandBatchPage />} />
              <Route path="/specifications" element={<SpecificationsPage />} />

              {/* 3. Statistical Process Control (SPC) */}
              <Route path="/spc/charts" element={<SPCAnalyticsPage />} />
              <Route path="/spc/capability" element={<ProcessCapabilityPage />} />

              {/* 4. Casting Rejections & Pareto */}
              <Route path="/rejections" element={<RejectionAnalyticsPage />} />
              <Route path="/rejections/pareto" element={<DefectParetoPage />} />
              <Route path="/correlations" element={<CorrelationPage />} />
              <Route path="/root-cause" element={<RootCausePage />} />

              {/* 5. Customer Complaints & 8D CAPA */}
              <Route path="/complaints" element={<ComplaintsPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route
                path="/reports"
                element={
                  <RoleGuard allowedRoles={['quality_engineer', 'supervisor', 'quality_manager', 'admin']}>
                    <ReportsPage />
                  </RoleGuard>
                }
              />
              <Route
                path="/audit-trail"
                element={
                  <RoleGuard allowedRoles={['quality_engineer', 'supervisor', 'quality_manager', 'admin']}>
                    <AuditTrailPage />
                  </RoleGuard>
                }
              />
              <Route
                path="/users"
                element={
                  <RoleGuard allowedRoles={['admin', 'quality_manager']}>
                    <UserManagementPage />
                  </RoleGuard>
                }
              />

              {/* Catch all fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
