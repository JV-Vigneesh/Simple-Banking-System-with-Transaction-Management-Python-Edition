import random
from database import database

def generate_account_number():
    """Generate a random account number"""
    return ''.join(random.choices('0123456789', k=10))

def create_account(account_name, initial_balance=0.0):
    """Create a new bank account"""
    account_number = generate_account_number()
    
    query = """
        INSERT INTO accounts (account_name, account_number, balance) 
        VALUES (%s, %s, %s)
    """
    params = (account_name, account_number, initial_balance)
    
    try:
        account_id = database.execute_query(query, params)
        return account_number
    except Exception as e:
        print(f"Error creating account: {e}")
        return None

def get_account(account_id):
    """Get account details by ID"""
    query = "SELECT * FROM accounts WHERE account_id = %s"
    params = (account_id,)
    
    try:
        result = database.execute_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting account: {e}")
        return None

def get_account_by_number(account_number):
    """Get account details by account number"""
    query = "SELECT * FROM accounts WHERE account_number = %s"
    params = (account_number,)
    
    try:
        result = database.execute_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting account: {e}")
        return None

def get_all_accounts():
    """Get all accounts"""
    query = "SELECT * FROM accounts ORDER BY account_id"
    
    try:
        return database.execute_query(query)
    except Exception as e:
        print(f"Error getting accounts: {e}")
        return []

def update_balance(account_id, new_balance):
    """Update account balance"""
    query = "UPDATE accounts SET balance = %s WHERE account_id = %s"
    params = (new_balance, account_id)
    
    try:
        database.execute_query(query, params)
        return True
    except Exception as e:
        print(f"Error updating balance: {e}")
        return False

def get_balance(account_id):
    """Get current balance of an account"""
    account = get_account(account_id)
    return float(account['balance']) if account else 0.0