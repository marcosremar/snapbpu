"""Setup script for Dumont Cloud CLI"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "docs" / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="dumont-cli",
    version="1.0.0",
    author="Dumont Cloud Team",
    author_email="contact@dumontcloud.com",
    description="Command-line interface for Dumont Cloud GPU management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dumontcloud/cli",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "dumont=cli.__main__:main",
        ],
    },
    include_package_data=True,
)
