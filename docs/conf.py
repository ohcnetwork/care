# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

# -- Project information -----------------------------------------------------
import os
import sys
from datetime import date
from pathlib import Path

import django

# import github_links

sys.path.insert(0, str(Path("..").resolve()))

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
django.setup()

project = "Care"
copyright = f"{date.today().year}, Open Healthcare Network"  # noqa: A001, DTZ011
author = "ohcnetwork"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    # "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.apidoc",
    "sphinx.ext.doctest",
]

# autosummary_generate = True


apidoc_modules = [
    {
        "path": "../care",
        "destination": "source/generated",
        "exclude_patterns": ["**/test*", "**/migrations*", "**/migrations_old*"],
        "max_depth": 4,
        "follow_links": False,
        "separate_modules": True,
        "include_private": False,
        "no_headings": False,
        "module_first": True,
        "implicit_namespaces": False,
    },
]

autodoc_inherit_docstrings = False

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": False,
    "show-inheritance": True,
    "inherited-members": False,
}

extlinks = {
    "commit": ("https://github.com/ohcnetwork/care/commit/%s", "%s"),
    # A file or directory. GitHub redirects from blob to tree if needed.
    "source": ("https://github.com/ohcnetwork/care/blob/develop/%s", "%s"),
    "issue": ("https://github.com/ohcnetwork/care/issues/%s", "#%s"),
    "pr": ("https://github.com/ohcnetwork/care/pull/%s", "PR #%s"),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".git",
    "**/tests*",
    "**/migrations*",
]


# Spelling check needs an additional module that is not installed by default.
# Add it only if spelling check is requested so docs can be generated without
# it.
if "spelling" in sys.argv:
    extensions.append("sphinxcontrib.spelling")

# Spelling language.
spelling_lang = "en_US"

# Location of word list.
spelling_word_list_filename = "spelling_wordlist"

spelling_warning = True

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = "default-role-error"

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "trac"

# Links to Python's docs should reference the most recent version of the 3.x
# branch, which is located at this URL.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "psycopg": ("https://www.psycopg.org/psycopg3/docs", None),
    "django": ("https://docs.djangoproject.com/en/stable/", None),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static", "../care/static"]
html_favicon = "../care/static/images/favicons/favicon.ico"
html_theme_options = {
    "light_logo": "images/logos/logo-light.svg",
    "dark_logo": "images/logos/logo-dark.svg",
}

# def version_github_linkcode_resolve(domain, info):
#     return github_links.github_linkcode_resolve(
#         domain, info, version=version, next_version=django_next_version
#     )


# linkcode_resolve = version_github_linkcode_resolve
