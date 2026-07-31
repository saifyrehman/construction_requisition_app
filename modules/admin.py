import streamlit as st
import pandas as pd
from database import get_db_connection
from auth import hash_password

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
    
    # In modules/admin.py - Replace the Categories tab section

    with tabs[2]:
        st.markdown("### Categories Management")
        
        # Add new category
        with st.expander("➕ Add New Category", expanded=False):
            with st.form("add_category_form"):
                cat_name = st.text_input("Category Name*")
                sort_order = st.number_input("Sort Order", min_value=0, value=999)
                submitted = st.form_submit_button("Add Category", use_container_width=True)
                
                if submitted and cat_name:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        
                        # Check if exists
                        cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            st.warning(f"Category '{cat_name}' already exists!")
                        else:
                            # Check if status column exists
                            cursor.execute("PRAGMA table_info(categories)")
                            columns = [col[1] for col in cursor.fetchall()]
                            
                            if 'status' in columns:
                                cursor.execute(
                                    "INSERT INTO categories (name, sort_order, status) VALUES (?, ?, ?)",
                                    (cat_name, sort_order, 'Active')
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                                    (cat_name, sort_order)
                                )
                            
                            conn.commit()
                            st.success(f"✅ Category '{cat_name}' added!")
                            st.rerun()
                        
                        conn.close()
                    except Exception as e:
                        st.error(f"Error adding category: {e}")
        
        # Display categories
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if status column exists
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        has_status = 'status' in columns
        
        if has_status:
            cursor.execute("SELECT * FROM categories ORDER BY sort_order, name")
        else:
            cursor.execute("SELECT id, name, sort_order FROM categories ORDER BY sort_order, name")
        
        categories = cursor.fetchall()
        conn.close()
        
        if categories:
            for cat in categories:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{cat['name']}**")
                        st.caption(f"ID: {cat['id']}")
                    
                    with col2:
                        st.write(f"Sort Order: {cat['sort_order']}")
                        # Check if status exists in the row
                        if has_status and 'status' in cat.keys():
                            status = cat['status'] if cat['status'] else 'Active'
                            st.write(f"Status: {'🟢 Active' if status == 'Active' else '🔴 Inactive'}")
                        else:
                            st.write("Status: 🟢 Active")
                    
                    with col3:
                        # Count items in this category
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE category_id = ?", (cat['id'],))
                        result = cursor.fetchone()
                        conn.close()
                        st.write(f"Items: {result['count'] if result else 0}")
                    
                    with col4:
                        # Edit button
                        if st.button("✏️ Edit", key=f"edit_cat_{cat['id']}"):
                            st.session_state.editing_category_id = cat['id']
                            st.rerun()
                        
                        # Delete button (only if no items)
                        if result and result['count'] == 0:
                            if st.button("🗑️ Delete", key=f"del_cat_{cat['id']}"):
                                try:
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM categories WHERE id = ?", (cat['id'],))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"✅ Category '{cat['name']}' deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting category: {e}")
                        else:
                            st.button("🗑️ Delete", key=f"del_cat_{cat['id']}", disabled=True, help="Category has items")
            
            # Edit category dialog
            if st.session_state.get("editing_category_id"):
                cat_id = st.session_state.editing_category_id
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if status column exists
                cursor.execute("PRAGMA table_info(categories)")
                columns = [col[1] for col in cursor.fetchall()]
                has_status = 'status' in columns
                
                if has_status:
                    cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
                else:
                    cursor.execute("SELECT id, name, sort_order FROM categories WHERE id = ?", (cat_id,))
                
                cat = cursor.fetchone()
                conn.close()
                
                if cat:
                    with st.expander(f"✏️ Editing: {cat['name']}", expanded=True):
                        with st.form("edit_category_form"):
                            new_name = st.text_input("Category Name", value=cat['name'])
                            new_sort_order = st.number_input("Sort Order", value=cat['sort_order'])
                            
                            # Only show status if column exists
                            if has_status:
                                current_status = cat['status'] if cat['status'] else 'Active'
                                new_status = st.selectbox("Status", ["Active", "Inactive"], 
                                                        index=0 if current_status == 'Active' else 1)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                    try:
                                        conn = get_db_connection()
                                        cursor = conn.cursor()
                                        
                                        if has_status:
                                            cursor.execute(
                                                "UPDATE categories SET name = ?, sort_order = ?, status = ? WHERE id = ?",
                                                (new_name, new_sort_order, new_status, cat_id)
                                            )
                                        else:
                                            cursor.execute(
                                                "UPDATE categories SET name = ?, sort_order = ? WHERE id = ?",
                                                (new_name, new_sort_order, cat_id)
                                            )
                                        
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ Category updated!")
                                        st.session_state.editing_category_id = None
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error updating category: {e}")
                            
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state.editing_category_id = None
                                    st.rerun()
        else:
            st.info("No categories found. Add your first category!")