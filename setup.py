#!/usr/bin/python
# _*_ coding:utf-8 _*_
from setuptools import setup
import os

this_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_directory, 'README_pypi.md'), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(this_directory,'version.py'), encoding="utf-8") as f:
    version = f.read()

version = version.split("=")[-1].split("print")[0].replace('"','').strip()

packages = ['pyettj']

package_data = \
{'': ['*'],
 'pyettj': ['exemplo/*', 'media/*']}

install_requires = \
['beautifulsoup4>=4.9.3,<5.0.0',
 'lxml>=4.6.3,<5.0.0',
 'matplotlib>=3.4.2,<4.0.0',
 'pandas>=1.2.4,<2.0.0',
 'requests>=2.25.1,<3.0.0']

setup_kwargs = {
    'name': 'pyettj',
    'version': version,
    'description': '"Capturar dados das estruturas a termo de algumas taxas de juros (ettj) brasileiras."',
    'long_description':long_description,
    'long_description_content_type':'text/markdown',
    'author': 'Rafael Rodrigues',
    'author_email': 'rafael.rafarod@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.8,<4.0',
}


setup(**setup_kwargs)