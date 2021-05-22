<!-- buttons -->
<p align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-v3-brightgreen.svg"
            alt="python"></a> &nbsp;
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"
            alt="MIT license"></a> &nbsp;
    <a href='https://coveralls.io/github/rafa-rod/pyettj?branch=main'><img src='https://coveralls.io/repos/github/rafa-rod/pyettj/badge.svg?branch=main' alt='Coverage Status' /></a>
</p>

<!-- content -->

**pyettj** é uma biblioteca Python para capturar dados públicos das curvas de juros, curva a termo ou estrutura a termo da taxa de juros (ETTJ) da B3 (Brasil, Bolsa e Balcão).

Para caputar os dados, basta informar a data:

```python
from pyettj import ettj
data = '18/05/2021'
ettj_dataframe = ettj.get_ettj(data)
```

Todas as curvas disponíveis são disponibilizadas, para selecionar a desejada basta filtrar o `panda.DataFrame` resultante.

E para plotar o gráfico da curva, invoque a função de plotagem da biblioteca:

```python
curva = "DI x pré"
ettj.plot_ettj(ettj_dataframe, curva, data)
```

<center>
<img src="https://github.com/rafa-rod/pyettj/blob/main/media/pre.png" style="width:60%;"/>
</center>