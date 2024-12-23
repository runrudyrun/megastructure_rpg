from setuptools import setup, find_packages

setup(
    name="megastructure_rpg",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.3",
        "pygame>=2.5.0",
        "pyyaml>=6.0.1",
        "sqlalchemy>=2.0.20",
        "attrs>=23.1.0",
        "pytest>=7.4.0",
    ],
    python_requires=">=3.10",
)
