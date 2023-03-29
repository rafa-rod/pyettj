# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup  # type: ignore
import requests, time
import pandas as pd  # type: ignore
import matplotlib.pyplot as plt

plt.style.use("fivethirtyeight")  # type: ignore
from pyettj import gettables
import bizdays, os
from typing import Any, List, Union, Dict

import warnings

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.5f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)


def _treat_parameters(data):
    """Checking all parameters and access to web data"""
    if isinstance(data, str) == False:
        raise ValueError(
            "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
        )
    elif isinstance(data, str):
        try:
            data = pd.to_datetime(data).strftime("%d/%m/%Y")
            return data
        except:
            raise ValueError(
                "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
            )


def listar_dias_uteis(de: str, ate: str) -> List[str]:
    """Baseado em uma lista de calendários, a função filtra somente datas úteis do calendário brasileiro
        Parâmetros:
            de  (string) => data formato "%Y-%m-%d" ou "%d/%m/%Y"
            ate (string) => data formato "%Y-%m-%d" ou "%d/%m/%Y"
        Retorno:
            dias_uteis (lista): lista contendo dias úteis no intervalo apontado.
    """
    path_feriados = os.path.realpath(__file__).split(".py")[0][:-4]
    de = _treat_parameters(de)
    ate = _treat_parameters(ate)
    holidays = bizdays.load_holidays(os.path.join(path_feriados, "Feriados.csv"))
    cal = bizdays.Calendar(holidays, ["Sunday", "Saturday"], name="Brazil")
    dataIni = pd.to_datetime(de).strftime("%Y-%m-%d")
    dataFim = pd.to_datetime(ate).strftime("%Y-%m-%d")
    dias_uteis = list(cal.seq(dataIni, dataFim))
    dias_uteis = [str(x).split(" ")[0] for x in dias_uteis]
    dias_uteis.sort()
    return dias_uteis


def get_ettj(
    data: str, curva: str = "TODOS", proxies: Union[Dict[str, str], None] = None
) -> pd.DataFrame:
    """Captura todas as curvas disponíveis pela B3 em data específica.
        Parâmetros:
            data  (string) => data formato "%Y-%m-%d" ou "%d/%m/%Y";
            curva (string) => opcional. caso selecionar curva específica, exemplo: PRE;
            proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
        Retorno:
            final_table_pandas (dataframe): dataframe contendo todas as curvas, maturidade e data solicitada.
    """
    start = time.time()

    curva = curva.upper()
    if curva == "TODOS":
        url = "http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?Data={}&Data1=20060201&slcTaxa={}".format(
            data, curva
        )
    else:
        url = f"http://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp?Data={data}&Data1=20060201&slcTaxa={curva}"

    session = requests.Session()
    session.trust_env = False
    if proxies:
        page = session.get(url, proxies=proxies, verify=False)
    else:
        page = session.get(url)

    if page.status_code == 404:
        raise Exception("Página não encontrada.")
    if page.status_code == 407:
        raise Exception("Necessária autenticação de proxy.")
    elif page.status_code == 502:
        raise Exception(
            "Não foi possível conectar ao website. Tente novamente mais tarde. Bad Gateway"
        )
    elif page.status_code == 200:
        pagetext = page.text
        if curva == "TODOS":
            soup = BeautifulSoup(pagetext, "lxml")
            try:
                table1 = soup.find_all("table")[1]
            except IndexError:
                raise ValueError(
                    "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
                )
            if "Não há dados para a data fornecida" in table1.text.strip():
                raise ValueError(
                    "Não há dados para a data fornecida. Dados a partir de 02/01/2004."
                )
            else:
                table2 = soup.find_all("table")[2]
                table3 = soup.find_all("table")[3]
                table4 = soup.find_all("table")[4]

                pandas_table1 = gettables.get_table(table1)
                pandas_table2 = gettables.get_table(table2)
                pandas_table3 = gettables.get_table(table3)
                pandas_table4 = gettables.get_table(table4)

                final_table_pandas = pd.concat(
                    [pandas_table1, pandas_table2, pandas_table3, pandas_table4], axis=1
                )
                final_table_pandas["Data"] = data
                final_table_pandas = final_table_pandas.loc[
                    :, ~final_table_pandas.columns.duplicated()
                ]
                final_table_pandas.columns = (
                    final_table_pandas.columns.str.split("(").str.get(0).str.strip()
                )
                print(
                    "Curvas capturadas em {} segundos.".format(
                        round(time.time() - start, 2)
                    )
                )
                return final_table_pandas
        else:
            final_table_pandas = pd.read_html(pagetext, flavor="bs4")[0]
            final_table_pandas.columns = final_table_pandas.columns.to_flat_index()
            final_table_pandas.columns = [
                final_table_pandas.columns[x][0]
                if x == 0
                else final_table_pandas.columns[x][0]
                + " "
                + final_table_pandas.columns[x][1]
                for x in range(len(final_table_pandas.columns))
            ]
            for cols in final_table_pandas.columns[1:]:
                final_table_pandas[cols] = final_table_pandas[cols] / 100
            print(
                "Curva capturada em {} segundos.".format(round(time.time() - start, 2))
            )
            return final_table_pandas


def plot_ettj(
    ettj: pd.DataFrame, curva: str, data: Union[str, None] = None, **opcionais: Any
) -> None:
    """Plota curva desejada.
        Parâmetros:
            ettj  (dataframe) => dados obtidos pela função get_ettj em data específica.
            curva (string)    => nome da curva.
            data  (string)    => data da curva
        Retorno:
            gráfico ettj (taxa x maturidade)
    """
    ettj_ = ettj.copy()
    if "Data" in ettj_.columns:
        ettj_ = ettj_[ettj_.Data == data]
    ettj_.index = ettj_[ettj_.columns[0]]
    ettj_ = ettj_[[curva]]

    plt.figure(figsize=(opcionais.get("figsize")))
    ettj_.plot(opcionais.get("lw"), opcionais.get("color"))
    plt.title("Curva - " + curva)
    plt.xticks(rotation=45)
    plt.xlabel("Maturidade (dias)")
    plt.ylabel("Taxa (%)  ", rotation=0, labelpad=50)
    plt.tight_layout()
    plt.legend("")
    plt.show()
