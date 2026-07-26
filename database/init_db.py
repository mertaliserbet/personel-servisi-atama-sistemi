"""Veritabanı şemasının uygulama başlangıcında hazırlanması."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect

from app.paths import DATABASE_PATH
from database.connection import engine
from database.models import Base


logger = logging.getLogger(__name__)


def _apply_compatibility_migrations(database_engine: Engine) -> None:
    """create_all tarafından güncellenmeyen mevcut SQLite tablolarını tamamlar."""
    inspector = inspect(database_engine)
    if "servis_vardiya" not in inspector.get_table_names():
        return
    column_names = {
        column["name"] for column in inspector.get_columns("servis_vardiya")
    }
    if "rota_adi" not in column_names:
        with database_engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE servis_vardiya ADD COLUMN rota_adi VARCHAR(300)"
            )
        logger.info("Veritabanı uyumluluk güncellemesi uygulandı: servis_vardiya.rota_adi")


def initialize_database(database_engine: Engine = engine) -> None:
    """Tanımlı tüm SQLAlchemy tablolarını yoksa oluşturur."""
    Base.metadata.create_all(database_engine)
    _apply_compatibility_migrations(database_engine)
    logger.info("SQLAlchemy veritabanı şeması hazır: %s", DATABASE_PATH)
