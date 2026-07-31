import re
from datetime import datetime
from database import get_db_connection

def normalize_text(text):
    """
    Normalize text for matching:
    - Convert to lowercase
    - Remove extra whitespace
    - Remove special characters
    """
    if not text:
        return ""
    text = str(text).lower().strip()
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep alphanumeric and spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text

def find_or_create_master_item(particulars, category_id, unit="nos", user_id=None):
    """
    Find an existing master item or create a new one.
    
    Args:
        particulars (str): The item description
        category_id (int): Category ID
        unit (str): Unit of measurement
        user_id (int): User ID creating the item
    
    Returns:
        int: Master item ID
    """
    if not particulars:
        return None
    
    # Normalize the name for matching
    normalized_name = normalize_text(particulars)
    
    # Truncate to reasonable length
    canonical_name = particulars[:100]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First try to find by exact match
    cursor.execute("""
        SELECT id FROM master_items 
        WHERE canonical_name = ? AND is_active = 1
    """, (canonical_name,))
    
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result['id']
    
    # Try to find by normalized name (approximate matching)
    # Get all active items and compare normalized
    cursor.execute("""
        SELECT id, canonical_name FROM master_items 
        WHERE category_id = ? AND is_active = 1
    """, (category_id,))
    
    items = cursor.fetchall()
    
    for item in items:
        item_normalized = normalize_text(item['canonical_name'])
        if item_normalized == normalized_name:
            conn.close()
            return item['id']
    
    # No match found, create new item
    cursor.execute("""
        INSERT INTO master_items (canonical_name, category_id, unit, aliases, is_active, created_at)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
    """, (canonical_name, category_id, unit, canonical_name))
    
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return item_id

def suggest_matches(text, category_id=None, limit=5):
    """
    Suggest matching master items for a given text.
    
    Args:
        text (str): The text to match
        category_id (int, optional): Filter by category
        limit (int): Maximum number of suggestions
    
    Returns:
        list: List of matching items with id and name
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, canonical_name, unit, category_id 
        FROM master_items 
        WHERE is_active = 1
    """
    params = []
    
    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)
    
    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()
    
    # Score matches based on normalized text similarity
    scored_items = []
    for item in items:
        item_normalized = normalize_text(item['canonical_name'])
        
        # Check if normalized text contains the search term
        if normalized in item_normalized or item_normalized in normalized:
            # Calculate similarity score (simple approach)
            score = 0
            if normalized in item_normalized:
                score += len(normalized) / len(item_normalized)
            if item_normalized in normalized:
                score += len(item_normalized) / len(normalized)
            
            scored_items.append({
                'id': item['id'],
                'name': item['canonical_name'],
                'unit': item['unit'],
                'category_id': item['category_id'],
                'score': score
            })
    
    # Sort by score descending
    scored_items.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top matches
    return scored_items[:limit]

def get_or_create_category(category_name):
    """
    Get or create a category by name.
    
    Args:
        category_name (str): Category name
    
    Returns:
        int: Category ID
    """
    if not category_name:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM categories WHERE name = ? AND is_active = 1", (category_name,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result['id']
    
    # Get max sort order
    cursor.execute("SELECT MAX(sort_order) FROM categories")
    max_order = cursor.fetchone()[0] or 0
    
    # Create new category
    cursor.execute("""
        INSERT INTO categories (name, sort_order, is_active)
        VALUES (?, ?, 1)
    """, (category_name, max_order + 1))
    
    category_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return category_id

def get_master_item(item_id):
    """
    Get a master item by ID.
    
    Args:
        item_id (int): Master item ID
    
    Returns:
        dict: Master item data or None if not found
    """
    if not item_id:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT mi.*, c.name as category_name 
        FROM master_items mi
        LEFT JOIN categories c ON mi.category_id = c.id
        WHERE mi.id = ? AND mi.is_active = 1
    """, (item_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def update_master_item(item_id, canonical_name=None, unit=None, aliases=None):
    """
    Update a master item.
    
    Args:
        item_id (int): Master item ID
        canonical_name (str, optional): New name
        unit (str, optional): New unit
        aliases (str, optional): New aliases
    
    Returns:
        bool: True if successful
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if canonical_name is not None:
        updates.append("canonical_name = ?")
        params.append(canonical_name[:100])
    
    if unit is not None:
        updates.append("unit = ?")
        params.append(unit)
    
    if aliases is not None:
        updates.append("aliases = ?")
        params.append(aliases[:200])
    
    if not updates:
        conn.close()
        return True
    
    query = f"UPDATE master_items SET {', '.join(updates)} WHERE id = ?"
    params.append(item_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return True

def delete_master_item(item_id, soft_delete=True):
    """
    Delete or deactivate a master item.
    
    Args:
        item_id (int): Master item ID
        soft_delete (bool): If True, just deactivate; if False, permanently delete
    
    Returns:
        bool: True if successful
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if soft_delete:
        cursor.execute("UPDATE master_items SET is_active = 0 WHERE id = ?", (item_id,))
    else:
        cursor.execute("DELETE FROM master_items WHERE id = ?", (item_id,))
    
    conn.commit()
    conn.close()
    
    return True

def search_master_items(search_term, category_id=None, limit=20):
    """
    Search for master items by name.
    
    Args:
        search_term (str): Search term
        category_id (int, optional): Filter by category
        limit (int): Maximum results
    
    Returns:
        list: List of matching items
    """
    if not search_term:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT mi.*, c.name as category_name 
        FROM master_items mi
        LEFT JOIN categories c ON mi.category_id = c.id
        WHERE mi.is_active = 1
        AND (mi.canonical_name LIKE ? OR mi.aliases LIKE ?)
    """
    params = [f"%{search_term}%", f"%{search_term}%"]
    
    if category_id:
        query += " AND mi.category_id = ?"
        params.append(category_id)
    
    query += " ORDER BY mi.canonical_name LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_items_by_category(category_id, active_only=True):
    """
    Get all master items in a category.
    
    Args:
        category_id (int): Category ID
        active_only (bool): If True, only return active items
    
    Returns:
        list: List of items
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM master_items WHERE category_id = ?"
    params = [category_id]
    
    if active_only:
        query += " AND is_active = 1"
    
    query += " ORDER BY canonical_name"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]