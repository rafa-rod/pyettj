#!/usr/bin/python
# _*_ coding:utf-8 _*_
from setuptools import setup

import subprocess
from os import path

this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, 'README.md'), encoding="utf-8") as f:
    long_description = f.read()

out = subprocess.Popen(['python', path.join(this_directory,'version.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
stdout, _ = out.communicate()
version = stdout.decode("utf-8").strip().split(" ")[-1]
print(version)

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