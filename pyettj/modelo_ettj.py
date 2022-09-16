import xml.etree.ElementTree as ET
import requests
import pandas as pd
import io
import numpy as np
from typing import Dict, Union

import warnings
warnings.filterwarnings("ignore")

def get_ettj_anbima(data: str, proxies: Union[Dict[str, str], None] = None) -> Union[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Captura dados ETTJ (PRE e IPCA) da ANBIMA.
        Parâmetros:
            data  (string) => data formato "%d/%m/%Y"
            proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
        Retorno:
            parametros_curva (dataframe): parâmetros para montagem da curva svensson.
            ettj (dataframe): vértices e taxas por tipo de curva.
            taxa (dataframe): ettj da taxa prefixada.
            erro (dataframe): erro de estimação por tipo de Título Público.
    """
    url = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
    payload = {"Idioma": "PT", "Dt_Ref": data, "saida": "xml"}
    headers = {"Content-type": "application/x-www-form-urlencoded", 
               "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"}
    if proxies:
        ettj_anbima = requests.post(url, proxies=proxies, verify=False,
                                              data=payload,
                                              headers=headers).text
    else:
        ettj_anbima = requests.post(url,
                                    data=payload,
                                   headers=headers).text
        
    ettj_anbima_str = io.StringIO(ettj_anbima)

    tree1 = ET.parse(ettj_anbima_str)
    root1 = tree1.getroot()

    parametros_curva = pd.DataFrame()
    ettj = pd.DataFrame()
    taxa = pd.DataFrame()
    erros = pd.DataFrame()
    for x in tree1.iter():
        dado = x.attrib
        if x.tag == 'PARAMETRO': #parametros da curva
            curva = pd.DataFrame.from_dict(dado, orient="index").T
            parametros_curva = pd.concat([parametros_curva, curva])
        if x.tag == 'VERTICES': #ETTJ
            curva = pd.DataFrame.from_dict(dado, orient="index").T
            ettj = pd.concat([ettj, curva])
        if x.tag == 'CIRCULAR': #taxa por vertice
            curva = pd.DataFrame.from_dict(dado, orient="index").T
            taxa = pd.concat([taxa, curva])
        if x.tag == 'ERRO': #taxa por vertice
            curva = pd.DataFrame.from_dict(dado, orient="index").T
            erros = pd.concat([erros, curva])
    ettj = ettj.rename(columns={"Inflacao":"Inflação Implícita"})
    taxa = taxa.rename(columns={"Taxa":"Taxa Prefixada"})
    return parametros_curva.set_index("Grupo"), ettj, taxa, erros


def svensson(beta1: float, beta2: float, beta3: float, beta4: float, lambda1: float, lambda2: float, t: float) -> float:
    """Captura dados ETTJ (PRE e IPCA) da ANBIMA segundo equação Svensson (1994). 
        Para equação de Nelson Siegel (1987), basta informar beta4 e lambda2 iguais a zero.
        Parâmetros:
            beta1, beta2, beta3, beta4, lambda1 e lambda2 (float) => parâmetros que definem nivel e curvatura;
            t (float) => maturidade/vértice em anos.
        Retorno:
            taxa (float): taxa de juros da curva.
    """    
    def exponencial(lambdas, t):
        return np.exp(1)**(-lambdas*t)
    
    return beta1 + beta2* ((1-exponencial(lambda1, t))/(lambda1*t)) + \
                    beta3* ((1-exponencial(lambda1, t))/(lambda1*t) - exponencial(lambda1, t)) + \
                       beta4* ((1-exponencial(lambda2, t))/(lambda2*t) - exponencial(lambda2, t))