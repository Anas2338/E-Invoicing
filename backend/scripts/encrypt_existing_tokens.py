"""
One-time migration script to encrypt existing FBR tokens.
Run this ONCE after deploying encryption changes.

IMPORTANT: Make sure ENCRYPTION_KEY is set in your .env file before running!
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, select
from src.database.session import engine
from src.models.user import User
from src.utils.encryption import get_encryption_service


def migrate_tokens():
    """Encrypt all existing plaintext FBR tokens."""
    print("🔐 Starting FBR token encryption migration...")

    try:
        encryption_service = get_encryption_service()
        print("✅ Encryption service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize encryption service: {e}")
        print("   Make sure ENCRYPTION_KEY is set in .env file")
        return

    with Session(engine) as db:
        # Get all users with FBR tokens
        users = db.exec(select(User)).all()

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for user in users:
            updated = False

            # Encrypt sandbox token if exists and not already encrypted
            if user.fbr_sandbox_token:
                try:
                    # Try to decrypt - if it succeeds, it's already encrypted
                    encryption_service.decrypt(user.fbr_sandbox_token)
                    print(f"⏭️  User {user.email}: Sandbox token already encrypted")
                    skipped_count += 1
                except:
                    # Not encrypted, encrypt it now
                    try:
                        user.fbr_sandbox_token = encryption_service.encrypt(user.fbr_sandbox_token)
                        updated = True
                        print(f"✅ User {user.email}: Encrypted sandbox token")
                    except Exception as e:
                        print(f"❌ User {user.email}: Failed to encrypt sandbox token: {e}")
                        error_count += 1

            # Encrypt production token if exists and not already encrypted
            if user.fbr_production_token:
                try:
                    # Try to decrypt - if it succeeds, it's already encrypted
                    encryption_service.decrypt(user.fbr_production_token)
                    print(f"⏭️  User {user.email}: Production token already encrypted")
                    skipped_count += 1
                except:
                    # Not encrypted, encrypt it now
                    try:
                        user.fbr_production_token = encryption_service.encrypt(user.fbr_production_token)
                        updated = True
                        print(f"✅ User {user.email}: Encrypted production token")
                    except Exception as e:
                        print(f"❌ User {user.email}: Failed to encrypt production token: {e}")
                        error_count += 1

            if updated:
                db.add(user)
                migrated_count += 1

        if migrated_count > 0:
            db.commit()
            print(f"\n✅ Migration complete!")
            print(f"   - Migrated: {migrated_count} users")
            print(f"   - Skipped: {skipped_count} (already encrypted)")
            print(f"   - Errors: {error_count}")
        else:
            print(f"\n✅ No migration needed - all tokens already encrypted")
            print(f"   - Skipped: {skipped_count} (already encrypted)")


if __name__ == "__main__":
    print("=" * 60)
    print("FBR TOKEN ENCRYPTION MIGRATION")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This will encrypt all FBR tokens in the database")
    print("⚠️  Make sure ENCRYPTION_KEY is set in .env file!")
    print()

    response = input("Continue with migration? (yes/no): ")
    if response.lower() == "yes":
        migrate_tokens()
    else:
        print("❌ Migration cancelled")
