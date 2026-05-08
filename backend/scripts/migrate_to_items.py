"""
Data migration script to convert existing separate saved items into unified saved products.

This script:
1. Queries all users with saved HS codes, descriptions, UOMs, or tax rates
2. Creates UserSavedProduct entries by combining the data
3. Generates item names: "Item - {hs_code}"
4. Preserves FBR validation status from HS codes
5. Logs migration results

Run with: python -m scripts.migrate_to_items
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.models.user_saved_hs_code import UserSavedHSCode
from src.models.user_saved_product_description import UserSavedProductDescription
from src.models.user_saved_uom import UserSavedUOM
from src.models.user_saved_tax_rate import UserSavedTaxRate
from src.models.user_saved_product import UserSavedProduct
from src.models.user import User
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_session():
    """Create database session"""
    engine = create_engine(settings.DATABASE_URL)
    return Session(engine)


def migrate_user_data(db: Session, user_id: str) -> dict:
    """
    Migrate data for a single user.

    Strategy:
    - Get all HS codes for the user
    - For each HS code, create a saved product
    - Use first available description, UOM, and tax rate as defaults
    - Generate item name as "Item - {hs_code}"
    """
    results = {
        'user_id': user_id,
        'items_created': 0,
        'errors': []
    }

    try:
        # Fetch user's saved data
        hs_codes = db.query(UserSavedHSCode).filter(
            UserSavedHSCode.user_id == user_id,
            UserSavedHSCode.is_active == 1
        ).order_by(UserSavedHSCode.display_order, UserSavedHSCode.created_at).all()

        descriptions = db.query(UserSavedProductDescription).filter(
            UserSavedProductDescription.user_id == user_id,
            UserSavedProductDescription.is_active == 1
        ).order_by(UserSavedProductDescription.display_order, UserSavedProductDescription.created_at).all()

        uoms = db.query(UserSavedUOM).filter(
            UserSavedUOM.user_id == user_id,
            UserSavedUOM.is_active == 1
        ).order_by(UserSavedUOM.display_order, UserSavedUOM.created_at).all()

        tax_rates = db.query(UserSavedTaxRate).filter(
            UserSavedTaxRate.user_id == user_id,
            UserSavedTaxRate.is_active == 1
        ).order_by(UserSavedTaxRate.display_order, UserSavedTaxRate.created_at).all()

        # If user has no saved data, skip
        if not hs_codes and not descriptions and not uoms and not tax_rates:
            logger.info(f"User {user_id} has no saved data to migrate")
            return results

        # Get default values
        default_uom = uoms[0].uom_code if uoms else None
        default_rate = tax_rates[0].tax_rate if tax_rates else None

        # If user has HS codes, create items based on them
        if hs_codes:
            for idx, hs_code in enumerate(hs_codes):
                # Pair with description if available
                description = descriptions[idx].product_description if idx < len(descriptions) else f"Product with HS Code {hs_code.hs_code}"

                # Check if item already exists
                existing = db.query(UserSavedProduct).filter(
                    UserSavedProduct.user_id == user_id,
                    UserSavedProduct.hs_code == hs_code.hs_code,
                    UserSavedProduct.product_description == description
                ).first()

                if existing:
                    logger.info(f"Item already exists for user {user_id}, HS code {hs_code.hs_code}")
                    continue

                # Create new saved product
                new_product = UserSavedProduct(
                    user_id=user_id,
                    item_name=f"Item - {hs_code.hs_code}",
                    hs_code=hs_code.hs_code,
                    product_description=description,
                    default_uom=default_uom,
                    default_rate=default_rate,
                    default_sale_type="01",  # Default sale type
                    transaction_type=None,
                    default_unit_price=None,
                    sro_schedule_no=None,
                    sro_item_serial_no=None,
                    fbr_validated=hs_code.fbr_validated,
                    fbr_validation_date=hs_code.fbr_validation_date,
                    fbr_validation_error=hs_code.fbr_validation_error,
                    is_active=1,
                    display_order=idx,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                db.add(new_product)
                results['items_created'] += 1
                logger.info(f"Created item for user {user_id}: {new_product.item_name}")

        # If user has descriptions but no HS codes, create generic items
        elif descriptions:
            for idx, desc in enumerate(descriptions):
                # Check if item already exists
                existing = db.query(UserSavedProduct).filter(
                    UserSavedProduct.user_id == user_id,
                    UserSavedProduct.product_description == desc.product_description
                ).first()

                if existing:
                    logger.info(f"Item already exists for user {user_id}, description {desc.product_description[:30]}")
                    continue

                # Create new saved product with generic HS code
                new_product = UserSavedProduct(
                    user_id=user_id,
                    item_name=f"Item - {desc.product_description[:20]}",
                    hs_code="00000000",  # Generic HS code
                    product_description=desc.product_description,
                    default_uom=default_uom,
                    default_rate=default_rate,
                    default_sale_type="01",
                    transaction_type=None,
                    default_unit_price=None,
                    sro_schedule_no=None,
                    sro_item_serial_no=None,
                    fbr_validated=False,
                    fbr_validation_date=None,
                    fbr_validation_error="Migrated from description without HS code",
                    is_active=1,
                    display_order=idx,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                db.add(new_product)
                results['items_created'] += 1
                logger.info(f"Created item for user {user_id}: {new_product.item_name}")

        db.commit()

    except Exception as e:
        logger.error(f"Error migrating data for user {user_id}: {str(e)}")
        results['errors'].append(str(e))
        db.rollback()

    return results


def main():
    """Main migration function"""
    logger.info("Starting data migration to unified items...")

    db = get_database_session()

    try:
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        logger.info(f"Found {len(users)} active users")

        total_items_created = 0
        users_migrated = 0
        users_with_errors = 0

        for user in users:
            logger.info(f"Migrating data for user: {user.email} ({user.id})")
            results = migrate_user_data(db, str(user.id))

            if results['items_created'] > 0:
                users_migrated += 1
                total_items_created += results['items_created']
                logger.info(f"✓ Created {results['items_created']} items for user {user.email}")

            if results['errors']:
                users_with_errors += 1
                logger.error(f"✗ Errors for user {user.email}: {results['errors']}")

        logger.info("\n" + "="*60)
        logger.info("Migration Summary:")
        logger.info(f"Total users processed: {len(users)}")
        logger.info(f"Users with data migrated: {users_migrated}")
        logger.info(f"Total items created: {total_items_created}")
        logger.info(f"Users with errors: {users_with_errors}")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Fatal error during migration: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
