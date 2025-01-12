from app import app, db

def create_tables():
    # Create tables in the database
    with app.app_context():
        db.create_all()  # This will create all tables based on models defined in app.py
        print("Tables created successfully.")

if __name__ == '__main__':
    create_tables()
