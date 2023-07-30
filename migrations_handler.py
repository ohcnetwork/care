from django.core.management import call_command
import django
import os
import psycopg
from psycopg import sql


# define the command options
# options = {
#     'verbosity': 1,   # adjust verbosity as needed
#     'interactive': False  # set to True if you want to prompt for user input
# }

def handler(*args, **kwargs):
    con = psycopg.connect(dbname='postgres',
                        user=os.environ.get("POSTGRES_USER"),
                        host=os.environ.get("POSTGRES_HOST"),
                        password=os.environ.get("POSTGRES_PASSWORD"),
                        port=os.environ.get("POSTGRES_PORT"),
                        autocommit=True
                        )

    cur = con.cursor()

    # Use the psycopg2.sql module instead of string concatenation
    # in order to avoid sql injection attacks.
    try:
        cur.execute(sql.SQL("CREATE DATABASE {};").format(
            sql.Identifier(os.environ.get("POSTGRES_DB")))
        )
    except psycopg.errors.DuplicateDatabase:
        pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    django.setup()
    call_command('migrate')

