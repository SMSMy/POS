"""
ملف الإعداد لنظام نقاط البيع
Setup file for Restaurant POS System
"""

from setuptools import setup, find_packages
from pathlib import Path

# قراءة محتوى README
this_directory = Path(__file__).parent
long_description = ""
if (this_directory / "README.md").exists():
    long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# قراءة المتطلبات
requirements = []
if (this_directory / "requirements.txt").exists():
    requirements = (this_directory / "requirements.txt").read_text().splitlines()

setup(
    name="restaurant-pos",
    version="2.0.0",
    author="Restaurant POS Team",
    author_email="support@restaurant-pos.com",
    description="نظام نقاط بيع متكامل للمطاعم - Restaurant POS System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/restaurant-pos/pos-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "pos-system=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "*.sql",
            "*.ts",
            "*.qm",
            "*.md",
            "*.txt",
        ],
    },
    exclude_package_data={
        "": ["*.pyc", "__pycache__/*"],
    },
)