#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
from setuptools import setup
import os

this_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_directory, 'README.md'), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(this_directory,'version.py'), encoding="utf-8") as f:
    version = f.read()

version = version.split("=")[-1].split("print")[0].replace('"','').strip()

package_dir = \
{'': 'src'}

packages = \
['pyettj']

package_data = \
{'': ['*'],
 'pyettj': ['exemplo/*', 'media/*']}

install_requires = \
['bizdays>=1.0.16,<2.0.0',
 'bs4>=0.0.2,<0.0.3',
 'lxml>=5.3.0,<6.0.0',
 'nelson-siegel-svensson>=0.5.0,<0.6.0',
 'pandas>=2.2.3,<3.0.0',
 'requests>=2.32.3,<3.0.0']

extras_require = \
{':python_version <= "3.9"': ['matplotlib<=3.7.1'],
 ':python_version >= "3.10"': ['matplotlib>=3.10.0']}

setup_kwargs = {
    'name': 'pyettj',
    'version': '0.3.2',
    'description': 'Coletar e tratar dados de curvas de juros (ettj).',
    'long_description': '<!-- buttons -->\n\n<p align="center">\n    <a href="https://www.python.org/">\n        <img src="https://img.shields.io/badge/python-v3-brightgreen.svg"\n            alt="python"></a> &nbsp;\n    <a href="https://opensource.org/licenses/MIT">\n        <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"\n            alt="MIT license"></a> &nbsp;\n    <a href="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml">\n        <img src="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml/badge.svg"\n            alt="CI/CD"></a> &nbsp;\n    <a href="https://codecov.io/gh/rafa-rod/pyettj">\n        <img src="https://codecov.io/gh/rafa-rod/pyettj/branch/main/graph/badge.svg?token=TRU9VIoqZB"/>\n    </a>\n    <a href="https://badge.fury.io/py/pyettj">\n        <img src="https://badge.fury.io/py/pyettj.svg" alt="PyPI version" height="18">\n    </a>\n    \n</p>\n\n<!-- content -->\n\n**pyettj** Ú uma biblioteca Python para capturar dados p·blicos das curvas de juros, curva a termo ou estrutura a termo da taxa de juros (ETTJ) da B3 (Brasil, Bolsa e BalcÒo).\n\n## InstalaþÒo\n\nBasta acionar o comando abaixo:\n\n```sh\npip install pyettj\n```\n\n## Exemplo de Uso\n\nPara caputar todos os dados disponÝveis, basta informar a data:\n\n```python\nimport pyettj.ettj as ettj\ndata = \'18/05/2021\'\nettj_dataframe = ettj.get_ettj(data)\n```\n\nCaso deseje apenas uma curva especÝfica, basta informß-la:\n\n```python\nimport pyettj.ettj as ettj\ndata = \'18/05/2021\'\nettj_dataframe = ettj.get_ettj(data, curva="PRE")\n```\n\nSe for necessßrio usar proxy, passe a informaþÒo Ó funþÒo:\n\nCaso deseje apenas uma curva especÝfica, basta informß-la:\n\n```python\nimport pyettj.ettj as ettj\nimport getpass\n\nUSER = getpass.getuser()\nPWD = getpass.getpass("Senha de rede: ")\nPROXY = "servidor"\nPORTA = 4300\n\nproxies = {"http":f\'http://{USER}:{PWD}@{PROXY}:{PORTA}\',\n           "https":f\'https://{USER}:{PWD}@{PROXY}{PORTA}\'}\n\nettj_dataframe = ettj.get_ettj(data, curva="PRE", proxies=proxies)\n```\n\nE para plotar o grßfico da curva, invoque a funþÒo de plotagem da biblioteca:\n\n```python\ncurva = "DI x prÚ 252"\nettj.plot_ettj(ettj_dataframe, curva, data)\n```\n\n<center>\n<img src="https://github.com/rafa-rod/pyettj/blob/main/media/pre.png" style="width:60%;"/>\n</center>\n\nPara coletar vßrias datas, chame a funþÒo `listar_dias_uteis` informando as datas iniciais e finais. Assim, ela retornarß somente os dias ·teis neste intervalo.\n\n```python\nimport pandas as pd\n\nde = \'13/05/2021\'\nate =\'18/05/2021\'\ndatas = ettj.listar_dias_uteis(de, ate)\n\ntodas_datas = pd.DataFrame()\nfor dat in datas:\n    ano, mes, dia = dat.split("-")\n    data = "/".join([dia, mes, ano])\n    dados = ettj.get_ettj(data)\n    todas_datas=pd.concat([dados, todas_datas])\n```\n\nA varißvel `todas_datas` possuirß todas as curvas em cada data do intervalo. Para identificar as datas, basta o comando:\n\n```python\ntodas_datas.Data.unique().tolist()\n```\n\nVocÛ pode obter dados os dados da ANBIMA - Estrutura a Termo das Taxas de Juros Estimada disponÝvel em: https://www.anbima.com.br/informacoes/est-termo/CZ.asp\n\n```python\nimport pyettj.modelo_ettj as modelo_ettj\n\nparametros_curva, ettj, taxa, erros = modelo_ettj.get_ettj_anbima("15/09/2022")\n```\n\nA partir dos parÔmetros estimados pela ANBIMA, vocÛ pode obter usar a equaþÒo de Svensson:\n\n```python\ncurva = parametros_curva.loc["PREFIXADOS", :].str.replace(",",".").astype(float)\n\nbeta1, beta2, beta3, beta4 = curva[:4]\nlambda1, lambda2 = curva[4:]\nt = 21/252 #em anos\n\ntaxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, t)\nprint(taxa)\n```\n\nPara coletar as taxas em diversas maturidades:\n\n```python\nmaturidades = [1,21,42,63,126,252,504,1008,1260,1890,2520]\ntaxas = []\n\nfor x in maturidades:\n    taxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, x/252)\n    taxas.append(taxa)\n\npd.DataFrame(np.array([taxas]), columns=[x/252 for x in maturidades]).T.multiply(100).plot()\n```\n\nCaso vocÛ nÒo possua os parÔmetros da curva Svensson, pode-se estimß-los conforme script a seguir:\n\n```python\ndata = \'20/03/2023\'\nettj_dataframe = ettj.get_ettj(data, curva="PRE")\n\nt = ettj_dataframe[ettj_dataframe.columns[0]].divide(252).values\ny = ettj_dataframe[ettj_dataframe.columns[1]].divide(100).values\n\nbeta1, beta2, beta3, beta4, lambda1, lambda2 = modelo_ettj.calibrar_curva_svensson(t, y)\n\nmaturidades = [1,21,42,63,126,252,504,1008,1260,1890,2520]\ntaxas = []\n\nfor x in maturidades:\n    taxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, x/252)\n    taxas.append(taxa)\n\nettj_pre = pd.DataFrame(np.array([taxas]), columns=[x/252 for x in maturidades]).T.multiply(100)\n\nplt.figure(figsize=(10,5))\nplt.plot(ettj_pre)\nplt.title("ETTJ PREFIXADA")\nplt.show()\n```\n\n<center>\n<img src="https://github.com/rafa-rod/pyettj/blob/main/media/pre_estimada.png" style="width:60%;"/>\n</center>\n',
    'author': 'Rafael Rodrigues',
    'author_email': 'rafael.rafarod@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'package_dir': package_dir,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'extras_require': extras_require,
    'python_requires': '>=3.9,<4.0',
}


setup(**setup_kwargs)