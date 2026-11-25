import React, { useEffect, useState } from 'react';
import { CheckCircle2, FileSpreadsheet, FileText, Table } from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

export const ReportsPage: React.FC = () => {
  const { selectedLine } = useAuth();
  const { showToast } = useToast();
  const [reportType, setReportType] = useState<string>('SAND_TEST_SHEET');
  const [lineCode, setLineCode] = useState<string>(selectedLine);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    setLineCode(selectedLine);
  }, [selectedLine]);

  const reportTypes = [
    {
      id: 'SAND_TEST_SHEET',
      title: 'Hourly Sand Test Log Sheet',
      desc: 'Complete physical sand measurements with specification conformity and operator stamps.',
    },
    {
      id: 'REJECTION_PARETO',
      title: 'Casting Rejection & Defect Report',
      desc: 'Shift-wise scrap piece counts, scrap percentages, and Pareto rankings.',
    },
    {
      id: 'AUDIT_TRAIL',
      title: 'IATF 16949 Digital Audit Trail',
      desc: 'Hash-chained log of user modifications, specification revisions, and test approvals.',
    },
    {
      id: 'COMPLAINTS',
      title: 'Customer Complaints & 8D CAPA Log',
      desc: 'Customer quality claims, 8D containment, root cause verification, and closure notes.',
    },
  ];

  const handleExport = async (fmt: 'pdf' | 'excel' | 'csv') => {
    if (downloading) return;
    setDownloading(fmt);
    try {
      await api.downloadReport(reportType, fmt, lineCode, startDate || undefined, endDate || undefined);
      showToast(`Exported ${reportType} as ${fmt.toUpperCase()}.`, 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to generate report', 'error');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            QUALITY REPORTS &amp; AUDIT EXPORT CENTER
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Export timestamped IATF-ready documentation in PDF, Excel (.xlsx), and RFC-compliant CSV formats via authenticated downloads.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
            {['ALL', 'D1', 'D2', 'D3', 'D4'].map(code => (
              <button
                key={code}
                type="button"
                onClick={() => setLineCode(code)}
                className={`px-2.5 py-1 text-xs font-bold rounded transition-colors ${lineCode === code ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
              >
                Line {code}
              </button>
            ))}
          </div>
          <input
            type="date"
            aria-label="Report start date"
            value={startDate}
            onChange={e => setStartDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />
          <input
            type="date"
            aria-label="Report end date"
            value={endDate}
            onChange={e => setEndDate(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reportTypes.map(rt => (
          <button
            key={rt.id}
            type="button"
            onClick={() => setReportType(rt.id)}
            className={`text-left p-5 rounded-xl border cursor-pointer transition-all shadow-xs ${reportType === rt.id
                ? 'bg-blue-50/40 border-blue-400 ring-2 ring-blue-100'
                : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-slate-800">{rt.title}</span>
              {reportType === rt.id && <CheckCircle2 className="w-5 h-5 text-blue-600" />}
            </div>
            <p className="text-xs text-slate-500">{rt.desc}</p>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Download Selected Report: {reportTypes.find(r => r.id === reportType)?.title}
            </h2>
            <p className="text-xs text-slate-500">Facility: Foundry Lines {lineCode} | System: PS-010 Quality 4.0</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <button
            type="button"
            onClick={() => handleExport('pdf')}
            disabled={Boolean(downloading)}
            className="p-5 rounded-xl border border-rose-200 bg-rose-50/50 hover:bg-rose-50 disabled:opacity-60 transition-all flex flex-col items-center justify-center gap-2 text-rose-800 shadow-xs group"
          >
            <FileText className="w-8 h-8 text-rose-600 group-hover:scale-110 transition-transform" />
            <div className="font-bold text-xs uppercase tracking-wider">
              {downloading === 'pdf' ? 'Generating PDF...' : 'Publication PDF Document'}
            </div>
            <span className="text-[10px] text-slate-500 text-center">Styled report with compliance signatures</span>
          </button>

          <button
            type="button"
            onClick={() => handleExport('excel')}
            disabled={Boolean(downloading)}
            className="p-5 rounded-xl border border-emerald-200 bg-emerald-50/50 hover:bg-emerald-50 disabled:opacity-60 transition-all flex flex-col items-center justify-center gap-2 text-emerald-800 shadow-xs group"
          >
            <FileSpreadsheet className="w-8 h-8 text-emerald-600 group-hover:scale-110 transition-transform" />
            <div className="font-bold text-xs uppercase tracking-wider">
              {downloading === 'excel' ? 'Generating XLSX...' : 'Excel Workbook (.XLSX)'}
            </div>
            <span className="text-[10px] text-slate-500 text-center">Formula-safe formatted spreadsheet</span>
          </button>

          <button
            type="button"
            onClick={() => handleExport('csv')}
            disabled={Boolean(downloading)}
            className="p-5 rounded-xl border border-blue-200 bg-blue-50/50 hover:bg-blue-50 disabled:opacity-60 transition-all flex flex-col items-center justify-center gap-2 text-blue-800 shadow-xs group"
          >
            <Table className="w-8 h-8 text-blue-600 group-hover:scale-110 transition-transform" />
            <div className="font-bold text-xs uppercase tracking-wider">
              {downloading === 'csv' ? 'Generating CSV...' : 'Raw Comma-Separated (CSV)'}
            </div>
            <span className="text-[10px] text-slate-500 text-center">RFC 4180 format for data pipelines</span>
          </button>
        </div>
      </div>
    </div>
  );
};