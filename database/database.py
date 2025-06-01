import pymysql
import time
import traceback

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DB_NAME = 'banking_system'

def get_connection():
    """Create a connection to the database"""
    try:
        # First try to connect to the database
        connection = pymysql.connect(
            **DB_CONFIG,
            database=DB_NAME
        )
        return connection
    except pymysql.MySQLError as e:
        # If database doesn't exist, create it
        if e.args[0] == 1049:  # 1049 is the error code for "Unknown database"
            temp_connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                charset=DB_CONFIG['charset']
            )
            with temp_connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            temp_connection.close()
            
            # Now connect to the newly created database
            connection = pymysql.connect(
                **DB_CONFIG,
                database=DB_NAME
            )
            return connection
        else:
            raise

def init_db():
    """Initialize the database with required tables"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS recovery_logs")
            cursor.execute("DROP TABLE IF EXISTS transaction_logs")
            cursor.execute("DROP TABLE IF EXISTS transactions")
            cursor.execute("DROP TABLE IF EXISTS accounts")
            
            # Create accounts table
            cursor.execute("""
                CREATE TABLE accounts (
                    account_id INT AUTO_INCREMENT PRIMARY KEY,
                    account_name VARCHAR(100) NOT NULL,
                    account_number VARCHAR(20) UNIQUE NOT NULL,
                    balance DECIMAL(15, 2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)
            
            # Create transactions table
            cursor.execute("""
                CREATE TABLE transactions (
                    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
                    transaction_type ENUM('deposit', 'withdrawal', 'transfer') NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    source_account_id INT,
                    destination_account_id INT,
                    status ENUM('pending', 'processing', 'completed', 'failed', 'rolled_back') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_account_id) REFERENCES accounts(account_id),
                    FOREIGN KEY (destination_account_id) REFERENCES accounts(account_id)
                ) ENGINE=InnoDB
            """)
            
            # Create transaction_logs table
            cursor.execute("""
                CREATE TABLE transaction_logs (
                    log_id INT AUTO_INCREMENT PRIMARY KEY,
                    transaction_id INT,
                    log_type ENUM('start', 'update', 'commit', 'rollback') NOT NULL,
                    account_id INT,
                    old_balance DECIMAL(15, 2),
                    new_balance DECIMAL(15, 2),
                    description TEXT,
                    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
                    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
                ) ENGINE=InnoDB
            """)
            
            # Create recovery_logs table
            cursor.execute("""
                CREATE TABLE recovery_logs (
                    recovery_id INT AUTO_INCREMENT PRIMARY KEY,
                    transaction_id INT,
                    recovery_type ENUM('automatic', 'manual') NOT NULL,
                    status ENUM('success', 'failed') NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
                ) ENGINE=InnoDB
            """)
            
        connection.commit()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        print(traceback.format_exc())
        connection.rollback()
        return False
    finally:
        connection.close()

def execute_query(query, params=None, commit=True):
    """Execute a database query and return results"""
    connection = get_connection()
    result = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                result = cursor.lastrowid
        
        if commit:
            connection.commit()
    except Exception as e:
        print(f"Query execution error: {e}")
        print(traceback.format_exc())
        if commit:
            connection.rollback()
        raise
    finally:
        connection.close()
    
    return result

def execute_transaction(operations):
    """
    Execute a series of operations as a single transaction
    
    Args:
        operations: List of (query, params) tuples to execute
    
    Returns:
        Tuple (success, result, error_message)
    """
    connection = get_connection()
    try:
        connection.begin()
        result = None
        
        with connection.cursor() as cursor:
            for query, params in operations:
                cursor.execute(query, params or ())
                if result is None and query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                elif result is None:
                    result = cursor.lastrowid
        
        connection.commit()
        return True, result, None
    except Exception as e:
        connection.rollback()
        error_message = f"Transaction error: {str(e)}"
        print(error_message)
        print(traceback.format_exc())
        return False, None, error_message
    finally:
        connection.close()