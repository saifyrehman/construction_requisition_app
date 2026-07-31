import streamlit as st
import bcrypt
from database import get_db_connection

def authenticate_user(username, password):
    """Authenticate a user"""
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
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def login_form():
    """Display the login form"""
    st.markdown("""
    
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
            
            # st.caption("Default: admin / admin123")