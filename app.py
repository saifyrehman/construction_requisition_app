# app.py - Fixed version

import streamlit as st
from streamlit_option_menu import option_menu
import sys
import os
import pandas as pd
from datetime import datetime
import sqlite3
import bcrypt
import io

# Import from your modules
from config import *
from database import (
    get_db_connection,
    init_database,
    seed_default_data,
    fix_database_nulls,
    fix_database_schema,
    initialize_database
)

from auth import authenticate_user, login_form, hash_password
from utils.helpers import get_status_badge, format_currency, import_excel_data
from utils.pdf_generator import generate_requisition_pdf, generate_project_summary_pdf

# Import page functions
from modules.dashboard import show_dashboard
from modules.requisitions import show_requisitions
from modules.projects import show_projects
from modules.contractors import show_contractors
from modules.categories import show_categories
from modules.reports import show_reports
from modules.approvals import show_approvals
from modules.admin import show_admin
from modules.balance import show_balance_statement

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize database on first run
from database import initialize_database
try:
    initialize_database()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

# Rest of your imports and code...
from config import *



# Initialize database
initialize_database()

# Configure page
st.set_page_config(
    page_title=APP_NAME,
    page_icon=ICON_PATH if has_icon() else "🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
def load_css():
    """Load custom CSS"""
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
        /* Banner container styling */
        .banner-container {
            text-align: center;
            margin: 0 auto 20px auto;
            max-width: 900px;
            padding: 10px;
        }
        .banner-container img {
            width: 100%;
            max-width: 900px;
            height: auto;
            border-radius: 10px;
            display: block;
            margin: 0 auto;
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
        /* Hide Streamlit's default sidebar navigation */
        .stSidebarNav {
            display: none !important;
        }
        /* Hide sidebar when not logged in */
        .css-1d391kg {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
def display_banner():
    """Display banner image with proper sizing"""
    # Check if banner exists
    banner_path = os.path.join(STATIC_DIR, "banner.png")
    
    if os.path.exists(banner_path):
        # Use HTML/CSS to display banner with exact dimensions
        import base64
        with open(banner_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
        
        # Use HTML with CSS for exact control
        st.markdown(f"""
        <div style="text-align: center; margin: 0 auto; padding: 10px 0;">
            <img src="data:image/png;base64,{img_data}" 
                 style="height: 300px; width: 1800px;  border-radius: 10px;">
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to text header if banner not found
        st.markdown(f"""
        <div class="main-header">
            <h1>🏗️ {APP_NAME}</h1>
            <p>{COMPANY_NAME} - Project Expense Management</p>
        </div>
        """, unsafe_allow_html=True)

# ==================== MAIN APPLICATION ====================
# ==================== MAIN APPLICATION ====================
def main():
    # Load CSS
    load_css()
    
    # Initialize session state
    if "auth" not in st.session_state:
        st.session_state.auth = {"logged_in": False, "user": None}
    
    if "editing_requisition_id" not in st.session_state:
        st.session_state.editing_requisition_id = None
    
    if "verifying_requisition_id" not in st.session_state:
        st.session_state.verifying_requisition_id = None
    
    if "approving_requisition_id" not in st.session_state:
        st.session_state.approving_requisition_id = None
    
    # Display banner
    display_banner()
    
    # =============================================
    # CHECK AUTHENTICATION - SIDEBAR ONLY SHOWS WHEN LOGGED IN
    # =============================================
    if not st.session_state.auth["logged_in"]:
        login_form()
        st.markdown("---")
        st.info("🔐 Please login to access the system")
        return
    
    # =============================================
    # USER IS LOGGED IN - SHOW SIDEBAR AND CONTENT
    # =============================================
    user = st.session_state.auth["user"]
    
    # === SIDEBAR (ONLY SHOWN WHEN LOGGED IN) ===
    with st.sidebar:
        # Show logo
        try:
            st.image("static/logo.png", width=80)
        except:
            st.image("https://cdn-icons-png.flaticon.com/512/1995/1995515.png", width=80)
        
        # User info
        st.markdown(f"""
        <div class="user-info-box">
            <div class="user-name">👤 {user['full_name']}</div>
            <div class="user-role">Role: {user['role']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Menu options based on role
        menu_options = ["🏠 Dashboard", "💰 Balance Statement", "👷 Contractors", "📊 Reports"]
        icons = ["speedometer2", "wallet", "people", "graph-up"]

        if user["role"] in ["ADMIN", "DATA_ENTRY", "VERIFIER", "CEO"]:
            menu_options.extend(["📋 Projects", "📄 Requisitions", "✅ Approvals"])
            icons.extend(["list-task", "clipboard", "check-circle"])

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
    
    # =============================================
    # ROUTE TO APPROPRIATE PAGE
    # =============================================
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
    elif selected == "👷 Contractors":
        show_contractors()
    elif selected == "📊 Reports":
        show_reports()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Construction Requisition System v1.0</p>
        <p>All rights reserved. &copy; 2026 HAJI ABDUL RAHEEM CONSTRUCTION COMPANY</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()