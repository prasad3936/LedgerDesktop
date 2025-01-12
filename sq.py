from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure the URI for SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customer_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking (optional)

# Initialize the SQLAlchemy object
db = SQLAlchemy(app)

# Define the Customer model
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    amount = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Customer {self.name}>'

# Define the User model with username and password
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Create the database and tables (if they don't already exist)
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    # Fetch all customers and users from the database
    customers = Customer.query.all()
    users = User.query.all()

    # Format customer data
    customer_data = "<br>".join([f"ID: {customer.id}, Name: {customer.name}, Mobile: {customer.mobile}, Amount: {customer.amount}" for customer in customers])
    if not customer_data:
        customer_data = "No customers found in the database."

    # Format user data (including username and password)
    user_data = "<br>".join([f"ID: {user.id}, Username: {user.username}, Password: {user.password}" for user in users])
    if not user_data:
        user_data = "No users found in the database."

    return f"<h1>All Customers Data</h1><p>{customer_data}</p><h1>All Users Data</h1><p>{user_data}</p>"

if __name__ == "__main__":
    app.run(debug=True)
