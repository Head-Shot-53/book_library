import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def test_openapi_schema_is_available(api_client):
    response = api_client.get(
        reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )

    assert response.status_code == 200

    schema = json.loads(response.content)

    assert schema["openapi"].startswith("3.")

    assert "/api/v1/bookings/" in schema["paths"]


def test_openapi_contains_custom_booking_endpoints(api_client):
    response = api_client.get(
        reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )

    schema = json.loads(response.content)

    paths = schema["paths"]

    assert any(path.endswith("/cancel/") for path in paths)

    assert any(path.endswith("/history/") for path in paths)

    assert any(path.endswith("/availability/") for path in paths)


def test_booking_create_documents_conflict_response(api_client):
    response = api_client.get(
        reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )

    schema = json.loads(response.content)

    booking_create = schema["paths"]["/api/v1/bookings/"]["post"]

    assert "201" in booking_create["responses"]
    assert "400" in booking_create["responses"]
    assert "409" in booking_create["responses"]


def test_swagger_ui_is_available(api_client):
    response = api_client.get(reverse("swagger-ui"))

    assert response.status_code == 200


def test_redoc_is_available(api_client):
    response = api_client.get(reverse("redoc"))

    assert response.status_code == 200
