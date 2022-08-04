#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    try:
        command = sys.argv[1]
    except IndexError:
        command = "help"

    if command == "test":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
        # TODO: remove in django 4.1+
        # patched for darwin
        # https://adamj.eu/tech/2020/07/21/how-to-use-djangos-parallel-testing-on-macos-with-python-3.8-plus/
        if sys.platform == "darwin":  # pragma: no cover
            import multiprocessing

            if os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "") != "YES":
                print(
                    (
                        "Set OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES in your"
                        + " environment to work around use of forking in Django's"
                        + " test runner."
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)
            multiprocessing.set_start_method("fork")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django  # noqa
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )

        raise

    # This allows easy placement of apps within the interior
    # care directory.
    current_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(current_path, "care"))

    execute_from_command_line(sys.argv)
