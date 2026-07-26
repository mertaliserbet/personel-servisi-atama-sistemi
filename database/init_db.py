"""Veritabanı şemasının uygulama başlangıcında hazırlanması."""

from __future__ import annotations

import logging

from sqlalchemy import Engine

from app.paths import DATABASE_PATH
from database.connection import engine
from database.models import Base


logger = logging.getLogger(__name__)


def initialize_database(database_engine: Engine = engine) -> None:
    """Tanımlı tüm SQLAlchemy tablolarını yoksa oluşturur."""
    Base.metadata.create_all(database_engine)
    logger.info("SQLAlchemy veritabanı şeması hazır: %s", DATABASE_PATH)
