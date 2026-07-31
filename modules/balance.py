import streamlit as st
import pandas as pd
from database import get_db_connection

def show_balance_statement():
    """Display balance statement for a project"""
    st.markdown('<div class="section-header">💰 Balance Statement</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects ORDER BY name")
    projects = cursor.fetchall()
    conn.close()
    
    if projects:
        project_names = [p[1] for p in projects]
        selected_project = st.selectbox("Select Project", project_names, key="balance_project")
        
        if st.button("Generate Balance Statement", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM projects WHERE name = ?", (selected_project,))
            project = cursor.fetchone()
            
            cursor.execute('''
            SELECT r.*, u.full_name as created_by_name
            FROM requisitions r
            LEFT JOIN users u ON r.created_by_id = u.id
            WHERE r.project_id = ? AND r.status = 'APPROVED'
            ORDER BY r.created_at
            ''', (project['id'],))
            requisitions = cursor.fetchall()
            conn.close()
            
            if requisitions:
                st.subheader(f"Balance Statement - {selected_project}")
                
                data = []
                running_balance = project['opening_balance'] or 0
                
                for req in requisitions:
                    expense_paid = float(req['expense_paid_last_req']) if req['expense_paid_last_req'] is not None else 0
                    total = float(req['total_amount']) if req['total_amount'] is not None else 0
                    closing = float(req['closing_balance']) if req['closing_balance'] is not None else 0
                    
                    data.append({
                        "Ref No": req['ref_no'],
                        "Period": f"{req['period_start'][:10] if req['period_start'] else ''} to {req['period_end'][:10] if req['period_end'] else ''}",
                        "Opening Balance": f"PKR {expense_paid:,.2f}",
                        "This Requisition": f"PKR {total:,.2f}",
                        "Closing Balance": f"PKR {closing:,.2f}"
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                total_expenses = sum(float(r['total_amount']) if r['total_amount'] is not None else 0 for r in requisitions)
                current_balance = project['current_balance'] or 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Opening Balance", f"PKR {project['opening_balance']:,.2f}")
                with col2:
                    st.metric("Total Expenses", f"PKR {total_expenses:,.2f}")
                with col3:
                    st.metric("Current Balance", f"PKR {current_balance:,.2f}")
            else:
                st.info("No approved requisitions found for this project")
    else:
        st.warning("No projects available")