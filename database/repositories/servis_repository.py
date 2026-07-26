"""Servis ve servis vardiyası veri erişim işlemleri."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Servis, ServisVardiyasi
from database.repositories.base import BaseRepository


class ServisRepository(BaseRepository[Servis]):
    model = Servis

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_code(self, service_code: str) -> Servis | None:
        statement = (
            select(Servis)
            .where(Servis.servis_kodu == service_code)
            .options(selectinload(Servis.vardiyalar))
        )
        return self.session.scalar(statement)


class ServisVardiyasiRepository(BaseRepository[ServisVardiyasi]):
    model = ServisVardiyasi

    def __init__(self, session: Session) -> None:
        super().__init__(session)
