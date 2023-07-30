from django.core.management import call_command
from django.conf import settings
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT # <-- ADD THIS LINE


# define the command options
options = {
    'verbosity': 1,   # adjust verbosity as needed
    'interactive': False  # set to True if you want to prompt for user input
}

def handler():
    con = psycopg2.connect(dbname='postgres',
                           user=settings.POSTGRES_USER,
                           host=settings.POSTGRES_HOST,
                           password = settings.POSTGRES_PASSWORD)

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # <-- ADD THIS LINE

    cur = con.cursor()

    # Use the psycopg2.sql module instead of string concatenation
    # in order to avoid sql injection attacks.
    cur.execute(sql.SQL("IF NOT EXISTS CREATE DATABASE {}").format(
        sql.Identifier(settings.POSTGRES_DB))
    )

    call_command('migrate', options)



