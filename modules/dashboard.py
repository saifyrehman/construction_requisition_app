import streamlit as st
import pandas as pd
from database import get_db_connection

def show_dashboard():
    user = st.session_state.auth['user']
    
    st.markdown(f"""
    <div class="welcome-banner">
        <h2>👋 Welcome, {user['full_name']}!</h2>
        <p>Role: <strong>{user['role']}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
    total_projects = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requisitions")
    total_requisitions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requisitions WHERE status IN ('SUBMITTED', 'UNDER_VERIFICATION')")
    pending_approvals = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_amount) FROM requisitions WHERE status = 'APPROVED'")
    total_expenses = cursor.fetchone()[0] or 0
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📋</div>
            <div class="metric-value">{total_projects}</div>
            <div class="metric-label">Active Projects</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #2196F3;">
            <div class="metric-icon">📄</div>
            <div class="metric-value">{total_requisitions}</div>
            <div class="metric-label">Total Requisitions</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #FF9800;">
            <div class="metric-icon">⏳</div>
            <div class="metric-value">{pending_approvals}</div>
            <div class="metric-label">Pending Approvals</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #4CAF50;">
            <div class="metric-icon">💰</div>
            <div class="metric-value">PKR {total_expenses:,.0f}</div>
            <div class="metric-label">Total Approved</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📋 Recent Requisitions")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT r.*, p.name as project_name
    FROM requisitions r
    LEFT JOIN projects p ON r.project_id = p.id
    ORDER BY r.created_at DESC
    LIMIT 5
    ''')
    recent = cursor.fetchall()
    conn.close()
    
    if recent:
        data = []
        for req in recent:
            data.append({
                "Ref No": req['ref_no'],
                "Project": req['project_name'],
                "Amount": f"PKR {req['total_amount']:,.2f}",
                "Status": req['status'],
                "Created": req['created_at'][:10] if req['created_at'] else ""
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent requisitions")