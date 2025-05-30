from database import database
from models import account
import time

def start_transaction(transaction_type, amount, source_account_id, destination_account_id=None):
    """
    Start a new transaction and log it
    
    Args:
        transaction_type: Type of transaction (deposit, withdrawal, transfer)
        amount: Amount involved in the transaction
        source_account_id: Source account ID
        destination_account_id: Destination account ID (for transfers)
        
    Returns:
        Tuple (success, transaction_id, message)
    """
    # Create transaction record
    query = """
        INSERT INTO transactions 
        (transaction_type, amount, source_account_id, destination_account_id, status) 
        VALUES (%s, %s, %s, %s, 'pending')
    """
    params = (transaction_type, amount, source_account_id, destination_account_id)
    
    try:
        transaction_id = database.execute_query(query, params)
        
        # Log the start of transaction
        if source_account_id:
            src_account = account.get_account(source_account_id)
            old_balance = src_account['balance'] if src_account else 0
            
            log_query = """
                INSERT INTO transaction_logs 
                (transaction_id, log_type, account_id, old_balance, new_balance, description) 
                VALUES (%s, 'start', %s, %s, %s, %s)
            """
            log_params = (
                transaction_id, 
                source_account_id, 
                old_balance,
                old_balance,  # No change yet
                f"Started {transaction_type} transaction of ${amount}"
            )
            database.execute_query(log_query, log_params)
        
        return True, transaction_id, "Transaction started"
    except Exception as e:
        return False, None, f"Error starting transaction: {str(e)}"

def update_transaction_status(transaction_id, status):
    """Update the status of a transaction"""
    query = "UPDATE transactions SET status = %s WHERE transaction_id = %s"
    params = (status, transaction_id)
    
    try:
        database.execute_query(query, params)
        return True
    except Exception as e:
        print(f"Error updating transaction status: {e}")
        return False

def log_transaction_update(transaction_id, account_id, old_balance, new_balance, description):
    """Log a transaction update"""
    query = """
        INSERT INTO transaction_logs 
        (transaction_id, log_type, account_id, old_balance, new_balance, description) 
        VALUES (%s, 'update', %s, %s, %s, %s)
    """
    params = (transaction_id, account_id, old_balance, new_balance, description)
    
    try:
        database.execute_query(query, params)
        return True
    except Exception as e:
        print(f"Error logging transaction update: {e}")
        return False

def commit_transaction(transaction_id, description):
    """Mark a transaction as committed"""
    query = """
        INSERT INTO transaction_logs 
        (transaction_id, log_type, description) 
        VALUES (%s, 'commit', %s)
    """
    params = (transaction_id, description)
    
    try:
        database.execute_query(query, params)
        update_transaction_status(transaction_id, 'completed')
        return True
    except Exception as e:
        print(f"Error committing transaction: {e}")
        return False

def rollback_transaction(transaction_id, description):
    """Mark a transaction as rolled back"""
    query = """
        INSERT INTO transaction_logs 
        (transaction_id, log_type, description) 
        VALUES (%s, 'rollback', %s)
    """
    params = (transaction_id, description)
    
    try:
        database.execute_query(query, params)
        update_transaction_status(transaction_id, 'rolled_back')
        return True
    except Exception as e:
        print(f"Error rolling back transaction: {e}")
        return False

def deposit(account_id, amount, should_crash=False):
    """
    Deposit money into an account
    
    Args:
        account_id: The account ID to deposit into
        amount: The amount to deposit
        should_crash: If True, simulate a crash after updating balance
        
    Returns:
        Tuple (success, message)
    """
    if amount <= 0:
        return False, "Deposit amount must be positive"
    
    # Get current account details
    acc = account.get_account(account_id)
    if not acc:
        return False, "Account not found"
    
    old_balance = float(acc['balance'])
    new_balance = old_balance + amount

    if should_crash:
        new_balance = old_balance
    
    # Start transaction
    success, transaction_id, message = start_transaction('deposit', amount, account_id)
    if not success:
        return False, message
    
    try:
        # Add artificial delay
        time.sleep(10)
        
        # Update account balance
        update_transaction_status(transaction_id, 'processing')
        if not account.update_balance(account_id, new_balance):
            raise Exception("Failed to update balance")
        
        # Log the update
        log_transaction_update(
            transaction_id, 
            account_id, 
            old_balance, 
            new_balance, 
            f"Deposited ${amount:.2f} into account"
        )
        
        if should_crash:
            # Simulate crash after balance update
            update_transaction_status(transaction_id, 'failed')
            return False, "Transaction crashed after balance update"
        
        # Commit the transaction
        commit_transaction(transaction_id, f"Successfully deposited ${amount:.2f}")
        return True, f"Successfully deposited ${amount:.2f}"
        
    except Exception as e:
        # Rollback on error
        rollback_transaction(transaction_id, f"Deposit failed: {str(e)}")
        # Restore original balance
        account.update_balance(account_id, old_balance)
        return False, f"Deposit failed: {str(e)}"

def withdraw(account_id, amount, should_crash=False):
    """
    Withdraw money from an account
    
    Args:
        account_id: The account ID to withdraw from
        amount: The amount to withdraw
        should_crash: If True, simulate a crash after updating balance
        
    Returns:
        Tuple (success, message)
    """
    if amount <= 0:
        return False, "Withdrawal amount must be positive"
    
    # Get current account details
    acc = account.get_account(account_id)
    if not acc:
        return False, "Account not found"
    
    old_balance = float(acc['balance'])
    if old_balance < amount:
        return False, "Insufficient funds"
    
    new_balance = old_balance - amount
    
    # Start transaction
    success, transaction_id, message = start_transaction('withdrawal', amount, account_id)
    if not success:
        return False, message
    
    try:
        # Add artificial delay
        time.sleep(10)
        
        # Update account balance
        update_transaction_status(transaction_id, 'processing')
        if not account.update_balance(account_id, new_balance):
            raise Exception("Failed to update balance")
        
        # Log the update
        log_transaction_update(
            transaction_id, 
            account_id, 
            old_balance, 
            new_balance, 
            f"Withdrew ${amount:.2f} from account"
        )
        
        if should_crash:
            # Simulate crash after balance update
            update_transaction_status(transaction_id, 'failed')
            return False, "Transaction crashed after balance update"
        
        # Commit the transaction
        commit_transaction(transaction_id, f"Successfully withdrew ${amount:.2f}")
        return True, f"Successfully withdrew ${amount:.2f}"
        
    except Exception as e:
        # Rollback on error
        rollback_transaction(transaction_id, f"Withdrawal failed: {str(e)}")
        # Restore original balance
        account.update_balance(account_id, old_balance)
        return False, f"Withdrawal failed: {str(e)}"

def transfer(from_account_id, to_account_id, amount, should_crash=False):
    """
    Transfer money between accounts
    
    Args:
        from_account_id: Source account ID
        to_account_id: Destination account ID
        amount: The amount to transfer
        should_crash: If True, simulate a crash after updating source account
        
    Returns:
        Tuple (success, message)
    """
    if from_account_id == to_account_id:
        return False, "Cannot transfer to the same account"
        
    if amount <= 0:
        return False, "Transfer amount must be positive"
    
    # Get account details
    from_acc = account.get_account(from_account_id)
    to_acc = account.get_account(to_account_id)
    
    if not from_acc:
        return False, "Source account not found"
    if not to_acc:
        return False, "Destination account not found"
    
    from_old_balance = float(from_acc['balance'])
    to_old_balance = float(to_acc['balance'])
    
    if from_old_balance < amount:
        return False, "Insufficient funds in source account"
    
    from_new_balance = from_old_balance - amount
    to_new_balance = to_old_balance + amount
    
    # Start transaction
    success, transaction_id, message = start_transaction('transfer', amount, from_account_id, to_account_id)
    if not success:
        return False, message
    
    try:
        # Add artificial delay
        time.sleep(10)
        
        # Update source account (withdraw)
        update_transaction_status(transaction_id, 'processing')
        if not account.update_balance(from_account_id, from_new_balance):
            raise Exception("Failed to update source account")
        
        # Log the update for source account
        log_transaction_update(
            transaction_id, 
            from_account_id, 
            from_old_balance, 
            from_new_balance, 
            f"Transferred ${amount:.2f} to account #{to_acc['account_number']}"
        )
        
        if should_crash:
            # Simulate crash after updating source account
            update_transaction_status(transaction_id, 'failed')
            return False, "Transaction crashed after debiting source account"
        
        # Update destination account (deposit)
        if not account.update_balance(to_account_id, to_new_balance):
            raise Exception("Failed to update destination account")
        
        # Log the update for destination account
        log_transaction_update(
            transaction_id, 
            to_account_id, 
            to_old_balance, 
            to_new_balance, 
            f"Received ${amount:.2f} from account #{from_acc['account_number']}"
        )
        
        # Commit the transaction
        commit_transaction(transaction_id, f"Successfully transferred ${amount:.2f}")
        return True, f"Successfully transferred ${amount:.2f}"
        
    except Exception as e:
        # Rollback on error
        rollback_transaction(transaction_id, f"Transfer failed: {str(e)}")
        
        # Restore original balances
        account.update_balance(from_account_id, from_old_balance)
        account.update_balance(to_account_id, to_old_balance)
        
        return False, f"Transfer failed: {str(e)}"

def get_transaction(transaction_id):
    """Get transaction details by ID"""
    query = "SELECT * FROM transactions WHERE transaction_id = %s"
    params = (transaction_id,)
    
    try:
        result = database.execute_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting transaction: {e}")
        return None

def get_transaction_logs(transaction_id):
    """Get logs for a specific transaction"""
    query = "SELECT * FROM transaction_logs WHERE transaction_id = %s ORDER BY log_time"
    params = (transaction_id,)
    
    try:
        return database.execute_query(query, params)
    except Exception as e:
        print(f"Error getting transaction logs: {e}")
        return []

def get_all_transactions():
    """Get all transactions with account details"""
    query = """
        SELECT t.*, 
               sa.account_number as source_account_number, 
               sa.account_name as source_account_name,
               da.account_number as dest_account_number, 
               da.account_name as dest_account_name
        FROM transactions t
        LEFT JOIN accounts sa ON t.source_account_id = sa.account_id
        LEFT JOIN accounts da ON t.destination_account_id = da.account_id
        ORDER BY t.created_at DESC
    """
    
    try:
        return database.execute_query(query)
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

def get_pending_transactions():
    """Get transactions that are in pending or processing state"""
    query = """
        SELECT t.*, 
               sa.account_number as source_account_number, 
               sa.account_name as source_account_name,
               da.account_number as dest_account_number, 
               da.account_name as dest_account_name
        FROM transactions t
        LEFT JOIN accounts sa ON t.source_account_id = sa.account_id
        LEFT JOIN accounts da ON t.destination_account_id = da.account_id
        WHERE t.status IN ('pending', 'processing')
        ORDER BY t.created_at DESC
    """
    
    try:
        return database.execute_query(query)
    except Exception as e:
        print(f"Error getting pending transactions: {e}")
        return []
