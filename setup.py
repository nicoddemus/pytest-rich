#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-rich",
    version="0.1.0",
    author="Bruno Oliveira",
    author_email="nicoddemus@gmail.com",
    maintainer="Bruno Oliveira",
    maintainer_email="nicoddemus@gmail.com",
    license="MIT",
    url="https://github.com/nicoddemus/pytest-rich",
    description="Leverage rich for richer test session output",
    long_description=read("README.rst"),
    py_modules=["pytest_rich"],
    python_requires=">=3.7",
    install_requires=["pytest>=7.0", "rich", "typing_extensions; python_version<'3.8'"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "pytest11": [
            "rich = pytest_rich",
        ],
    },
)
