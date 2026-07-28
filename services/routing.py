"""OSRM rota API istemcisi ve cevap doğrulaması."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from services.external_http import (
    ExternalServiceError,
    InvalidExternalResponseError,
    JsonHttpClient,
)
from services.geocoding import APPLICATION_USER_AGENT


logger = logging.getLogger(__name__)
DEFAULT_OSRM_URL = os.getenv(
    "SERVIS_ATAMA_OSRM_URL",
    "https://router.project-osrm.org/route/v1/driving",
)


class RoutingError(ExternalServiceError):
    """OSRM rota hesabı tamamlanamadığında üretilir."""


@dataclass(frozen=True, slots=True)
class RouteCoordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class RoutingResult:
    distance_meters: float
    duration_seconds: float
    geometry: dict[str, object]


class OsrmRoutingService:
    def __init__(
        self,
        *,
        http_client: JsonHttpClient | None = None,
        base_url: str = DEFAULT_OSRM_URL,
        timeout_seconds: float = 25.0,
    ) -> None:
        self.http_client = http_client or JsonHttpClient()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def calculate(self, coordinates: tuple[RouteCoordinate, ...]) -> RoutingResult:
        if len(coordinates) < 2:
            raise RoutingError("Rota hesaplamak için en az iki koordinatlı nokta gerekir.")
        coordinate_path = ";".join(
            f"{point.longitude:.8f},{point.latitude:.8f}" for point in coordinates
        )
        try:
            payload = self.http_client.get_json(
                f"{self.base_url}/{coordinate_path}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "false",
                },
                headers={"User-Agent": APPLICATION_USER_AGENT},
                timeout=self.timeout_seconds,
            )
        except ExternalServiceError:
            logger.warning("OSRM rota isteği tamamlanamadı.")
            raise
        if not isinstance(payload, dict) or payload.get("code") != "Ok":
            message = payload.get("message") if isinstance(payload, dict) else None
            raise RoutingError(
                str(message or "Rota servisi bu noktalar için rota bulamadı.")
            )
        routes = payload.get("routes")
        if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
            raise InvalidExternalResponseError("Rota servisi geçersiz cevap döndürdü.")
        route = routes[0]
        geometry = route.get("geometry")
        try:
            distance = float(route["distance"])
            duration = float(route["duration"])
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidExternalResponseError(
                "Rota servisinin mesafe veya süre cevabı geçersiz."
            ) from error
        if (
            distance < 0
            or duration < 0
            or not isinstance(geometry, dict)
            or geometry.get("type") != "LineString"
            or not isinstance(geometry.get("coordinates"), list)
        ):
            raise InvalidExternalResponseError("Rota servisi geçersiz rota döndürdü.")
        return RoutingResult(
            distance_meters=distance,
            duration_seconds=duration,
            geometry=geometry,
        )
