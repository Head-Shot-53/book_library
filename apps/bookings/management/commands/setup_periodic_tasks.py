from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask

TASK_NAME = "Complete expired bookings"

TASK_PATH = "bookings.complete_expired_bookings"


class Command(BaseCommand):
    help = "Create or update Booking Management System periodic Celery tasks."

    def handle(self, *args, **options):
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.MINUTES
        )

        periodic_task, created = PeriodicTask.objects.update_or_create(
            name=TASK_NAME,
            defaults={
                "task": TASK_PATH,
                "interval": schedule,
                "enabled": True,
                "args": "[]",
                "kwargs": "{}",
                "description": (
                    "Automatically completes "
                    "confirmed bookings whose "
                    "end time has passed."
                ),
            },
        )

        action = "Created" if created else "Updated"

        self.stdout.write(
            self.style.SUCCESS(f"{action} periodic task: {periodic_task.name}")
        )
