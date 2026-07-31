import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import streamlit as st
from database import get_db_connection

def generate_requisition_pdf(req_id):
    """Generate PDF for a specific requisition"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM requisitions WHERE id = ?", (req_id,))
        req = cursor.fetchone()
        if not req:
            conn.close()
            return None, "Requisition not found"
        
        cursor.execute("SELECT * FROM projects WHERE id = ?", (req['project_id'],))
        project = cursor.fetchone()
        
        cursor.execute('''
        SELECT t.*, c.name as category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.requisition_id = ?
        ORDER BY t.sr_no
        ''', (req_id,))
        transactions = cursor.fetchall()
        conn.close()
        
        if not transactions:
            return None, "No transactions found"
        
        ref_no = req['ref_no'] if req['ref_no'] is not None else "N/A"
        status = req['status'] if req['status'] is not None else "DRAFT"
        period_start = req['period_start'][:10] if req['period_start'] is not None else ""
        period_end = req['period_end'][:10] if req['period_end'] is not None else ""
        opening_balance = float(req['opening_balance']) if req['opening_balance'] is not None else 0.0
        closing_balance = float(req['closing_balance']) if req['closing_balance'] is not None else 0.0
        total_amount = float(req['total_amount']) if req['total_amount'] is not None else 0.0
        expense_paid_last = float(req['expense_paid_last_req']) if req['expense_paid_last_req'] is not None else 0.0
        project_name = project['name'] if project and project['name'] is not None else "Unknown"
        project_code = project['code'] if project and project['code'] is not None else "N/A"
        
        pdf_filename = f"Requisition_{ref_no}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(os.getcwd(), pdf_filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []
        
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, textColor=colors.darkblue, spaceAfter=6, fontName='Helvetica-Bold')
        story.append(Paragraph("HAJI ABDUL RAHEEM CONSTRUCTION COMPANY", header_style))
        story.append(Spacer(1, 0.1*inch))
        
        info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
        story.append(Paragraph(f"<b>Project:</b> {project_name} ({project_code})", info_style))
        story.append(Paragraph(f"<b>Ref No:</b> {ref_no}", info_style))
        story.append(Spacer(1, 0.2*inch))
        
        req_header_style = ParagraphStyle('ReqHeaderStyle', parent=styles['Heading2'], fontSize=14, alignment=TA_CENTER, textColor=colors.darkblue, spaceAfter=6, fontName='Helvetica-Bold')
        story.append(Paragraph("REQUISITION FORM FOR SITE WORK DONE", req_header_style))
        story.append(Spacer(1, 0.1*inch))
        
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER)
        story.append(Paragraph(f"<b>Date:</b> {period_start} <b>To</b> {period_end}", date_style))
        story.append(Spacer(1, 0.1*inch))
        
        info_data = [
            ['Ref No:', ref_no, 'Status:', status],
            ['Period:', f"{period_start} to {period_end}", 'Date:', datetime.now().strftime('%d-%b-%Y')],
            ['Opening Balance:', f"PKR {opening_balance:,.2f}", 'Expense Paid Last:', f"PKR {expense_paid_last:,.2f}"],
            ['Total Amount:', f"PKR {total_amount:,.2f}", 'Closing Balance:', f"PKR {closing_balance:,.2f}"]
        ]
        
        info_table = Table(info_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('BACKGROUND', (0, 1), (1, 1), colors.lightgrey),
            ('BACKGROUND', (0, 2), (1, 2), colors.lightgrey),
            ('BACKGROUND', (0, 3), (1, 3), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (2, 0), (-1, 0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (2, 0), (-1, 0), colors.darkblue),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2*inch))
        
        if status in ["APPROVED", "REJECTED"]:
            stamp_color = colors.green if status == "APPROVED" else colors.red
            stamp_style = ParagraphStyle('StampStyle', parent=styles['Normal'], fontSize=36, alignment=TA_CENTER, textColor=stamp_color, fontName='Helvetica-Bold')
            story.append(Paragraph(f"<font color={stamp_color}><b>{status}</b></font>", stamp_style))
            story.append(Spacer(1, 0.2*inch))
        
        categories = {}
        for trans in transactions:
            cat_name = trans['category_name'] if trans['category_name'] is not None else "Uncategorized"
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(trans)
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ])
        
        for cat_name, trans_list in categories.items():
            cat_style = ParagraphStyle('CatStyle', parent=styles['Heading3'], fontSize=11, textColor=colors.darkblue, fontName='Helvetica-Bold')
            story.append(Paragraph(f"<u>{cat_name}</u>", cat_style))
            story.append(Spacer(1, 0.05*inch))
            
            table_data = [['Sr. #', 'Particulars', 'Qty', 'Market Rate', 'Amount', 'Remarks']]
            for trans in trans_list:
                sr_no = trans['sr_no'] if trans['sr_no'] is not None else 0
                particulars = trans['particulars_raw'] if trans['particulars_raw'] is not None else ""
                qty = float(trans['qty']) if trans['qty'] is not None else 0.0
                rate = float(trans['rate']) if trans['rate'] is not None else 0.0
                amount = float(trans['amount']) if trans['amount'] is not None else 0.0
                remarks = trans['remarks'] if trans['remarks'] is not None else ""
                
                table_data.append([
                    str(sr_no),
                    particulars[:50] + "..." if len(particulars) > 50 else particulars,
                    f"{qty:.2f}" if qty else "",
                    f"{rate:,.2f}" if rate else "",
                    f"{amount:,.2f}",
                    remarks
                ])
            
            subtotal = sum(float(t['amount']) if t['amount'] is not None else 0.0 for t in trans_list)
            table_data.append(['', '', '', '', f"Subtotal: {subtotal:,.2f}", ''])
            
            table = Table(table_data, colWidths=[0.4*inch, 2.5*inch, 0.5*inch, 0.8*inch, 1*inch, 1.5*inch])
            table.setStyle(table_style)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (4, -1), (-1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (4, -1), (-1, -1), colors.darkblue),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.1*inch))
        
        grand_total = sum(float(t['amount']) if t['amount'] is not None else 0.0 for t in transactions)
        total_style = ParagraphStyle('TotalStyle', parent=styles['Heading3'], fontSize=13, alignment=TA_RIGHT, textColor=colors.darkblue, fontName='Helvetica-Bold')
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Total Amount: PKR {grand_total:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Expense Paid Last Req: PKR {expense_paid_last:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Closing Balance: PKR {closing_balance:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=10))
        sig_style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
        ])
        sig_data = [
            ['', '', ''],
            ['<b>Data Entry</b>', '<b>Verifier</b>', '<b>CEO / Approver</b>'],
            ['', '', ''],
            ['Signature: ___________', 'Signature: ___________', 'Signature: ___________'],
            ['Date: _______________', 'Date: _______________', 'Date: _______________'],
            ['Name: _______________', 'Name: _______________', 'Name: _______________'],
        ]
        sig_table = Table(sig_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
        sig_table.setStyle(sig_style)
        story.append(sig_table)
        
        footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("This is a system-generated document. Valid without signature.", footer_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M')}", footer_style))
        
        doc.build(story)
        return pdf_path, None
    except Exception as e:
        return None, str(e)
def generate_project_summary_pdf(project_id):
    """Generate PDF summary for a project"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
            KeepTogether, Image
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import re
        
        # ============================================================
        # CREATE TEMP DIRECTORY IF IT DOESN'T EXIST
        # ============================================================
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Get project data
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT p.*, u.full_name as created_by_name
                FROM projects p
                LEFT JOIN users u ON p.created_by_id = u.id
                WHERE p.id = ?
            ''', (project_id,))
            project = cursor.fetchone()
            
            if not project:
                st.error("Project not found")
                return
            
            # Get requisitions for this project
            cursor.execute('''
                SELECT r.*, u.full_name as created_by_name
                FROM requisitions r
                LEFT JOIN users u ON r.created_by_id = u.id
                WHERE r.project_id = ?
                ORDER BY r.created_at DESC
            ''', (project_id,))
            requisitions = cursor.fetchall()
            
            # Get transactions for this project
            cursor.execute('''
                SELECT 
                    t.*,
                    c.name as category_name,
                    r.ref_no
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN requisitions r ON t.requisition_id = r.id
                WHERE r.project_id = ?
                ORDER BY r.created_at DESC, t.sr_no
            ''', (project_id,))
            transactions = cursor.fetchall()
            
        except Exception as e:
            st.error(f"Error loading project data: {e}")
            return
        finally:
            conn.close()
        
        # ============================================================
        # SANITIZE FILENAME - REMOVE INVALID CHARACTERS
        # ============================================================
        def sanitize_filename(filename):
            """Remove invalid characters from filename"""
            # Replace invalid characters with underscore
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            # Remove any other non-printable characters
            filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
            # Limit filename length
            if len(filename) > 200:
                filename = filename[:200]
            return filename
        
        # Generate filename with sanitized project code
        project_code_sanitized = sanitize_filename(project['code'] or 'project')
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"Project_Summary_{project_code_sanitized}_{date_str}.pdf"
        filepath = os.path.join(temp_dir, filename)
        
        # ============================================================
        # CREATE THE PDF
        # ============================================================
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )
        styles = getSampleStyleSheet()
        story = []
        
        # Add styles
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'],
            fontSize=18, alignment=TA_CENTER, spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e")
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle', parent=styles['Heading2'],
            fontSize=14, alignment=TA_CENTER, spaceAfter=12,
            textColor=colors.HexColor("#444444")
        )
        section_header_style = ParagraphStyle(
            'SectionHeader', parent=styles['Heading3'],
            fontSize=12, spaceBefore=10, spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e")
        )
        body_style = ParagraphStyle(
            'BodySmall', parent=styles['BodyText'],
            fontName="Helvetica", fontSize=9, leading=12
        )
        
        # Title
        story.append(Paragraph("PROJECT SUMMARY REPORT", title_style))
        story.append(Paragraph(project['name'], subtitle_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Project Details
        story.append(Paragraph("<b>Project Details</b>", section_header_style))
        
        details_data = [
            ["Project Code:", project['code'] or "N/A"],
            ["Location:", project['location'] or "N/A"],
            ["Opening Balance:", f"PKR {float(project['opening_balance'] or 0):,.2f}"],
            ["Current Balance:", f"PKR {float(project['current_balance'] or 0):,.2f}"],
            ["Status:", project['status'] or "Active"],
            ["Total Requisitions:", str(len(requisitions) if requisitions else 0)],
            ["Total Transactions:", str(len(transactions) if transactions else 0)],
        ]
        
        details_table = Table(details_data, colWidths=[2.5 * inch, 3.5 * inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F5F5F5")),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Transactions by Category
        if transactions:
            story.append(Paragraph("<b>Transactions by Category</b>", section_header_style))
            
            # Group by category
            category_data = {}
            for t in transactions:
                category = t['category_name'] or "Uncategorized"
                if category not in category_data:
                    category_data[category] = []
                category_data[category].append(t)
            
            category_order = ["Labours", "Materials", "Miscellaneous & Administration"]
            remaining = [c for c in category_data if c not in category_order]
            ordered_categories = [c for c in category_order if c in category_data] + remaining
            
            for category in ordered_categories:
                items = category_data[category]
                cat_total = sum(float(t['amount'] or 0) for t in items)
                
                story.append(Paragraph(
                    f"<b>{category}</b> (Total: PKR {cat_total:,.2f})",
                    ParagraphStyle('CatHeader', parent=styles['Heading4'],
                                 fontSize=11, textColor=colors.HexColor("#37474F"))
                ))
                
                # Create table with only a few columns for summary
                table_data = [["Sr", "Particulars", "Amount"]]
                for item in items[:10]:  # Show first 10 items
                    table_data.append([
                        str(item['sr_no'] or ''),
                        item['particulars_raw'] or '',
                        f"{float(item['amount'] or 0):,.2f}"
                    ])
                
                if len(items) > 10:
                    table_data.append(["", "...", ""])
                
                # Add total row
                table_data.append(["", "Category Total", f"{cat_total:,.2f}"])
                
                t_table = Table(table_data, colWidths=[0.5 * inch, 3.5 * inch, 1.5 * inch])
                t_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#607D8B")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#B0BEC5")),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#ECEFF1")),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('ALIGN', (1, -1), (1, -1), 'RIGHT'),
                    ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
                ]))
                story.append(t_table)
                story.append(Spacer(1, 0.15 * inch))
        
        # Financial Summary
        story.append(Paragraph("<b>Financial Summary</b>", section_header_style))
        
        # Calculate financials
        total_amount = sum(float(t['amount'] or 0) for t in transactions) if transactions else 0
        
        # Get financial data from requisitions
        latest_req = requisitions[0] if requisitions else None
        paid_amount = float(latest_req['paid_amount'] or 0) if latest_req and 'paid_amount' in latest_req.keys() else 0
        rar_bills = float(latest_req['rar_bills'] or 0) if latest_req and 'rar_bills' in latest_req.keys() else 0
        retention_money = float(latest_req['retention_money'] or 0) if latest_req and 'retention_money' in latest_req.keys() else 0
        total_expense = float(latest_req['total_expense'] or 0) if latest_req and 'total_expense' in latest_req.keys() else 0
        profit_loss = float(latest_req['profit_loss'] or 0) if latest_req and 'profit_loss' in latest_req.keys() else 0
        
        balance = total_amount - paid_amount
        total_received = rar_bills + retention_money
        profit = profit_loss if profit_loss else (total_received - total_expense)
        
        summary_data = [
            ["Total Amount", f"PKR {total_amount:,.2f}"],
            ["Paid Amount", f"PKR {paid_amount:,.2f}"],
            ["Balance", f"PKR {balance:,.2f}"],
            ["Amount Received in RAR (Bills)", f"PKR {rar_bills:,.2f}"],
            ["5% Retention Money", f"PKR {retention_money:,.2f}"],
            ["Total Received", f"PKR {total_received:,.2f}"],
            ["Total Expense Made", f"PKR {total_expense:,.2f}"],
            ["PROFIT / LOSS", f"PKR {profit:,.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3.5 * inch, 2.5 * inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F5F5F5")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#C8E6C9") if profit >= 0 else colors.HexColor("#FFCDD2")),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#1B5E20") if profit >= 0 else colors.HexColor("#B71C1C")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(summary_table)
        
        # Build PDF
        doc.build(story)
        
        # Offer download
        with open(filepath, 'rb') as f:
            pdf_data = f.read()
        
        st.download_button(
            label="📥 Download Project Summary",
            data=pdf_data,
            file_name=filename,
            mime="application/pdf"
        )
        
        # Clean up temp file
        try:
            os.remove(filepath)
        except:
            pass
        
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        import traceback
        traceback.print_exc()