from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Loads tags'

    def handle(self, *args, **kwargs):
        data = [
            {'name': 'завтрак', 'color': '#E26C2D', 'slug': 'breakfast'},
            {'name': 'обед', 'color': '#49B64E', 'slug': 'dinner'},
            {'name': 'ужин', 'color': '#8775D2', 'slug': 'late_dinner'},
        ]
        Tag.objects.bulk_create(Tag(**tag) for tag in data)
        self.stdout.write(
            self.style.SUCCESS('Тэги загружены')
        )