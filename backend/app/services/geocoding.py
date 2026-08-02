"""Forward and reverse geocoding for the fixed installation location."""

import os
import threading
import time
import unicodedata
from functools import lru_cache

import httpx

_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
_REQUEST_LOCK = threading.Lock()
_last_request_at = 0.0


class GeocodingUnavailableError(RuntimeError):
    """Raised when a location cannot be resolved safely."""


def _normalized(value: str | None) -> str:
    value = (value or "").translate(str.maketrans({"ı": "i", "İ": "I"})).casefold()
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def _get(url: str, params: dict) -> dict | list:
    global _last_request_at
    contact = os.getenv("WATTRA_CONTACT_EMAIL", "admin@altspacelabs.com")
    headers = {
        "User-Agent": f"Wattra/0.2 ({contact})",
        "Referer": "https://altspacelabs.com/",
        "Accept-Language": "tr",
    }
    try:
        # The public Nominatim service requires at most one request per second.
        with _REQUEST_LOCK:
            delay = 1.0 - (time.monotonic() - _last_request_at)
            if delay > 0:
                time.sleep(delay)
            response = httpx.get(url, params=params, headers=headers, timeout=12)
            _last_request_at = time.monotonic()
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, TypeError, ValueError) as error:
        raise GeocodingUnavailableError("Konum çözümlenemedi") from error


def _label(district: str | None, province: str | None) -> str:
    if district and province and _normalized(district) != _normalized(province):
        return f"{district}, {province}"
    return district or province or "Konum"


@lru_cache(maxsize=2048)
def resolve_location(province: str, district: str) -> dict:
    """Resolve a selected Turkish province/district to a representative point."""
    province = province.strip()
    district = district.strip()
    search_name = province if _normalized(district) == "merkez" else f"{district}, {province}"
    results = _get(_SEARCH_URL, {
        "q": f"{search_name}, Türkiye",
        "format": "jsonv2",
        "addressdetails": 1,
        "countrycodes": "tr",
        "limit": 5,
    })
    if not isinstance(results, list):
        raise GeocodingUnavailableError("Konum çözümlenemedi")

    province_key = _normalized(province)
    district_key = _normalized(district)

    def score(item: dict) -> int:
        address = item.get("address") or {}
        result_province = address.get("province") or address.get("state")
        result_name = item.get("name")
        points = 100 if _normalized(result_province) == province_key else 0
        if district_key != "merkez" and _normalized(result_name) == district_key:
            points += 50
        if item.get("category") == "boundary":
            points += 10
        return points

    matches = [item for item in results if score(item) >= 100]
    if not matches:
        raise GeocodingUnavailableError("Seçilen ilçe için koordinat bulunamadı")
    best = max(matches, key=score)
    try:
        lat = round(float(best["lat"]), 6)
        lon = round(float(best["lon"]), 6)
    except (KeyError, TypeError, ValueError) as error:
        raise GeocodingUnavailableError("Geçersiz koordinat yanıtı") from error

    return {
        "province": province,
        "district": district,
        "label": _label(district, province),
        "lat": lat,
        "lon": lon,
        "source": "openstreetmap",
    }


@lru_cache(maxsize=4096)
def reverse_location(lat: float, lon: float) -> dict:
    """Return a district/province label for an exact GPS coordinate."""
    body = _get(_REVERSE_URL, {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 14,
    })
    if not isinstance(body, dict):
        raise GeocodingUnavailableError("Konum çözümlenemedi")
    address = body.get("address") or {}
    province = address.get("province") or address.get("state")
    district = (
        address.get("town")
        or address.get("city_district")
        or address.get("county")
        or address.get("municipality")
        or address.get("district")
        or address.get("city")
    )
    if not province and not district:
        raise GeocodingUnavailableError("Adres bilgisi bulunamadı")
    return {
        "province": province,
        "district": district,
        "label": _label(district, province),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "source": "openstreetmap",
    }
