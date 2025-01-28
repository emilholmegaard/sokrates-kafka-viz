"""Setup file for kafka-viz package."""
from setuptools import setup, find_packages

setup(
    name="kafka-viz",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'typer',
        'rich',
    ],
    entry_points={
        'console_scripts': [
            'kafka-viz=kafka_viz.cli:app',
        ],
    },
)
