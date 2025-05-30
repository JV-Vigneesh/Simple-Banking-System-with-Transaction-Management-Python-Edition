from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from database import database
from models import account, transaction, recovery

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database
@app.route('/init_db')
def init_db():
    database.init_db()
    flash('Database initialized successfully!', 'success')
    return redirect(url_for('index'))

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Account management
@app.route('/accounts', methods=['GET', 'POST'])
def accounts():
    if request.method == 'POST':
        account_name = request.form['account_name']
        initial_balance = float(request.form['initial_balance'])
        
        new_account = account.create_account(account_name, initial_balance)
        if new_account:
            flash(f'Account created successfully! Account number: {new_account}', 'success')
        else:
            flash('Failed to create account', 'danger')
            
    accounts_list = account.get_all_accounts()
    return render_template('accounts.html', accounts=accounts_list)

# Deposit functionality
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    accounts_list = account.get_all_accounts()
    
    if request.method == 'POST':
        account_id = int(request.form['account_id'])
        amount = float(request.form['amount'])
        should_crash = 'crash' in request.form
        
        success, message = transaction.deposit(account_id, amount, should_crash)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('deposit'))
        
    return render_template('deposit.html', accounts=accounts_list)

# Withdraw functionality
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    accounts_list = account.get_all_accounts()
    
    if request.method == 'POST':
        account_id = int(request.form['account_id'])
        amount = float(request.form['amount'])
        should_crash = 'crash' in request.form
        
        success, message = transaction.withdraw(account_id, amount, should_crash)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('withdraw'))
        
    return render_template('withdraw.html', accounts=accounts_list)

# Transfer functionality
@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    accounts_list = account.get_all_accounts()
    
    if request.method == 'POST':
        from_account_id = int(request.form['from_account_id'])
        to_account_id = int(request.form['to_account_id'])
        amount = float(request.form['amount'])
        should_crash = 'crash' in request.form
        
        success, message = transaction.transfer(from_account_id, to_account_id, amount, should_crash)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('transfer'))
        
    return render_template('transfer.html', accounts=accounts_list)

# Transaction history
@app.route('/transactions')
def transactions():
    transaction_list = transaction.get_all_transactions()
    return render_template('transactions.html', transactions=transaction_list)

# System crash simulation
@app.route('/simulate_crash', methods=['GET', 'POST'])
def simulate_crash():
    if request.method == 'POST':
        transaction_id = int(request.form['transaction_id'])
        crash_point = request.form['crash_point']
        
        success, message = recovery.simulate_crash(transaction_id, crash_point)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('transactions'))
        
    pending_transactions = transaction.get_pending_transactions()
    return render_template('simulate_crash.html', transactions=pending_transactions)

# Recovery management
@app.route('/recovery')
def recovery_page():
    logs = recovery.get_recovery_logs()
    return render_template('recovery.html', logs=logs)

# Manual recovery process
@app.route('/recover/<int:transaction_id>', methods=['POST'])
def recover_transaction(transaction_id):
    success, message = recovery.recover_transaction(transaction_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('recovery_page'))

if __name__ == '__main__':
    app.run(debug=True)