#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="directo",
    version="0.0.1",
    description="School Student-Parent Directory",
    author="Travis Mattera",
    author_email="travis@mattera.io",
    packages=find_packages(include=["directo", "directo.*"]),
    install_requires=[
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "jinja2",
    ],
    entry_points={"console_scripts": ["directo=directo.main:main"]},
)
