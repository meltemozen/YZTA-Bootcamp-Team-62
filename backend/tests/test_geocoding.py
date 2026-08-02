"""Deterministic tests for installation-location geocoding."""

import pytest

from app.services import geocoding


@pytest.fixture(autouse=True)
def clear_geocoding_cache():
    geocoding.resolve_location.cache_clear()
    geocoding.reverse_location.cache_clear()


def test_resolve_location_selects_matching_province(monkeypatch):
    monkeypatch.setattr(geocoding, "_get", lambda _url, _params: [
        {
            "name": "Kadıköy",
            "lat": "40.62015",
            "lon": "29.22536",
            "category": "place",
            "address": {"province": "Yalova"},
        },
        {
            "name": "Kadıköy",
            "lat": "40.9912955",
            "lon": "29.0245631",
            "category": "boundary",
            "address": {"province": "İstanbul"},
        },
    ])

    result = geocoding.resolve_location("İstanbul", "Kadıköy")

    assert result["label"] == "Kadıköy, İstanbul"
    assert result["lat"] == 40.991295
    assert result["lon"] == 29.024563


def test_reverse_location_returns_district_and_province(monkeypatch):
    monkeypatch.setattr(geocoding, "_get", lambda _url, _params: {
        "address": {"town": "Çankaya", "province": "Ankara"},
    })

    result = geocoding.reverse_location(39.9179, 32.86268)

    assert result["label"] == "Çankaya, Ankara"
    assert result["district"] == "Çankaya"
    assert result["province"] == "Ankara"


def test_resolve_location_rejects_wrong_province(monkeypatch):
    monkeypatch.setattr(geocoding, "_get", lambda _url, _params: [{
        "name": "Kadıköy",
        "lat": "40.62015",
        "lon": "29.22536",
        "address": {"province": "Yalova"},
    }])

    with pytest.raises(geocoding.GeocodingUnavailableError):
        geocoding.resolve_location("İstanbul", "Kadıköy")
