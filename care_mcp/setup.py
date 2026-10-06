#!/usr/bin/env python

"""The setup script."""

from pathlib import Path

from setuptools import find_packages, setup

readme = Path("README.md").read_text()

# Everything else (Django, DRF, jsonschema, django-ratelimit) comes from Care itself.
requirements = []

setup(
    author="Open Healthcare Network",
    author_email="info@ohc.network",
    python_requires=">=3.13",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
    ],
    description="Model Context Protocol (MCP) server for CARE, running inside Care.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="care_mcp",
    name="care_mcp",
    packages=find_packages(include=["care_mcp", "care_mcp.*"]),
    url="https://github.com/ohcnetwork/care_mcp",
    version="0.1.0",
    zip_safe=False,
)
