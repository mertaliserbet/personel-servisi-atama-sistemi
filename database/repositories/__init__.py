"""Repository sınıflarının merkezi dışa aktarımı."""

from database.repositories.base import BaseRepository
from database.repositories.mapping_repository import (
    AddressCacheRepository,
    ApplicationSettingRepository,
    PersonnelCoordinateRepository,
    RouteGeometryRepository,
    RoutePointCoordinateRepository,
)
from database.repositories.personel_repository import PersonelRepository
from database.repositories.route_repository import RoutePointRepository
from database.repositories.route_design_repository import (
    RouteControlPointRepository,
    SavedRouteRepository,
    ServiceRouteLinkRepository,
    delete_unused_service,
    service_historical_assignment_count,
)
from database.repositories.sofor_repository import SoforRepository
from database.repositories.servis_repository import (
    ServisRepository,
    ServisVardiyasiRepository,
)

__all__ = [
    "BaseRepository",
    "AddressCacheRepository",
    "ApplicationSettingRepository",
    "PersonnelCoordinateRepository",
    "PersonelRepository",
    "RoutePointRepository",
    "RouteControlPointRepository",
    "SavedRouteRepository",
    "ServiceRouteLinkRepository",
    "RoutePointCoordinateRepository",
    "RouteGeometryRepository",
    "SoforRepository",
    "ServisRepository",
    "ServisVardiyasiRepository",
    "delete_unused_service",
    "service_historical_assignment_count",
]
