# modules/categories.py

import streamlit as st
import pandas as pd
from database import get_db_connection

def show_categories():
    """Categories management page"""
    st.markdown('<div class="section-header">🏷️ Categories</div>', unsafe_allow_html=True)
    
    # Add new category
    with st.expander("➕ Add New Category", expanded=False):
        with st.form("add_category_form"):
            category_name = st.text_input("Category Name*")
            submitted = st.form_submit_button("Add Category", use_container_width=True, type="primary")
            
            if submitted and category_name:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Check if category exists
                    cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        st.warning(f"Category '{category_name}' already exists!")
                    else:
                        cursor.execute(
                            "INSERT INTO categories (name, sort_order, status) VALUES (?, ?, ?)",
                            (category_name, 999, 'Active')
                        )
                        conn.commit()
                        st.success(f"✅ Category '{category_name}' added successfully!")
                        st.rerun()
                    
                    conn.close()
                except Exception as e:
                    st.error(f"Error adding category: {e}")
    
    # Display categories
    st.subheader("All Categories")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, sort_order, status, created_at FROM categories ORDER BY sort_order, name")
    categories = cursor.fetchall()
    conn.close()
    
    if categories:
        # Convert to DataFrame for display
        data = []
        for cat in categories:
            data.append({
                "ID": cat['id'],
                "Category Name": cat['name'],
                "Sort Order": cat['sort_order'],
                "Status": cat['status'],
                "Created": cat['created_at'][:10] if cat['created_at'] else ''
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Delete category option
        st.subheader("Delete Category")
        category_options = {f"{cat['name']} (ID: {cat['id']})": cat['id'] for cat in categories}
        selected_category = st.selectbox("Select category to delete", list(category_options.keys()))
        
        if st.button("🗑️ Delete Selected Category", type="primary"):
            category_id = category_options[selected_category]
            
            # Check if category has transactions
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE category_id = ?", (category_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result['count'] > 0:
                st.error(f"Cannot delete category with {result['count']} transactions. Please reassign transactions first.")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                    conn.commit()
                    conn.close()
                    st.success("✅ Category deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting category: {e}")
    else:
        st.info("No categories found. Add your first category!")