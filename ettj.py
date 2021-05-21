# -*- coding: utf-8 -*-
"""
Created on Fri May 21 09:30:26 2021

@author: RRAFA
"""
from bs4 import BeautifulSoup
import requests, time
import pandas as pd
import matplotlib.pyplot as plt; plt.style.use('fivethirtyeight')
import get_all_tables

pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_rows',100)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',1000)

def get_ettj(data):
    data = pd.to_datetime(data).strftime("%d/%m/%Y")
    curva = "TODOS"
    url = "http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/TxRef1.asp?Data={}&Data1=20060201&slcTaxa={}".format(data,curva)

    page = requests.get(url)
    pagetext = page.text

    soup = BeautifulSoup(pagetext, 'lxml')
    table1 = soup.find_all('table')[1]
    table2 = soup.find_all('table')[2]
    table3 = soup.find_all('table')[3]
    table4 = soup.find_all('table')[4]

    pandas_table1 = get_all_tables.get_first_table(table1)
    pandas_table2 = get_all_tables.get_second_table(table2)
    pandas_table3 = get_all_tables.get_third_table(table3)
    pandas_table4 = get_all_tables.get_fourth_table(table4)

    final_table_pandas = pd.concat([pandas_table1, pandas_table2, pandas_table3, pandas_table4], axis=1)
    final_table_pandas["Data"] = data

    return final_table_pandas

start = time.time()
data = "2021/05/18"
ettj = get_ettj(data)#.to_excel("ettj.xlsx")
print("Curvas capturadas em {} segundos.".format(round(time.time()-start,2)))

def plot_ettj(ettj, curva, data):
    ettj_ = ettj.copy()
    data = pd.to_datetime(data).strftime("%d/%m/%Y")
    ettj_ = ettj_[ettj_.Data==data]
    ettj_.index = ettj_[ettj.columns[0]]
    ettj_ = ettj_[[curva]]
    ettj_.plot()
    plt.title('Curva - '+curva)
    plt.xticks(rotation=45)
    plt.xlabel('Maturidade (dias)')
    plt.ylabel('Taxa (%)  ',rotation=0, labelpad=50)
    plt.tight_layout()
    plt.legend('')
    plt.show()

import pandas as pd
#ettj = pd.read_excel("C:\\Users\\rrafa\\Desktop\\pyettj\\exemplo\\ettj.xlsx", index_col=0)
curvas = ettj.columns.tolist()[1:]
curva = curvas[2]
data = "2021/05/18"

plot_ettj(ettj.drop(ettj.columns[0],axis=1), curva, data)