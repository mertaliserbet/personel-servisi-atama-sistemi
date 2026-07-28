"""Nominatim adres arama, sonuç normalizasyonu ve adres karşılaştırma kuralları."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable

from normalization.text import comparison_key, normalize_text
from services.external_http import (
    ExternalServiceError,
    InvalidExternalResponseError,
    JsonHttpClient,
)


logger = logging.getLogger(__name__)

DEFAULT_NOMINATIM_URL = os.getenv(
    "SERVIS_ATAMA_NOMINATIM_URL",
    "https://nominatim.openstreetmap.org/search",
)
APPLICATION_USER_AGENT = os.getenv(
    "SERVIS_ATAMA_USER_AGENT",
    "PersonelServisiAtamaSistemi/1.0",
)


class GeocodingError(ExternalServiceError):
    """Nominatim araması tamamlanamadığında üretilir."""


@dataclass(frozen=True, slots=True)
class AddressInput:
    address: str | None
    city: str | None
    district: str | None
    neighborhood: str | None

    def full_query(self) -> str:
        return _join_query(
            self.address,
            self.neighborhood,
            self.district,
            self.city,
            "Türkiye",
        )

    def fallback_query(self) -> str:
        return _join_query(
            self.neighborhood,
            self.district,
            self.city,
            "Türkiye",
        )

    def signature(self) -> str:
        normalized = "|".join(
            comparison_key(value) or ""
            for value in (self.address, self.city, self.district, self.neighborhood)
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class GeocodingCandidate:
    place_id: str
    display_name: str
    latitude: float
    longitude: float
    city: str | None
    district: str | None
    neighborhood: str | None


@dataclass(frozen=True, slots=True)
class AddressMismatch:
    field: str
    expected: str
    found: str

    @property
    def message(self) -> str:
        return f"{self.field}: mevcut '{self.expected}', bulunan '{self.found}'"


@dataclass(frozen=True, slots=True)
class GeocodingSearchResponse:
    candidates: tuple[GeocodingCandidate, ...]
    used_fallback: bool


def _join_query(*values: object) -> str:
    return ", ".join(
        normalized
        for value in values
        if (normalized := normalize_text(value)) is not None
    )


def compare_address(
    expected: AddressInput,
    candidate: GeocodingCandidate,
) -> tuple[AddressMismatch, ...]:
    mismatches: list[AddressMismatch] = []
    for label, expected_value, found_value in (
        ("İl", expected.city, candidate.city),
        ("İlçe", expected.district, candidate.district),
        ("Mahalle", expected.neighborhood, candidate.neighborhood),
    ):
        expected_key = comparison_key(expected_value)
        found_key = comparison_key(found_value)
        if expected_key and found_key and expected_key != found_key:
            mismatches.append(
                AddressMismatch(
                    field=label,
                    expected=normalize_text(expected_value) or "",
                    found=normalize_text(found_value) or "",
                )
            )
    return tuple(mismatches)


class NominatimGeocodingService:
    """Nominatim kullanım politikasına uygun, tek iş parçacıklı oran sınırlı istemci."""

    _rate_lock = threading.Lock()
    _last_request_time = 0.0

    def __init__(
        self,
        *,
        http_client: JsonHttpClient | None = None,
        base_url: str = DEFAULT_NOMINATIM_URL,
        timeout_seconds: float = 15.0,
        minimum_interval_seconds: float = 1.05,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.http_client = http_client or JsonHttpClient()
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.minimum_interval_seconds = minimum_interval_seconds
        self.clock = clock
        self.sleeper = sleeper

    def search(self, address: AddressInput) -> GeocodingSearchResponse:
        full_query = address.full_query()
        fallback_query = address.fallback_query()
        if not full_query:
            raise GeocodingError("Adres çözümleme için yeterli konum bilgisi bulunmuyor.")
        candidates = self._search_query(full_query)
        used_fallback = False
        if not candidates and fallback_query and fallback_query != full_query:
            candidates = self._search_query(fallback_query)
            used_fallback = True
        return GeocodingSearchResponse(
            candidates=tuple(candidates),
            used_fallback=used_fallback,
        )

    def _search_query(self, query: str) -> list[GeocodingCandidate]:
        self._wait_for_rate_limit()
        try:
            payload = self.http_client.get_json(
                self.base_url,
                params={
                    "q": query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "limit": 5,
                    "countrycodes": "tr",
                    "accept-language": "tr",
                },
                headers={"User-Agent": APPLICATION_USER_AGENT},
                timeout=self.timeout_seconds,
            )
        except ExternalServiceError:
            logger.warning("Nominatim isteği tamamlanamadı; adres içeriği loglanmadı.")
            raise
        if not isinstance(payload, list):
            raise InvalidExternalResponseError(
                "Adres servisi beklenmeyen bir cevap döndürdü."
            )
        candidates: list[GeocodingCandidate] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                continue
            address = item.get("address")
            details = address if isinstance(address, dict) else {}
            candidates.append(
                GeocodingCandidate(
                    place_id=str(item.get("place_id") or ""),
                    display_name=str(item.get("display_name") or "İsimsiz sonuç"),
                    latitude=latitude,
                    longitude=longitude,
                    city=_first(details, "province", "state", "city"),
                    district=_first(
                        details,
                        "county",
                        "town",
                        "city_district",
                        "district",
                    ),
                    neighborhood=_first(
                        details,
                        "neighbourhood",
                        "suburb",
                        "quarter",
                        "village",
                    ),
                )
            )
        return candidates

    def _wait_for_rate_limit(self) -> None:
        with self._rate_lock:
            now = self.clock()
            wait_seconds = self.minimum_interval_seconds - (
                now - type(self)._last_request_time
            )
            if wait_seconds > 0:
                self.sleeper(wait_seconds)
            type(self)._last_request_time = self.clock()


def _first(values: dict[object, object], *keys: str) -> str | None:
    for key in keys:
        value = normalize_text(values.get(key))
        if value is not None:
            return value
    return None
