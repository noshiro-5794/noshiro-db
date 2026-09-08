from django.core.management.base import BaseCommand, CommandError

from apps.sync.services.mal_service import mal_import_service


class Command(BaseCommand):
    help = "Import one MAL anime entry into the knowledge graph."

    def add_arguments(self, parser):
        parser.add_argument("mal_id", type=int)

    def handle(self, *args, **options):
        try:
            entity = mal_import_service.import_anime(options["mal_id"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Imported MAL {options['mal_id']} as {entity.id}")
        )
