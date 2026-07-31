import streamlit as st
from database import get_db_connection
from utils.pdf_generator import generate_project_summary_pdf

def show_projects():
    user = st.session_state.auth["user"]
    
    st.markdown('<div class="section-header">📋 Projects</div>', unsafe_allow_html=True)
    
    if user["role"] in ["ADMIN", "DATA_ENTRY"]:
        with st.expander("➕ Create New Project", expanded=False):
            with st.form("create_project_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Project Name*", placeholder="Enter project name")
                    code = st.text_input("Project Code*", placeholder="Enter unique code")
                with col2:
                    location = st.text_input("Location", placeholder="Project location")
                    opening_balance = st.number_input("Opening Balance (PKR)", min_value=0.0, step=1000.0, value=0.0)
                
                submitted = st.form_submit_button("Create Project", use_container_width=True)
                if submitted:
                    if not name or not code:
                        st.error("Please fill in all required fields")
                    else:
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('''
                            INSERT INTO projects (name, code, location, opening_balance, current_balance, created_by_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''', (name, code.upper(), location or "", opening_balance, opening_balance, user["id"]))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Project '{name}' created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating project: {e}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fix NULL values before displaying
    cursor.execute('''
    UPDATE projects 
    SET opening_balance = COALESCE(opening_balance, 0),
        current_balance = COALESCE(current_balance, 0),
        status = COALESCE(status, 'Active'),
        location = COALESCE(location, '')
    WHERE opening_balance IS NULL OR current_balance IS NULL OR status IS NULL
    ''')
    conn.commit()
    
    cursor.execute('''
    SELECT p.*, u.full_name as created_by_name,
           (SELECT COUNT(*) FROM requisitions WHERE project_id = p.id) as req_count
    FROM projects p
    LEFT JOIN users u ON p.created_by_id = u.id
    ORDER BY p.created_at DESC
    ''')
    projects = cursor.fetchall()
    conn.close()
    
    if projects:
        for project in projects:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
                with col1:
                    project_name = project['name'] or "Unnamed Project"
                    project_code = project['code'] or "N/A"
                    project_location = project['location'] or "No location specified"
                    
                    st.markdown(f"### {project_name}")
                    st.markdown(f"*Code: {project_code}*")
                    st.markdown(f"📍 {project_location}")
                with col2:
                    st.markdown("**Balance**")
                    current_balance = project['current_balance'] or 0
                    st.markdown(f"PKR {current_balance:,.2f}")
                with col3:
                    st.markdown("**Status**")
                    status = project['status'] or "Active"
                    status_color = "#4CAF50" if status == "Active" else "#FF9800"
                    st.markdown(f'<span style="color: {status_color}; font-weight: 600;">● {status}</span>', unsafe_allow_html=True)
                with col4:
                    st.markdown(f"**Requisitions**")
                    req_count = project['req_count'] or 0
                    st.markdown(f"{req_count}")
                
                if st.button(f"📊 Export Summary", key=f"export_summary_{project['id']}"):
                    generate_project_summary_pdf(project['id'])
    else:
        st.info("No projects found. Create your first project!")