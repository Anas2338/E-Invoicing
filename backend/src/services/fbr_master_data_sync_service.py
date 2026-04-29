"""
FBR Master Data Sync Service with Change Detection
Fetches reference data from FBR APIs, compares with existing data,
and only updates when changes are detected. Generates notifications for changes.
"""

import httpx
import logging
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.models.fbr_master_data import (
    FBRProvince,
    FBRUOM,
    FBRHSCode,
    FBRTransactionType,
    FBRInvoiceType,
    FBRSyncLog
)
from src.models.fbr_notifications import FBRChangeNotification, FBRDataSnapshot

logger = logging.getLogger(__name__)


class FBRMasterDataSyncService:
    """Service for syncing FBR master data with change detection"""

    FBR_BASE_URL = "https://gw.fbr.gov.pk"
    REQUEST_TIMEOUT = 30.0

    def __init__(self, db: Session, fbr_token: str):
        """
        Initialize sync service.

        Args:
            db: Database session
            fbr_token: FBR access token (admin-controlled system token)
        """
        self.db = db
        self.fbr_token = fbr_token

    async def fetch_from_fbr(self, endpoint: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data from FBR API."""
        if not self.fbr_token:
            logger.error("No FBR token provided for sync")
            return None

        url = f"{self.FBR_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.fbr_token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"Unauthorized access to FBR API: {endpoint}")
                    return None
                else:
                    logger.error(f"FBR API error: {response.status_code} - {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching from FBR API: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from FBR API: {str(e)}")
            return None

    def _calculate_data_hash(self, records: List[Dict[str, Any]]) -> str:
        """Calculate SHA256 hash of records for change detection."""
        # Sort records by code/id for consistent hashing
        sorted_records = sorted(records, key=lambda x: str(x.get('code', x.get('id', ''))))
        data_string = json.dumps(sorted_records, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()

    def _detect_changes(self, data_type: str, new_records: List[Dict[str, Any]],
                       model_class, key_field: str = 'code') -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Detect changes between new data and existing database records.

        Returns:
            Tuple of (added_records, modified_records, deleted_records)
        """
        # Get existing records from database
        existing_records = self.db.query(model_class).all()
        existing_dict = {getattr(r, key_field): r for r in existing_records}

        # Build new records dict
        new_dict = {r[key_field]: r for r in new_records}

        # Detect additions
        added = [r for code, r in new_dict.items() if code not in existing_dict]

        # Detect modifications
        modified = []
        for code, new_rec in new_dict.items():
            if code in existing_dict:
                existing_rec = existing_dict[code]
                # Check if any field changed
                has_changes = False
                for field, value in new_rec.items():
                    if field != 'id' and hasattr(existing_rec, field):
                        if getattr(existing_rec, field) != value:
                            has_changes = True
                            break
                if has_changes:
                    modified.append({
                        'old': {k: getattr(existing_rec, k) for k in new_rec.keys() if hasattr(existing_rec, k)},
                        'new': new_rec
                    })

        # Detect deletions
        deleted = [{'code': code, 'record': existing_dict[code]}
                  for code in existing_dict.keys() if code not in new_dict]

        return added, modified, deleted

    def _create_notifications(self, data_type: str, added: List[Dict],
                            modified: List[Dict], deleted: List[Dict],
                            sync_log_id: Optional[int] = None) -> int:
        """
        Create notifications for detected changes.

        Returns:
            Number of notifications created
        """
        notifications = []

        # Notifications for additions
        for record in added:
            summary = self._generate_summary(data_type, 'added', record)
            notifications.append(FBRChangeNotification(
                data_type=data_type,
                change_type='added',
                record_code=record.get('code', ''),
                old_value=None,
                new_value=record,
                summary=summary,
                sync_log_id=sync_log_id,
                is_read=False
            ))

        # Notifications for modifications
        for change in modified:
            summary = self._generate_summary(data_type, 'modified', change['new'], change['old'])
            notifications.append(FBRChangeNotification(
                data_type=data_type,
                change_type='modified',
                record_code=change['new'].get('code', ''),
                old_value=change['old'],
                new_value=change['new'],
                summary=summary,
                sync_log_id=sync_log_id,
                is_read=False
            ))

        # Notifications for deletions
        for item in deleted:
            record = {
                'code': item['code'],
                'name': getattr(item['record'], 'name', '') or getattr(item['record'], 'description', '')
            }
            summary = self._generate_summary(data_type, 'deleted', record)
            notifications.append(FBRChangeNotification(
                data_type=data_type,
                change_type='deleted',
                record_code=item['code'],
                old_value=record,
                new_value=None,
                summary=summary,
                sync_log_id=sync_log_id,
                is_read=False
            ))

        # Bulk insert notifications
        if notifications:
            self.db.bulk_save_objects(notifications)
            self.db.commit()

        return len(notifications)

    def _generate_summary(self, data_type: str, change_type: str,
                         new_record: Dict, old_record: Optional[Dict] = None) -> str:
        """Generate human-readable summary for a change."""
        data_type_labels = {
            'provinces': 'Province',
            'uom': 'Unit of Measure',
            'hs_codes': 'HS Code',
            'transaction_types': 'Transaction Type',
            'invoice_types': 'Invoice Type'
        }

        label = data_type_labels.get(data_type, data_type)
        code = new_record.get('code', '')
        name = new_record.get('name', '') or new_record.get('description', '')

        if change_type == 'added':
            return f"New {label} added: {code} - {name}"
        elif change_type == 'modified':
            old_name = old_record.get('name', '') or old_record.get('description', '') if old_record else ''
            if old_name != name:
                return f"{label} updated: {code} - Name changed from '{old_name}' to '{name}'"
            return f"{label} updated: {code} - {name}"
        elif change_type == 'deleted':
            return f"{label} removed: {code} - {name}"

        return f"{label} {change_type}: {code}"

    def _update_snapshot(self, data_type: str, records: List[Dict[str, Any]]) -> None:
        """Update data snapshot for change detection."""
        data_hash = self._calculate_data_hash(records)
        record_count = len(records)

        # Upsert snapshot
        stmt = insert(FBRDataSnapshot).values(
            data_type=data_type,
            record_count=record_count,
            data_hash=data_hash
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['data_type'],
            set_={'record_count': record_count, 'data_hash': data_hash, 'last_updated': datetime.utcnow()}
        )
        self.db.execute(stmt)
        self.db.commit()

    def _upsert_records(self, model_class, records: List[Dict[str, Any]], unique_key: str) -> int:
        """Upsert records into database."""
        if not records:
            return 0

        try:
            stmt = insert(model_class).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=[unique_key],
                set_={k: stmt.excluded[k] for k in records[0].keys() if k != 'id'}
            )
            self.db.execute(stmt)
            self.db.commit()
            return len(records)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error upserting {model_class.__tablename__}: {str(e)}")
            raise

    async def sync_with_change_detection(self, data_type: str, endpoint: str,
                                        model_class, transform_func,
                                        unique_key: str = 'code') -> Dict[str, Any]:
        """
        Generic sync method with change detection.

        Returns:
            Dictionary with sync results including change counts
        """
        logger.info(f"Syncing {data_type} from FBR with change detection...")

        # Fetch from FBR
        fbr_data = await self.fetch_from_fbr(endpoint)
        if not fbr_data:
            logger.warning(f"No {data_type} data received from FBR")
            return {'synced': 0, 'added': 0, 'modified': 0, 'deleted': 0}

        # Transform data
        new_records = transform_func(fbr_data)

        # Check if data has changed using hash
        data_hash = self._calculate_data_hash(new_records)
        snapshot = self.db.query(FBRDataSnapshot).filter_by(data_type=data_type).first()

        if snapshot and snapshot.data_hash == data_hash:
            logger.info(f"No changes detected in {data_type} (hash match)")
            return {'synced': 0, 'added': 0, 'modified': 0, 'deleted': 0, 'unchanged': True}

        # Detect detailed changes
        added, modified, deleted = self._detect_changes(data_type, new_records, model_class, unique_key)

        # Only update if there are changes
        if added or modified or deleted:
            logger.info(f"Changes detected in {data_type}: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted")

            # Update database
            count = self._upsert_records(model_class, new_records, unique_key)

            # Handle deletions (soft delete or actual delete based on requirements)
            # For now, we'll keep deleted records but could mark them as inactive

            # Create notifications
            notification_count = self._create_notifications(data_type, added, modified, deleted)

            # Update snapshot
            self._update_snapshot(data_type, new_records)

            logger.info(f"Synced {count} {data_type} records, created {notification_count} notifications")

            return {
                'synced': count,
                'added': len(added),
                'modified': len(modified),
                'deleted': len(deleted),
                'notifications': notification_count
            }
        else:
            logger.info(f"No changes detected in {data_type}")
            return {'synced': 0, 'added': 0, 'modified': 0, 'deleted': 0, 'unchanged': True}

    async def sync_provinces(self) -> Dict[str, Any]:
        """Sync provinces with change detection."""
        def transform(data):
            records = []
            seen_codes = set()
            for item in data:
                code = str(item.get("stateProvinceCode", ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    records.append({"code": code, "name": item.get("stateProvinceDesc", "")})
            return records

        return await self.sync_with_change_detection(
            'provinces', '/pdi/v1/provinces', FBRProvince, transform
        )

    async def sync_uom(self) -> Dict[str, Any]:
        """Sync UOM codes with change detection."""
        def transform(data):
            records = []
            seen_codes = set()
            for item in data:
                code = str(item.get("uoM_ID", ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    records.append({"code": code, "name": item.get("description", "")})
            return records

        return await self.sync_with_change_detection(
            'uom', '/pdi/v1/uom', FBRUOM, transform
        )

    async def sync_hs_codes(self) -> Dict[str, Any]:
        """Sync HS codes with change detection."""
        def transform(data):
            records = []
            seen_codes = set()
            for item in data:
                code = item.get("hS_CODE", "")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    records.append({"code": code, "description": item.get("description", "")})
            return records

        return await self.sync_with_change_detection(
            'hs_codes', '/pdi/v1/itemdesccode', FBRHSCode, transform
        )

    async def sync_transaction_types(self) -> Dict[str, Any]:
        """Sync transaction types with change detection."""
        def transform(data):
            records = []
            seen_codes = set()
            for item in data:
                code = str(item.get("transactioN_TYPE_ID", ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    records.append({"code": code, "name": item.get("transactioN_DESC", "")})
            return records

        return await self.sync_with_change_detection(
            'transaction_types', '/pdi/v1/transtypecode', FBRTransactionType, transform
        )

    async def sync_invoice_types(self) -> Dict[str, Any]:
        """Sync invoice types with change detection."""
        def transform(data):
            records = []
            seen_codes = set()
            for item in data:
                code = str(item.get("docTypeId", ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    records.append({"code": code, "name": item.get("docDescription", "")})
            return records

        return await self.sync_with_change_detection(
            'invoice_types', '/pdi/v1/doctypecode', FBRInvoiceType, transform
        )

    def _create_sync_log(self, sync_type: str, status: str, records_synced: int,
                        error_message: Optional[str], started_at: datetime,
                        completed_at: datetime, change_summary: Optional[Dict] = None) -> int:
        """Create a sync log entry and return its ID."""
        try:
            duration = int((completed_at - started_at).total_seconds())
            log = FBRSyncLog(
                sync_type=sync_type,
                status=status,
                records_synced=records_synced,
                error_message=error_message,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log.id
        except Exception as e:
            logger.error(f"Error creating sync log: {str(e)}")
            self.db.rollback()
            return None

    async def sync_all(self) -> Dict[str, Any]:
        """Sync all master data with change detection."""
        started_at = datetime.utcnow()
        results = {}
        errors = []
        total_changes = 0

        logger.info("Starting FBR master data sync with change detection...")

        # Sync each data type
        sync_methods = [
            ('provinces', self.sync_provinces),
            ('uom', self.sync_uom),
            ('hs_codes', self.sync_hs_codes),
            ('transaction_types', self.sync_transaction_types),
            ('invoice_types', self.sync_invoice_types)
        ]

        for data_type, method in sync_methods:
            try:
                result = await method()
                results[data_type] = result
                if not result.get('unchanged'):
                    total_changes += result.get('added', 0) + result.get('modified', 0) + result.get('deleted', 0)
            except Exception as e:
                logger.error(f"Error syncing {data_type}: {str(e)}")
                errors.append(f"{data_type}: {str(e)}")
                results[data_type] = {'error': str(e)}

        completed_at = datetime.utcnow()
        total_records = sum(r.get('synced', 0) for r in results.values())

        # Determine status
        if errors:
            status = "partial" if total_records > 0 else "failed"
            error_message = "; ".join(errors)
        else:
            status = "success"
            error_message = None

        # Create sync log
        sync_log_id = self._create_sync_log("all", status, total_records, error_message,
                                            started_at, completed_at, results)

        logger.info(f"FBR master data sync completed. Status: {status}, Total changes: {total_changes}")

        return {
            "status": status,
            "results": results,
            "total_records": total_records,
            "total_changes": total_changes,
            "errors": errors if errors else None,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "sync_log_id": sync_log_id
        }
