"""SQLAlchemy şeması ve temel bütünlük kuralları testleri."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.connection import create_database_engine
from database.init_db import initialize_database
from database.models import (
    Atama,
    AtamaDurumu,
    Personel,
    PersonelTuru,
    Servis,
    ServisVardiyasi,
    VardiyaTuru,
    YakaTuru,
)
from database.repositories import PersonelRepository


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test.db"
        self.engine = create_database_engine(database_path)
        initialize_database(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    @staticmethod
    def create_personnel(personnel_number: str = "P000001") -> Personel:
        return Personel(
            sicil_no=personnel_number,
            ad="Ayşe",
            soyad="Yılmaz",
            ad_soyad="Ayşe Yılmaz",
            acik_adres="Test adresi",
            il="MERSİN",
            ilce="TARSUS",
            mahalle="TEST MAHALLESİ",
            enlem=None,
            boylam=None,
            vardiya_turu=VardiyaTuru.SABAH,
            yaka_turu=YakaTuru.MAVI,
            personel_turu=PersonelTuru.KADROLU,
            aktarim_grup_kodu=None,
            staj_baslangic_tarihi=None,
            staj_bitis_tarihi=None,
        )

    def test_required_tables_are_created(self) -> None:
        expected_tables = {
            "adres_onbellek",
            "atama",
            "ayar",
            "personel",
            "servis",
            "servis_guzergah_geometrisi",
            "servis_guzergah_noktasi",
            "servis_vardiya",
            "sofor",
        }
        self.assertTrue(expected_tables.issubset(set(inspect(self.engine).get_table_names())))

    def test_existing_database_receives_shift_route_column(self) -> None:
        legacy_engine = create_database_engine(
            Path(self.temporary_directory.name) / "legacy.db"
        )
        try:
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE servis_vardiya (id INTEGER PRIMARY KEY)"
                )
            initialize_database(legacy_engine)
            columns = {
                column["name"]
                for column in inspect(legacy_engine).get_columns("servis_vardiya")
            }
            self.assertIn("rota_adi", columns)
        finally:
            legacy_engine.dispose()

    def test_existing_database_receives_person_name_columns(self) -> None:
        legacy_engine = create_database_engine(
            Path(self.temporary_directory.name) / "legacy_personnel.db"
        )
        try:
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE personel (id INTEGER PRIMARY KEY)"
                )
            initialize_database(legacy_engine)
            columns = {
                column["name"]
                for column in inspect(legacy_engine).get_columns("personel")
            }
            self.assertTrue({"ad", "soyad"}.issubset(columns))
            self.assertTrue(
                {"koordinat_durumu", "koordinat_adres_ozeti"}.issubset(columns)
            )
        finally:
            legacy_engine.dispose()

    def test_existing_database_receives_driver_name_columns(self) -> None:
        legacy_engine = create_database_engine(
            Path(self.temporary_directory.name) / "legacy_driver.db"
        )
        try:
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE sofor ("
                    "id INTEGER PRIMARY KEY, "
                    "ad_soyad VARCHAR(200) NOT NULL, "
                    "telefon VARCHAR(30)"
                    ")"
                )
            initialize_database(legacy_engine)
            columns = {
                column["name"]
                for column in inspect(legacy_engine).get_columns("sofor")
            }
            self.assertTrue({"ad", "soyad", "ad_soyad", "telefon"}.issubset(columns))
        finally:
            legacy_engine.dispose()

    def test_legacy_route_rows_are_preserved_before_shift_schema_is_created(self) -> None:
        legacy_engine = create_database_engine(
            Path(self.temporary_directory.name) / "legacy_route.db"
        )
        try:
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE servis_guzergah_noktasi ("
                    "id INTEGER PRIMARY KEY, "
                    "servis_id INTEGER NOT NULL, "
                    "sira_no INTEGER NOT NULL, "
                    "nokta_adi VARCHAR(300) NOT NULL, "
                    "enlem FLOAT NOT NULL, "
                    "boylam FLOAT NOT NULL, "
                    "aktif_mi BOOLEAN NOT NULL"
                    ")"
                )
                connection.exec_driver_sql(
                    "INSERT INTO servis_guzergah_noktasi "
                    "(id, servis_id, sira_no, nokta_adi, enlem, boylam, aktif_mi) "
                    "VALUES (1, 7, 1, 'Eski nokta', 36.8, 34.6, 1)"
                )

            initialize_database(legacy_engine)
            inspector = inspect(legacy_engine)
            tables = set(inspector.get_table_names())
            columns = {
                column["name"]: column
                for column in inspector.get_columns("servis_guzergah_noktasi")
            }
            self.assertIn("servis_guzergah_noktasi_legacy", tables)
            self.assertIn("servis_vardiya_id", columns)
            self.assertIn("aciklama", columns)
            self.assertTrue(columns["enlem"]["nullable"])
            self.assertTrue(columns["boylam"]["nullable"])
            with legacy_engine.connect() as connection:
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT COUNT(*) FROM servis_guzergah_noktasi_legacy"
                    ).scalar_one(),
                    1,
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT COUNT(*) FROM servis_guzergah_noktasi"
                    ).scalar_one(),
                    0,
                )
        finally:
            legacy_engine.dispose()

    def test_legacy_physical_service_geometry_is_preserved_before_shift_schema(self) -> None:
        legacy_engine = create_database_engine(
            Path(self.temporary_directory.name) / "legacy_geometry.db"
        )
        try:
            with legacy_engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE servis_guzergah_geometrisi ("
                    "id INTEGER PRIMARY KEY, "
                    "servis_id INTEGER NOT NULL UNIQUE, "
                    "geojson TEXT NOT NULL, "
                    "toplam_mesafe_metre FLOAT NOT NULL, "
                    "hesaplanma_tarihi DATETIME NOT NULL, "
                    "aktif_mi BOOLEAN NOT NULL"
                    ")"
                )
                connection.exec_driver_sql(
                    "INSERT INTO servis_guzergah_geometrisi VALUES "
                    "(1, 7, '{}', 1000, CURRENT_TIMESTAMP, 1)"
                )
            initialize_database(legacy_engine)
            inspector = inspect(legacy_engine)
            tables = set(inspector.get_table_names())
            columns = {
                column["name"]
                for column in inspector.get_columns("servis_guzergah_geometrisi")
            }
            self.assertIn("servis_guzergah_geometrisi_legacy", tables)
            self.assertTrue(
                {
                    "servis_vardiya_id",
                    "toplam_sure_saniye",
                    "nokta_ozeti",
                    "guncel_mi",
                }.issubset(columns)
            )
            with legacy_engine.connect() as connection:
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT COUNT(*) FROM servis_guzergah_geometrisi_legacy"
                    ).scalar_one(),
                    1,
                )
        finally:
            legacy_engine.dispose()

    def test_duplicate_personnel_number_is_rejected(self) -> None:
        with self.session_factory() as session:
            session.add(self.create_personnel())
            session.commit()
            session.add(self.create_personnel())
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_duplicate_physical_service_code_is_rejected(self) -> None:
        with self.session_factory() as session:
            session.add_all([Servis(servis_kodu="S_001"), Servis(servis_kodu="S_001")])
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_same_service_can_have_different_shifts(self) -> None:
        with self.session_factory() as session:
            service = Servis(servis_kodu="S_001")
            service.vardiyalar.extend(
                [
                    ServisVardiyasi(
                        vardiya_turu=VardiyaTuru.SABAH,
                        yaka_turu=YakaTuru.MAVI,
                        kapasite=46,
                    ),
                    ServisVardiyasi(
                        vardiya_turu=VardiyaTuru.AKSAM,
                        yaka_turu=YakaTuru.MAVI,
                        kapasite=46,
                    ),
                ]
            )
            session.add(service)
            session.commit()
            self.assertEqual(len(service.vardiyalar), 2)

    def test_sqlite_foreign_keys_are_enabled_and_enforced(self) -> None:
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("PRAGMA foreign_keys")), 1)

        with self.session_factory() as session:
            session.add(
                ServisVardiyasi(
                    servis_id=999_999,
                    vardiya_turu=VardiyaTuru.SABAH,
                    yaka_turu=YakaTuru.MAVI,
                    kapasite=16,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_personnel_can_have_only_one_active_assignment(self) -> None:
        with self.session_factory() as session:
            personnel = self.create_personnel()
            service = Servis(servis_kodu="S_001")
            first_shift = ServisVardiyasi(
                vardiya_turu=VardiyaTuru.SABAH,
                yaka_turu=YakaTuru.MAVI,
                kapasite=46,
            )
            second_shift = ServisVardiyasi(
                vardiya_turu=VardiyaTuru.AKSAM,
                yaka_turu=YakaTuru.MAVI,
                kapasite=46,
            )
            service.vardiyalar.extend([first_shift, second_shift])
            session.add_all([personnel, service])
            session.flush()
            session.add(
                Atama(
                    personel_id=personnel.id,
                    servis_vardiya_id=first_shift.id,
                    atama_durumu=AtamaDurumu.ATANDI,
                    aktif_mi=True,
                )
            )
            session.commit()
            session.add(
                Atama(
                    personel_id=personnel.id,
                    servis_vardiya_id=second_shift.id,
                    atama_durumu=AtamaDurumu.ATANDI,
                    aktif_mi=True,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_inactive_assignment_history_allows_a_new_active_assignment(self) -> None:
        with self.session_factory() as session:
            personnel = self.create_personnel()
            service = Servis(servis_kodu="S_001")
            first_shift = ServisVardiyasi(
                vardiya_turu=VardiyaTuru.SABAH,
                yaka_turu=YakaTuru.MAVI,
                kapasite=46,
            )
            second_shift = ServisVardiyasi(
                vardiya_turu=VardiyaTuru.AKSAM,
                yaka_turu=YakaTuru.MAVI,
                kapasite=46,
            )
            service.vardiyalar.extend([first_shift, second_shift])
            session.add_all([personnel, service])
            session.flush()
            session.add_all(
                [
                    Atama(
                        personel_id=personnel.id,
                        servis_vardiya_id=first_shift.id,
                        atama_durumu=AtamaDurumu.ATANDI,
                        aktif_mi=False,
                    ),
                    Atama(
                        personel_id=personnel.id,
                        servis_vardiya_id=second_shift.id,
                        atama_durumu=AtamaDurumu.ATANDI,
                        aktif_mi=True,
                    ),
                ]
            )
            session.commit()

    def test_repository_supports_lookup_and_soft_deactivation(self) -> None:
        with self.session_factory() as session:
            repository = PersonelRepository(session)
            personnel = repository.add(self.create_personnel())
            self.assertIs(repository.get_by_sicil_no("P000001"), personnel)
            repository.set_active(personnel, False)
            self.assertEqual(repository.list_all(), [])
            self.assertEqual(repository.list_all(include_inactive=True), [personnel])


if __name__ == "__main__":
    unittest.main()
