"""runserver que requiere autenticarse de nuevo después de un reinicio."""

from django.contrib.sessions.models import Session
from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticFilesRunserverCommand,
)


class Command(StaticFilesRunserverCommand):
    def handle(self, *args, **options):
        Session.objects.all().delete()
        return super().handle(*args, **options)
