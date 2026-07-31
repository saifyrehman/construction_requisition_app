import streamlit as st
import pandas as pd
from database import get_db_connection

def show_approvals():
    user = st.session_state.auth["user"]
    
    st.markdown('<div class="section-header">✅ Approvals</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT r.*, p.name as project_name, u.full_name as created_by_name
    FROM requisitions r
    LEFT JOIN projects p ON r.project_id = p.id
    LEFT JOIN users u ON r.created_by_id = u.id
    WHERE r.status IN ('SUBMITTED', 'UNDER_VERIFICATION')
    ORDER BY r.created_at
    ''')
    pending = cursor.fetchall()
    conn.close()
    
    if pending:
        st.markdown(f"### Pending Approvals ({len(pending)})")
        
        for req in pending:
            with st.expander(f"📄 {req['ref_no']} - {req['project_name']} (PKR {req['total_amount']:,.2f})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Period:** {req['period_start'][:10] if req['period_start'] else ''} to {req['period_end'][:10] if req['period_end'] else ''}")
                    st.markdown(f"**Status:** {req['status']}")
                    st.markdown(f"**Opening Balance:** PKR {req['opening_balance']:,.2f}")
                    st.markdown(f"**Total Amount:** PKR {req['total_amount']:,.2f}")
                    st.markdown(f"**Closing Balance:** PKR {req['closing_balance']:,.2f}")
                
                with col2:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                    SELECT t.*, c.name as category_name
                    FROM transactions t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.requisition_id = ?
                    ORDER BY t.sr_no
                    ''', (req['id'],))
                    transactions = cursor.fetchall()
                    conn.close()
                    
                    if transactions:
                        data = []
                        for trans in transactions:
                            data.append({
                                "Sr": trans['sr_no'],
                                "Particulars": trans['particulars_raw'],
                                "Amount": trans['amount']
                            })
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                
                if req['status'] == "SUBMITTED" and user["role"] in ["ADMIN", "VERIFIER"]:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Verify", key=f"verify_{req['id']}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'VERIFIED', verified_at = CURRENT_TIMESTAMP, verified_by_id = ?
                                WHERE id = ?
                                ''', (user["id"], req['id']))
                                conn.commit()
                                conn.close()
                                st.success("✅ Requisition verified!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col2:
                        if st.button("🔄 Return", key=f"return_{req['id']}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'RETURNED', verifier_comments = 'Returned for revision'
                                WHERE id = ?
                                ''', (req['id'],))
                                conn.commit()
                                conn.close()
                                st.info("🔄 Requisition returned for revision!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col3:
                        if st.button("❌ Reject", key=f"reject_{req['id']}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'REJECTED', rejection_reason = 'Rejected by verifier'
                                WHERE id = ?
                                ''', (req['id'],))
                                conn.commit()
                                conn.close()
                                st.error("❌ Requisition rejected!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                
                if req['status'] == "VERIFIED" and user["role"] in ["ADMIN", "CEO"]:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{req['id']}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'APPROVED', approved_at = CURRENT_TIMESTAMP, approved_by_id = ?
                                WHERE id = ?
                                ''', (user["id"], req['id']))
                                conn.commit()
                                conn.close()
                                st.success("✅ Requisition approved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col2:
                        if st.button("❌ Reject", key=f"reject_ceo_{req['id']}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'REJECTED', rejection_reason = 'Rejected by CEO'
                                WHERE id = ?
                                ''', (req['id'],))
                                conn.commit()
                                conn.close()
                                st.error("❌ Requisition rejected!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
    else:
        st.info("No pending approvals")