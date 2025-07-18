from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="care-whatsapp-bot",
    version="1.0.0",
    author="CARE Development Team",
    author_email="care@ohc.network",
    description="WhatsApp Bot Plugin for CARE Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ohcnetwork/care_whatsapp_bot",
    project_urls={
        "Bug Tracker": "https://github.com/ohcnetwork/care_whatsapp_bot/issues",
        "Documentation": "https://care-docs.ohc.network/",
        "Source Code": "https://github.com/ohcnetwork/care_whatsapp_bot",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-django>=4.5.0",
            "pytest-cov>=3.0.0",
            "factory-boy>=3.2.0",
            "freezer>=0.4.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "isort>=5.10.0",
        ],
        "media": [
            "ffmpeg-python>=0.2.0",
            "qrcode>=7.3.0",
        ],
    },
    include_package_data=True,
    package_data={
        "care_whatsapp_bot": [
            "migrations/*.py",
            "management/commands/*.py",
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
    entry_points={
        "console_scripts": [
            "care-whatsapp-setup=care_whatsapp_bot.management.commands.setup_whatsapp_webhook:Command",
        ],
    },
    keywords=[
        "care",
        "whatsapp",
        "bot",
        "healthcare",
        "django",
        "emr",
        "hospital",
        "patient",
        "messaging",
        "api",
    ],
    zip_safe=False,
)