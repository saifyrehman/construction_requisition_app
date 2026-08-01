# database.py - Complete file with all functions for cloud deployment

import sqlite3
import bcrypt
from datetime import datetime
import os
import time

DB_PATH = "requisition.db"

def get_db_connection():
    """Get database connection with proper settings for cloud"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_database():
    """Initialize database with all tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
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
    
    # Projects table
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
    
    # Categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        sort_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert default categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany('''
        INSERT OR IGNORE INTO categories (name, sort_order, status) 
        VALUES (?, ?, ?)
        ''', [
            ('Site Work', 1, 'Active'),
            ('Materials', 2, 'Active'),
            ('Miscellaneous & Administration', 3, 'Active')
        ])
    
    # Create index for categories
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)")
    
    # Master Items table
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
    
    # Requisitions table
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
        expense_paid_last_req REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        rar_bills REAL DEFAULT 0,
        retention_money REAL DEFAULT 0,
        total_expense REAL DEFAULT 0,
        profit_loss REAL DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    ''')
    
    # Transactions table
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
        contractor_id INTEGER,
        FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (master_item_id) REFERENCES master_items (id),
        FOREIGN KEY (contractor_id) REFERENCES contractors (id)
    )
    ''')
    
    # Contractors table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contractors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        cnic TEXT,
        bank_name TEXT,
        bank_account TEXT,
        tax_id TEXT,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_id INTEGER,
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    ''')
    
    # Contractor Payments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contractor_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contractor_id INTEGER NOT NULL,
        requisition_id INTEGER,
        project_id INTEGER NOT NULL,
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        payment_reference TEXT,
        amount REAL DEFAULT 0,
        payment_type TEXT,
        description TEXT,
        status TEXT DEFAULT 'PENDING',
        approved_by_id INTEGER,
        created_by_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contractor_id) REFERENCES contractors (id),
        FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (approved_by_id) REFERENCES users (id),
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requisitions_project ON requisitions(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requisitions_status ON requisitions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_requisition ON transactions(requisition_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_contractor ON contractor_payments(contractor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_project ON contractor_payments(project_id)")
    
    conn.commit()
    conn.close()
    print("✅ Database tables created successfully")

def fix_admin_tables():
    """Fix admin tables with missing columns"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add is_active to categories if missing
    cursor.execute("PRAGMA table_info(categories)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_active' not in columns:
        try:
            cursor.execute("ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1")
            print("✅ Added is_active column to categories")
        except Exception as e:
            print(f"⚠️ Could not add is_active to categories: {e}")
    
    # Add is_active to master_items if missing
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

# Call this in your initialize_database function

def seed_default_data():
    """Seed default data into the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    if not admin:
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
        INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ("admin", "admin@company.com", "System Administrator", hashed, "ADMIN", 1))
        print("✅ Admin user created")
    
    conn.commit()
    conn.close()

def fix_database_nulls():
    """Fix NULL values in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist before fixing
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if cursor.fetchone():
            cursor.execute('''
            UPDATE projects 
            SET opening_balance = COALESCE(opening_balance, 0),
                current_balance = COALESCE(current_balance, 0),
                status = COALESCE(status, 'Active'),
                location = COALESCE(location, '')
            WHERE opening_balance IS NULL OR current_balance IS NULL OR status IS NULL
            ''')
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requisitions'")
        if cursor.fetchone():
            cursor.execute('''
            UPDATE requisitions 
            SET opening_balance = COALESCE(opening_balance, 0),
                closing_balance = COALESCE(closing_balance, 0),
                total_amount = COALESCE(total_amount, 0),
                status = COALESCE(status, 'DRAFT')
            ''')
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        if cursor.fetchone():
            cursor.execute('''
            UPDATE transactions 
            SET qty = COALESCE(qty, 0),
                rate = COALESCE(rate, 0),
                amount = COALESCE(amount, 0)
            ''')
        
        conn.commit()
        conn.close()
        print("✅ Fixed NULL values in database")
    except Exception as e:
        print(f"⚠️ Error fixing nulls: {e}")

def fix_database_schema():
    """Add missing columns to existing database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if requisitions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requisitions'")
        if cursor.fetchone():
            # Check for existing columns
            cursor.execute("PRAGMA table_info(requisitions)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Add financial summary columns if they don't exist
            columns_to_add = {
                'expense_paid_last_req': 'REAL DEFAULT 0',
                'paid_amount': 'REAL DEFAULT 0',
                'rar_bills': 'REAL DEFAULT 0',
                'retention_money': 'REAL DEFAULT 0',
                'total_expense': 'REAL DEFAULT 0',
                'profit_loss': 'REAL DEFAULT 0'
            }
            
            for col_name, col_type in columns_to_add.items():
                if col_name not in column_names:
                    try:
                        cursor.execute(f"ALTER TABLE requisitions ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added {col_name} column")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"⚠️ Could not add {col_name}: {e}")
        
        # Check if transactions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(transactions)")
            trans_columns = cursor.fetchall()
            trans_column_names = [col[1] for col in trans_columns]
            
            if 'contractor_id' not in trans_column_names:
                try:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN contractor_id INTEGER")
                    print("✅ Added contractor_id column to transactions")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"⚠️ Could not add contractor_id: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Schema fixed")
        
    except Exception as e:
        print(f"⚠️ Error fixing schema: {e}")

def initialize_database():
    """Complete database initialization"""
    try:
        # Check if database exists
        if not os.path.exists(DB_PATH):
            print("🔄 Creating new database...")
            init_database()
            seed_default_data()
            fix_admin_tables()
            print("✅ Database created and seeded")
        else:
            print("🔄 Updating existing database...")
            
            # Check if requisitions table exists
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requisitions'")
            requisitions_exists = cursor.fetchone()
            conn.close()
            
            # If requisitions table doesn't exist, reinitialize the database
            if not requisitions_exists:
                print("🔄 Requisitions table missing - recreating database...")
                # Backup old database
                if os.path.exists(DB_PATH):
                    import shutil
                    backup_path = f"{DB_PATH}.backup"
                    shutil.copy2(DB_PATH, backup_path)
                    print(f"📦 Backed up old database to {backup_path}")
                    
                    # Remove old database
                    os.remove(DB_PATH)
                    print("🗑️ Removed old database")
                
                # Create fresh database
                init_database()
                seed_default_data()
                print("✅ Fresh database created")
            else:
                # Check and create contractors table if needed
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contractors'")
                if not cursor.fetchone():
                    cursor.execute('''
                    CREATE TABLE contractors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        code TEXT UNIQUE NOT NULL,
                        contact_person TEXT,
                        phone TEXT,
                        email TEXT,
                        address TEXT,
                        cnic TEXT,
                        bank_name TEXT,
                        bank_account TEXT,
                        tax_id TEXT,
                        status TEXT DEFAULT 'Active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by_id INTEGER,
                        FOREIGN KEY (created_by_id) REFERENCES users (id)
                    )
                    ''')
                    print("✅ Created contractors table")
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contractor_payments'")
                if not cursor.fetchone():
                    cursor.execute('''
                    CREATE TABLE contractor_payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contractor_id INTEGER NOT NULL,
                        requisition_id INTEGER,
                        project_id INTEGER NOT NULL,
                        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        payment_reference TEXT,
                        amount REAL DEFAULT 0,
                        payment_type TEXT,
                        description TEXT,
                        status TEXT DEFAULT 'PENDING',
                        approved_by_id INTEGER,
                        created_by_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (contractor_id) REFERENCES contractors (id),
                        FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
                        FOREIGN KEY (project_id) REFERENCES projects (id),
                        FOREIGN KEY (approved_by_id) REFERENCES users (id),
                        FOREIGN KEY (created_by_id) REFERENCES users (id)
                    )
                    ''')
                    print("✅ Created contractor_payments table")
                
                conn.commit()
                conn.close()
                
                # Fix data and schema
                fix_database_nulls()
                fix_database_schema()
                print("✅ Database updated successfully")
                
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
        import traceback
        traceback.print_exc()

# ============ USER FUNCTIONS ============

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        print(f"Error in get_user_by_username: {e}")
        return None
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials"""
    try:
        user = get_user_by_username(username)
        if user and user['is_active'] == 1:
            if bcrypt.checkpw(password.encode('utf-8'), user['hashed_password'].encode('utf-8')):
                return user
        return None
    except Exception as e:
        print(f"Error in verify_user: {e}")
        return None

def update_last_login(user_id):
    """Update user's last login timestamp"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_last_login: {e}")
        return False
    finally:
        conn.close()

def create_user(username, email, full_name, password, role='USER'):
    """Create a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
        INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, full_name, hashed, role, 1))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError as e:
        print(f"Error in create_user (integrity): {e}")
        return None
    except Exception as e:
        print(f"Error in create_user: {e}")
        return None
    finally:
        conn.close()

def get_users():
    """Get all users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, email, full_name, role, is_active, created_at, last_login FROM users ORDER BY username")
        users = cursor.fetchall()
        return [dict(user) for user in users]
    except Exception as e:
        print(f"Error in get_users: {e}")
        return []
    finally:
        conn.close()

# ============ PROJECT FUNCTIONS ============

def get_projects():
    """Get all projects"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM projects ORDER BY name")
        projects = cursor.fetchall()
        return [dict(project) for project in projects]
    except Exception as e:
        print(f"Error in get_projects: {e}")
        return []
    finally:
        conn.close()

def get_project(project_id):
    """Get a single project"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        return dict(project) if project else None
    except Exception as e:
        print(f"Error in get_project: {e}")
        return None
    finally:
        conn.close()

def create_project(name, code, location, opening_balance=0, created_by_id=None):
    """Create a new project"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO projects (name, code, location, opening_balance, current_balance, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, code, location, opening_balance, opening_balance, created_by_id))
        project_id = cursor.lastrowid
        conn.commit()
        return project_id
    except sqlite3.IntegrityError as e:
        print(f"Error in create_project (integrity): {e}")
        return None
    except Exception as e:
        print(f"Error in create_project: {e}")
        return None
    finally:
        conn.close()

def update_project(project_id, name, location, status):
    """Update project details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        UPDATE projects 
        SET name = ?, location = ?, status = ?
        WHERE id = ?
        ''', (name, location, status, project_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_project: {e}")
        return False
    finally:
        conn.close()

# ============ CONTRACTOR FUNCTIONS ============

def get_contractors(status='Active'):
    """Get all contractors"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if status == 'All':
            cursor.execute("SELECT * FROM contractors ORDER BY name")
        else:
            cursor.execute("SELECT * FROM contractors WHERE status = ? ORDER BY name", (status,))
        contractors = cursor.fetchall()
        
        result = []
        for c in contractors:
            result.append({
                'id': c['id'],
                'name': c['name'] or '',
                'code': c['code'] or '',
                'contact_person': c['contact_person'] or '',
                'phone': c['phone'] or '',
                'email': c['email'] or '',
                'address': c['address'] or '',
                'cnic': c['cnic'] or '',
                'bank_name': c['bank_name'] or '',
                'bank_account': c['bank_account'] or '',
                'tax_id': c['tax_id'] or '',
                'status': c['status'] or 'Active',
                'created_at': c['created_at'],
                'created_by_id': c['created_by_id']
            })
        return result
    except Exception as e:
        print(f"Error in get_contractors: {e}")
        return []
    finally:
        conn.close()

def get_contractor(contractor_id):
    """Get a single contractor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM contractors WHERE id = ?", (contractor_id,))
        c = cursor.fetchone()
        if not c:
            return None
        
        return {
            'id': c['id'],
            'name': c['name'] or '',
            'code': c['code'] or '',
            'contact_person': c['contact_person'] or '',
            'phone': c['phone'] or '',
            'email': c['email'] or '',
            'address': c['address'] or '',
            'cnic': c['cnic'] or '',
            'bank_name': c['bank_name'] or '',
            'bank_account': c['bank_account'] or '',
            'tax_id': c['tax_id'] or '',
            'status': c['status'] or 'Active',
            'created_at': c['created_at'],
            'created_by_id': c['created_by_id']
        }
    except Exception as e:
        print(f"Error in get_contractor: {e}")
        return None
    finally:
        conn.close()

def create_contractor(data, user_id):
    """Create a new contractor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO contractors 
        (name, code, contact_person, phone, email, address, cnic, bank_name, bank_account, tax_id, status, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['code'], data['contact_person'], data['phone'], data['email'], 
              data['address'], data['cnic'], data['bank_name'], data['bank_account'], data['tax_id'], 
              'Active', user_id))
        contractor_id = cursor.lastrowid
        conn.commit()
        return contractor_id
    except sqlite3.IntegrityError as e:
        print(f"Error in create_contractor (integrity): {e}")
        return None
    except Exception as e:
        print(f"Error in create_contractor: {e}")
        return None
    finally:
        conn.close()

def add_contractor_payment(data, user_id):
    """Add a payment record for a contractor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO contractor_payments 
            (contractor_id, project_id, requisition_id, payment_date, 
             payment_reference, amount, payment_type, description, status, created_by_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['contractor_id'],
            data['project_id'],
            data.get('requisition_id'),
            data['payment_date'],
            data['payment_reference'],
            data['amount'],
            data['payment_type'],
            data.get('description', ''),
            'PENDING',
            user_id
        ))
        
        payment_id = cursor.lastrowid
        conn.commit()
        return payment_id
    except Exception as e:
        conn.rollback()
        print(f"Error in add_contractor_payment: {e}")
        return None
    finally:
        conn.close()

def get_contractor_payments(contractor_id=None, project_id=None, status=None):
    """Get contractor payments with filters"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = '''
        SELECT 
            cp.*, 
            c.name as contractor_name, 
            p.name as project_name,
            u.full_name as created_by_name
        FROM contractor_payments cp
        LEFT JOIN contractors c ON cp.contractor_id = c.id
        LEFT JOIN projects p ON cp.project_id = p.id
        LEFT JOIN users u ON cp.created_by_id = u.id
        WHERE 1=1
        '''
        params = []
        
        if contractor_id:
            query += " AND cp.contractor_id = ?"
            params.append(contractor_id)
        
        if project_id:
            query += " AND cp.project_id = ?"
            params.append(project_id)
        
        if status and status != 'All':
            query += " AND cp.status = ?"
            params.append(status)
        
        query += " ORDER BY cp.payment_date DESC"
        
        cursor.execute(query, params)
        payments = cursor.fetchall()
        
        result = []
        for p in payments:
            result.append({
                'id': p['id'],
                'contractor_id': p['contractor_id'],
                'contractor_name': p['contractor_name'] or '',
                'project_id': p['project_id'],
                'project_name': p['project_name'] or '',
                'requisition_id': p['requisition_id'],
                'payment_date': p['payment_date'],
                'payment_reference': p['payment_reference'] or '',
                'amount': p['amount'] if p['amount'] is not None else 0,
                'payment_type': p['payment_type'] or '',
                'description': p['description'] or '',
                'status': p['status'] or 'PENDING',
                'created_by_name': p['created_by_name'] or '',
                'created_at': p['created_at'],
                'updated_at': p['updated_at']
            })
        return result
        
    except Exception as e:
        print(f"Error in get_contractor_payments: {e}")
        return []
    finally:
        conn.close()

def get_contractor_summary(contractor_id):
    """Get summary of payments for a contractor"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT 
            COUNT(*) as total_payments,
            COALESCE(SUM(amount), 0) as total_amount,
            COALESCE(SUM(CASE WHEN status = 'PAID' THEN amount ELSE 0 END), 0) as paid_amount,
            COALESCE(SUM(CASE WHEN status = 'PENDING' THEN amount ELSE 0 END), 0) as pending_amount
        FROM contractor_payments
        WHERE contractor_id = ?
        ''', (contractor_id,))
        
        summary = cursor.fetchone()
        
        if not summary:
            return {
                'total_payments': 0,
                'total_amount': 0,
                'paid_amount': 0,
                'pending_amount': 0
            }
        
        return {
            'total_payments': summary['total_payments'] if summary['total_payments'] is not None else 0,
            'total_amount': summary['total_amount'] if summary['total_amount'] is not None else 0,
            'paid_amount': summary['paid_amount'] if summary['paid_amount'] is not None else 0,
            'pending_amount': summary['pending_amount'] if summary['pending_amount'] is not None else 0
        }
        
    except Exception as e:
        print(f"Error in get_contractor_summary: {e}")
        return {
            'total_payments': 0,
            'total_amount': 0,
            'paid_amount': 0,
            'pending_amount': 0
        }
    finally:
        conn.close()

def update_payment_status(payment_id, status, user_id):
    """Update payment status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        UPDATE contractor_payments 
        SET status = ?, updated_at = CURRENT_TIMESTAMP, approved_by_id = ?
        WHERE id = ?
        ''', (status, user_id, payment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_payment_status: {e}")
        return False
    finally:
        conn.close()

def delete_payment(payment_id):
    """Delete a payment record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM contractor_payments WHERE id = ?", (payment_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in delete_payment: {e}")
        return False
    finally:
        conn.close()

# ============ CATEGORY FUNCTIONS ============

def get_categories():
    """Get all categories"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM categories WHERE status = 'Active' ORDER BY sort_order")
        categories = cursor.fetchall()
        return [dict(category) for category in categories]
    except Exception as e:
        print(f"Error in get_categories: {e}")
        return []
    finally:
        conn.close()

# ============ REQUISITION FUNCTIONS ============

def create_requisition(project_id, ref_no, period_start, period_end, created_by_id):
    """Create a new requisition"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO requisitions (
            project_id, ref_no, period_start, period_end, 
            created_by_id, status, opening_balance, closing_balance, total_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, ref_no, period_start, period_end, created_by_id, 'DRAFT', 0, 0, 0))
        requisition_id = cursor.lastrowid
        conn.commit()
        return requisition_id
    except Exception as e:
        print(f"Error in create_requisition: {e}")
        return None
    finally:
        conn.close()

def get_requisitions(project_id=None, status=None):
    """Get requisitions with optional filters"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
        SELECT r.*, p.name as project_name, 
               u1.full_name as created_by_name,
               u2.full_name as submitted_by_name,
               u3.full_name as verified_by_name,
               u4.full_name as approved_by_name
        FROM requisitions r
        LEFT JOIN projects p ON r.project_id = p.id
        LEFT JOIN users u1 ON r.created_by_id = u1.id
        LEFT JOIN users u2 ON r.submitted_by_id = u2.id
        LEFT JOIN users u3 ON r.verified_by_id = u3.id
        LEFT JOIN users u4 ON r.approved_by_id = u4.id
        WHERE 1=1
        '''
        params = []
        
        if project_id:
            query += " AND r.project_id = ?"
            params.append(project_id)
        
        if status:
            query += " AND r.status = ?"
            params.append(status)
        
        query += " ORDER BY r.created_at DESC"
        
        cursor.execute(query, params)
        requisitions = cursor.fetchall()
        return [dict(req) for req in requisitions]
    except Exception as e:
        print(f"Error in get_requisitions: {e}")
        return []
    finally:
        conn.close()

def get_requisition(requisition_id):
    """Get a single requisition with its details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        SELECT r.*, p.name as project_name, 
               u1.full_name as created_by_name,
               u2.full_name as submitted_by_name,
               u3.full_name as verified_by_name,
               u4.full_name as approved_by_name
        FROM requisitions r
        LEFT JOIN projects p ON r.project_id = p.id
        LEFT JOIN users u1 ON r.created_by_id = u1.id
        LEFT JOIN users u2 ON r.submitted_by_id = u2.id
        LEFT JOIN users u3 ON r.verified_by_id = u3.id
        LEFT JOIN users u4 ON r.approved_by_id = u4.id
        WHERE r.id = ?
        ''', (requisition_id,))
        requisition = cursor.fetchone()
        return dict(requisition) if requisition else None
    except Exception as e:
        print(f"Error in get_requisition: {e}")
        return None
    finally:
        conn.close()

def update_requisition_status(requisition_id, status, user_id=None, comments=None):
    """Update requisition status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get current requisition first
        cursor.execute("SELECT status, project_id, total_amount FROM requisitions WHERE id = ?", (requisition_id,))
        req = cursor.fetchone()
        if not req:
            return False
        
        update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if status == 'SUBMITTED':
            update_fields.append("submitted_at = CURRENT_TIMESTAMP")
            update_fields.append("submitted_by_id = ?")
            params.append(user_id)
        elif status == 'VERIFIED':
            update_fields.append("verified_at = CURRENT_TIMESTAMP")
            update_fields.append("verified_by_id = ?")
            params.append(user_id)
            if comments:
                update_fields.append("verifier_comments = ?")
                params.append(comments)
        elif status == 'APPROVED':
            update_fields.append("approved_at = CURRENT_TIMESTAMP")
            update_fields.append("approved_by_id = ?")
            params.append(user_id)
            if comments:
                update_fields.append("approver_comments = ?")
                params.append(comments)
        elif status == 'REJECTED':
            if comments:
                update_fields.append("rejection_reason = ?")
                params.append(comments)
        
        params.append(requisition_id)
        query = f"UPDATE requisitions SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in update_requisition_status: {e}")
        return False
    finally:
        conn.close()

# ============ TRANSACTION FUNCTIONS ============

def add_transaction(requisition_id, data):
    """Add a transaction to a requisition"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO transactions (
            requisition_id, category_id, master_item_id, particulars_raw,
            qty, unit, rate, amount, remarks, sr_no, is_lump_sum, entered_by_id, contractor_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            requisition_id,
            data.get('category_id'),
            data.get('master_item_id'),
            data.get('particulars_raw', ''),
            data.get('qty', 0),
            data.get('unit', ''),
            data.get('rate', 0),
            data.get('amount', 0),
            data.get('remarks', ''),
            data.get('sr_no'),
            data.get('is_lump_sum', 0),
            data.get('entered_by_id'),
            data.get('contractor_id')
        ))
        transaction_id = cursor.lastrowid
        
        # Update requisition total
        cursor.execute("UPDATE requisitions SET total_amount = COALESCE((SELECT SUM(amount) FROM transactions WHERE requisition_id = ?), 0) WHERE id = ?", 
                     (requisition_id, requisition_id))
        conn.commit()
        return transaction_id
    except Exception as e:
        print(f"Error in add_transaction: {e}")
        return None
    finally:
        conn.close()

def get_transactions(requisition_id):
    """Get all transactions for a requisition"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        SELECT t.*, c.name as category_name, mi.canonical_name as item_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN master_items mi ON t.master_item_id = mi.id
        WHERE t.requisition_id = ?
        ORDER BY t.sr_no, t.id
        ''', (requisition_id,))
        transactions = cursor.fetchall()
        return [dict(trans) for trans in transactions]
    except Exception as e:
        print(f"Error in get_transactions: {e}")
        return []
    finally:
        conn.close()

def delete_transaction(transaction_id, requisition_id):
    """Delete a transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        # Update requisition total
        cursor.execute("UPDATE requisitions SET total_amount = COALESCE((SELECT SUM(amount) FROM transactions WHERE requisition_id = ?), 0) WHERE id = ?", 
                     (requisition_id, requisition_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in delete_transaction: {e}")
        return False
    finally:
        conn.close()

# ============ DASHBOARD FUNCTIONS ============

def get_dashboard_stats():
    """Get statistics for dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Total projects
        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
        total_projects = cursor.fetchone()[0] or 0
        
        # Total requisitions by status
        cursor.execute("SELECT status, COUNT(*) FROM requisitions GROUP BY status")
        req_stats = cursor.fetchall()
        requisitions_by_status = {row[0]: row[1] for row in req_stats}
        
        # Total contractors
        cursor.execute("SELECT COUNT(*) FROM contractors WHERE status = 'Active'")
        total_contractors = cursor.fetchone()[0] or 0
        
        # Total payments
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM contractor_payments WHERE status = 'PAID'")
        total_payments = cursor.fetchone()[0] or 0
        
        # Pending payments
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM contractor_payments WHERE status = 'PENDING'")
        pending_payments = cursor.fetchone()[0] or 0
        
        return {
            'total_projects': total_projects,
            'requisitions_by_status': requisitions_by_status,
            'total_contractors': total_contractors,
            'total_payments': total_payments,
            'pending_payments': pending_payments
        }
    except Exception as e:
        print(f"Error in get_dashboard_stats: {e}")
        return {
            'total_projects': 0,
            'requisitions_by_status': {},
            'total_contractors': 0,
            'total_payments': 0,
            'pending_payments': 0
        }
    finally:
        conn.close()