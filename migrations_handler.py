from django.core.management import call_command
import django
import os
from django.conf import settings
import psycopg
from psycopg import sql


# define the command options
# options = {
#     'verbosity': 1,   # adjust verbosity as needed
#     'interactive': False  # set to True if you want to prompt for user input
# }

def handler(*args, **kwargs):
    con = psycopg.connect(dbname=settings.POSTGRES_DB,
                        user=settings.POSTGRES_USER,
                        host=settings.POSTGRES_HOST,
                        password=settings.POSTGRES_PASSWORD,
                        autocommit=True
                        )

    cur = con.cursor()

    # Use the psycopg2.sql module instead of string concatenation
    # in order to avoid sql injection attacks.
    try:
        cur.execute(sql.SQL("CREATE DATABASE {};").format(
            sql.Identifier('previewlocal'))
        )
    except psycopg.errors.DuplicateDatabase:
        pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    django.setup()
    call_command('migrate')

