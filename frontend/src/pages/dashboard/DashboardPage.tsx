import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  LineChart as LineChartIcon,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../../services/api';
import { DashboardMetrics, LineCardInfo, QualityAlert } from '../../types';
import { StatCard } from '../../components/StatCard';
import { StatusBadge } from '../../components/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const DashboardPage: React.FC = () => {
  const { selectedLine, refreshAlertsCount, demoMode, user } = useAuth();
  const { showToast } = useToast();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [lines, setLines] = useState<LineCardInfo[]>([]);
  const [rejectionTrends, setRejectionTrends] = useState<any[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<QualityAlert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState<boolean>(false);
  const [confirmSeed, setConfirmSeed] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, alerts] = await Promise.all([
        api.getDashboardSummary(selectedLine),
        api.getAlerts(selectedLine !== 'ALL' ? selectedLine : undefined),
      ]);
      setMetrics(data.metrics);
      setLines(data.lines);
      setRejectionTrends(data.rejection_trends);
      setRecentAlerts(alerts.slice(0, 5));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load dashboard summary';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedLine]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSeedData = async () => {
    setSeeding(true);
    try {
      await api.seedData(true);
      await loadData();
      await refreshAlertsCount();
      setConfirmSeed(false);
      showToast('Demo dataset refreshed for lines D1–D4.', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Error resetting demo dataset', 'error');
    } finally {
      setSeeding(false);
    }
  };

  const filteredLines = selectedLine === 'ALL' ? lines : lines.filter(l => l.line_code === selectedLine);
  const canSeedDemo = demoMode && user && ['admin', 'quality_manager'].includes(user.role);
  const highestScrapLine = [...lines].sort((a, b) => b.rejection_rate - a.rejection_rate)[0];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-black text-slate-800 tracking-tight">FOUNDRY QUALITY 4.0 OVERVIEW</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700 tracking-wider">
              REAL-TIME SPC
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Integrated Digital Sand Testing, Process Capability &amp; Downstream Rejection Analytics for Lines D1, D2, D3 &amp; D4.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => loadData()}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {canSeedDemo && (
            <button
              type="button"
              onClick={() => setConfirmSeed(true)}
              disabled={seeding}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              {seeding ? 'Resetting...' : 'Reset Demo Data'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center justify-between text-xs text-rose-800">
          <span>{error}</span>
          <button type="button" onClick={loadData} className="px-3 py-1 bg-rose-600 text-white font-bold rounded-lg">
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Tests Conforming"
          value={metrics ? `${metrics.conforming_percentage}%` : '--'}
          subtext={`Past 7 Days (${metrics?.total_tests_week ?? 0} tests)`}
          icon={CheckCircle2}
          color="emerald"
          trend="up"
          trendText="Within Tolerance"
        />
        <StatCard
          title="Scrap / Rejection Rate"
          value={metrics ? `${metrics.overall_rejection_rate}%` : '--'}
          subtext={`Rejected: ${metrics?.total_rejected_qty ?? 0} / Inspected: ${metrics?.total_inspected_qty ?? 0}`}
          icon={TrendingDown}
          color={Number(metrics?.overall_rejection_rate || 0) > 3.0 ? 'rose' : 'blue'}
        />
        <StatCard
          title="Open Quality Alerts"
          value={metrics?.open_alerts ?? 0}
          subtext="Nelson rules & spec violations"
          icon={AlertTriangle}
          color={(metrics?.open_alerts || 0) > 0 ? 'rose' : 'emerald'}
        />
        <StatCard
          title="Customer Complaints"
          value={metrics?.active_complaints ?? 0}
          subtext="Active 8D CAPA investigations"
          icon={ShieldCheck}
          color="amber"
        />
      </div>

      {/* Production Lines Status Cards (D1, D2, D3, D4) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-slate-800 tracking-wider uppercase">
            Production Lines Quality Status
          </h2>
          <span className="text-xs text-slate-500 font-medium">Automatic Green Sand Molding Plants</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {filteredLines.map(line => (
            <div
              key={line.line_code}
              className={`bg-white rounded-xl border p-4 shadow-xs transition-all hover:shadow-md ${
                line.health === 'CRITICAL'
                  ? 'border-rose-300 ring-1 ring-rose-200'
                  : line.health === 'WARNING'
                  ? 'border-amber-300'
                  : 'border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg bg-slate-900 text-white font-black text-sm flex items-center justify-center">
                    {line.line_code}
                  </span>
                  <div>
                    <div className="font-bold text-slate-800 text-xs">{line.molding_line}</div>
                    <div className="text-[10px] text-slate-400 font-medium">Muller Plant Active</div>
                  </div>
                </div>
                <StatusBadge status={line.health} size="sm" />
              </div>

              <div className="space-y-2 py-2 border-y border-slate-100 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>7-Day Scrap Rate:</span>
                  <span className={`font-bold tabular-nums ${line.rejection_rate > 3.0 ? 'text-rose-600' : 'text-slate-800'}`}>
                    {line.rejection_rate}%
                  </span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Open Alerts:</span>
                  <span className={`font-bold tabular-nums ${line.open_alerts > 0 ? 'text-rose-600' : 'text-slate-800'}`}>
                    {line.open_alerts}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Latest Test:</span>
                  <StatusBadge status={line.latest_test_status} size="sm" />
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between pt-1">
                <Link
                  to={`/spc/charts?line=${line.line_code}`}
                  className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <LineChartIcon className="w-3.5 h-3.5" />
                  View SPC
                </Link>
                <Link
                  to={`/sand-tests/entry?line=${line.line_code}`}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-0.5"
                >
                  Log Test <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Charts & Feeds Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rejection Trends Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800 tracking-wider uppercase">
                14-Day Line Scrap Rate Trend (%)
              </h3>
              <p className="text-xs text-slate-400">Comparing casting defect percentages across lines D1, D2, D3, D4</p>
            </div>
            <Link to="/rejections" className="text-xs font-semibold text-blue-600 hover:text-blue-800">
              Details &rarr;
            </Link>
          </div>

          <div className="h-64">
            {rejectionTrends.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No rejection trend records in the last 14 days.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rejectionTrends} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => String(d).slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#1e293b',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '11px',
                    }}
                    formatter={(val: any) => [`${val}%`, 'Scrap Rate']}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line type="monotone" dataKey="D1" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="D2" stroke="#e11d48" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="D3" stroke="#d97706" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="D4" stroke="#059669" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="mt-2 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <b>Live Line Summary:</b>{' '}
            {highestScrapLine
              ? `Line ${highestScrapLine.line_code} currently exhibits the highest 7-day scrap rate (${highestScrapLine.rejection_rate}%) with ${highestScrapLine.open_alerts} open alert(s). Inspect the Correlation Engine for potential sand parameter associations.`
              : 'All molding lines within baseline telemetry.'}
          </div>
        </div>

        {/* Recent Quality Alerts Feed (1 col) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800 tracking-wider uppercase">
                Active Alerts Feed
              </h3>
              <p className="text-xs text-slate-400">Spec &amp; Nelson Rule Triggers</p>
            </div>
            <Link to="/alerts" className="text-xs font-semibold text-blue-600 hover:text-blue-800">
              View All ({metrics?.open_alerts || 0})
            </Link>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto max-h-[300px]">
            {recentAlerts.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                No active quality alerts. All lines conforming.
              </div>
            ) : (
              recentAlerts.map(alert => (
                <div
                  key={alert.id}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-100/60 transition-colors text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-800 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                      Line {alert.line_code}
                    </span>
                    <StatusBadge status={alert.severity} size="sm" />
                  </div>
                  <p className="text-slate-600 line-clamp-2">{alert.description}</p>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                    <span>{new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <Link to="/alerts" className="text-blue-600 font-bold hover:underline">
                      Acknowledge &rarr;
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Demo Reset */}
      {confirmSeed && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 bg-slate-900/45 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <h3 className="text-sm font-bold text-slate-800 uppercase">Reset Demo Dataset?</h3>
            <p className="text-xs text-slate-600">
              This will regenerate the simulated 30-day foundry dataset for Lines D1–D4 in demo mode.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmSeed(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSeedData}
                disabled={seeding}
                className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
              >
                {seeding ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
