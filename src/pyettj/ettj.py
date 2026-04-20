"""
ettj.py
=======
Captura das curvas ETTJ (Estrutura a Termo da Taxa de Juros) da B3
via arquivo TaxaSwap — endpoint vigente a partir de dez/2025.

Fonte : Pesquisa por Pregão → Mercado de Derivativos → Taxas de Mercado para Swaps
URL   : https://www.b3.com.br/pesquisapregao/download?filelist=TS{YYMMDD}.ex_,

Layout do arquivo TaxaSwap (posições 0-based, conforme manual B3):
  [00:06]  seq. transação
  [11:19]  data (AAAAMMDD)
  [21:26]  código da taxa      ex: 'PRE  ', 'DIC  ', 'DCL  '
  [26:41]  descrição da taxa
  [41:46]  dias corridos
  [46:51]  dias úteis
  [51]     sinal da taxa (+ ou -)
  [52:66]  taxa teórica (14 dígitos, 7 decimais → ÷ 1e9 = decimal)
  [66]     característica do vértice (F=fixo / M=móvel)
  [67:72]  código do vértice

Uso básico:
    import pyettj.ettj as ettj

    df = ettj.get_ettj("09/04/2026")
    df = ettj.get_ettj("09/04/2026", curva="DIC", proxies=proxies)
    df = ettj.get_ettj("09/04/2026", curva=["PRE", "DIC"])
    df = ettj.get_ettj_historico("01/01/2026", "09/04/2026", curva="PRE")
    ettj.listar_curvas()
    ettj.listar_dias_uteis("01/01/2026", "09/04/2026")
"""

from __future__ import annotations

import io
import time
import warnings
import zipfile
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pyettj.exceptions import (
    CurvaInvalidaError,
    DataFormatoError,
    HolidayError,
    NoDataError,
    ParsingError,
    ProxyAuthError,
    PyETTJError,
    ServerUnavailableError,
    TimeoutError,
)
from pyettj.cache import (
    _cache_valido,
    _cache_ler,
    _cache_salvar,
    cache_info,
    cache_clear,
)

# ---------------------------------------------------------------------------
# Catálogo de curvas disponíveis (extraído do TaxaSwap de 09/04/2026)
# ---------------------------------------------------------------------------
CURVAS_DISPONIVEIS: Dict[str, str] = {
    "ACC": "DIxDOL Aj. Cupom",
    "APR": "DIxPRE Aj. PRE",
    "ARB": "REAIS X ARS",
    "ARS": "ARS X DOL",
    "AUD": "DOL X AUD",
    "BIT": "Futuro de Bitcoin",
    "BRP": "IBRX50 X PRE",
    "CAD": "CAD X DOL",
    "CHF": "CHF X DOL",
    "CLP": "CLP X DOL",
    "CNH": "CNH X DOL",
    "CNL": "Curva Futuro CNH",
    "CNY": "CNY X DOL",
    "CYI": "CONV. YIELD",
    "CYM": "Convenience Yield M",
    "CYS": "Convenience Yield S",
    "CYX": "Convenience Yield X",
    "DCL": "CUPOM LIMPO - Dólar",
    "DCO": "SELIC X DOL",
    "DCP": "CUPOM LIMPO",
    "DEU": "DOL X EUR",
    "DGL": "Cupom Limpo de Ouro",
    "DIC": "DI X IPCA",
    "DIM": "DIxIGPM",
    "DOC": "DIxXDOL Cupom limpo",
    "DOL": "DIxDOL",
    "DP":  "DOLxPRE",
    "DPL": "Cupom Limpo de Petro",
    "DYE": "DOL X YEN",
    "EBR": "Futuro de Ethereum",
    "ECC": "CUPOM SUJO DE EURO",
    "EST": "Curva Futuro Taxa",
    "ETR": "Futuro de Ethereum",
    "EUC": "CUPOM EURO",
    "EUR": "R$ x EURO",
    "FTS": "FTSE/JSE TOP 40",
    "GBP": "DOL X GBP",
    "GLD": "Curva Futuro Ouro",
    "HAN": "HANG SENG INDEX",
    "IAS": "IPCA SINTÉTICO",
    "INP": "IBOVESPA",
    "IPS": "IGPxPRE SINTET.",
    "ITC": "ITC X SELIC",
    "JPY": "REAIS X IENE",
    "LEU": "Juros em EUR",
    "LIB": "Juros em USD",
    "LJP": "Juros em JPY",
    "MBR": "Curva de Índice BR",
    "MXN": "MXN X DOL",
    "NOK": "NOK X DOL",
    "NZD": "NZD X DOL",
    "PRE": "DIxPRE",
    "PTX": "PTAX",
    "RDA": "REAIS X DOLAR A",
    "RDC": "REAIS X DOLAR C",
    "RFS": "REAIS X FRANCO",
    "RLI": "REAIS X LIBRA",
    "RPL": "REAIS X PESO CHL",
    "RPM": "REAIS X PESO MEX",
    "RRA": "REAIS X RANDE SUL",
    "RUB": "RUB X DOL",
    "RYN": "REAIS X IUAN",
    "RYR": "REAIS X LIRA TUR",
    "RZE": "REAIS X DOLAR NZL",
    "SAB": "BOI GORDO",
    "SAC": "C.ARÁBICA (US$)",
    "SAM": "MILHO",
    "SAU": "SPREAD DOL AUST",
    "SBP": "S.BASKET X PRÉ",
    "SBR": "Futuro de Solana",
    "SCA": "SPREAD DOL CANADENSE",
    "SCF": "SPREAD FRANCO SUÍÇO",
    "SCL": "SPREAD PESO CHILENO",
    "SCN": "SPREAD IUAN X DOL",
    "SDE": "DOLx EURO",
    "SEK": "SEK X DOL",
    "SFR": "Curva Futuro Taxa FR",
    "SGP": "SPREAD LIBRA X DOL",
    "SJC": "Curva de Soja CBOT",
    "SLP": "SELICxPRE",
    "SLT": "SPREAD LTN",
    "SML": "Curva Small Cap",
    "SMX": "SPREAD PESO MEX",
    "SNZ": "SPREAD DOLAR NZL",
    "SOL": "Futuro de Solana",
    "SOY": "Curva de Soja Futura",
    "STR": "SPREAD LIRA TURCA",
    "SYD": "SPREAD IEN X DOL",
    "SZA": "SPREAD RANDE SUL AFR",
    "TFP": "TBFxPRE",
    "TIC": "NTN-B",
    "TIE": "Curva Futuro Taxa IE",
    "TIM": "NTN-C",
    "TJP": "TJLPxPRE",
    "TLF": "LFT",
    "TP":  "TRxPRE",
    "TPR": "LTN",
    "TR":  "DIxTR",
    "TRY": "TRY X DOL",
    "VIX": "Curva Futuro VIX",
    "XFI": "IFIX",
    "YCC": "Cupom sujo de yen",
    "YCL": "IENE - Cupom Limpo",
    "YCS": "IEN X CUPOM",
    "ZAR": "ZAR X DOL",
    "ZEU": "Curva Zero Juro EUR",
    "ZMX": "Curva Zero Juro MXN",
    "ZUS": "Curva Zero Juro USD",
}

CURVA_PADRAO = "PRE"

_HEADERS_DEFAULT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": (
        "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/"
        "market-data/historico/boletins-diarios/pesquisa-por-pregao/"
        "pesquisa-por-pregao/"
    ),
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _parse_data(data: str) -> date:
    """Converte string de data para objeto date. Aceita dd/mm/yyyy ou yyyy-mm-dd."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(data.strip(), fmt).date()
        except ValueError:
            continue
    raise DataFormatoError(data)


def _is_fim_de_semana(d: date) -> bool:
    return d.weekday() >= 5


def _proximo_dia_util(d: date) -> date:
    """Retorna o próximo dia útil (apenas considera fins de semana)."""
    prox = d + timedelta(days=1)
    while _is_fim_de_semana(prox):
        prox += timedelta(days=1)
    return prox


def _montar_url(d: date) -> str:
    yymmdd = d.strftime("%y%m%d")
    return f"https://www.b3.com.br/pesquisapregao/download?filelist=TS{yymmdd}.ex_,"


def _filtrar_curvas(df: pd.DataFrame, curvas: List[str]) -> pd.DataFrame:
    """Filtra o DataFrame completo pelas curvas solicitadas."""
    return df[df["curva"].isin(curvas)].reset_index(drop=True)


def _baixar_raw(
    d: date,
    proxies: Optional[Dict] = None,
    timeout: int = 120,
    retry: int = 3,
) -> bytes:
    """Baixa o arquivo TaxaSwap.ex_ para a data d. Retorna bytes brutos."""
    url = _montar_url(d)
    ultimo_erro: Exception = PyETTJError("Erro desconhecido")

    for tentativa in range(1, retry + 1):
        try:
            r = requests.get(
                url,
                headers=_HEADERS_DEFAULT,
                proxies=proxies,
                verify=False,
                timeout=timeout,
            )
        except requests.exceptions.ProxyError as e:
            raise ProxyAuthError(
                "Falha no proxy. Verifique as configurações de proxy."
            ) from e
        except requests.exceptions.Timeout as e:
            ultimo_erro = TimeoutError(
                f"Timeout após {timeout}s ao acessar {url}"
            )
            if tentativa < retry:
                time.sleep(2 ** tentativa)
            continue
        except requests.exceptions.ConnectionError as e:
            raise PyETTJError(f"Erro de conexão: {e}") from e

        if r.status_code == 407:
            raise ProxyAuthError("Proxy requer autenticação (407).")
        if r.status_code in (502, 503, 504):
            ultimo_erro = ServerUnavailableError(
                f"Servidor B3 indisponível (HTTP {r.status_code})."
            )
            if tentativa < retry:
                time.sleep(2 ** tentativa)
            continue
        if r.status_code != 200:
            raise PyETTJError(f"HTTP {r.status_code} ao acessar {url}")

        if len(r.content) == 0:
            raise NoDataError(
                d.strftime("%d/%m/%Y"),
                "servidor retornou resposta vazia",
            )
        # ZIP vazio = 22 bytes (end-of-central-directory sem entradas) = sem dados
        if len(r.content) <= 22:
            raise NoDataError(
                d.strftime("%d/%m/%Y"),
                "arquivo vazio — possível feriado não identificado",
            )

        return r.content

    raise ultimo_erro


def _extrair_txt(raw: bytes, data_str: str) -> str:
    """Descomprime ZIP externo → self-extracting EXE → ZIP interno → TaxaSwap.txt."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z_outer:
            nomes = z_outer.namelist()
            if not nomes:
                raise ParsingError("ZIP externo vazio.", data=data_str)
            inner_bytes = z_outer.read(nomes[0])
    except zipfile.BadZipFile as e:
        raise ParsingError(
            f"Arquivo baixado não é um ZIP válido: {e}", data=data_str
        ) from e

    pk_offset = inner_bytes.find(b"PK\x03\x04")
    if pk_offset < 0:
        raise ParsingError(
            "Não foi possível localizar o ZIP interno no .ex_. "
            "O formato do arquivo pode ter mudado.",
            data=data_str,
        )

    try:
        with zipfile.ZipFile(io.BytesIO(inner_bytes[pk_offset:])) as z_inner:
            nomes_inner = z_inner.namelist()
            if not nomes_inner:
                raise ParsingError("ZIP interno vazio.", data=data_str)
            conteudo = z_inner.read(nomes_inner[0])
    except zipfile.BadZipFile as e:
        raise ParsingError(f"ZIP interno corrompido: {e}", data=data_str) from e

    try:
        return conteudo.decode("latin-1")
    except UnicodeDecodeError as e:
        raise ParsingError(
            f"Erro ao decodificar TaxaSwap.txt como latin-1: {e}", data=data_str
        ) from e


def _parsear_txt(
    txt: str,
    curvas_filtro: List[str],
    data_ref: date,
) -> pd.DataFrame:
    """
    Parseia o TaxaSwap.txt conforme layout oficial B3 (manual TaxaSwap.xls).

    Layout (0-based):
      [21:26] código da taxa  [41:46] dias corridos  [46:51] dias úteis
      [51]    sinal           [52:66] taxa (÷1e9 = decimal)  [66] vértice F/M
    """
    registros = []
    erros = 0

    for linha in txt.splitlines():
        linha = linha.rstrip("\r\n")
        if len(linha) < 67:
            continue

        cod = linha[21:26].rstrip()
        if curvas_filtro and cod not in curvas_filtro:
            continue

        try:
            dc      = int(linha[41:46])
            du      = int(linha[46:51])
            sinal   = 1 if linha[51] == "+" else -1
            taxa    = sinal * int(linha[52:66]) / 1e9
            vertice = linha[66]
            desc    = linha[26:41].rstrip()
        except (ValueError, IndexError):
            erros += 1
            continue

        registros.append({
            "refdate":       data_ref,
            "curva":         cod,
            "descricao":     desc,
            "dias_corridos": dc,
            "dias_uteis":    du,
            "taxa":          taxa,
            "vertice":       vertice,
        })

    if erros > 0:
        warnings.warn(
            f"[pyettj] {erros} linha(s) ignorada(s) por erro de parse "
            f"em {data_ref.strftime('%d/%m/%Y')}.",
            stacklevel=4,
        )

    if not registros:
        return pd.DataFrame(
            columns=[
                "refdate", "curva", "descricao",
                "dias_corridos", "dias_uteis", "taxa", "vertice",
            ]
        )

    df = pd.DataFrame(registros)
    df["refdate"] = pd.to_datetime(df["refdate"])
    return df.sort_values(["curva", "dias_corridos"]).reset_index(drop=True)


def _validar_output(
    df: pd.DataFrame,
    curvas: List[str],
    data_str: str,
) -> None:
    """Valida o DataFrame retornado. Lança exceção ou emite warning em anomalias."""
    if df.empty:
        raise NoDataError(
            data_str,
            "nenhum registro encontrado — verifique se as curvas "
            "solicitadas existem nesta data.",
        )

    ausentes = [c for c in curvas if c not in set(df["curva"].unique())]
    if ausentes:
        warnings.warn(
            f"[pyettj] Curva(s) não encontrada(s) nos dados: {ausentes}. "
            "Pode não estar disponível nesta data.",
            stacklevel=3,
        )

    for curva, grupo in df.groupby("curva"):
        if len(grupo) < 5:
            warnings.warn(
                f"[pyettj] Curva '{curva}' retornou apenas {len(grupo)} "
                "vértice(s) — dado pode estar incompleto.",
                stacklevel=3,
            )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def listar_curvas(verbose: bool = True) -> pd.DataFrame:
    """
    Lista todas as curvas disponíveis no arquivo TaxaSwap da B3.

    Parâmetros
    ----------
    verbose : bool
        Se True (padrão), imprime a tabela no console.

    Retorno
    -------
    pd.DataFrame com colunas ['codigo', 'descricao'].

    Exemplos
    --------
    >>> curvas = listar_curvas()
    >>> curvas = listar_curvas(verbose=False)  # só o DataFrame, sem imprimir
    """
    df = pd.DataFrame(
        [{"codigo": k, "descricao": v}
         for k, v in sorted(CURVAS_DISPONIVEIS.items())]
    )
    if verbose:
        print(f"\n{'Código':<8}  Descrição")
        print("-" * 40)
        for _, row in df.iterrows():
            print(f"{row['codigo']:<8}  {row['descricao']}")
        print(f"\nTotal: {len(df)} curvas disponíveis.")
    return df


def listar_dias_uteis(de: str, ate: str) -> List[str]:
    """
    Retorna lista de dias úteis entre duas datas (apenas fins de semana excluídos).

    Parâmetros
    ----------
    de : str
        Data inicial no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
    ate : str
        Data final no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.

    Retorno
    -------
    list[str] com datas no formato 'dd/mm/yyyy', ordenadas crescentemente.

    Nota
    ----
    Feriados nacionais não são excluídos automaticamente — dias com
    ausência de dados serão identificados pelo get_ettj_historico,
    que os pula silenciosamente.

    Exemplos
    --------
    >>> dias = listar_dias_uteis("01/04/2026", "09/04/2026")
    >>> for d in dias:
    ...     df = get_ettj(d, proxies=proxies)
    """
    d_ini = _parse_data(de)
    d_fim = _parse_data(ate)

    if d_ini > d_fim:
        raise PyETTJError(
            f"Data inicial ({de}) é posterior à data final ({ate})."
        )

    dias = []
    d_atual = d_ini
    while d_atual <= d_fim:
        if not _is_fim_de_semana(d_atual):
            dias.append(d_atual.strftime("%d/%m/%Y"))
        d_atual += timedelta(days=1)

    return dias


def get_ettj(
    data: str,
    curva: Union[str, List[str]] = CURVA_PADRAO,
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 120,
    retry: int = 3,
    cache: bool = True,
) -> pd.DataFrame:
    """
    Captura as curvas ETTJ da B3 para uma data específica.

    Parâmetros
    ----------
    data : str
        Data no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
    curva : str ou list[str]
        Código(s) da(s) curva(s) desejada(s). Padrão: 'PRE'.
        Use 'TODOS' para todas as curvas disponíveis.
        Use listar_curvas() para ver as opções.
    proxies : dict, opcional
        Dicionário de proxies. Exemplo:
        proxies = {"http":  "http://user:pwd@proxy:porta",
                   "https": "http://user:pwd@proxy:porta"}
    timeout : int
        Timeout da requisição em segundos. Padrão: 120.
    retry : int
        Tentativas em caso de erro transitório. Padrão: 3.
    cache : bool
        Se True (padrão), usa cache local para evitar downloads repetidos.
        O cache salva todas as curvas do dia — independente da curva pedida.

    Retorno
    -------
    pd.DataFrame com colunas:
        refdate       : data de referência (datetime)
        curva         : código da curva, ex: 'PRE' (str)
        descricao     : nome da curva, ex: 'DIxPRE' (str)
        dias_corridos : dias corridos até o vértice (int)
        dias_uteis    : dias úteis até o vértice (int)
        taxa          : taxa anual em decimal, ex: 0.1465 = 14.65% (float)
        vertice       : F (fixo) ou M (móvel) (str)

    Exceções
    --------
    HolidayError           : fim de semana
    NoDataError            : dia útil sem dados publicados
    CurvaInvalidaError     : código de curva não reconhecido
    ProxyAuthError         : proxy requer autenticação
    ServerUnavailableError : servidor B3 indisponível (5xx)
    TimeoutError           : timeout na requisição
    ParsingError           : arquivo baixado mas não parseável
    PyETTJError            : outros erros

    Exemplos
    --------
    >>> df = get_ettj("09/04/2026")
    >>> df = get_ettj("09/04/2026", curva="DIC", proxies=proxies)
    >>> df = get_ettj("09/04/2026", curva=["PRE", "DIC"])
    >>> df = get_ettj("09/04/2026", curva="TODOS")
    """
    # 1. Parsear e validar a data
    d = _parse_data(data)
    data_str = d.strftime("%d/%m/%Y")

    if _is_fim_de_semana(d):
        sugestao = _proximo_dia_util(d).strftime("%d/%m/%Y")
        raise HolidayError(data_str, sugestao=sugestao)

    if d > date.today():
        raise NoDataError(data_str, "data futura — dados ainda não disponíveis")

    # 2. Normalizar e validar curvas
    if isinstance(curva, str):
        if curva.upper() == "TODOS":
            curvas_filtro = list(CURVAS_DISPONIVEIS.keys())
            warnings.warn(
                "[pyettj] curva='TODOS' retorna ~100 curvas. "
                "Para uso cotidiano prefira especificar as curvas desejadas.",
                UserWarning,
                stacklevel=2,
            )
        else:
            curvas_filtro = [curva.upper().strip()]
    else:
        curvas_filtro = [c.upper().strip() for c in curva]

    for c in curvas_filtro:
        if c not in CURVAS_DISPONIVEIS:
            raise CurvaInvalidaError(c)

    # 3. Tentar cache
    if cache and _cache_valido(d):
        df_cache = _cache_ler(d)
        if df_cache is not None:
            df_filtrado = _filtrar_curvas(df_cache, curvas_filtro)
            if not df_filtrado.empty:
                mtime_str = ""
                from pyettj.cache import _cache_path
                try:
                    from datetime import datetime as _dt
                    mtime = _dt.fromtimestamp(_cache_path(d).stat().st_mtime)
                    delta = _dt.now() - mtime
                    h, m = divmod(int(delta.total_seconds() / 60), 60)
                    mtime_str = f" (salvo há {h}h{m:02d}min)" if h else f" (salvo há {m}min)"
                except Exception:
                    pass
                print(f"[pyettj] Cache: {data_str}{mtime_str}")
                return df_filtrado

    # 4. Download — sempre todas as curvas quando cache=True
    curvas_download = list(CURVAS_DISPONIVEIS.keys()) if cache else curvas_filtro
    raw = _baixar_raw(d, proxies=proxies, timeout=timeout, retry=retry)

    # 5. Descompressão e parse
    txt = _extrair_txt(raw, data_str)
    df_completo = _parsear_txt(txt, curvas_download, d)

    # 6. Salvar no cache antes de filtrar
    if cache and not df_completo.empty:
        _cache_salvar(d, df_completo)
        print(
            f"[pyettj] Baixado e salvo no cache: "
            f"{data_str} ({len(df_completo)} registros, "
            f"{len(df_completo['curva'].unique())} curvas)"
        )

    # 7. Filtrar pela(s) curva(s) solicitada(s)
    df = _filtrar_curvas(df_completo, curvas_filtro)

    # 8. Validar output
    _validar_output(df, curvas_filtro, data_str)

    return df


def get_ettj_historico(
    data_ini: str,
    data_fim: str,
    curva: Union[str, List[str]] = CURVA_PADRAO,
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 120,
    retry: int = 3,
    cache: bool = True,
    ignorar_erros: bool = True,
) -> pd.DataFrame:
    """
    Captura ETTJ para um intervalo de datas, pulando fins de semana
    e dias sem dados automaticamente.

    Parâmetros
    ----------
    data_ini : str
        Data inicial no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
    data_fim : str
        Data final no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
    curva : str ou list[str]
        Código(s) da(s) curva(s). Padrão: 'PRE'.
    proxies : dict, opcional
        Configuração de proxy.
    timeout : int
        Timeout por requisição em segundos. Padrão: 120.
    retry : int
        Tentativas por data. Padrão: 3.
    cache : bool
        Se True (padrão), usa cache local. Muito útil para séries longas
        — datas já baixadas não são rebaixadas.
    ignorar_erros : bool
        Se True (padrão), datas com falha são puladas com warning.
        Se False, lança exceção na primeira falha.

    Retorno
    -------
    pd.DataFrame concatenado de todas as datas com sucesso,
    com coluna 'refdate' identificando cada data.

    Exemplos
    --------
    >>> df = get_ettj_historico("01/01/2026", "09/04/2026", proxies=proxies)
    >>> df = get_ettj_historico("01/01/2026", "09/04/2026",
    ...                         curva=["PRE", "DIC"], proxies=proxies)
    """
    d_ini = _parse_data(data_ini)
    d_fim = _parse_data(data_fim)

    if d_ini > d_fim:
        raise PyETTJError(
            f"data_ini ({data_ini}) é posterior a data_fim ({data_fim})."
        )

    frames: List[pd.DataFrame] = []
    datas_sem_dados: List[str] = []
    datas_com_erro: List[str] = []

    d_atual = d_ini
    while d_atual <= d_fim:
        if _is_fim_de_semana(d_atual):
            d_atual += timedelta(days=1)
            continue

        data_str = d_atual.strftime("%d/%m/%Y")

        try:
            df = get_ettj(
                data_str,
                curva=curva,
                proxies=proxies,
                timeout=timeout,
                retry=retry,
                cache=cache,
            )
            frames.append(df)

        except (HolidayError, NoDataError) as e:
            datas_sem_dados.append(data_str)

        except PyETTJError as e:
            datas_com_erro.append(data_str)
            if not ignorar_erros:
                raise
            warnings.warn(
                f"[pyettj] Erro em {data_str}: {e}",
                stacklevel=2,
            )

        d_atual += timedelta(days=1)

    # Reportar datas sem dados
    if datas_sem_dados:
        n = len(datas_sem_dados)
        amostra = ", ".join(datas_sem_dados[:5])
        reticencias = " ..." if n > 5 else ""
        warnings.warn(
            f"[pyettj] {n} data(s) sem dados (feriados/sem publicação): "
            f"{amostra}{reticencias}",
            stacklevel=2,
        )

    # Reportar datas com erro
    if datas_com_erro:
        n = len(datas_com_erro)
        amostra = ", ".join(datas_com_erro[:5])
        reticencias = " ..." if n > 5 else ""
        warnings.warn(
            f"[pyettj] {n} data(s) com erro de download/parse: "
            f"{amostra}{reticencias}",
            stacklevel=2,
        )

    if not frames:
        raise NoDataError(
            f"{data_ini} a {data_fim}",
            "nenhuma data retornou dados no intervalo solicitado",
        )

    print(
        f"[pyettj] Concluído: {len(frames)} data(s) retornada(s) "
        f"de {data_ini} a {data_fim}."
    )

    return pd.concat(frames, ignore_index=True)
