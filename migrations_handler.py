from django.core.management import call_command

# define the command options
options = {
    'verbosity': 1,   # adjust verbosity as needed
    'interactive': False  # set to True if you want to prompt for user input
}

def handler():
    call_command('migrate', options)

