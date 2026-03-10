from app import app
from database import get_db
from werkzeug.security import generate_password_hash

with app.app_context():
    db = get_db()

    # USERS TABLE
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            age INTEGER,
            gender TEXT
        );
    """)

    # DISEASE HISTORY TABLE
    db.execute("""
        CREATE TABLE IF NOT EXISTS disease_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            disease TEXT,
            confidence REAL,
            timestamp TEXT
        );
    """)

    # CREATE ADMIN USER
    admin = db.execute(
        "SELECT id FROM users WHERE name = ?",
        ("admin",)
    ).fetchone()

    if not admin:

        password_hash = generate_password_hash("admini")

        db.execute(
            """
            INSERT INTO users (name,email,password_hash,age,gender)
            VALUES (?,?,?,?,?)
            """,
            ("admin", "admin@system.com", password_hash, 30, "male")
        )

        print("Admin user created")

    db.commit()

    print("Database initialized successfully")