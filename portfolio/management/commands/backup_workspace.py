import sqlite3
from contextlib import closing
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = 'Make a consistent SQLite copy of the local workspace at a new path.'

    def add_arguments(self, parser):
        parser.add_argument('destination', type=Path)

    def handle(self, *args, **options):
        source = connections['default']
        if source.vendor != 'sqlite' or source.in_atomic_block:
            raise CommandError('Run the backup on a SQLite workspace outside of a transaction.')
        if not Path(source.settings_dict['NAME']).is_file():
            raise CommandError('The workspace database does not exist. Run setup first.')

        target = options['destination'].expanduser().absolute()
        try:
            with target.open('xb'):
                pass
        except OSError as exc:
            raise CommandError(f'Could not create a new backup file: {exc}') from exc

        try:
            source.ensure_connection()
            with closing(sqlite3.connect(target)) as dest:
                source.connection.backup(dest)
                if dest.execute('PRAGMA quick_check').fetchone() != ('ok',):
                    raise CommandError('The backup did not pass SQLite integrity verification.')
        except BaseException:
            target.unlink(missing_ok=True)
            raise

        self.stdout.write(self.style.SUCCESS(f'Workspace backup saved to {target}'))
