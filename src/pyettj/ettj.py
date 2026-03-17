# -*- coding: utf-8 -*-
import getpass
import time
from io import BytesIO
from os.path import join as joinpath
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd  # type: ignore
import requests
from bs4 import BeautifulSoup  # type: ignore

plt.style.use("fivethirtyeight")  # type: ignore
import os  # noqa: E402
import warnings
from typing import Any, Dict, List, Union

import bizdays  # noqa: E402

from pyettj import gettables

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.5f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)


def _treat_parameters(data):
    """Checking all parameters and access to web data"""
    if not isinstance(data, str):
        raise ValueError(
            "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
        )
    elif isinstance(data, str):
        try:
            data = pd.to_datetime(data, dayfirst=True).strftime("%d/%m/%Y")
            return data
        except:
            raise ValueError(
                "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
            )


def feriados(override: bool = False, ligar_proxy: bool = True) -> None:
    """
    Função que faz o download dos feriados do site da Anbima e os compila em um formato a ser utilizado.
    Salva o arquivo na pasta de Downloads do usuário em formato CSV.

    Parâmetros:
        override (bool): Se True, força o download mesmo se o arquivo já existir
        ligar_proxy (bool): Se True, usa proxy para a conexão
    """

    # Define o caminho da pasta Downloads
    downloads_path = joinpath(str(Path.home()), "Downloads")
    arquivo_feriados = joinpath(downloads_path, "Feriados.csv")

    # Verifica se o arquivo já existe na pasta Downloads
    arquivo_existe = os.path.isfile(arquivo_feriados)

    # Se o arquivo existir e não for para sobrescrever, lê diretamente
    if arquivo_existe and not override:
        print(f"Arquivo encontrado em: {arquivo_feriados}")
        print("Carregando feriados do arquivo local...")
        feriados_df = pd.read_csv(arquivo_feriados)
    else:
        # Se não existir ou for para sobrescrever, faz o download
        print("Fazendo download dos feriados do site da ANBIMA...")

        # Configurar o proxy se necessário
        proxies = None
        if ligar_proxy:
            user = getpass.getuser().lower()
            pwd = getpass.getpass(prompt="Senha do proxy: ")
            proxy = "proxy.inf.bndes.net"
            porta = 8080
            proxies = {
                "http": f"http://{user}:{pwd}@{proxy}:{porta}",
                "https": f"http://{user}:{pwd}@{proxy}:{porta}",
            }
            print("Proxy configurado.")

        try:
            # Fazer a requisição (com ou sem proxy)
            response = requests.get(
                "https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls",
                proxies=proxies,
                verify=True,
                timeout=30,  # Timeout de 30 segundos
            )

            if response.status_code == 200:
                print("Download realizado com sucesso!")

                # Ler o arquivo Excel
                df = pd.read_excel(BytesIO(response.content), engine="calamine")

                # Processar os feriados
                fonte_index = df[df["Data"] == "Fonte: ANBIMA"].index

                if len(fonte_index) > 0:
                    # Pega as datas até a linha antes do footer
                    feriados_datas = df["Data"][: fonte_index[0]].values
                else:
                    # Se não encontrar o footer, pega todas as datas não nulas
                    feriados_datas = df["Data"].dropna().values

                # Criar DataFrame com os feriados
                feriados_df = pd.DataFrame(
                    {"Feriados ANBIMA": pd.to_datetime(feriados_datas).values}
                )

                feriados_df.to_csv(arquivo_feriados, index=False, header=False)
                print(f"Arquivo salvo em: {arquivo_feriados}")

            else:
                raise Exception(f"Erro ao acessar a URL: {response.status_code}")

        except Exception as e:
            print(f"Erro durante o download: {e}")

            # Se falhou o download mas existe arquivo antigo, tenta usar ele
            if arquivo_existe:
                print("Tentando usar arquivo existente...")
                feriados_df = pd.read_csv(arquivo_feriados)
            else:
                raise Exception(
                    "Não foi possível obter os feriados e não há arquivo local disponível."
                )


def listar_dias_uteis(
    de: str, ate: str, override: bool = False, ligar_proxy: bool = False
) -> List[str]:
    """Baseado em uma lista de calendários, a função filtra somente datas úteis do calendário brasileiro da ANBIMA.
    Parâmetros:
        de  (string) => data formato "%Y-%m-%d" ou "%d/%m/%Y"
        ate (string) => data formato "%Y-%m-%d" ou "%d/%m/%Y"
        override (bool) => True: sobrescreve arquivo existente em downloads
        ligar_proxy => True: download de feriados com proxy ligada
    Retorno:
        dias_uteis (lista): lista contendo dias úteis no intervalo apontado.
    """
    try:
        downloads_path = joinpath(str(Path.home()), "Downloads")
        path_feriados = joinpath(downloads_path, "Feriados.csv")
        feriados(override, ligar_proxy)
    except:
        path_feriados = os.path.realpath(__file__).split(".py")[0][:-4]

    holidays = bizdays.load_holidays(os.path.join(path_feriados, "Feriados.csv"))
    cal = bizdays.Calendar(holidays, ["Sunday", "Saturday"], name="Brazil")
    de = _treat_parameters(de)
    ate = _treat_parameters(ate)
    dataIni = pd.to_datetime(de, dayfirst=True).strftime("%Y-%m-%d")
    dataFim = pd.to_datetime(ate, dayfirst=True).strftime("%Y-%m-%d")
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
        url = "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?Data={}&Data1=20060201&slcTaxa={}".format(
            data, curva
        )
    else:
        url = f"https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp?Data={data}&Data1=20060201&slcTaxa={curva}"

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
