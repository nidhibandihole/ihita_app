from app import app, db

# Create an application context
with app.app_context():
    # Create all tables in the database
    db.create_all()
    print("Tables created successfully!")
