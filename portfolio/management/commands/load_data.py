from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from portfolio.services import load_portfolio_data

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--excel-path",
            type=str,
            default=str(Path(settings.BASE_DIR) / "data" / "datos.xlsx")
        )
    
    def handle(self, *args, **options):
        excel_path = Path(options["excel_path"])

        self.stdout.write(self.style.NOTICE(f"cargando datos desde: {excel_path}"))

        try:
            load_portfolio_data(excel_path)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc
        except ValueError as exc:
            raise CommandError(f"Error de validación: {exc}") from exc
        except Exception as exc:
            raise CommandError(f"Error inesperado: {exc}") from exc 
        
        self.stdout.write(self.style.SUCCESS("Datos cargados correctamente"))