# _*_ coding:utf-8 _*_
import os

from setuptools import setup

this_directory = os.path.abspath(os.path.dirname(__file__))

PACKAGE = "pyettj"

with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(this_directory, "version.py"), encoding="utf-8") as f:
    version = f.read()

version = version.split("=")[-1].split("print")[0].replace('"', "").strip()

package_dir = {"": "src"}

packages = [PACKAGE]

package_data = {"": ["*"], PACKAGE: ["exemplo/*", "media/*"]}

install_requires = [
    "bs4>=0.0.2,<0.0.3",
    "lxml>=5.3.0,<6.0.0",
    "nelson-siegel-svensson>=0.5.0,<0.6.0",
    "requests>=2.32.3,<3.0.0",
]

extras_require = {
    ':python_version <= "3.9"': [
        "matplotlib<=3.7.1",
        "pandas<=1.5.3",
        "numpy<1.26.0",
        "bizdays<=1.0.13",
        "scipy>=1,7,<1.9.1",
    ],
    ':python_version >= "3.10"': [
        "matplotlib>=3.10.0",
        "pandas>=2.2.3",
        "numpy>=1.26.0",
        "bizdays>=1.0.16",
        "scipy>=1.13.1",
    ],
}

setup_kwargs = {
    "name": PACKAGE,
    "version": "0.3.4",
    "description": "Coletar e tratar dados de curvas de juros (ettj).",
    "long_description": long_description,
    "long_description_content_type": "text/markdown",
    "author_email": "rafael.rafarod@gmail.com",
    "maintainer": None,
    "maintainer_email": None,
    "url": f"https://github.com/rafa-rod/{PACKAGE}",
    "package_dir": package_dir,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "python_requires": ">=3.8.5,<4.0",
}


setup(**setup_kwargs)
