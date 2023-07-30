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

Para caputar todos os dados disponíveis, basta informar a data:

```python
import pyettj.ettj as ettj
data = '18/05/2021'
ettj_dataframe = ettj.get_ettj(data)
```

Caso deseje apenas uma curva específica, basta informá-la:

```python
import pyettj.ettj as ettj
data = '18/05/2021'
ettj_dataframe = ettj.get_ettj(data, curva="PRE")
```

Se for necessário usar proxy, passe a informação à função:

Caso deseje apenas uma curva específica, basta informá-la:

```python
import pyettj.ettj as ettj
import getpass

USER = getpass.getuser()
PWD = getpass.getpass("Senha de rede: ")
PROXY = "servidor"
PORTA = 4300

proxies = {"http":f'http://{USER}:{PWD}@{PROXY}:{PORTA}',
           "https":f'https://{USER}:{PWD}@{PROXY}{PORTA}'}

ettj_dataframe = ettj.get_ettj(data, curva="PRE", proxies=proxies)
```

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
    ano, mes, dia = dat.split("-")
    data = "/".join([dia, mes, ano])
    dados = ettj.get_ettj(data)
    todas_datas=pd.concat([dados, todas_datas])
```

A variável `todas_datas` possuirá todas as curvas em cada data do intervalo. Para identificar as datas, basta o comando:

```python
todas_datas.Data.unique().tolist()
```

Você pode obter dados os dados da ANBIMA - Estrutura a Termo das Taxas de Juros Estimada disponível em: https://www.anbima.com.br/informacoes/est-termo/CZ.asp

```python
import pyettj.modelo_ettj as modelo_ettj

parametros_curva, ettj, taxa, erros = modelo_ettj.get_ettj_anbima("15/09/2022")
```

A partir dos parâmetros estimados pela ANBIMA, você pode obter usar a equação de Svensson:

```python
curva = parametros_curva.loc["PREFIXADOS", :].str.replace(",",".").astype(float)

beta1, beta2, beta3, beta4 = curva[:4]
lambda1, lambda2 = curva[4:]
t = 21/252 #em anos

taxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, t)
print(taxa)
```

Para coletar as taxas em diversas maturidades:

```python
maturidades = [1,21,42,63,126,252,504,1008,1260,1890,2520]
taxas = []

for x in maturidades:
    taxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, x/252)
    taxas.append(taxa)

pd.DataFrame(np.array([taxas]), columns=[x/252 for x in maturidades]).T.multiply(100).plot()
```

Caso você não possua os parâmetros da curva Svensson, pode-se estimá-los conforme script a seguir:

```python
data = '20/03/2023'
ettj_dataframe = ettj.get_ettj(data, curva="PRE")

t = ettj_dataframe[ettj_dataframe.columns[0]].divide(252).values
y = ettj_dataframe[ettj_dataframe.columns[1]].divide(100).values

beta1, beta2, beta3, beta4, lambda1, lambda2 = modelo_ettj.calibrar_curva_svensson(t, y)

maturidades = [1,21,42,63,126,252,504,1008,1260,1890,2520]
taxas = []

for x in maturidades:
    taxa = modelo_ettj.svensson(beta1, beta2, beta3, beta4, lambda1, lambda2, x/252)
    taxas.append(taxa)

ettj_pre = pd.DataFrame(np.array([taxas]), columns=[x/252 for x in maturidades]).T.multiply(100)

plt.figure(figsize=(10,5))
plt.plot(ettj_pre)
plt.title("ETTJ PREFIXADA")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/pyettj/blob/main/media/pre_estimada.png" style="width:60%;"/>
</center>
