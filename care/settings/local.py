from . import base
# import os

class Settings(base.Settings):

    ########## DATABASE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'covid19',
            'USER': 'root',
            'PASSWORD': '123456',
            'HOST': 'localhost',
            'PORT': '3306',
            'TEST': {
                'CHARSET': 'utf8',
                'COLLATION': 'utf8_bin',
            },
            'OPTIONS': {
                'sql_mode': 'POSTGRESQL,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_postgresql
                             'STRICT_ALL_TABLES,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_strict_all_tables
                             'ERROR_FOR_DIVISION_BY_ZERO,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_error_for_division_by_zero
                             'NO_AUTO_CREATE_USER,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_no_auto_create_user
                             'NO_AUTO_VALUE_ON_ZERO,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_no_auto_value_on_zero
                             'NO_ENGINE_SUBSTITUTION,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_no_engine_substitution
                             'NO_ZERO_DATE,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_no_zero_date
                             'NO_ZERO_IN_DATE,'  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_no_zero_in_date
                             'ONLY_FULL_GROUP_BY',  # https://dev.mysql.com/doc/refman/5.7/en/sql-mode.html#sqlmode_only_full_group_by
                'charset': 'utf8',
                'init_command': 'SET '
                                 'collation_connection=utf8_bin;'
                                 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED',
            }
        }
    }
    ########## END DATABASE CONFIGURATION

    DEBUG = True
