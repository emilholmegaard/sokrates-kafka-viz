from setuptools import setup, find_packages

setup(
    name="sokrates-kafka-viz",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "mypy>=1.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "flake8>=6.0.0",
        ]
    },
)