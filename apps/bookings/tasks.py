from celery import shared_task


@shared_task(name="bookings.celery_health_check")
def celery_health_check() -> dict[str, str]:
    return {"status": "ok"}
