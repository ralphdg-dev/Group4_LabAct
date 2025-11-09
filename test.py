import pytest
from unittest.mock import patch, MagicMock
from fantasticTour import RouteAPI 

@pytest.fixture
def api():
    return RouteAPI()

def test_validate_api_key_missing(monkeypatch, api):
    monkeypatch.setattr(api, "key", None)
    result = api.validate_api_key()
    assert result["status"] == "error"
    assert "not found" in result["message"]

def test_validate_api_key_invalid(api):
    api.key = " "
    result = api.validate_api_key()
    assert result["status"] == "error"
    assert "Invalid API key format" in result["message"]

def test_validate_api_key_success(api):
    api.key = "valid_key_123"
    result = api.validate_api_key()
    assert result["status"] == "success"

def test_validate_location_input_empty(api):
    result = api.validate_location_input("")
    assert result["status"] == "error"

def test_validate_location_input_short(api):
    result = api.validate_location_input("a")
    assert result["status"] == "error"

def test_validate_location_input_invalid_chars(api):
    result = api.validate_location_input("Manila; DROP TABLE")
    assert result["status"] == "error"

def test_validate_location_input_success(api):
    result = api.validate_location_input("Manila")
    assert result["status"] == "success"

def test_validate_vehicle_type_invalid(api):
    result = api.validate_vehicle_type("plane")
    assert result["status"] == "error"

def test_validate_vehicle_type_success(api):
    result = api.validate_vehicle_type("car")
    assert result["status"] == "success"

@patch("requests.get")
def test_geocode_success(mock_get, api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {"point": {"lat": 14.5995, "lng": 120.9842}, "name": "Manila", "country": "Philippines", "state": "NCR"}
        ]
    }
    mock_get.return_value = mock_response
    api.key = "mock_key"
    result = api.geocode("Manila")
    assert result["status"] == "success"
    assert result["lat"] == 14.5995
    assert result["lng"] == 120.9842

@patch("requests.get")
def test_geocode_no_results(mock_get, api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"hits": []}
    mock_get.return_value = mock_response
    api.key = "mock_key"
    result = api.geocode("Unknown Place")
    assert result["status"] == "error"
    assert "No results" in result["message"]

@patch("requests.get")
def test_get_route_success(mock_get, api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "paths": [{"distance": 5000, "time": 600000, "points": {"coordinates": [[120.98, 14.60], [121.00, 14.61]]}}]
    }
    mock_get.return_value = mock_response
    api.key = "mock_key"
    start = {"lat": 14.6, "lng": 120.98}
    end = {"lat": 14.61, "lng": 121.00}
    result = api.get_route(start, end, "car")
    assert result["status"] == "success"
    assert "paths" in result["data"]

def test_get_route_invalid_coords(api):
    start = {"lat": 200, "lng": 300}
    end = {"lat": 14.6, "lng": 121.0}
    api.key = "mock_key"
    result = api.get_route(start, end, "car")
    assert result["status"] == "error"
    assert "Invalid coordinate values" in result["message"]

def test_get_google_maps_url(api):
    start = {"lat": 14.6, "lng": 120.98}
    end = {"lat": 14.61, "lng": 121.0}
    url = api.get_google_maps_url(start, end, "bike")
    assert "bicycling" in url
    assert "origin=14.6,120.98" in url
    assert "destination=14.61,121.0" in url
