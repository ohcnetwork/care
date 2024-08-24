from setuptools import find_packages, setup

setup(
    name="care",
    version="0.1",
    packages=find_packages(include=["care", "care.*"]),
    include_package_data=True,
    install_requires=[],
    author="Open Healthcare Network",
    author_email="info@ohc.network",
    description="A Django app for managing healthcare across hospitals and care centers.",
    license="MIT",
    keywords="django care ohc",
    url="https://github.com/ohcnetwork/care",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)
