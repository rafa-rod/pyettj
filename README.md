<!-- buttons -->

<p align="center">
    <a href="https://www.linkedin.com/in/rafaelrod/">
        <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white"
            alt="LinkedIn"></a> &nbsp;
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-v3-brightgreen.svg"
            alt="python"></a> &nbsp;
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"
            alt="MIT license"></a> &nbsp;
    <a href="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml">
        <img src="https://github.com/rafa-rod/pyettj/actions/workflows/pipeline.yml/badge.svg"
            alt="CI/CD"></a> &nbsp;
    <a href="https://pepy.tech/projects/pyettj">
        <img src="https://static.pepy.tech/badge/pyettj" alt="PyPI Downloads">
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

Ou:

```sh
python -m pip install git+https://github.com/rafa-rod/pyettj.git
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
import matplotlib.pyplot as plt

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

# Geração de Cenários de Estresse para Curva de Juros usando Heath-Jarrow-Morton (HJM)

Baseado no artigo de:
Dario, A.D.G. and Fernández, M., 2011. Geraçao de Cenarios de Estresse para Curva de Juros. Brazilian Review of Finance, 9(3), pp.413-436.

O modelo HJM facilita a incorporação de opinião de especialistas na construção de cenários de estresse das curvas de juros. Além disso, segundo o estudo, o modelo HJM se mostra superior ao modelo de Nelson-Siegel-Svensson (NSS).

Ele modela a estrutura de volatilidade do processo das taxas e pode ser descrito usando apenas 3 componentes (3 fatores) que explicam mais de 95% da variação das taxas de juros: 1- nível, 2- inclinação e 3- curvatura.

Uma vez determinadas as funções de volatilidades $\sigma_j$ e os valores para cada
fator $\xi_j$, $j = 1, 2, 3$, a curva de estresse para um _holding period_ de $HP$ dias úteis
pode ser construída como segue para cada maturidade $T_i$:

$$
r_{0+HP}(T_i) = r_0(T_i) + \frac{HP}{252} \mu(T_i) + \sqrt{\frac{HP}{252}} \sum_{j=1}^{3} \sigma_j(T_i)\xi_j
$$

onde:

- $HP$ é o _holding period_ em dias úteis
- $\mu(T_i)$ é o _drift_ oriundo da equação diferencial estocástica multivariada
- $\sigma_j(T_i)$ são as volatilidades dos fatores
- $\xi_j$ são os choques dos fatores

O uso de três fatores é suficiente para descrever mais de 95% da variação da taxa de juros, segundo o referido estudo. Em termos de PCA (análise de componentes principais), são usados os três maiores autovalores, identificados como a representação dos movimentos de deslocamento paralelo, inclinação e curvatura.

Contudo, conforme minhas experiências, o uso de 3 fatores depende dos dados de calibração e forma de otimização. Aqui o algoritmo já possui ajustes de otimização para facilitar encontrar resposta ótima mais adequada, mas qualquer método que use PCA (análise de componentes principais) depende fortemente da qualidade dos dados (_missing values_ e _outliers_ influenciam muito).

Mais detalhes podem ser vistos no referido artigo, vamos para um exemplo de implementação.
O dataframe `dados_historicos_taxas` contem dados históricos obtidos usando `ettj.get_ettj(data)`

```python
import pyettj.HJM as HJM
import pyettj.ettj as ettj
import pandas as pd
import numpy as np

import seaborn as sns; sns.set_style("white")
import matplotlib.pyplot as plt

#1. Coleta dos Dados:
de = '13/05/2019'
ate ='18/02/2026'
datas = ettj.listar_dias_uteis(de, ate)

def obter_dados_e_preparar_dataframe(datas, curva = 'DI x pré 252', vertices = None) -> pd.DataFrame:
    dados_historicos_taxas = pd.DataFrame()
    for dat in tqdm(datas):
        ano, mes, dia = dat.split("-")
        data = "/".join([dia, mes, ano])
        dados = ettj.get_ettj(data)
        dados_historicos_taxas = pd.concat([dados, dados_historicos_taxas])
    taxa_pre = dados_historicos_taxas[['Data', 'Dias Corridos', curva]].set_index('Data')
    taxa_pre.columns = ["Dias", curva]
    taxa_pre['colunas'] = taxa_pre["Dias"]

    taxa_pre = taxa_pre.pivot_table(values=curva, columns="colunas", index=taxa_pre.index)
    colunas_ordenadas = sorted(taxa_pre.columns)
    taxa_pre = taxa_pre[colunas_ordenadas]

    if vertices:
        taxa_pre = taxa_pre[[col for col in taxa_pre.columns if col in vertices]]
        return taxa_pre
    else:
        return taxa_pre.dropna(axis=1)

taxa_pre = obter_dados_e_preparar_dataframe(datas, curva = 'DI x pré 252')
```

O exemplo de saida para esse dataframe é:

```
| Data       |      210 |      420 |      630 |      840 |      1050 |      2520 |
|------------|----------|----------|----------|----------|-----------|-----------|
| 13/05/2019 |     6.41 |     6.56 |     6.99 |     7.38 |      7.73 |      8.81 |
| 14/05/2019 |     6.4  |     6.51 |     6.92 |     7.32 |      7.63 |      8.77 |
| 15/05/2019 |     6.4  |     6.52 |     6.92 |     7.32 |      7.65 |      8.82 |
| 16/05/2019 |     6.43 |     6.59 |     7.01 |     7.43 |      7.75 |      8.93 |
| 17/05/2019 |     6.46 |     6.7  |     7.14 |     7.57 |      7.9  |      9.13 |
```

No índice estão as datas de coleta das taxas da curva e o nome das colunas são renomeadas seguida dos seus respectivos vértices, em dias. Importante ressaltar que haverá bastante dados faltantes (_missing values_), cabe ao usuário selecionar as melhores colunas e interpolar, se for preciso.

```python
#2 - Analisar os dados:
# Recomendo fortemente verificar dados faltantes e valores *estranhos*
# Use ferramentas gráficas para ajudar como:
HP = 10
choques_historicos_pre = taxa_pre.diff(HP).dropna()

sns.distplot(choques_historicos_pre["210"])

sns.boxplot(data=choques_historicos_pre["210"])

#Veja também os choques históricos. Isso ajuda para construir cenários e saber o nível dos choques:

pontos_base_estresses_historicos_pre = pd.concat([
                                        choques_historicos_pre.quantile(0.99, interpolation="nearest"),
                                        choques_historicos_pre.quantile(1-0.99, interpolation="nearest")],
                                                 axis=1)*10_000 #em bps
pontos_base_estresses_historicos_pre.columns = ["Choques Positivos", "Choques Negativos"]
pontos_base_estresses_historicos_pre


#3. Modelo HJM:
modelo = HJM.ModeloHJM(convencao_dias=252, verbose=1)

#sempre usar dias uteis conforme dados oriundos do pyettj acima
vertices_calibracao = [420, 840, 1050, 2520]

modelo.calibrar(taxa_pre, vertices_calibracao)
if modelo.calibrado:
    print(f"✅ Calibração concluída! {modelo}")

data_choque = "2026-01-02"

resultado_pos = modelo.aplicar_choques(
    data_choque=data_choque,
    vertices_choques_dias=[21, 504, 252*10],
    choques_observados = np.array([-100, 0, 255])/10_000, #choque dos especialistas em bps
    hp_dias=10,
    retornar_detalhes=True
)

resultado_neg = modelo.aplicar_choques(
    data_choque=data_choque,
    vertices_choques_dias=[21, 504, 252*10],
    choques_observados = np.array([100, 0, -200])/10_000, #choque dos especialistas em bps
    hp_dias=10,
    retornar_detalhes=True
)

#caso precise salvar o modelo:
caminho_modelo = "modelo_hjm_calibrado.json"
modelo.salvar(caminho_modelo)

#carregar o modelo que foi salvo:
modelo_carregado = ModeloHJM.carregar(caminho_modelo, verbose=1)
```

Para visualizar os choques, use:

```python
resultado = resultado_neg['curva'][resultado_neg['curva'].columns[1:]]
resultado.columns = ["Curva Original", "Curva Choque Negativo"]
resultado = pd.concat([resultado, resultado_pos['curva'][resultado_pos['curva'].columns[2:]] ], axis=1).multiply(100)
resultado.columns = ["Curva Original", "Curva Choque Positivo", "Curva Choque Negativo"]

plt.figure(figsize=(10,6))
plt.plot(resultado[["Curva Original"]], 'k--')
plt.plot(resultado[["Curva Choque Positivo"]], 'b')
plt.plot(resultado[["Curva Choque Negativo"]], 'r')
plt.xlabel('Vertice em anos')
plt.ylabel('% aa\n', loc="top", rotation=0, labelpad=-20)
locs, vals = plt.yticks()
plt.yticks(locs, np.round(locs,1))
plt.suptitle(f'Choques Paralelos na Curva Prefixada em {data_choque}')
plt.legend(resultado.columns)
plt.box(False)
plt.grid(axis="y")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/pyettj/blob/main/media/curva_estressada_hjm.png" style="width:60%;"/>
</center>

Para visualizar os parâmetros e demais resultados:

```python
print("=== Análise de Componentes Principais ===")
print(modelo.pca)

print("=== Parâmetros Estimados ===")
print(modelo.parametros)

print("=== Resumo do Modelo ===")
resumo = modelo.resumo()
print(resumo)

print(f"Número de componentes: {modelo.num_componentes}")

# Vértices usados na calibração (em dias)
print(f"Vértices: {modelo.vertices_dias}")
```
