import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, select
from app.database import engine, User, create_db_and_tables
from app.auth import get_password_hash

def main():
    create_db_and_tables()
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        user_names = [u.username for u in users]
        if "admin" not in user_names:
            admin = User(username="admin", hashed_password=get_password_hash("admin123"))
            session.add(admin)
            session.commit()
            print("Created test account: admin / admin123")
        else:
            print(f"Existing accounts: {user_names}")

if __name__ == "__main__":
    main()
