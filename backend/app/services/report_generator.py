import io
import csv
from datetime import datetime, timezone
from typing import Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportGenerator:
    """
    Industrial Report Generation Engine.
    Produces IATF 16949 compliant Sand Quality, SPC, Rejection & Audit Reports
    in PDF, Excel (XLSX), and CSV formats.
    """

    @staticmethod
    def generate_csv(headers: list[str], rows: list[list[Any]], title: str = "Quality Report") -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Metadata banner
        writer.writerow([f"# {title}"])
        writer.writerow([f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
        writer.writerow([f"# Foundry Lines: D1, D2, D3, D4 | System: PS-010 Digital Sand Quality"])
        writer.writerow([])
        
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
            
        return output.getvalue().encode("utf-8")

    @staticmethod
    def generate_excel(sheets_data: list[dict[str, Any]], title: str = "Foundry Quality Report") -> bytes:
        """
        sheets_data: list of dicts with:
        {"title": "Sheet Name", "headers": [...], "rows": [[...], ...]}
        """
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # Style definitions
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=9, italic=True, color="64748B")
        regular_font = Font(name="Calibri", size=10)
        border_thin = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        for sheet_spec in sheets_data:
            ws_title = sheet_spec.get("title", "Data")[:31]
            ws = wb.create_sheet(title=ws_title)

            # Title Header
            ws.cell(row=1, column=1, value=f"PS-010 FOUNDRY QUALITY 4.0: {sheet_spec.get('title', title).upper()}").font = title_font
            ws.cell(row=2, column=1, value=f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Lines: D1-D4 | IATF 16949 Audit Ready").font = sub_font

            headers = sheet_spec.get("headers", [])
            rows = sheet_spec.get("rows", [])

            # Write Table Header at Row 4
            for col_idx, h in enumerate(headers, start=1):
                cell = ws.cell(row=4, column=col_idx, value=h)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Write Rows
            start_row = 5
            for r_idx, row_data in enumerate(rows, start=start_row):
                for c_idx, val in enumerate(row_data, start=1):
                    cell = ws.cell(row=r_idx, column=c_idx, value=val)
                    cell.font = regular_font
                    cell.border = border_thin
                    if isinstance(val, (int, float)):
                        cell.alignment = Alignment(horizontal="right")
                    else:
                        cell.alignment = Alignment(horizontal="left")

            # Auto-fit columns
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.row >= 4 and cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def generate_pdf(
        title: str,
        subtitle: str,
        metadata: dict[str, str],
        headers: list[str],
        rows: list[list[Any]],
        summary_kpis: Optional[dict[str, str]] = None
    ) -> bytes:
        """
        Generates a publication-grade PDF report using ReportLab Platypus.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=12
        )
        meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#475569'),
            fontName="Helvetica-Bold"
        )
        meta_val_style = ParagraphStyle(
            'MetaVal',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A')
        )
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )

        elements = []

        # Document Header
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(subtitle, subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=10))

        # Metadata Grid
        if metadata:
            meta_rows = []
            keys = list(metadata.keys())
            for i in range(0, len(keys), 3):
                row_cells = []
                for k in keys[i:i+3]:
                    txt = f"<b>{k}:</b> {metadata[k]}"
                    row_cells.append(Paragraph(txt, meta_val_style))
                while len(row_cells) < 3:
                    row_cells.append(Paragraph("", meta_val_style))
                meta_rows.append(row_cells)

            meta_table = Table(meta_rows, colWidths=[240, 240, 240])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 12))

        # Summary KPIs if provided
        if summary_kpis:
            kpi_cells = []
            for k, v in summary_kpis.items():
                p = Paragraph(f"<b>{k}</b><br/><font size=12 color='#1E3A8A'><b>{v}</b></font>", meta_val_style)
                kpi_cells.append(p)
            
            kpi_table = Table([kpi_cells])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BFDBFE')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BFDBFE')),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(kpi_table)
            elements.append(Spacer(1, 14))

        # Main Data Table
        table_data = []
        # Header row
        table_data.append([Paragraph(f"<b>{h}</b>", ParagraphStyle('TH', parent=table_cell_style, fontName='Helvetica-Bold', textColor=colors.white)) for h in headers])
        
        # Rows (limit to first 45 rows to prevent giant multi-page overflows in one view)
        display_rows = rows[:50]
        for r in display_rows:
            table_data.append([Paragraph(str(cell), table_cell_style) for cell in r])

        num_cols = len(headers)
        avail_width = 720.0
        col_width = avail_width / max(num_cols, 1)

        main_table = Table(table_data, colWidths=[col_width] * num_cols, repeatRows=1)
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(main_table)

        # Compliance Sign-off Block
        elements.append(Spacer(1, 20))
        sign_block = [
            [
                Paragraph("<b>Prepared By:</b> Quality Lab Inspector", meta_val_style),
                Paragraph("<b>Reviewed By:</b> Quality Assurance Lead", meta_val_style),
                Paragraph("<b>Approved By:</b> Plant Quality Manager", meta_val_style)
            ],
            [
                Paragraph("Sign: ___________________", meta_val_style),
                Paragraph("Sign: ___________________", meta_val_style),
                Paragraph("Sign: ___________________", meta_val_style)
            ]
        ]
        sign_table = Table(sign_block, colWidths=[240, 240, 240])
        sign_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sign_table)

        doc.build(elements)
        return buffer.getvalue()
