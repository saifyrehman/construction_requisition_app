import streamlit as st
from streamlit_option_menu import option_menu
import sys
import os
import pandas as pd
import hashlib
from datetime import datetime
import sqlite3
import bcrypt
import traceback
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io
import openpyxl

# Configure page
st.set_page_config(
    page_title="Construction Requisition System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-header h1 {
        margin: 0;
        font-size: 28px;
    }
    .main-header p {
        margin: 5px 0 0 0;
        opacity: 0.9;
    }
    .stButton button {
        width: 100%;
        border-radius: 5px;
        font-weight: 500;
    }
    .stButton button:hover {
        transform: scale(1.02);
        transition: all 0.2s;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .status-draft { background: #e0e0e0; color: #424242; }
    .status-submitted { background: #fff3e0; color: #e65100; }
    .status-under-verification { background: #fff3e0; color: #e65100; }
    .status-verified { background: #e3f2fd; color: #0d47a1; }
    .status-approved { background: #e8f5e9; color: #1b5e20; }
    .status-rejected { background: #ffebee; color: #b71c1c; }
    .status-returned { background: #fff8e1; color: #f57f17; }
    .status-archived { background: #f3e5f5; color: #4a148c; }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 10px;
        text-align: center;
    }
    .metric-card .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #1a1a2e;
    }
    .metric-card .metric-label {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
    .metric-card .metric-icon {
        font-size: 24px;
        margin-bottom: 5px;
    }
    .user-info-box {
        background: #e8f5e9;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .user-info-box .user-name {
        font-weight: 600;
        font-size: 16px;
    }
    .user-info-box .user-role {
        font-size: 12px;
        color: #666;
    }
    .section-header {
        font-size: 20px;
        font-weight: 600;
        margin: 20px 0 10px 0;
        color: #1a1a2e;
    }
    .welcome-banner {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .welcome-banner h2 {
        margin: 0;
    }
    .welcome-banner p {
        margin: 5px 0 0 0;
        color: #2e7d32;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #ddd;
        font-size: 12px;
        color: gray;
    }
    .upload-section {
        background: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE SETUP ====================
DB_PATH = "requisition.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        full_name TEXT,
        hashed_password TEXT,
        role TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        location TEXT,
        status TEXT DEFAULT 'Active',
        opening_balance REAL DEFAULT 0,
        current_balance REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_id INTEGER,
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS master_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name TEXT NOT NULL UNIQUE,
        category_id INTEGER,
        unit TEXT,
        aliases TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requisitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        ref_no TEXT NOT NULL,
        period_start TIMESTAMP NOT NULL,
        period_end TIMESTAMP NOT NULL,
        opening_balance REAL DEFAULT 0,
        closing_balance REAL DEFAULT 0,
        status TEXT DEFAULT 'DRAFT',
        total_amount REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submitted_at TIMESTAMP,
        verified_at TIMESTAMP,
        approved_at TIMESTAMP,
        created_by_id INTEGER,
        verified_by_id INTEGER,
        approved_by_id INTEGER,
        submitted_by_id INTEGER,
        verifier_comments TEXT,
        approver_comments TEXT,
        rejection_reason TEXT,
        expense_paid_last_req REAL DEFAULT 0,  -- ADD THIS FIELD
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requisition_id INTEGER NOT NULL,
        category_id INTEGER,
        master_item_id INTEGER,
        particulars_raw TEXT,
        qty REAL DEFAULT 0,
        unit TEXT,
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        remarks TEXT,
        sr_no INTEGER,
        is_lump_sum INTEGER DEFAULT 0,
        entered_by_id INTEGER,
        FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (master_item_id) REFERENCES master_items (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def seed_default_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    if not admin:
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
        INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ("admin", "admin@company.com", "System Administrator", hashed, "ADMIN", 1))
    
    cursor.execute("SELECT COUNT(*) FROM categories")
    count = cursor.fetchone()[0]
    
    if count == 0:
        default_categories = [
            ("Site Work", 1),
            ("Materials", 2),
            ("Miscellaneous & Administration", 3)
        ]
        cursor.executemany('''
        INSERT INTO categories (name, sort_order, is_active)
        VALUES (?, ?, 1)
        ''', default_categories)
    
    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    init_database()
    seed_default_data()

# ==================== AUTH FUNCTIONS ====================
def authenticate_user(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['hashed_password'].encode('utf-8')):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            conn.commit()
            conn.close()
            
            return {
                "id": user['id'],
                "username": user['username'],
                "full_name": user['full_name'],
                "role": user['role'],
                "email": user['email']
            }
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def login_form():
    st.markdown("""
    <div style="max-width: 400px; margin: 50px auto;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 48px;">🏗️</div>
            <h2>Login to Requisition System</h2>
            <p style="color: #666;">HAJI ABDUL RAHEEM CONSTRUCTION COMPANY</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            if st.button("Login", type="primary", use_container_width=True):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.auth = {"logged_in": True, "user": user}
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.warning("Please enter both username and password")
            
            st.caption("Default: admin / admin123")

# ==================== DASHBOARD ====================
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
                    # Get safe values
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
                
                # Export Project Summary PDF
                if st.button(f"📊 Export Summary", key=f"export_summary_{project['id']}"):
                    generate_project_summary_pdf(project['id'])
    else:
        st.info("No projects found. Create your first project!")

def fix_database_nulls():
    """Fix all NULL values in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fix projects
    cursor.execute('''
    UPDATE projects 
    SET opening_balance = COALESCE(opening_balance, 0),
        current_balance = COALESCE(current_balance, 0),
        status = COALESCE(status, 'Active'),
        location = COALESCE(location, '')
    ''')
    
    # Fix requisitions
    cursor.execute('''
    UPDATE requisitions 
    SET opening_balance = COALESCE(opening_balance, 0),
        closing_balance = COALESCE(closing_balance, 0),
        total_amount = COALESCE(total_amount, 0),
        status = COALESCE(status, 'DRAFT')
    ''')
    
    # Fix transactions
    cursor.execute('''
    UPDATE transactions 
    SET qty = COALESCE(qty, 0),
        rate = COALESCE(rate, 0),
        amount = COALESCE(amount, 0)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Fixed NULL values in database")

# Call this after database initialization
if not os.path.exists(DB_PATH):
    init_database()
    seed_default_data()
else:
    # Fix existing data
    fix_database_nulls()
def import_excel_data(file, user_id):
    """Import Excel file data into database with proper parsing"""
    try:
        # Read the Excel file
        df = pd.read_excel(file, header=None)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find categories
        cursor.execute("SELECT id, name FROM categories")
        categories = {c['name']: c['id'] for c in cursor.fetchall()}
        
        # Extract project name and details from the first few rows
        project_name = None
        ref_no = None
        period_start = None
        period_end = None
        expense_paid_last = 0
        
        for idx in range(min(10, len(df))):
            if pd.notna(df.iloc[idx, 0]):
                val = str(df.iloc[idx, 0]).strip()
                if "Ref No" in val or "Ref No." in val:
                    # Extract Ref No
                    parts = val.split("Ref No")
                    if len(parts) > 1:
                        ref_no = parts[-1].strip()
                        if ref_no and ref_no[0] in ['.', ':']:
                            ref_no = ref_no[1:].strip()
                elif "Date" in val and "To" in val:
                    # Extract dates
                    import re
                    dates = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', val)
                    if len(dates) >= 2:
                        period_start = datetime.strptime(dates[0], '%d-%b-%Y')
                        period_end = datetime.strptime(dates[1], '%d-%b-%Y')
                elif "Expense paid last req" in val or "Expense paid" in val:
                    # Extract expense paid last
                    import re
                    numbers = re.findall(r'[\d,]+\.?\d*', val)
                    if numbers:
                        expense_paid_last = float(numbers[-1].replace(',', ''))
                elif "CONSTRUCTION" in val.upper():
                    continue
                elif not project_name and idx < 5:
                    project_name = val
                    break
        
        # If project name not found, use a default
        if not project_name:
            project_name = f"Imported Project {datetime.now().strftime('%Y%m%d')}"
        
        if not ref_no:
            ref_no = f"IMP-{datetime.now().strftime('%Y%m%d')}-{hash(str(df)) % 1000:03d}"
        
        if not period_start:
            period_start = datetime.now()
        if not period_end:
            period_end = datetime.now()
        
        # Create or get project
        cursor.execute("SELECT id, opening_balance FROM projects WHERE name = ?", (project_name,))
        project = cursor.fetchone()
        
        if not project:
            # Create new project
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
        
        # Create requisition
        cursor.execute('''
        INSERT INTO requisitions 
        (project_id, ref_no, period_start, period_end, opening_balance, closing_balance, 
         expense_paid_last_req, status, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, ref_no, period_start, period_end, opening_balance, opening_balance, 
              expense_paid_last, "DRAFT", user_id))
        
        req_id = cursor.lastrowid
        
        # Parse transactions
        current_category = None
        sr_no = 1
        in_total_section = False
        
        for idx, row in df.iterrows():
            if idx < 3:  # Skip header rows
                continue
            
            # Get first column value
            first_val = str(row[0]) if pd.notna(row[0]) else ""
            first_val_lower = first_val.lower().strip()
            
            # Check for section headers
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
            
            # Skip total rows
            if in_total_section and "total" in first_val_lower:
                in_total_section = False
                continue
            
            # Parse transaction data
            particulars = str(row[1]) if len(row) > 1 and pd.notna(row[1]) else ""
            
            # Skip empty rows or header rows
            if not particulars or particulars.strip() in ["Sr. #", "Particulars", "Qty", "Market Rate", "Amount", "Remarks"]:
                continue
            
            # Get values with proper handling
            qty = 0
            rate = 0
            amount = 0
            remarks = ""
            
            # Try to parse numeric values
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
            
            # If amount is 0 but qty and rate have values, calculate amount
            if amount == 0 and qty > 0 and rate > 0:
                amount = qty * rate
            
            # Skip if no amount or particulars
            if amount == 0 and particulars:
                # Check if it's a description without amount (like "Nazam Chokidar Salary jun 2026")
                if len(particulars) > 10 and not any(c.isdigit() for c in particulars[:5]):
                    # This is likely a description for the previous item
                    # Find the last transaction and update its remarks
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
            
            # Insert transaction if we have a category and particulars
            if current_category and particulars and amount > 0:
                cat_id = categories.get(current_category)
                if cat_id:
                    # Try to find or create master item
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
        
        # Update totals
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE requisition_id = ?", (req_id,))
        total = cursor.fetchone()[0] or 0
        
        # Get opening balance
        cursor.execute("SELECT opening_balance FROM requisitions WHERE id = ?", (req_id,))
        req_data = cursor.fetchone()
        opening_balance = req_data['opening_balance'] if req_data else 0
        
        closing_balance = opening_balance + total
        
        cursor.execute('''
        UPDATE requisitions 
        SET total_amount = ?, closing_balance = ?
        WHERE id = ?
        ''', (total, closing_balance, req_id))
        
        # Update project balance
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


# Add this function to fix the database
def fix_database_schema():
    """Add missing columns to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if expense_paid_last_req column exists
    cursor.execute("PRAGMA table_info(requisitions)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'expense_paid_last_req' not in column_names:
        cursor.execute("ALTER TABLE requisitions ADD COLUMN expense_paid_last_req REAL DEFAULT 0")
        print("✅ Added expense_paid_last_req column")
    
    if 'closing_balance' not in column_names:
        cursor.execute("ALTER TABLE requisitions ADD COLUMN closing_balance REAL DEFAULT 0")
        print("✅ Added closing_balance column")
    
    conn.commit()
    conn.close()

# Call this at startup
fix_database_schema()


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
        
        # Get safe values
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
        
        # Header with Ref No
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, textColor=colors.darkblue, spaceAfter=6, fontName='Helvetica-Bold')
        story.append(Paragraph("HAJI ABDUL RAHEEM CONSTRUCTION COMPANY", header_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Project and Ref No
        info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
        story.append(Paragraph(f"<b>Project:</b> {project_name} ({project_code})", info_style))
        story.append(Paragraph(f"<b>Ref No:</b> {ref_no}", info_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Requisition Title with Date
        req_header_style = ParagraphStyle('ReqHeaderStyle', parent=styles['Heading2'], fontSize=14, alignment=TA_CENTER, textColor=colors.darkblue, spaceAfter=6, fontName='Helvetica-Bold')
        story.append(Paragraph("REQUISITION FORM FOR SITE WORK DONE", req_header_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Date and Ref No row (matching the Excel format)
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER)
        story.append(Paragraph(f"<b>Date:</b> {period_start} <b>To</b> {period_end}", date_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Info table with opening balance
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
        
        # Status Stamp
        if status in ["APPROVED", "REJECTED"]:
            stamp_color = colors.green if status == "APPROVED" else colors.red
            stamp_style = ParagraphStyle('StampStyle', parent=styles['Normal'], fontSize=36, alignment=TA_CENTER, textColor=stamp_color, fontName='Helvetica-Bold')
            story.append(Paragraph(f"<font color={stamp_color}><b>{status}</b></font>", stamp_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Group by category
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
        
        # Grand Total
        grand_total = sum(float(t['amount']) if t['amount'] is not None else 0.0 for t in transactions)
        total_style = ParagraphStyle('TotalStyle', parent=styles['Heading3'], fontSize=13, alignment=TA_RIGHT, textColor=colors.darkblue, fontName='Helvetica-Bold')
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Total Amount: PKR {grand_total:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Expense Paid Last Req: PKR {expense_paid_last:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>Closing Balance: PKR {closing_balance:,.2f}</b>", total_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Signature
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
        
        # Footer
        footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("This is a system-generated document. Valid without signature.", footer_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M')}", footer_style))
        
        doc.build(story)
        return pdf_path, None
    except Exception as e:
        return None, str(e)

    
def generate_project_summary_pdf(project_id):
    """Generate project summary PDF"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            conn.close()
            st.error("Project not found")
            return
        
        cursor.execute('''
        SELECT r.*, u.full_name as created_by_name
        FROM requisitions r
        LEFT JOIN users u ON r.created_by_id = u.id
        WHERE r.project_id = ?
        ORDER BY r.created_at DESC
        ''', (project_id,))
        requisitions = cursor.fetchall()
        conn.close()
        
        # Get safe values with defaults
        project_name = project['name'] or "Unnamed Project"
        project_code = project['code'] or "N/A"
        project_location = project['location'] or "Not specified"
        opening_balance = project['opening_balance'] or 0
        current_balance = project['current_balance'] or 0
        
        pdf_filename = f"Project_Summary_{project_code}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(os.getcwd(), pdf_filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, textColor=colors.darkblue)
        story.append(Paragraph("PROJECT SUMMARY REPORT", header_style))
        story.append(Spacer(1, 0.2*inch))
        
        project_style = ParagraphStyle('ProjectStyle', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)
        story.append(Paragraph(f"<b>Project:</b> {project_name} ({project_code})", project_style))
        story.append(Paragraph(f"<b>Location:</b> {project_location}", project_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Stats
        total_requisitions = len(requisitions)
        approved = len([r for r in requisitions if r['status'] == "APPROVED"])
        total_amount = sum(float(r['total_amount'] or 0) for r in requisitions if r['status'] == "APPROVED")
        
        stats_data = [
            ['Total Requisitions:', str(total_requisitions)],
            ['Approved Requisitions:', str(approved)],
            ['Total Approved Amount:', f"PKR {total_amount:,.2f}"],
            ['Opening Balance:', f"PKR {opening_balance:,.2f}"],
            ['Current Balance:', f"PKR {current_balance:,.2f}"]
        ]
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 2.5*inch])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Requisitions list
        story.append(Paragraph("<b>REQUISITION HISTORY</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        req_data = [['Ref No', 'Period', 'Status', 'Amount', 'Created']]
        for req in requisitions:
            # Get safe values
            ref_no = req['ref_no'] or "N/A"
            period_start = req['period_start'][:10] if req['period_start'] else ""
            period_end = req['period_end'][:10] if req['period_end'] else ""
            period = f"{period_start} to {period_end}" if period_start and period_end else "N/A"
            status = req['status'] or "UNKNOWN"
            amount = req['total_amount'] or 0
            created = req['created_at'][:10] if req['created_at'] else ""
            
            req_data.append([
                ref_no,
                period,
                status,
                f"PKR {amount:,.2f}",
                created
            ])
        
        req_table = Table(req_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.5*inch, 1.2*inch])
        req_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        story.append(req_table)
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph(f"Report generated on: {datetime.now().strftime('%d-%b-%Y %H:%M')}", styles['Normal']))
        
        doc.build(story)
        
        # Provide download
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Project Summary",
                    data=f,
                    file_name=f"Project_Summary_{project_code}.pdf",
                    mime="application/pdf",
                    key=f"summary_download_{project_id}"
                )
            # Clean up
            os.remove(pdf_path)
        else:
            st.error("PDF generation failed")
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        import traceback
        st.error(traceback.format_exc())

# ==================== REQUISITIONS ====================
def get_status_badge(status):
    classes = {
        "DRAFT": "status-draft",
        "SUBMITTED": "status-submitted",
        "UNDER_VERIFICATION": "status-under-verification",
        "VERIFIED": "status-verified",
        "APPROVED": "status-approved",
        "REJECTED": "status-rejected",
        "RETURNED": "status-returned",
        "ARCHIVED": "status-archived"
    }
    display = status.replace("_", " ").title()
    return f'<span class="status-badge {classes.get(status, "status-draft")}">{display}</span>'

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
            
            # Get project details
            cursor.execute("SELECT * FROM projects WHERE name = ?", (selected_project,))
            project = cursor.fetchone()
            
            # Get all approved requisitions for this project
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
                
                # Prepare data for display
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
                
                # Summary
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

def show_requisitions():
    user = st.session_state.auth["user"]
    
    if st.session_state.get("editing_requisition_id"):
        show_requisition_editor(st.session_state.editing_requisition_id)
        return
    
    st.markdown('<div class="section-header">📄 Requisitions</div>', unsafe_allow_html=True)
    
    # Add this in the import section of show_requisitions()
    with st.expander("📥 Import from Excel", expanded=False):
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.info("Upload an Excel file in the existing requisition format with Site Work, Materials, and Misc sections")
        
        # Add a sample template download button
        if st.button("📄 Download Sample Excel Template", use_container_width=True):
            # Create a sample Excel file
            sample_data = {
                'A': ['REQUISITION FORM FOR SITE WORK DONE', '', '', 'Ref No.18'],
                'B': ['Date.17-Jul-2025', 'To', 'Date.23-Jul-2025', ''],
                'C': ['', '', '', ''],
                'D': ['', '', '', ''],
                'E': ['', '', '', ''],
                'F': ['', '', '', ''],
            }
            sample_df = pd.DataFrame({
                'A': ['REQUISITION FORM FOR SITE WORK DONE', '', '', 'Ref No.18', 'Date.17-Jul-2025', 'To', 'Date.23-Jul-2025', '', 'Sr. #', 'Particulars', 'Qty', 'Market Rate', 'Amount', 'Remarks'],
                'B': ['', '', '', '', '', '', '', '', '1', 'sun room work', '1', '40000', '40000', ''],
                'C': ['', '', '', '', '', '', '', '', '2', 'chockat fixing', '1', '2500', '2500', ''],
                'D': ['', '', '', '', '', '', '', '', '3', 'Salary Khan pt paint', '1', '15000', '15000', ''],
                'E': ['', '', '', '', '', '', '', '', '4', 'Shahib PT wood work', '1', '200000', '200000', ''],
                'F': ['', '', '', '', '', '', '', '', 'Total', '', '', '', '257500', ''],
                'G': ['', '', '', '', '', '', '', '', 'Materials', '', '', '', '', ''],
                'H': ['', '', '', '', '', '', '', '', '1', 'Blocks', '1000', '72', '72000', ''],
                'I': ['', '', '', '', '', '', '', '', '2', 'Stone', '3', '4000', '12000', ''],
                'J': ['', '', '', '', '', '', '', '', 'Total', '', '', '', '180340', ''],
                'K': ['', '', '', '', '', '', '', '', 'Miscellaneous & Administration', '', '', '', '', ''],
                'L': ['', '', '', '', '', '', '', '', '1', 'Staff food', '', '', '2100', ''],
                'M': ['', '', '', '', '', '', '', '', '2', 'Bike petrol', '', '', '500', ''],
                'N': ['', '', '', '', '', '', '', '', 'Total', '', '', '', '2600', ''],
                'O': ['', '', '', '', '', '', '', '', 'Total Amount', '', '', '', '440440', ''],
                'P': ['', '', '', '', '', '', '', '', 'Expense paid last req. 15 till', '', '', '', '9546797', ''],
            }).T
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False, header=False)
            
            output.seek(0)
            st.download_button(
                label="📥 Download Sample Template",
                data=output,
                file_name="Sample_Requisition_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_template"
            )
        
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=["xlsx", "xls"],
            help="Upload a requisition Excel file"
        )
        
        if uploaded_file:
            if st.button("📥 Import Excel Data", type="primary", use_container_width=True):
                with st.spinner("Importing data..."):
                    success, result, count = import_excel_data(uploaded_file, user["id"])
                    if success:
                        st.success(f"✅ Successfully imported requisition {result} with {count} items!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Import failed: {result}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== PDF EXPORT SECTION ==========
    with st.expander("📄 Export Reports", expanded=False):
        st.info("Generate PDF reports for requisitions")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects ORDER BY name")
        projects = cursor.fetchall()
        conn.close()
        
        if projects:
            project_names = [p[1] for p in projects]
            selected_project = st.selectbox("Select Project", project_names)
            
            if st.button("📊 Export Project Summary", use_container_width=True):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM projects WHERE name = ?", (selected_project,))
                project = cursor.fetchone()
                conn.close()
                if project:
                    generate_project_summary_pdf(project['id'])
        else:
            st.warning("No projects available")
    
    # ========== CREATE NEW REQUISITION ==========
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects ORDER BY name")
    projects = cursor.fetchall()
    conn.close()
    
    project_options = {p[1]: p[0] for p in projects}
    project_options["All Projects"] = None
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_project_name = st.selectbox("Filter by Project", list(project_options.keys()), key="req_project_filter")
        project_id = project_options[selected_project_name]
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "DRAFT", "SUBMITTED", "VERIFIED", "APPROVED", "REJECTED", "RETURNED"])
    
    # ========== CREATE REQUISITION FORM ==========
    if user["role"] in ["ADMIN", "DATA_ENTRY"] and projects:
        with st.expander("➕ Create New Requisition", expanded=False):
            st.markdown("### Requisition Details")
            with st.form("create_requisition_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    project_name = st.selectbox("Select Project*", [p[1] for p in projects])
                    
                    # Get opening balance for this project
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT opening_balance, current_balance, code FROM projects WHERE name = ?", (project_name,))
                    proj = cursor.fetchone()
                    conn.close()
                    
                    if proj:
                        # Access by column name
                        opening_balance = proj['opening_balance'] if proj['opening_balance'] is not None else 0
                        current_balance = proj['current_balance'] if proj['current_balance'] is not None else 0
                        st.info(f"Opening Balance: PKR {opening_balance:,.2f}")
                        st.info(f"Current Balance: PKR {current_balance:,.2f}")
                    else:
                        opening_balance = 0
                        current_balance = 0
                    
                with col2:
                    # Get project code for ref no
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT code FROM projects WHERE name = ?", (project_name,))
                    proj_code = cursor.fetchone()
                    conn.close()
                    
                    # Access by column name
                    project_code = proj_code['code'] if proj_code else "REQ"
                    
                    ref_no = st.text_input(
                        "Reference No.*", 
                        value=f"{project_code}-{datetime.now().strftime('%Y%m')}-{len(projects)+1:04d}",
                        help="Format: PROJECTCODE-YYYYMM-XXXX"
                    )
                    period_start = st.date_input("Period Start*")
                    
                with col3:
                    # Get expense paid last requisition
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT closing_balance FROM requisitions 
                        WHERE project_id = (SELECT id FROM projects WHERE name = ?)
                        AND status = 'APPROVED'
                        ORDER BY created_at DESC LIMIT 1
                    ''', (project_name,))
                    last_req = cursor.fetchone()
                    conn.close()
                    
                    # Access by column name
                    expense_paid_last = last_req['closing_balance'] if last_req else 0
                    
                    st.text_input(
                        "Expense Paid Last Req",
                        value=f"PKR {expense_paid_last:,.2f}",
                        disabled=True
                    )
                    period_end = st.date_input("Period End*")
                
                # Opening Balance (carried forward)
                opening_balance_display = st.number_input(
                    "Opening Balance (Carried Forward)",
                    min_value=0.0,
                    step=1000.0,
                    value=float(expense_paid_last) if expense_paid_last else 0.0,
                    help="This is carried forward from the previous requisition"
                )
                
                submitted = st.form_submit_button("Create Requisition", use_container_width=True, type="primary")
                if submitted and ref_no and period_start and period_end:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, opening_balance FROM projects WHERE name = ?", (project_name,))
                        project = cursor.fetchone()
                        
                        if project:
                            # Get opening balance from last requisition
                            cursor.execute('''
                            SELECT closing_balance FROM requisitions 
                            WHERE project_id = ? 
                            AND status = 'APPROVED'
                            ORDER BY created_at DESC LIMIT 1
                            ''', (project['id'],))
                            last_req = cursor.fetchone()
                            opening_balance = last_req['closing_balance'] if last_req else project['opening_balance']
                            
                            cursor.execute('''
                            INSERT INTO requisitions 
                            (project_id, ref_no, period_start, period_end, opening_balance, 
                             closing_balance, expense_paid_last_req, status, created_by_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                project['id'], 
                                ref_no, 
                                period_start, 
                                period_end, 
                                opening_balance,
                                opening_balance,
                                expense_paid_last,
                                "DRAFT", 
                                user["id"]
                            ))
                            
                            req_id = cursor.lastrowid
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Requisition {ref_no} created successfully!")
                            st.info(f"📋 Opening Balance: PKR {opening_balance:,.2f}")
                            st.info(f"📋 Expense Paid Last Req: PKR {expense_paid_last:,.2f}")
                            st.session_state.editing_requisition_id = req_id
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error creating requisition: {e}")
    
    # ========== DISPLAY REQUISITIONS ==========
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT r.*, p.name as project_name, u.full_name as created_by_name
    FROM requisitions r
    LEFT JOIN projects p ON r.project_id = p.id
    LEFT JOIN users u ON r.created_by_id = u.id
    WHERE 1=1
    '''
    params = []
    
    if project_id:
        query += " AND r.project_id = ?"
        params.append(project_id)
    
    if status_filter != "All":
        query += " AND r.status = ?"
        params.append(status_filter)
    
    query += " ORDER BY r.created_at DESC"
    
    cursor.execute(query, params)
    requisitions = cursor.fetchall()
    conn.close()
    
    if requisitions:
        for req in requisitions:
            with st.container(border=True):
                # Access by column name (dictionary-style)
                req_id = req['id']
                ref_no = req['ref_no'] if req['ref_no'] is not None else "N/A"
                project_name = req['project_name'] if req['project_name'] is not None else "Unknown"
                total_amount = float(req['total_amount']) if req['total_amount'] is not None else 0
                opening_balance = float(req['opening_balance']) if req['opening_balance'] is not None else 0
                closing_balance = float(req['closing_balance']) if req['closing_balance'] is not None else 0
                expense_paid_last = float(req['expense_paid_last_req']) if req['expense_paid_last_req'] is not None else 0
                status = req['status'] if req['status'] is not None else "DRAFT"
                period_start = req['period_start'] if req['period_start'] is not None else ""
                period_end = req['period_end'] if req['period_end'] is not None else ""
                
                # Create two rows: Header row and detail row
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.2, 1, 0.8])
                with col1:
                    st.markdown(f"**Ref No: {ref_no}**")
                    st.markdown(f"📋 {project_name}")
                    st.markdown(f"📅 {period_start[:10] if period_start else ''} to {period_end[:10] if period_end else ''}")
                with col2:
                    st.markdown(f"**Amount**")
                    st.markdown(f"PKR {total_amount:,.2f}")
                    st.markdown(f"**Expense Paid Last:** PKR {expense_paid_last:,.2f}")
                with col3:
                    st.markdown(f"**Opening:** PKR {opening_balance:,.2f}")
                    st.markdown(f"**Closing:** PKR {closing_balance:,.2f}")
                with col4:
                    st.markdown(f"**Status**")
                    st.markdown(get_status_badge(status), unsafe_allow_html=True)
                with col5:
                    if status == "DRAFT" and user["role"] in ["ADMIN", "DATA_ENTRY"]:
                        if st.button("✏️ Edit", key=f"edit_req_{req_id}"):
                            st.session_state.editing_requisition_id = req_id
                            st.rerun()
                    
                    if status == "DRAFT" and user["role"] in ["ADMIN", "DATA_ENTRY"]:
                        if st.button("📤 Submit", key=f"submit_req_{req_id}"):
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                UPDATE requisitions 
                                SET status = 'SUBMITTED', submitted_at = CURRENT_TIMESTAMP, submitted_by_id = ?
                                WHERE id = ?
                                ''', (user["id"], req_id))
                                conn.commit()
                                conn.close()
                                st.success("✅ Requisition submitted for verification!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error submitting: {e}")
                    
                    if status == "SUBMITTED" and user["role"] in ["ADMIN", "VERIFIER"]:
                        if st.button("🔍 Verify", key=f"verify_req_{req_id}"):
                            st.session_state.verifying_requisition_id = req_id
                            st.rerun()
                    
                    if status == "VERIFIED" and user["role"] in ["ADMIN", "CEO"]:
                        if st.button("✅ Approve", key=f"approve_req_{req_id}"):
                            st.session_state.approving_requisition_id = req_id
                            st.rerun()
                    
                    if st.button("📄 PDF", key=f"pdf_req_{req_id}"):
                        with st.spinner("Generating PDF..."):
                            pdf_path, error = generate_requisition_pdf(req_id)
                            if pdf_path and os.path.exists(pdf_path):
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="📥 Download PDF",
                                        data=f,
                                        file_name=f"Requisition_{ref_no}.pdf",
                                        mime="application/pdf",
                                        key=f"download_pdf_{req_id}"
                                    )
                                os.remove(pdf_path)
                                st.success("✅ PDF generated successfully!")
                            else:
                                st.error(f"❌ PDF generation failed: {error}")
    else:
        st.info("No requisitions found. Create your first requisition!")
def add_missing_columns():
    """Add missing columns to existing database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if expense_paid_last_req column exists
        cursor.execute("PRAGMA table_info(requisitions)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'expense_paid_last_req' not in column_names:
            cursor.execute("ALTER TABLE requisitions ADD COLUMN expense_paid_last_req REAL DEFAULT 0")
            print("✅ Added expense_paid_last_req column")
        
        if 'closing_balance' not in column_names:
            cursor.execute("ALTER TABLE requisitions ADD COLUMN closing_balance REAL DEFAULT 0")
            print("✅ Added closing_balance column")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding columns: {e}")

# Call this at startup, after database initialization
if not os.path.exists(DB_PATH):
    init_database()
    seed_default_data()
else:
    fix_database_nulls()
    add_missing_columns()  # Add this line

# Call this after database initialization
if not os.path.exists(DB_PATH):
    init_database()
    seed_default_data()
else:
    fix_database_nulls()
    add_missing_columns()
def show_requisition_editor(req_id):
    user = st.session_state.auth["user"]
    conn = get_db_connection()
    cursor = conn.cursor()
    
    req = cursor.execute("SELECT * FROM requisitions WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        st.error("Requisition not found")
        return
    
    project = cursor.execute("SELECT * FROM projects WHERE id = ?", (req['project_id'],)).fetchone()
    
    cursor.execute("SELECT * FROM categories ORDER BY sort_order")
    categories = cursor.fetchall()
    category_options = {c['name']: c['id'] for c in categories}
    
    cursor.execute('''
    SELECT t.*, c.name as category_name
    FROM transactions t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.requisition_id = ?
    ORDER BY t.sr_no
    ''', (req_id,))
    transactions = cursor.fetchall()
    conn.close()
    
    st.markdown(f"""
    <div style="background: #e3f2fd; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <h3 style="margin: 0;">✏️ Editing: {req['ref_no']}</h3>
        <p style="margin: 5px 0 0 0; color: #666;">
            Project: {project['name'] if project else 'Unknown'} | 
            Period: {req['period_start'][:10] if req['period_start'] else ''} to {req['period_end'][:10] if req['period_end'] else ''} | 
            Opening: PKR {req['opening_balance']:,.2f}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if transactions:
        st.subheader("Current Items")
        data = []
        for trans in transactions:
            data.append({
                "Sr": trans['sr_no'],
                "Particulars": trans['particulars_raw'],
                "Category": trans['category_name'] or "Uncategorized",
                "Qty": float(trans['qty']),
                "Unit": trans['unit'] or "",
                "Rate": float(trans['rate']),
                "Amount": float(trans['amount']),
                "Remarks": trans['remarks'] or ""
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        total = sum(t['amount'] for t in transactions)
        st.markdown(f"**Total Amount:** PKR {total:,.2f}")
    
    st.subheader("Add New Item")
    with st.form("add_transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            category_name = st.selectbox("Category*", list(category_options.keys()))
            particulars = st.text_input("Particulars/Description*")
            sr_no = len(transactions) + 1
        with col2:
            qty = st.number_input("Quantity", min_value=0.0, step=1.0, value=1.0)
            unit = st.text_input("Unit (e.g., nos, kg, ft)", "nos")
            rate = st.number_input("Rate (PKR)", min_value=0.0, step=10.0, value=0.0)
            is_lump_sum = st.checkbox("Lump Sum (No Qty×Rate)")
        
        remarks = st.text_area("Remarks")
        
        submitted = st.form_submit_button("Add Item")
        if submitted and particulars and category_name:
            try:
                category_id = category_options[category_name]
                amount = rate if is_lump_sum else qty * rate
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Insert transaction
                cursor.execute('''
                INSERT INTO transactions 
                (requisition_id, category_id, master_item_id, particulars_raw, qty, unit, rate, amount, remarks, sr_no, is_lump_sum, entered_by_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (req_id, category_id, None, particulars, qty if not is_lump_sum else 0, 
                      unit, rate if not is_lump_sum else 0, amount, remarks, len(transactions) + 1, 
                      1 if is_lump_sum else 0, user["id"]))
                
                # Update requisition total
                cursor.execute("SELECT SUM(amount) FROM transactions WHERE requisition_id = ?", (req_id,))
                total = cursor.fetchone()[0] or 0
                
                # Get opening balance - FIXED: Access by column name
                cursor.execute("SELECT opening_balance, expense_paid_last_req FROM requisitions WHERE id = ?", (req_id,))
                req_data = cursor.fetchone()
                opening_balance = req_data['opening_balance'] if req_data and req_data['opening_balance'] is not None else 0
                expense_paid_last = req_data['expense_paid_last_req'] if req_data and req_data['expense_paid_last_req'] is not None else 0
                
                # Calculate closing balance
                closing_balance = opening_balance + total
                
                cursor.execute('''
                UPDATE requisitions 
                SET total_amount = ?, closing_balance = ?, expense_paid_last_req = ?
                WHERE id = ?
                ''', (total, closing_balance, expense_paid_last, req_id))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Item added successfully! New Total: PKR {total:,.2f}")
                st.balloons()  # Add a fun animation to show success
                st.rerun()
            except Exception as e:
                st.error(f"Error adding item: {e}")
                import traceback
                st.error(traceback.format_exc())
    
    if transactions:
        st.subheader("Delete Item")
        trans_options = {f"{t['sr_no']}. {t['particulars_raw'][:50]}": t['id'] for t in transactions}
        trans_to_delete = st.selectbox("Select item to delete", list(trans_options.keys()))
        if st.button("🗑️ Delete Selected Item", type="primary"):
            try:
                trans_id = trans_options[trans_to_delete]
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
                
                # Update total after deletion
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
                
                conn.commit()
                conn.close()
                st.success("✅ Item deleted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting item: {e}")
    
    if st.button("⬅️ Back to Requisitions"):
        st.session_state.editing_requisition_id = None
        st.rerun()

# ==================== APPROVALS ====================
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

# ==================== ADMIN ====================
def show_admin():
    user = st.session_state.auth["user"]
    
    if user["role"] != "ADMIN":
        st.warning("⚠️ Admin access required")
        return
    
    st.markdown('<div class="section-header">⚙️ Admin Panel</div>', unsafe_allow_html=True)
    
    tabs = st.tabs(["👥 Users", "📦 Master Items", "🏷️ Categories"])
    
    with tabs[0]:
        st.markdown("### User Management")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at")
        users = cursor.fetchall()
        conn.close()
        
        if users:
            user_data = []
            for u in users:
                user_data.append({
                    "ID": u['id'],
                    "Username": u['username'],
                    "Full Name": u['full_name'],
                    "Email": u['email'],
                    "Role": u['role'],
                    "Status": "Active" if u['is_active'] else "Inactive"
                })
            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with st.expander("➕ Create New User", expanded=False):
            with st.form("create_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Username*")
                    email = st.text_input("Email*")
                    full_name = st.text_input("Full Name*")
                with col2:
                    password = st.text_input("Password*", type="password")
                    role = st.selectbox("Role*", ["DATA_ENTRY", "VERIFIER", "CEO", "ADMIN"])
                    is_active = st.checkbox("Active", value=True)
                
                submitted = st.form_submit_button("Create User", use_container_width=True)
                if submitted and username and email and full_name and password:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        hashed = hash_password(password)
                        cursor.execute('''
                        INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (username, email, full_name, hashed, role, 1 if is_active else 0))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ User '{username}' created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating user: {e}")
    
    with tabs[1]:
        st.markdown("### Master Items")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories WHERE is_active = 1")
        categories = cursor.fetchall()
        conn.close()
        
        cat_options = {c[1]: c[0] for c in categories}
        cat_options["All"] = None
        
        selected_cat = st.selectbox("Filter by Category", list(cat_options.keys()))
        search = st.text_input("Search Items", placeholder="Type to search...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM master_items WHERE is_active = 1"
        params = []
        if cat_options[selected_cat]:
            query += " AND category_id = ?"
            params.append(cat_options[selected_cat])
        if search:
            query += " AND canonical_name LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY canonical_name"
        
        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()
        
        if items:
            item_data = []
            for item in items:
                cat_name = next((c[1] for c in categories if c[0] == item['category_id']), "Uncategorized")
                item_data.append({
                    "ID": item['id'],
                    "Name": item['canonical_name'],
                    "Category": cat_name,
                    "Unit": item['unit'] or "",
                    "Aliases": item['aliases'] or ""
                })
            df = pd.DataFrame(item_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No master items found")
    
    with tabs[2]:
        st.markdown("### Categories")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY sort_order")
        categories = cursor.fetchall()
        conn.close()
        
        if categories:
            cat_data = []
            for cat in categories:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM master_items WHERE category_id = ?", (cat['id'],))
                item_count = cursor.fetchone()[0]
                conn.close()
                
                cat_data.append({
                    "ID": cat['id'],
                    "Name": cat['name'],
                    "Order": cat['sort_order'],
                    "Items": item_count,
                    "Status": "Active" if cat['is_active'] else "Inactive"
                })
            df = pd.DataFrame(cat_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

# ==================== MAIN APPLICATION ====================
def main():
    if "auth" not in st.session_state:
        st.session_state.auth = {"logged_in": False, "user": None}
    
    if "editing_requisition_id" not in st.session_state:
        st.session_state.editing_requisition_id = None
    
    if "verifying_requisition_id" not in st.session_state:
        st.session_state.verifying_requisition_id = None
    
    if "approving_requisition_id" not in st.session_state:
        st.session_state.approving_requisition_id = None
    
    st.markdown("""
    <div class="main-header">
        <h1>🏗️ Construction Requisition System</h1>
        <p>HAJI ABDUL RAHEEM CONSTRUCTION COMPANY - Project Expense Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.auth["logged_in"]:
        login_form()
        st.markdown("---")
        st.info("🔐 Please login to access the system")
        return  # <-- IMPORTANT: Return here, don't show sidebar
    
    # =============================================
    # ONLY SHOW SIDEBAR AND MENU IF LOGGED IN
    # =============================================
    user = st.session_state.auth["user"]
    
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1995/1995515.png", width=80)
        st.markdown(f"""
        <div class="user-info-box">
            <div class="user-name">👤 {user['full_name']}</div>
            <div class="user-role">Role: {user['role']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu_options = []
        icons = []
        
        menu_options.append("🏠 Dashboard")
        icons.append("speedometer2")

        menu_options.append("💰 Balance Statement")
        icons.append("wallet")
        
        if user["role"] in ["ADMIN", "DATA_ENTRY", "VERIFIER", "CEO"]:
            menu_options.append("📋 Projects")
            icons.append("list-task")
            menu_options.append("📄 Requisitions")
            icons.append("clipboard")
            menu_options.append("✅ Approvals")
            icons.append("check-circle")
        
        if user["role"] == "ADMIN":
            menu_options.append("⚙️ Admin")
            icons.append("gear")
        
        menu_options.append("🚪 Logout")
        icons.append("box-arrow-right")
        
        selected = option_menu(
            menu_title=None,
            options=menu_options,
            icons=icons,
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "18px"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "padding": "8px 15px"},
                "nav-link-selected": {"background-color": "#4CAF50", "color": "white"},
            }
        )
        
        if selected == "🚪 Logout":
            st.session_state.auth = {"logged_in": False, "user": None}
            st.rerun()
    
    # Now handle the selected menu option
    if selected == "🏠 Dashboard":
        show_dashboard()
    elif selected == "📋 Projects":
        show_projects()
    elif selected == "📄 Requisitions":
        show_requisitions()
    elif selected == "✅ Approvals":
        show_approvals()
    elif selected == "⚙️ Admin":
        show_admin()
    elif selected == "💰 Balance Statement":
        show_balance_statement()
    
    st.markdown("""
    <div class="footer">
        <p>Construction Requisition System v1.0</p>
        <p>All rights reserved. &copy; 2026 HAJI ABDUL RAHEEM CONSTRUCTION COMPANY</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()