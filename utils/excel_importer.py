"""
Excel Importer Module
Handles importing Excel requisition files into the system.
"""

import pandas as pd
from openpyxl import load_workbook
import re
from datetime import datetime
from database import get_db_connection
import streamlit as st
import io
import os

def import_excel_data(file, user_id):
    """Import Excel file data into database with proper parsing"""
    try:
        df = pd.read_excel(file, header=None)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM categories")
        categories = {c['name']: c['id'] for c in cursor.fetchall()}
        
        project_name = None
        ref_no = None
        period_start = None
        period_end = None
        expense_paid_last = 0
        
        for idx in range(min(10, len(df))):
            if pd.notna(df.iloc[idx, 0]):
                val = str(df.iloc[idx, 0]).strip()
                if "Ref No" in val or "Ref No." in val:
                    parts = val.split("Ref No")
                    if len(parts) > 1:
                        ref_no = parts[-1].strip()
                        if ref_no and ref_no[0] in ['.', ':']:
                            ref_no = ref_no[1:].strip()
                elif "Date" in val and "To" in val:
                    dates = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', val)
                    if len(dates) >= 2:
                        period_start = datetime.strptime(dates[0], '%d-%b-%Y')
                        period_end = datetime.strptime(dates[1], '%d-%b-%Y')
                elif "Expense paid last req" in val or "Expense paid" in val:
                    numbers = re.findall(r'[\d,]+\.?\d*', val)
                    if numbers:
                        expense_paid_last = float(numbers[-1].replace(',', ''))
                elif "CONSTRUCTION" in val.upper():
                    continue
                elif not project_name and idx < 5:
                    project_name = val
                    break
        
        if not project_name:
            project_name = f"Imported Project {datetime.now().strftime('%Y%m%d')}"
        
        if not ref_no:
            ref_no = f"IMP-{datetime.now().strftime('%Y%m%d')}-{hash(str(df)) % 1000:03d}"
        
        if not period_start:
            period_start = datetime.now()
        if not period_end:
            period_end = datetime.now()
        
        cursor.execute("SELECT id, opening_balance FROM projects WHERE name = ?", (project_name,))
        project = cursor.fetchone()
        
        if not project:
            project_code = project_name[:10].upper().replace(" ", "_")
            cursor.execute('''
            INSERT INTO projects (name, code, location, status, opening_balance, current_balance, created_by_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_name, project_code, "Imported", "Active", expense_paid_last, expense_paid_last, user_id))
            project_id = cursor.lastrowid
            opening_balance = expense_paid_last
        else:
            project_id = project['id']
            opening_balance = project['opening_balance'] or 0
        
        cursor.execute('''
        INSERT INTO requisitions 
        (project_id, ref_no, period_start, period_end, opening_balance, closing_balance, 
         expense_paid_last_req, status, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, ref_no, period_start, period_end, opening_balance, opening_balance, 
              expense_paid_last, "DRAFT", user_id))
        
        req_id = cursor.lastrowid
        
        current_category = None
        sr_no = 1
        in_total_section = False
        
        for idx, row in df.iterrows():
            if idx < 3:
                continue
            
            first_val = str(row[0]) if pd.notna(row[0]) else ""
            first_val_lower = first_val.lower().strip()
            
            if "site work" in first_val_lower:
                current_category = "Site Work"
                in_total_section = False
                continue
            elif "materials" in first_val_lower:
                current_category = "Materials"
                in_total_section = False
                continue
            elif "miscellaneous" in first_val_lower or "administration" in first_val_lower:
                current_category = "Miscellaneous & Administration"
                in_total_section = False
                continue
            elif "total" in first_val_lower:
                in_total_section = True
                continue
            elif first_val_lower in ["sr. #", "sr #", "particulars", ""]:
                continue
            
            if in_total_section and "total" in first_val_lower:
                in_total_section = False
                continue
            
            particulars = str(row[1]) if len(row) > 1 and pd.notna(row[1]) else ""
            
            if not particulars or particulars.strip() in ["Sr. #", "Particulars", "Qty", "Market Rate", "Amount", "Remarks"]:
                continue
            
            qty = 0
            rate = 0
            amount = 0
            remarks = ""
            
            if len(row) > 2 and pd.notna(row[2]):
                try:
                    qty = float(str(row[2]).replace(',', ''))
                except:
                    qty = 0
            
            if len(row) > 3 and pd.notna(row[3]):
                try:
                    rate = float(str(row[3]).replace(',', ''))
                except:
                    rate = 0
            
            if len(row) > 4 and pd.notna(row[4]):
                try:
                    amount = float(str(row[4]).replace(',', ''))
                except:
                    amount = 0
            
            if len(row) > 5 and pd.notna(row[5]):
                remarks = str(row[5])
            
            if amount == 0 and qty > 0 and rate > 0:
                amount = qty * rate
            
            if amount == 0 and particulars:
                if len(particulars) > 10 and not any(c.isdigit() for c in particulars[:5]):
                    cursor.execute('''
                    SELECT id FROM transactions 
                    WHERE requisition_id = ? 
                    ORDER BY sr_no DESC LIMIT 1
                    ''', (req_id,))
                    last_trans = cursor.fetchone()
                    if last_trans:
                        cursor.execute('''
                        UPDATE transactions 
                        SET remarks = remarks || ' | ' || ?
                        WHERE id = ?
                        ''', (particulars, last_trans['id']))
                    continue
            
            if current_category and particulars and amount > 0:
                cat_id = categories.get(current_category)
                if cat_id:
                    cursor.execute('''
                    INSERT OR IGNORE INTO master_items (canonical_name, category_id, unit, aliases, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    ''', (particulars[:100], cat_id, "nos", particulars[:100]))
                    
                    cursor.execute("SELECT id FROM master_items WHERE canonical_name = ?", (particulars[:100],))
                    master_item = cursor.fetchone()
                    
                    cursor.execute('''
                    INSERT INTO transactions 
                    (requisition_id, category_id, master_item_id, particulars_raw, qty, unit, rate, amount, remarks, sr_no, is_lump_sum, entered_by_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (req_id, cat_id, master_item[0] if master_item else None, particulars, 
                          qty, "nos", rate, amount, remarks, sr_no, 0 if qty > 0 else 1, user_id))
                    sr_no += 1
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE requisition_id = ?", (req_id,))
        total = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT opening_balance FROM requisitions WHERE id = ?", (req_id,))
        req_data = cursor.fetchone()
        opening_balance = req_data['opening_balance'] if req_data else 0
        
        closing_balance = opening_balance + total
        
        cursor.execute('''
        UPDATE requisitions 
        SET total_amount = ?, closing_balance = ?
        WHERE id = ?
        ''', (total, closing_balance, req_id))
        
        cursor.execute('''
        UPDATE projects 
        SET current_balance = current_balance + ?
        WHERE id = ?
        ''', (total, project_id))
        
        conn.commit()
        conn.close()
        
        return True, ref_no, sr_no - 1
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Import error: {error_details}")
        return False, str(e), 0