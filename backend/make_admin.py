"""
Script to make a user an admin.
Run this from the backend directory: python make_admin.py <user_email>
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlmodel import Session, select
from sqlalchemy.orm.attributes import flag_modified
from src.database.session import engine
from src.models.user import User

def make_admin(email: str):
    """Make a user an admin by setting approval flags."""
    try:
        with Session(engine) as session:
            # Find user by email
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()

            if not user:
                print(f"✗ User with email '{email}' not found")
                return False

            # Update user to admin
            if not user.approval_flags:
                user.approval_flags = {}

            user.approval_flags['is_admin'] = True
            user.account_status = 'approved'  # Ensure admin is approved

            # Mark the JSON field as modified so SQLAlchemy detects the change
            flag_modified(user, 'approval_flags')

            session.add(user)
            session.commit()
            session.refresh(user)

            print(f"[SUCCESS] User '{email}' is now an admin!")
            print(f"  User ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Status: {user.account_status}")
            return True

    except Exception as e:
        print(f"[ERROR] Failed to make user admin: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <user_email>")
        print("Example: python make_admin.py admin@company.com")
        sys.exit(1)

    email = sys.argv[1]
    success = make_admin(email)
    sys.exit(0 if success else 1)
