"""Personel veri erişim işlemleri."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Personel
from database.repositories.base import BaseRepository


class PersonelRepository(BaseRepository[Personel]):
    model = Personel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_sicil_no(self, sicil_no: str) -> Personel | None:
        statement = select(Personel).where(Personel.sicil_no == sicil_no)
        return self.session.scalar(statement)

    def get_by_sicil_numbers(self, sicil_numbers: set[str]) -> list[Personel]:
        if not sicil_numbers:
            return []
        statement = select(Personel).where(Personel.sicil_no.in_(sicil_numbers))
        return list(self.session.scalars(statement))
