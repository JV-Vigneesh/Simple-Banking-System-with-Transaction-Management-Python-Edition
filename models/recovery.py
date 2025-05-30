from database import database
from models import account, transaction
import time

def log_recovery_attempt(transaction_id, recovery_type, status, description):
    """Log a recovery attempt"""
    query = """
        INSERT INTO recovery_logs 
        (transaction_id, recovery_type, status, description) 
        VALUES (%s, %s, %s, %s)
    """
    params = (transaction_id, recovery_type, status, description)
    
    try:
        database.execute_query(query, params)
        return True
    except Exception as e:
        print(f"Error logging recovery attempt: {e}")
        return False

def simulate_crash(transaction_id, crash_point):
    """
    Simulate a system crash during a transaction
    
    Args:
        transaction_id: The transaction to crash
        crash_point: When to crash ('before_deposit', 'after_withdrawal', etc.)
        
    Returns:
        Tuple (success, message)
    """
    # Get transaction details
    tx = transaction.get_transaction(transaction_id)
    if not tx:
        return False, "Transaction not found"
    
    if tx['status'] not in ('pending', 'processing'):
        return False, f"Cannot simulate crash on {tx['status']} transaction"
    
    # Set transaction to 'processing' if it's still pending
    if tx['status'] == 'pending':
        transaction.update_transaction_status(transaction_id, 'processing')
    
    # Different crash scenarios based on transaction type
    if tx['transaction_type'] == 'deposit':
        success, message = simulate_deposit_crash(tx, crash_point)
    elif tx['transaction_type'] == 'withdrawal':
        success, message = simulate_withdrawal_crash(tx, crash_point)
    elif tx['transaction_type'] == 'transfer':
        success, message = simulate_transfer_crash(tx, crash_point)
    else:
        return False, "Invalid transaction type"
    
    if success:
        # Log the simulated crash
        log_recovery_attempt(
            transaction_id,
            'manual',
            'success',
            f"Simulated crash at '{crash_point}' point: {message}"
        )
    
    return success, message

def simulate_deposit_crash(tx, crash_point):
    """Simulate crash during deposit"""
    if crash_point == 'before_update':
        # Crash before the deposit is recorded - nothing happens to balance
        transaction.log_transaction_update(
            tx['transaction_id'], 
            tx['source_account_id'], 
            None, 
            None, 
            "CRASH: Before balance update"
        )
        return True, "Crashed before deposit was recorded"
        
    elif crash_point == 'after_update':
        # Crash after deposit is recorded but before transaction is committed
        acc = account.get_account(tx['source_account_id'])
        if acc:
            old_balance = float(acc['balance']) - float(tx['amount'])
            new_balance = float(acc['balance'])
            
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                old_balance, 
                new_balance, 
                "CRASH: After balance update, before commit"
            )
            return True, "Crashed after deposit was recorded"
    
    return False, "Invalid crash point for deposit"

def simulate_withdrawal_crash(tx, crash_point):
    """Simulate crash during withdrawal"""
    if crash_point == 'before_update':
        # Crash before the withdrawal is recorded
        transaction.log_transaction_update(
            tx['transaction_id'], 
            tx['source_account_id'], 
            None, 
            None, 
            "CRASH: Before balance update"
        )
        return True, "Crashed before withdrawal was recorded"
        
    elif crash_point == 'after_update':
        # Crash after withdrawal is recorded but before transaction is committed
        acc = account.get_account(tx['source_account_id'])
        if acc:
            old_balance = float(acc['balance']) + float(tx['amount'])
            new_balance = float(acc['balance'])
            
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                old_balance, 
                new_balance, 
                "CRASH: After balance update, before commit"
            )
            
            # Update transaction status to failed
            transaction.update_transaction_status(tx['transaction_id'], 'failed')
            return True, "Crashed after withdrawal was recorded"
    
    return False, "Invalid crash point for withdrawal"

def simulate_transfer_crash(tx, crash_point):
    """Simulate crash during transfer"""
    if crash_point == 'before_source_update':
        # Crash before source account is debited
        transaction.log_transaction_update(
            tx['transaction_id'], 
            tx['source_account_id'], 
            None, 
            None, 
            "CRASH: Before source account update"
        )
        return True, "Crashed before transfer started"
        
    elif crash_point == 'after_source_update':
        # Crash after source is debited but before destination is credited
        acc = account.get_account(tx['source_account_id'])
        if acc:
            old_balance = float(acc['balance']) + float(tx['amount'])
            new_balance = float(acc['balance'])
            
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                old_balance, 
                new_balance, 
                "CRASH: After source update, before destination update"
            )
            
            # Update transaction status to failed
            transaction.update_transaction_status(tx['transaction_id'], 'failed')
            return True, "Crashed after source account was debited"
            
    elif crash_point == 'after_destination_update':
        # Crash after both accounts are updated but before commit
        src_acc = account.get_account(tx['source_account_id'])
        dst_acc = account.get_account(tx['destination_account_id'])
        
        if src_acc and dst_acc:
            # Log source account update
            src_old_balance = float(src_acc['balance']) + float(tx['amount'])
            src_new_balance = float(src_acc['balance'])
            
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                src_old_balance, 
                src_new_balance, 
                "CRASH: After both accounts updated, before commit"
            )
            
            # Log destination account update
            dst_old_balance = float(dst_acc['balance']) - float(tx['amount'])
            dst_new_balance = float(dst_acc['balance'])
            
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['destination_account_id'], 
                dst_old_balance, 
                dst_new_balance, 
                "CRASH: After both accounts updated, before commit"
            )
            return True, "Crashed after both accounts were updated"
    
    return False, "Invalid crash point for transfer"

def get_recovery_logs():
    """Get all recovery logs with transaction details"""
    query = """
        SELECT r.*, t.transaction_type, t.amount, t.status as tx_status,
               sa.account_number as source_account_number,
               da.account_number as dest_account_number
        FROM recovery_logs r
        JOIN transactions t ON r.transaction_id = t.transaction_id
        LEFT JOIN accounts sa ON t.source_account_id = sa.account_id
        LEFT JOIN accounts da ON t.destination_account_id = da.account_id
        ORDER BY r.created_at DESC
    """
    
    try:
        return database.execute_query(query)
    except Exception as e:
        print(f"Error getting recovery logs: {e}")
        return []

def recover_transaction(transaction_id):
    """
    Attempt to recover a transaction after a crash
    
    Args:
        transaction_id: The transaction to recover
        
    Returns:
        Tuple (success, message)
    """
    # Get transaction details
    tx = transaction.get_transaction(transaction_id)
    if not tx:
        return False, "Transaction not found"
    
    if tx['status'] not in ('processing', 'failed'):
        return False, f"Cannot recover transaction in {tx['status']} state"
    
    # Get transaction logs to determine crash point
    logs = transaction.get_transaction_logs(transaction_id)
    
    # Determine transaction state from logs
    start_log = None
    update_logs = []
    commit_log = None
    rollback_log = None
    
    for log in logs:
        if log['log_type'] == 'start':
            start_log = log
        elif log['log_type'] == 'update':
            update_logs.append(log)
        elif log['log_type'] == 'commit':
            commit_log = log
        elif log['log_type'] == 'rollback':
            rollback_log = log
    
    # Cannot recover if already rolled back or committed
    if rollback_log:
        return False, "Transaction was already rolled back"
    if commit_log:
        return False, "Transaction was already committed"
    
    # If no start log, transaction is invalid
    if not start_log:
        return False, "Invalid transaction: no start log found"
    
    # Recovery logic based on transaction type
    if tx['transaction_type'] == 'deposit':
        success, message = recover_deposit(tx, update_logs)
    elif tx['transaction_type'] == 'withdrawal':
        success, message = recover_withdrawal(tx, update_logs)
    elif tx['transaction_type'] == 'transfer':
        success, message = recover_transfer(tx, update_logs)
    else:
        return False, "Invalid transaction type"
    
    if success:
        # Log the recovery attempt
        log_recovery_attempt(
            transaction_id,
            'manual',
            'success',
            f"Manual recovery performed: {message}"
        )
    
    return success, message

def recover_deposit(tx, update_logs):
    """Recover a crashed deposit transaction"""
    if not update_logs:
        # No updates means transaction didn't start
        transaction.rollback_transaction(
            tx['transaction_id'], 
            "Recovery: Rolled back unstarted deposit"
        )
        return True, "Rolled back unstarted deposit"
    else:
        # Transaction was in progress, commit it
        transaction.commit_transaction(
            tx['transaction_id'], 
            "Recovery: Committed incomplete deposit"
        )
        return True, "Committed incomplete deposit"

def recover_withdrawal(tx, update_logs):
    """Recover a crashed withdrawal transaction"""
    if not update_logs:
        # No updates means transaction didn't start
        transaction.rollback_transaction(
            tx['transaction_id'], 
            "Recovery: Rolled back unstarted withdrawal"
        )
        return True, "Rolled back unstarted withdrawal"
    else:
        # Restore the original balance
        acc = account.get_account(tx['source_account_id'])
        if acc:
            new_balance = float(acc['balance']) + float(tx['amount'])
            account.update_balance(tx['source_account_id'], new_balance)
            
            # Log the rollback
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                float(acc['balance']), 
                new_balance, 
                "RECOVERY: Restored original balance"
            )
            
            transaction.rollback_transaction(
                tx['transaction_id'], 
                "Recovery: Rolled back incomplete withdrawal"
            )
            return True, "Rolled back incomplete withdrawal"
    
    return False, "Failed to recover withdrawal"

def recover_transfer(tx, update_logs):
    """Recover a crashed transfer transaction"""
    # Count updates to source and destination
    source_updates = [log for log in update_logs if log['account_id'] == tx['source_account_id']]
    dest_updates = [log for log in update_logs if log['account_id'] == tx['destination_account_id']]
    
    if not source_updates and not dest_updates:
        # No updates to either account, transaction didn't start
        transaction.rollback_transaction(
            tx['transaction_id'], 
            "Recovery: Rolled back unstarted transfer"
        )
        return True, "Rolled back unstarted transfer"
        
    elif source_updates and not dest_updates:
        # Source was debited but destination not credited
        # This is critical - restore the source account
        source_acc = account.get_account(tx['source_account_id'])
        if source_acc:
            new_balance = float(source_acc['balance']) + float(tx['amount'])
            account.update_balance(tx['source_account_id'], new_balance)
            
            # Log the rollback
            transaction.log_transaction_update(
                tx['transaction_id'], 
                tx['source_account_id'], 
                float(source_acc['balance']), 
                new_balance, 
                "RECOVERY: Restored source account balance"
            )
            
            transaction.rollback_transaction(
                tx['transaction_id'], 
                "Recovery: Rolled back partial transfer (source debited only)"
            )
            return True, "Rolled back partial transfer"
            
    elif source_updates and dest_updates:
        # Both accounts were updated, commit the transaction
        transaction.commit_transaction(
            tx['transaction_id'], 
            "Recovery: Committed complete transfer"
        )
        return True, "Committed complete transfer"
    
    return False, "Failed to recover transfer"