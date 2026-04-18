"""
List all users and optionally make one an admin.
Run this from the backend directory: uv run python list_users.py
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlmodel import Session, select
from src.database.session import engine
from src.models.user import User

def list_users():
    """List all users in the database."""
    try:
        with Session(engine) as session:
            statement = select(User).order_by(User.created_at.desc())
            users = session.exec(statement).all()

            if not users:
                print("No users found in database.")
                print("\nTo create your first user:")
                print("1. Go to http://localhost:3000/register")
                print("2. Register a new account")
                print("3. Run: uv run python make_admin.py your-email@example.com")
                return

            print(f"\nFound {len(users)} user(s):\n")
            print("-" * 100)
            print(f"{'Email':<35} {'Name':<20} {'Status':<12} {'Is Admin':<10}")
            print("-" * 100)

            for user in users:
                is_admin = user.approval_flags and user.approval_flags.get('is_admin', False)
                print(f"{user.email:<35} {(user.name or 'N/A'):<20} {user.account_status:<12} {'Yes' if is_admin else 'No':<10}")

            print("-" * 100)
            print(f"\nTo make a user admin, run:")
            print(f"  uv run python make_admin.py <email>")

    except Exception as e:
        print(f"[ERROR] Failed to list users: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_users()
