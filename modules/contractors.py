# pages/contractors.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    get_db_connection, get_contractors, get_contractor, 
    create_contractor, add_contractor_payment, 
    get_contractor_payments, get_contractor_summary,
    update_payment_status
)

def safe_currency_format(value):
    """Safely format currency values, handling None and non-numeric values"""
    if value is None:
        return "PKR 0.00"
    try:
        return f"PKR {float(value):,.2f}"
    except (ValueError, TypeError):
        return "PKR 0.00"

def show_contractors():
    """Display contractors management page"""
    user = st.session_state.auth["user"]
    
    st.markdown('<div class="section-header">👷 Contractor Management</div>', unsafe_allow_html=True)
    
    # Tabs for different contractor operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Contractors", "➕ New Contractor", "💰 Payments", "📊 Reports"])
    
    with tab1:
        show_contractors_list(user)
    
    with tab2:
        show_new_contractor_form(user)
    
    with tab3:
        show_payments_section(user)
    
    with tab4:
        show_contractor_reports(user)

def show_contractors_list(user):
    """Display list of contractors"""
    st.subheader("All Contractors")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "Active", "Inactive"])
    
    try:
        contractors = get_contractors(status_filter)
        st.write(f"Debug: Found {len(contractors) if contractors else 0} contractors")  # Debug line
    except Exception as e:
        st.error(f"Error loading contractors: {e}")
        return
    
    if contractors and len(contractors) > 0:
        data = []
        for c in contractors:
            try:
                # Debug: Print contractor data
                st.write(f"Debug: Processing contractor: {c.get('name', 'Unknown')}")
                
                # Get summary - this should now return a dict with default values
                summary = get_contractor_summary(c['id'])
                
                # Get values with safe defaults
                total_paid = summary.get('paid_amount', 0) if summary else 0
                pending = summary.get('pending_amount', 0) if summary else 0
                
                data.append({
                    "ID": c.get('id', ''),
                    "Name": c.get('name', ''),
                    "Code": c.get('code', ''),
                    "Contact": c.get('contact_person', ''),
                    "Phone": c.get('phone', ''),
                    "Total Paid": safe_currency_format(total_paid),
                    "Pending": safe_currency_format(pending),
                    "Status": c.get('status', 'Active')
                })
            except Exception as e:
                st.warning(f"Error processing contractor {c.get('name', 'Unknown')}: {e}")
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # View contractor details
            st.subheader("View Contractor Details")
            contractor_names = {c.get('name'): c.get('id') for c in contractors if c.get('name')}
            
            if contractor_names:
                selected_name = st.selectbox("Select Contractor", list(contractor_names.keys()))
                
                if selected_name:
                    contractor = get_contractor(contractor_names[selected_name])
                    if contractor:
                        show_contractor_detail(contractor, user)
            else:
                st.info("No contractors available to view details")
        else:
            st.info("No contractor data available")
    else:
        st.info("No contractors found. Create your first contractor!")

def show_contractor_detail(contractor, user):
    """Show detailed view of a contractor"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### {contractor.get('name', 'Unknown')}")
        st.markdown(f"**Code:** {contractor.get('code', 'N/A')}")
        st.markdown(f"**Contact Person:** {contractor.get('contact_person', 'N/A')}")
        st.markdown(f"**Phone:** {contractor.get('phone', 'N/A')}")
        st.markdown(f"**Email:** {contractor.get('email', 'N/A')}")
        st.markdown(f"**Address:** {contractor.get('address', 'N/A')}")
    
    with col2:
        st.markdown(f"**CNIC:** {contractor.get('cnic', 'N/A')}")
        st.markdown(f"**Bank:** {contractor.get('bank_name', 'N/A')}")
        st.markdown(f"**Account:** {contractor.get('bank_account', 'N/A')}")
        st.markdown(f"**Tax ID:** {contractor.get('tax_id', 'N/A')}")
        st.markdown(f"**Status:** {contractor.get('status', 'Active')}")
    
    # Show payment history
    st.subheader("Payment History")
    try:
        payments = get_contractor_payments(contractor_id=contractor.get('id'))
    except Exception as e:
        st.error(f"Error loading payments: {e}")
        return
    
    if payments and len(payments) > 0:
        data = []
        for p in payments:
            try:
                data.append({
                    "Date": p.get('payment_date', '')[:10] if p.get('payment_date') else "",
                    "Reference": p.get('payment_reference', ''),
                    "Project": p.get('project_name', ''),
                    "Type": p.get('payment_type', ''),
                    "Amount": safe_currency_format(p.get('amount', 0)),
                    "Status": p.get('status', 'PENDING')
                })
            except Exception as e:
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Summary stats
            try:
                summary = get_contractor_summary(contractor.get('id'))
                total_amount = summary.get('total_amount', 0) if summary else 0
                paid_amount = summary.get('paid_amount', 0) if summary else 0
                pending_amount = summary.get('pending_amount', 0) if summary else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Payments", safe_currency_format(total_amount))
                with col2:
                    st.metric("Paid", safe_currency_format(paid_amount))
                with col3:
                    st.metric("Pending", safe_currency_format(pending_amount))
            except Exception as e:
                st.warning(f"Error loading summary: {e}")
        else:
            st.info("No payment data available")
    else:
        st.info("No payments recorded for this contractor")
def show_new_contractor_form(user):
    """Form to create a new contractor"""
    st.subheader("Create New Contractor")
    
    with st.form("create_contractor_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Contractor Name*", placeholder="Enter full name")
            code = st.text_input("Contractor Code*", placeholder="Unique code")
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email Address")
        
        with col2:
            address = st.text_area("Address", placeholder="Full address")
            cnic = st.text_input("CNIC Number")
            bank_name = st.text_input("Bank Name")
            bank_account = st.text_input("Bank Account Number")
            tax_id = st.text_input("Tax ID / NTN")
        
        submitted = st.form_submit_button("Create Contractor", type="primary")
        
        if submitted:
            if not name or not code:
                st.error("Please fill in all required fields (Name and Code)")
            else:
                try:
                    data = {
                        'name': name.strip(),
                        'code': code.strip().upper(),
                        'contact_person': contact_person.strip() if contact_person else "",
                        'phone': phone.strip() if phone else "",
                        'email': email.strip() if email else "",
                        'address': address.strip() if address else "",
                        'cnic': cnic.strip() if cnic else "",
                        'bank_name': bank_name.strip() if bank_name else "",
                        'bank_account': bank_account.strip() if bank_account else "",
                        'tax_id': tax_id.strip() if tax_id else ""
                    }
                    contractor_id = create_contractor(data, user['id'])
                    st.success(f"✅ Contractor '{name}' created successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating contractor: {e}")
def show_payments_section(user):
    """Show payment management section"""
    st.subheader("Manage Contractor Payments")
    
    # Get projects and contractors for dropdowns
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name FROM projects ORDER BY name")
        projects = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM contractors WHERE status = 'Active' ORDER BY name")
        contractors = cursor.fetchall()
        
        cursor.execute("SELECT id, ref_no FROM requisitions WHERE status = 'APPROVED' ORDER BY ref_no")
        requisitions = cursor.fetchall()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    finally:
        conn.close()
    
    with st.form("add_payment_form"):
        col1, col2 = st.columns(2)
        with col1:
            if contractors and len(contractors) > 0:
                contractor_options = {c['name']: c['id'] for c in contractors}
                contractor_name = st.selectbox("Contractor*", list(contractor_options.keys()))
                contractor_id = contractor_options.get(contractor_name)
            else:
                st.warning("No active contractors available")
                contractor_id = None
                contractor_name = st.selectbox("Contractor*", ["No contractors available"])
            
            if projects and len(projects) > 0:
                project_options = {p['name']: p['id'] for p in projects}
                project_name = st.selectbox("Project*", list(project_options.keys()))
                project_id = project_options.get(project_name)
            else:
                st.warning("No projects available")
                project_id = None
                project_name = st.selectbox("Project*", ["No projects available"])
            
            req_options = {"None": None}
            for r in requisitions:
                req_options[r['ref_no']] = r['id']
            req_name = st.selectbox("Requisition (Optional)", list(req_options.keys()))
            requisition_id = req_options.get(req_name)
        
        with col2:
            payment_date = st.date_input("Payment Date", datetime.now())
            payment_reference = st.text_input("Payment Reference", placeholder="e.g., INV-001")
            # Make amount optional - allow 0 or empty
            amount = st.number_input("Amount (PKR)", min_value=0.0, step=1000.0, value=0.0, help="Enter 0 or leave as 0 to add later")
            payment_type = st.selectbox("Payment Type", ["LABOUR", "MATERIAL", "MISCELLANEOUS", "ADVANCE", "FINAL"])
            description = st.text_area("Description", placeholder="Brief description of the payment")
        
        submitted = st.form_submit_button("Add Payment", type="primary")
        
        if submitted:
            if not contractor_id or not project_id:
                st.error("Please fill in all required fields (Contractor and Project)")
            else:
                try:
                    payment_data = {
                        'contractor_id': contractor_id,
                        'project_id': project_id,
                        'requisition_id': requisition_id,
                        'payment_date': payment_date.strftime('%Y-%m-%d'),
                        'payment_reference': payment_reference or f"PAY-{datetime.now().strftime('%Y%m%d')}",
                        'amount': amount,  # Can be 0
                        'payment_type': payment_type,
                        'description': description or ""
                    }
                    payment_id = add_contractor_payment(payment_data, user['id'])
                    if amount > 0:
                        st.success(f"✅ Payment of PKR {amount:,.2f} added successfully!")
                    else:
                        st.success(f"✅ Payment record added successfully! Amount can be updated later.")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding payment: {e}")
    
    # Show recent payments
    st.subheader("Recent Payments")
    try:
        payments = get_contractor_payments(status='All')[:50]
    except Exception as e:
        st.error(f"Error loading payments: {e}")
        return
    
    if payments and len(payments) > 0:
        data = []
        for p in payments:
            try:
                data.append({
                    "Date": p.get('payment_date', '')[:10] if p.get('payment_date') else "",
                    "Contractor": p.get('contractor_name', ''),
                    "Project": p.get('project_name', ''),
                    "Reference": p.get('payment_reference', ''),
                    "Type": p.get('payment_type', ''),
                    "Amount": safe_currency_format(p.get('amount', 0)),
                    "Status": p.get('status', 'PENDING')
                })
            except Exception as e:
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Add approve/reject buttons for pending payments
            st.subheader("Approve/Reject Pending Payments")
            pending_payments = [p for p in payments if p.get('status') == 'PENDING']
            
            if pending_payments and len(pending_payments) > 0:
                try:
                    payment_options = {}
                    for p in pending_payments:
                        label = f"{p.get('contractor_name', 'Unknown')} - PKR {p.get('amount', 0):,.2f} ({p.get('payment_date', '')[:10] if p.get('payment_date') else ''})"
                        payment_options[label] = p.get('id')
                    
                    selected_payment = st.selectbox("Select Payment to Approve/Reject", list(payment_options.keys()))
                    
                    if selected_payment:
                        payment_id = payment_options[selected_payment]
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Approve Payment", key=f"approve_{payment_id}"):
                                update_payment_status(payment_id, 'PAID', user['id'])
                                st.success("✅ Payment approved!")
                                st.rerun()
                        with col2:
                            if st.button("❌ Reject Payment", key=f"reject_{payment_id}"):
                                update_payment_status(payment_id, 'CANCELLED', user['id'])
                                st.warning("❌ Payment rejected!")
                                st.rerun()
                except Exception as e:
                    st.warning(f"Error with pending payments: {e}")
            else:
                st.info("No pending payments to approve")
        else:
            st.info("No payment data available")
    else:
        st.info("No payments recorded yet")

def show_contractor_reports(user):
    """Show contractor reports"""
    st.subheader("Contractor Reports")
    
    report_type = st.selectbox("Select Report Type", 
                              ["Contractor-wise Payment Summary", "Project-wise Contractor Payments", 
                               "Payment Status Report", "Contractor Payment History"])
    
    if report_type == "Contractor-wise Payment Summary":
        show_contractor_summary_report()
    elif report_type == "Project-wise Contractor Payments":
        show_project_contractor_report()
    elif report_type == "Payment Status Report":
        show_payment_status_report()
    elif report_type == "Contractor Payment History":
        show_payment_history_report()

def show_contractor_summary_report():
    """Show summary report by contractor"""
    try:
        contractors = get_contractors('All')
    except Exception as e:
        st.error(f"Error loading contractors: {e}")
        return
    
    if contractors and len(contractors) > 0:
        data = []
        for c in contractors:
            try:
                summary = get_contractor_summary(c.get('id'))
                if summary:
                    total = summary.get('total_amount', 0)
                    paid = summary.get('paid_amount', 0)
                    pending = summary.get('pending_amount', 0)
                else:
                    total = 0
                    paid = 0
                    pending = 0
                
                if total > 0:
                    data.append({
                        "Contractor": c.get('name', ''),
                        "Code": c.get('code', ''),
                        "Total Payments": safe_currency_format(total),
                        "Paid": safe_currency_format(paid),
                        "Pending": safe_currency_format(pending),
                        "Status": c.get('status', 'Active')
                    })
            except Exception as e:
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Report (CSV)",
                data=csv,
                file_name=f"Contractor_Summary_Report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No payment data available")
    else:
        st.warning("No contractors found")

def show_project_contractor_report():
    """Show project-wise contractor payments"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name FROM projects ORDER BY name")
        projects = cursor.fetchall()
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return
    finally:
        conn.close()
    
    if projects and len(projects) > 0:
        project_names = [p['name'] for p in projects]
        selected_project = st.selectbox("Select Project", project_names)
        
        if selected_project:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM projects WHERE name = ?", (selected_project,))
                project = cursor.fetchone()
            except Exception as e:
                st.error(f"Error loading project: {e}")
                return
            finally:
                conn.close()
            
            if project:
                try:
                    payments = get_contractor_payments(project_id=project['id'])
                except Exception as e:
                    st.error(f"Error loading payments: {e}")
                    return
                
                if payments and len(payments) > 0:
                    data = []
                    for p in payments:
                        try:
                            data.append({
                                "Date": p.get('payment_date', '')[:10] if p.get('payment_date') else "",
                                "Contractor": p.get('contractor_name', ''),
                                "Reference": p.get('payment_reference', ''),
                                "Type": p.get('payment_type', ''),
                                "Amount": safe_currency_format(p.get('amount', 0)),
                                "Status": p.get('status', 'PENDING')
                            })
                        except Exception as e:
                            continue
                    
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # Total
                        total = sum(p.get('amount', 0) for p in payments)
                        st.metric("Total Payments for Project", safe_currency_format(total))
                    else:
                        st.info("No payment data available")
                else:
                    st.info("No payments found for this project")
    else:
        st.warning("No projects available")

def show_payment_status_report():
    """Show payment status report"""
    status_filter = st.selectbox("Payment Status", ["All", "PENDING", "PAID", "CANCELLED"])
    
    try:
        payments = get_contractor_payments(status=status_filter if status_filter != "All" else None)
    except Exception as e:
        st.error(f"Error loading payments: {e}")
        return
    
    if payments and len(payments) > 0:
        data = []
        for p in payments:
            try:
                data.append({
                    "Date": p.get('payment_date', '')[:10] if p.get('payment_date') else "",
                    "Contractor": p.get('contractor_name', ''),
                    "Project": p.get('project_name', ''),
                    "Amount": safe_currency_format(p.get('amount', 0)),
                    "Status": p.get('status', 'PENDING')
                })
            except Exception as e:
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Summary
            total_pending = sum(p.get('amount', 0) for p in payments if p.get('status') == 'PENDING')
            total_paid = sum(p.get('amount', 0) for p in payments if p.get('status') == 'PAID')
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Pending", safe_currency_format(total_pending))
            with col2:
                st.metric("Total Paid", safe_currency_format(total_paid))
        else:
            st.info("No payment data available")
    else:
        st.info("No payments found")

def show_payment_history_report():
    """Show detailed payment history"""
    try:
        contractors = get_contractors('All')
    except Exception as e:
        st.error(f"Error loading contractors: {e}")
        return
    
    if contractors and len(contractors) > 0:
        contractor_names = ["All"] + [c.get('name', '') for c in contractors if c.get('name')]
        selected_contractor = st.selectbox("Select Contractor", contractor_names)
        
        contractor_id = None
        if selected_contractor != "All":
            contractor_id = next((c.get('id') for c in contractors if c.get('name') == selected_contractor), None)
        
        try:
            payments = get_contractor_payments(contractor_id=contractor_id)
        except Exception as e:
            st.error(f"Error loading payments: {e}")
            return
        
        if payments and len(payments) > 0:
            data = []
            for p in payments:
                try:
                    data.append({
                        "Date": p.get('payment_date', '')[:10] if p.get('payment_date') else "",
                        "Contractor": p.get('contractor_name', ''),
                        "Project": p.get('project_name', ''),
                        "Reference": p.get('payment_reference', ''),
                        "Type": p.get('payment_type', ''),
                        "Amount": safe_currency_format(p.get('amount', 0)),
                        "Status": p.get('status', 'PENDING'),
                        "Description": p.get('description', '')
                    })
                except Exception as e:
                    continue
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Export
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Payment History (CSV)",
                    data=csv,
                    file_name=f"Payment_History_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No payment data available")
        else:
            st.info("No payment history found")
    else:
        st.warning("No contractors available")