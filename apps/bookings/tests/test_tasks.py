from apps.bookings.tasks import celery_health_check


def test_celery_health_check():
    result = celery_health_check.run()

    assert result == {"status": "ok"}
