import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from modules.daily_logs.repository import DailyLogRepository
from modules.daily_logs.schemas import DailyLogUpdate, DailyLogUpsert

_repo = DailyLogRepository()


class DailyLogService:
    def upsert_log(self, db: Session, user_id: uuid.UUID, data: DailyLogUpsert):
        return _repo.upsert_log(db, user_id, data)

    def get_log_by_date(self, db: Session, log_date: date, user_id: uuid.UUID):
        return _repo.get_log_by_date(db, log_date, user_id)

    def list_logs(self, db: Session, user_id: uuid.UUID,
                  from_date: Optional[date] = None, to_date: Optional[date] = None):
        return _repo.list_logs(db, user_id, from_date, to_date)

    def patch_log(self, db: Session, log_date: date, user_id: uuid.UUID, data: DailyLogUpdate):
        return _repo.patch_log(db, log_date, user_id, data)
