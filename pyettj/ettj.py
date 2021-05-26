# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup # type: ignore
import requests, time
import pandas as pd # type: ignore
import matplotlib.pyplot as plt; plt.style.use('fivethirtyeight') # type: ignore
from pyettj import gettables

pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_rows',100)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',1000)

def _treat_parameters(data):
    '''Checking all parameters and access to web data'''
    if isinstance(data, str)==False:
        raise ValueError("O parametro data deve ser em formato string, exemplo: '18/05/2021'")
    elif isinstance(data, str):
        try:
            data = pd.to_datetime(data).strftime("%d/%m/%Y")
            return data
        except:
            raise ValueError("O parametro data deve ser em formato string, exemplo: '18/05/2021'")   

def get_ettj(data):
    start = time.time()

    data = _treat_parameters(data)

    #data = pd.to_datetime(data).strftime("%d/%m/%Y")
    curva = "TODOS"
    url = "http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?Data={}&Data1=20060201&slcTaxa={}".format(data,curva)

    try:
        page = requests.get(url)
        pagetext = page.text
    except:
        raise Exception("Não foi possível conectar ao website. Tente novamente mais tarde.")

    soup = BeautifulSoup(pagetext, 'lxml')
    table1 = soup.find_all('table')[1]
    table2 = soup.find_all('table')[2]
    table3 = soup.find_all('table')[3]
    table4 = soup.find_all('table')[4]

    pandas_table1 = gettables.get_first_table(table1)
    pandas_table2 = gettables.get_second_table(table2)
    pandas_table3 = gettables.get_third_table(table3)
    pandas_table4 = gettables.get_fourth_table(table4)

    final_table_pandas = pd.concat([pandas_table1, pandas_table2, pandas_table3, pandas_table4], axis=1)
    final_table_pandas["Data"] = data
    final_table_pandas = final_table_pandas.loc[:,~final_table_pandas.columns.duplicated()]
    print("Curvas capturadas em {} segundos.".format(round(time.time()-start,2)))
    return final_table_pandas

def plot_ettj(ettj, curva, data): #pragma: no cover
    ettj_ = ettj.copy()
    data = pd.to_datetime(data).strftime("%d/%m/%Y")
    ettj_ = ettj_[ettj_.Data==data]
    ettj_.index = ettj_[ettj_.columns[0]]
    ettj_ = ettj_[[curva]]
    ettj_.plot()
    plt.title('Curva - '+curva)
    plt.xticks(rotation=45)
    plt.xlabel('Maturidade (dias)')
    plt.ylabel('Taxa (%)  ',rotation=0, labelpad=50)
    plt.tight_layout()
    plt.legend('')
    plt.show()