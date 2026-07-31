import sqlite3

def add_financial_columns():
    conn = sqlite3.connect("requisition.db")
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(requisitions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Columns to add
    new_columns = ['paid_amount', 'rar_bills', 'retention_money', 'total_expense', 'profit_loss']
    
    for col in new_columns:
        if col not in columns:
            try:
                cursor.execute(f"ALTER TABLE requisitions ADD COLUMN {col} REAL DEFAULT 0")
                print(f"✅ Added column: {col}")
            except Exception as e:
                print(f"Error adding {col}: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Financial columns added successfully!")

# Run this
add_financial_columns()