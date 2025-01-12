from flask import Flask, render_template, request, redirect, url_for ,session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import signal
import threading
import webview
import pywhatkit as kit
app = Flask(__name__)


# Secret key for session management (must be set early in the app initialization)
app.secret_key = os.urandom(24)  # Generates a random secret key
# Configuration for SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://ledger_user:strongpassword123@localhost/ledger_db"

#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customer_db.sqlite'
#app.config['SQLALCHEMY_DATABASE_URI'] = (
 #   "mysql+pymysql://avnadmin:AVNS_Rt3kVJGJry4vPpm2fd0@mysql-1f761a7d-prasadcpatil246-f8f0.b.aivencloud.com:14627/leadgerdb"
#)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def get_all_customers():
    return Customer.query.all()  # Fetch all customers from the database


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'credit' or 'debit'
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    remark = db.Column(db.String(255), nullable=True)  # New remark column


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    #products = db.Column(db.String(255), nullable=False)
    transactions = db.relationship('Transaction', cascade="all, delete-orphan", backref='customer')

# Routes


# Function to send WhatsApp reminder message
def send_whatsapp_reminder(customer_name, customer_mobile, reminder_details, amount):
    """
    Sends a WhatsApp reminder message to the customer.
    """
    message_body = f"Dear {customer_name},\n\nYou have the following unpaid bills:\n{reminder_details}\n\nTotal Amount Due: {amount}\n\nPlease make the payment at your earliest convenience.\n\nRegards,\nYour Store Name Powered By Ledger"

    try:
        # Send message instantly without switching to WhatsApp Web
        kit.sendwhatmsg_instantly(f"+{customer_mobile}", message_body, wait_time=15)
        return {"status": "success", "message": f"WhatsApp message sent to {customer_name}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send message: {str(e)}"}


# Route to send reminder about unpaid bills to a customer
@app.route('/send_reminder/<int:customer_id>', methods=['GET'])
def send_reminder(customer_id):
    """
    Sends a WhatsApp reminder message to a customer with unpaid bills.
    Displays a flash message indicating success or failure.
    """
    customer = Customer.query.get_or_404(customer_id)
    reminder_details = f"Unpaid bills for {customer.name}"  # Customize this as needed
    amount = customer.amount  # Fetch customer's total due amount

    # Call the function to send a WhatsApp reminder
    result = send_whatsapp_reminder(customer.name, customer.mobile, reminder_details, amount)

    # Flash a message based on the result
    if result["status"] == "success":
        flash(result["message"], "success")
    else:
        flash(result["message"], "error")

    # Redirect to the index page or any appropriate page
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # If user is already logged in, redirect to the index page
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists in the database
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('index'))  # Redirect to the main page after successful login
        else:
            flash("Invalid username or password. Please try again.", "error")
            error_message = "Invalid username or password. Please try again.New To Leadger?, Consider Signing Up"
            return render_template('user_error.html', error_message=error_message), 400
    
    return render_template('login.html')

CUSTOMERS_PER_PAGE=7

@app.route('/')
def index():
    if 'user_id' not in session:  # Check if user is logged in
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    # Get the page number from the query string (default is 1)
    page = request.args.get('page', 1, type=int)

    # Query to get all customers and paginate them
    customers = Customer.query.paginate(page=page, per_page=CUSTOMERS_PER_PAGE, error_out=False)

    # Get the total amount of customers
    total_amount = db.session.query(db.func.sum(Customer.amount)).scalar() or 0

    # Pass pagination data to the template
    return render_template('index.html', customers=customers.items, total_amount=total_amount, query=None, pagination=customers)

@app.route('/logout')
def logout():
    """Logout the user by clearing the session."""
    session.pop('user_id', None)  # Remove user_id from session
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))  # Redirect to login page after logging out


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Sign-up (setup) page for first-time users."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different username.", "error")
            error_message = "User Exists. Please try with new username again.", "error"
            return render_template('error.html', error_message=error_message), 400
    
        
        # Add new user
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Logging you in...", "success")
        
        # Automatically log the user in after signing up
        session['user_id'] = new_user.id
        return redirect(url_for('index'))  # Redirect to main page after successful sign-up
    
    return render_template('setup.html')

@app.route('/search')
def search():
    query = request.args.get('query')
    page = request.args.get('page', 1, type=int)  # Get the current page number
    if query:
        # Perform search on the 'name' or 'mobile' field
        customers = Customer.query.filter(
            Customer.name.ilike(f"%{query}%") | Customer.mobile.ilike(f"%{query}%")
        ).paginate(page=page, per_page=CUSTOMERS_PER_PAGE, error_out=False)

        # Get the total amount of customers in the search result
        total_amount = db.session.query(db.func.sum(Customer.amount)).filter(
            Customer.name.ilike(f"%{query}%") | Customer.mobile.ilike(f"%{query}%")
        ).scalar() or 0
    else:
        flash("No Matching Records Found", "info")
        customers = Customer.query.filter(
            Customer.name.ilike(f"%{query}%") | Customer.mobile.ilike(f"%{query}%")
        ).paginate(page=page, per_page=CUSTOMERS_PER_PAGE, error_out=False)

        if not customers.items:
            total_amount = 0
            return render_template('index.html', customers=[], total_amount=total_amount, query=query, pagination=None, no_data=True)
        total_amount = 0
        flash("No matching records found.", "info")

    # Pass data to the template, including pagination information
    return render_template('index.html', customers=customers.items, total_amount=total_amount, query=query, pagination=customers)



@app.route('/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        amount = request.form['amount']
        #products = request.form['products']

        new_customer = Customer(name=name, mobile=mobile, amount=amount)
        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for('index'))
    return render_template('add_customer.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.mobile = request.form['mobile']
        customer.amount = request.form['amount']
        #customer.products = request.form['products']

        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete/<int:id>')
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/transaction/<int:id>', methods=['POST'])
def transaction(id):
    customer = Customer.query.get_or_404(id)
    amount = float(request.form['amount'])
    remark = request.form['remark']
    action = request.form['action']  # Get the action (credit or debit) from the clicked button

    if action == 'credit':
        # Credit transaction logic
        customer.amount += amount
        transaction = Transaction(customer_id=id, type='credit', amount=amount, remark=remark)
        
    elif action == 'debit':
        # Debit transaction logic
        if customer.amount >= amount:
            customer.amount -= amount
            transaction = Transaction(customer_id=id, type='debit', amount=amount, remark=remark)
        else:
            error_message = "Insufficient balance. Please check your account and try again."
            return render_template('error.html', error_message=error_message), 400
    
    # Save the transaction and update the customer balance
    db.session.add(transaction)
    db.session.commit()

    # Redirect to a success page or the customer's details page
    return redirect(url_for('index'))


@app.route('/print_invoice/<int:id>')
def print_invoice(id):
    customer = Customer.query.get_or_404(id)
    transactions = Transaction.query.filter_by(customer_id=id).order_by(Transaction.date.desc()).all()
    current_datetime = datetime.utcnow()
    return render_template('invoice.html', customer=customer, transactions=transactions, current_datetime=current_datetime)

import webview

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        webview.destroy_window()  # Use destroy_window instead of close
        return "Shutting down", 200
    except Exception as e:
        app.logger.error(f"Error shutting down: {e}")
        return "Error shutting down", 500



@app.route('/print_customers')
def print_customers():
    # Fetch all customers from the database
    customers = Customer.query.all()
    
    # Calculate total amount
    total_amount = sum(customer.amount for customer in customers)
    
    # Get the current date and time
    current_datetime = datetime.utcnow()
    
    # Render the print.html template with customer data, total amount, and total count
    return render_template('print.html', 
                           customers=customers, 
                           total_amount=total_amount, 
                           total_customers=len(customers), 
                           current_datetime=current_datetime)



# Function to run Flask in a separate thread
def run_flask():
    app.run(debug=False, use_reloader=False)


if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Launch PyWebView
    webview.create_window('Ledger - A Customer Management App', 'http://127.0.0.1:5000', width=1000, height=600,background_color="#F0F0F0")
    webview.start()
