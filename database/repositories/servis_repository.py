"""Servis ve servis vardiyası veri erişim işlemleri."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import (
    Servis,
    ServisVardiyasi,
    VardiyaTuru,
    YakaTuru,
)
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

    def get_by_codes(self, service_codes: set[str]) -> list[Servis]:
        if not service_codes:
            return []
        statement = (
            select(Servis)
            .where(Servis.servis_kodu.in_(service_codes))
            .options(selectinload(Servis.vardiyalar))
        )
        return list(self.session.scalars(statement).unique())


class ServisVardiyasiRepository(BaseRepository[ServisVardiyasi]):
    model = ServisVardiyasi

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_identity(
        self,
        service_id: int,
        shift: VardiyaTuru,
        collar: YakaTuru,
    ) -> ServisVardiyasi | None:
        statement = select(ServisVardiyasi).where(
            ServisVardiyasi.servis_id == service_id,
            ServisVardiyasi.vardiya_turu == shift,
            ServisVardiyasi.yaka_turu == collar,
        )
        return self.session.scalar(statement)
