<!-- buttons -->

<p align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-v3-brightgreen.svg"
            alt="python"></a> &nbsp;
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"
            alt="MIT license"></a> &nbsp;
    <a href="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml">
        <img src="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml/badge.svg"
            alt="CI/CD"></a> &nbsp;
    <a href="https://codecov.io/gh/rafa-rod/pyettj">
        <img src="https://codecov.io/gh/rafa-rod/pyettj/branch/main/graph/badge.svg?token=TRU9VIoqZB"/>
    </a>
    <a href="https://badge.fury.io/py/pyettj">
        <img src="https://badge.fury.io/py/pyettj.svg" alt="PyPI version" height="18">
    </a>
    
</p>

<!-- content -->

**pyettj** é uma biblioteca Python para capturar dados públicos das curvas de juros, curva a termo ou estrutura a termo da taxa de juros (ETTJ) da B3 (Brasil, Bolsa e Balcão).

## Instalação

Basta acionar o comando abaixo:

```sh
pip install pyettj
```

## Exemplo de Uso

Para caputar os dados, basta informar a data:

```python
from pyettj import ettj
data = '18/05/2021'
ettj_dataframe = ettj.get_ettj(data)
```

Todas as curvas disponíveis são disponibilizadas, para selecionar a desejada basta filtrar o `pandas.DataFrame` resultante.

E para plotar o gráfico da curva, invoque a função de plotagem da biblioteca:

```python
curva = "DI x pré 252"
ettj.plot_ettj(ettj_dataframe, curva, data)
```

<center>
<img src="https://github.com/rafa-rod/pyettj/blob/main/media/pre.png" style="width:60%;"/>
</center>

Para coletar várias datas, chame a função `listar_dias_uteis` informando as datas iniciais e finais. Assim, ela retornará somente os dias úteis neste intervalo.

```python
import pandas as pd

de = '13/05/2021'
ate ='18/05/2021'
datas = ettj.listar_dias_uteis(de, ate)

todas_datas = pd.DataFrame()
for dat in datas:
    dados=ettj.get_ettj(dat)
    todas_datas=pd.concat([dados, todas_datas])
```

A variável `todas_datas` possuirá todas as curvas em cada data do intervalo. Para identificar as datas, basta o comando:

```python
todas_datas.Data.unique().tolist()
```