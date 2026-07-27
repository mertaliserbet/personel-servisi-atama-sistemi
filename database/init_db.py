"""Veritabanı şemasının uygulama başlangıcında hazırlanması."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect

from app.paths import DATABASE_PATH
from database.connection import engine
from database.models import Base, ServisGuzergahNoktasi


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

    inspector = inspect(database_engine)
    if "personel" not in inspector.get_table_names():
        return
    personnel_columns = {
        column["name"] for column in inspector.get_columns("personel")
    }
    missing_name_columns = [
        column_name
        for column_name in ("ad", "soyad")
        if column_name not in personnel_columns
    ]
    if missing_name_columns:
        with database_engine.begin() as connection:
            for column_name in missing_name_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE personel ADD COLUMN {column_name} VARCHAR(100)"
                )
        logger.info(
            "Veritabanı uyumluluk güncellemesi uygulandı: personel.%s",
            ", personel.".join(missing_name_columns),
        )

    inspector = inspect(database_engine)
    if "sofor" not in inspector.get_table_names():
        return
    driver_columns = {
        column["name"] for column in inspector.get_columns("sofor")
    }
    missing_driver_name_columns = [
        column_name
        for column_name in ("ad", "soyad")
        if column_name not in driver_columns
    ]
    if missing_driver_name_columns:
        with database_engine.begin() as connection:
            for column_name in missing_driver_name_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE sofor ADD COLUMN {column_name} VARCHAR(100)"
                )
        logger.info(
            "Veritabanı uyumluluk güncellemesi uygulandı: sofor.%s",
            ", sofor.".join(missing_driver_name_columns),
        )

    inspector = inspect(database_engine)
    if "servis_guzergah_noktasi" not in inspector.get_table_names():
        return
    route_columns = {
        column["name"]: column
        for column in inspector.get_columns("servis_guzergah_noktasi")
    }
    route_schema_is_current = (
        "servis_vardiya_id" in route_columns
        and "aciklama" in route_columns
        and route_columns.get("enlem", {}).get("nullable", False)
        and route_columns.get("boylam", {}).get("nullable", False)
    )
    if route_schema_is_current:
        return

    backup_table = "servis_guzergah_noktasi_legacy"
    with database_engine.begin() as connection:
        row_count = int(
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM servis_guzergah_noktasi"
            ).scalar_one()
        )
        if row_count:
            existing_tables = set(inspect(connection).get_table_names())
            if backup_table in existing_tables:
                raise RuntimeError(
                    "Eski güzergâh noktaları için yedek tablo zaten mevcut. "
                    "Şema güncellemesi güvenli biçimde tamamlanamadı."
                )
            connection.exec_driver_sql(
                f"ALTER TABLE servis_guzergah_noktasi RENAME TO {backup_table}"
            )
            for index_row in connection.exec_driver_sql(
                f"PRAGMA index_list('{backup_table}')"
            ).mappings():
                index_name = str(index_row["name"])
                if index_row["origin"] == "c":
                    quoted_name = index_name.replace('"', '""')
                    connection.exec_driver_sql(f'DROP INDEX "{quoted_name}"')
            logger.warning(
                "Eski güzergâh noktaları %s tablosunda korundu; vardiya ilişkisi "
                "belirsiz olduğu için otomatik eşleştirme yapılmadı.",
                backup_table,
            )
        else:
            connection.exec_driver_sql("DROP TABLE servis_guzergah_noktasi")

    ServisGuzergahNoktasi.__table__.create(database_engine, checkfirst=True)
    logger.info(
        "Veritabanı uyumluluk güncellemesi uygulandı: "
        "servis_guzergah_noktasi artık servis_vardiya kaydına bağlı."
    )


def initialize_database(database_engine: Engine = engine) -> None:
    """Tanımlı tüm SQLAlchemy tablolarını yoksa oluşturur."""
    Base.metadata.create_all(database_engine)
    _apply_compatibility_migrations(database_engine)
    logger.info("SQLAlchemy veritabanı şeması hazır: %s", DATABASE_PATH)
