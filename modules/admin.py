# modules/admin.py - Complete fixed version

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
    
    # ==================== USERS TAB ====================
    with tabs[0]:
        st.markdown("### User Management")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if is_active column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        has_is_active = 'is_active' in columns
        
        if has_is_active:
            cursor.execute("SELECT * FROM users ORDER BY created_at")
        else:
            cursor.execute("SELECT id, username, email, full_name, role, created_at, last_login FROM users ORDER BY created_at")
        
        users = cursor.fetchall()
        conn.close()
        
        if users:
            user_data = []
            for u in users:
                row = {
                    "ID": u['id'],
                    "Username": u['username'],
                    "Full Name": u['full_name'],
                    "Email": u['email'],
                    "Role": u['role'],
                }
                if has_is_active:
                    row["Status"] = "Active" if u['is_active'] else "Inactive"
                else:
                    row["Status"] = "Active"
                user_data.append(row)
            
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
                        
                        # Check if is_active column exists
                        cursor.execute("PRAGMA table_info(users)")
                        columns = [col[1] for col in cursor.fetchall()]
                        has_is_active = 'is_active' in columns
                        
                        if has_is_active:
                            cursor.execute('''
                            INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''', (username, email, full_name, hashed, role, 1 if is_active else 0))
                        else:
                            cursor.execute('''
                            INSERT INTO users (username, email, full_name, hashed_password, role)
                            VALUES (?, ?, ?, ?, ?)
                            ''', (username, email, full_name, hashed, role))
                        
                        conn.commit()
                        conn.close()
                        st.success(f"✅ User '{username}' created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating user: {e}")
    
    # ==================== MASTER ITEMS TAB ====================
    with tabs[1]:
        st.markdown("### Master Items")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if is_active column exists in categories
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        has_is_active = 'is_active' in columns
        
        if has_is_active:
            cursor.execute("SELECT id, name FROM categories WHERE is_active = 1")
        else:
            cursor.execute("SELECT id, name FROM categories")
        
        categories = cursor.fetchall()
        conn.close()
        
        cat_options = {c['name']: c['id'] for c in categories}
        cat_options["All Categories"] = None
        
        selected_cat = st.selectbox("Filter by Category", list(cat_options.keys()))
        search = st.text_input("Search Items", placeholder="Type to search...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if is_active column exists in master_items
        cursor.execute("PRAGMA table_info(master_items)")
        columns = [col[1] for col in cursor.fetchall()]
        has_is_active = 'is_active' in columns
        
        query = "SELECT * FROM master_items"
        params = []
        conditions = []
        
        if has_is_active:
            conditions.append("is_active = 1")
        
        if selected_cat != "All Categories":
            conditions.append("category_id = ?")
            params.append(cat_options[selected_cat])
        
        if search:
            conditions.append("canonical_name LIKE ?")
            params.append(f"%{search}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY canonical_name"
        
        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()
        
        if items:
            item_data = []
            for item in items:
                cat_name = next((c['name'] for c in categories if c['id'] == item['category_id']), "Uncategorized")
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
        
        # Add new master item
        with st.expander("➕ Add New Master Item", expanded=False):
            with st.form("add_master_item_form"):
                col1, col2 = st.columns(2)
                with col1:
                    item_name = st.text_input("Item Name*")
                    cat_choice = st.selectbox("Category", list(cat_options.keys()) if len(cat_options) > 1 else ["No categories"])
                with col2:
                    unit = st.text_input("Unit (e.g., kg, m, pcs)")
                    aliases = st.text_input("Aliases (comma separated)")
                
                submitted = st.form_submit_button("Add Item", use_container_width=True)
                if submitted and item_name and cat_choice != "All Categories" and cat_choice != "No categories":
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                        INSERT INTO master_items (canonical_name, category_id, unit, aliases, is_active)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (item_name, cat_options[cat_choice], unit, aliases, 1))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Item '{item_name}' added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding item: {e}")
    
    # ==================== CATEGORIES TAB ====================
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
                            
                            if 'status' in columns and 'is_active' in columns:
                                cursor.execute(
                                    "INSERT INTO categories (name, sort_order, status, is_active) VALUES (?, ?, ?, ?)",
                                    (cat_name, sort_order, 'Active', 1)
                                )
                            elif 'status' in columns:
                                cursor.execute(
                                    "INSERT INTO categories (name, sort_order, status) VALUES (?, ?, ?)",
                                    (cat_name, sort_order, 'Active')
                                )
                            elif 'is_active' in columns:
                                cursor.execute(
                                    "INSERT INTO categories (name, sort_order, is_active) VALUES (?, ?, ?)",
                                    (cat_name, sort_order, 1)
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
        
        # Check available columns
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        has_status = 'status' in columns
        has_is_active = 'is_active' in columns
        
        # Build SELECT query based on available columns
        select_cols = ['id', 'name', 'sort_order']
        if has_status:
            select_cols.append('status')
        if has_is_active:
            select_cols.append('is_active')
        
        cursor.execute(f"SELECT {', '.join(select_cols)} FROM categories ORDER BY sort_order, name")
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
                        if has_status:
                            # Access directly, not with .get()
                            status = cat['status'] if cat['status'] else 'Active'
                            st.write(f"Status: {'🟢 Active' if status == 'Active' else '🔴 Inactive'}")
                        elif has_is_active:
                            # Access directly, not with .get()
                            is_active = cat['is_active'] if cat['is_active'] is not None else 1
                            st.write(f"Status: {'🟢 Active' if is_active == 1 else '🔴 Inactive'}")
                        else:
                            st.write("Status: 🟢 Active")
                    
                    with col3:
                        # Count items in this category
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) as count FROM master_items WHERE category_id = ?", (cat['id'],))
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
                cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
                cat = cursor.fetchone()
                conn.close()
                
                if cat:
                    with st.expander(f"✏️ Editing: {cat['name']}", expanded=True):
                        with st.form("edit_category_form"):
                            new_name = st.text_input("Category Name", value=cat['name'])
                            new_sort_order = st.number_input("Sort Order", value=cat['sort_order'])
                            
                            # Check available columns for status
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("PRAGMA table_info(categories)")
                            columns = [col[1] for col in cursor.fetchall()]
                            conn.close()
                            
                            has_status = 'status' in columns
                            has_is_active = 'is_active' in columns
                            
                            if has_status:
                                # Access directly, not with .get()
                                current_status = cat['status'] if cat['status'] else 'Active'
                                new_status = st.selectbox("Status", ["Active", "Inactive"], 
                                                        index=0 if current_status == 'Active' else 1)
                            elif has_is_active:
                                # Access directly, not with .get()
                                current_is_active = cat['is_active'] if cat['is_active'] is not None else 1
                                new_is_active = st.selectbox("Status", [1, 0], 
                                                           format_func=lambda x: "Active" if x == 1 else "Inactive",
                                                           index=0 if current_is_active == 1 else 1)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                    try:
                                        conn = get_db_connection()
                                        cursor = conn.cursor()
                                        
                                        update_parts = ["name = ?", "sort_order = ?"]
                                        params = [new_name, new_sort_order]
                                        
                                        if has_status:
                                            update_parts.append("status = ?")
                                            params.append(new_status)
                                        elif has_is_active:
                                            update_parts.append("is_active = ?")
                                            params.append(new_is_active)
                                        
                                        params.append(cat_id)
                                        query = f"UPDATE categories SET {', '.join(update_parts)} WHERE id = ?"
                                        
                                        cursor.execute(query, params)
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

# Add this to fix the database schema if needed
def fix_admin_schema():
    """Fix missing columns in admin tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check and add is_active to categories if missing
    cursor.execute("PRAGMA table_info(categories)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_active' not in columns and 'status' not in columns:
        try:
            cursor.execute("ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ Added is_active column to categories")
        except Exception as e:
            print(f"⚠️ Could not add is_active to categories: {e}")
    
    # Check and add is_active to master_items if missing
    cursor.execute("PRAGMA table_info(master_items)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_active' not in columns:
        try:
            cursor.execute("ALTER TABLE master_items ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ Added is_active column to master_items")
        except Exception as e:
            print(f"⚠️ Could not add is_active to master_items: {e}")
    
    conn.commit()
    conn.close()

# Call this function when initializing the database