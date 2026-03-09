"""
Management command: add product names into the Product table (project.Product).
Run: python manage.py addProductsName
"""
from django.core.management.base import BaseCommand
from project.models import Product


# Product names to insert. Edit this list to add or change names.
PRODUCT_NAMES = [
    "Cropeye",
    "BMS",
    "RAMS",
    "Climateye",
    "solar",
    "cropeyeApp",
    "Topography",
    "Nearlive crop monitoring",
]


class Command(BaseCommand):
    help = "Add certain product names into the Product database table (project.Product)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be added, do not write to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes will be saved."))

        created = []
        skipped = []

        for name in PRODUCT_NAMES:
            name = (name or "").strip()
            if not name:
                continue
            exists = Product.objects.filter(name__iexact=name).exists()
            if dry_run:
                if exists:
                    skipped.append(name)
                else:
                    created.append(name)
                continue
            if exists:
                skipped.append(name)
            else:
                Product.objects.create(name=name, description="")
                created.append(name)

        if dry_run:
            if created:
                self.stdout.write(self.style.SUCCESS(f"Would create: {', '.join(created)}"))
            if skipped:
                self.stdout.write(self.style.NOTICE(f"Already exist (would skip): {', '.join(skipped)}"))
        else:
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {len(created)} product(s): {', '.join(created)}"))
            if skipped:
                self.stdout.write(self.style.NOTICE(f"Skipped (already exist): {', '.join(skipped)}"))

        if not created and not skipped:
            self.stdout.write(self.style.WARNING("No product names to add (list is empty or all blank)."))
