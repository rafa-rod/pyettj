"""
plot_ettj.py
============
Funções de visualização das curvas ETTJ do pyettj.

O DataFrame de entrada deve ter o formato retornado por get_ettj() ou
get_ettj_historico():
    refdate, curva, descricao, dias_corridos, dias_uteis, taxa, vertice

Uso:
    import pyettj.ettj as ettj
    import pyettj.plot_ettj as plot

    df = ettj.get_ettj("09/04/2026", curva=["PRE", "DIC"])
    plot.plot_ettj(df)
    plot.plot_ettj(df, curva="PRE")
    plot.plot_ettj(df, curva=["PRE", "DIC"], eixo_x="dias_uteis")
"""

from __future__ import annotations

from typing import List, Optional, Union

import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise ImportError(
        "matplotlib é necessário para plot_ettj. "
        "Instale com: pip install matplotlib"
    )


def plot_ettj(
    ettj: pd.DataFrame,
    curva: Union[str, List[str], None] = None,
    data: Optional[str] = None,
    eixo_x: str = "dias_corridos",
    figsize: tuple = (12, 6),
    **kwargs,
) -> None:
    """
    Plota a(s) curva(s) ETTJ a partir do DataFrame retornado por get_ettj().

    Parâmetros
    ----------
    ettj : pd.DataFrame
        DataFrame retornado por get_ettj() ou get_ettj_historico().
    curva : str ou list[str], opcional
        Curva(s) a plotar. Se None, plota todas as curvas presentes no DataFrame.
    data : str, opcional
        Filtra por data de referência (formato 'dd/mm/yyyy' ou 'yyyy-mm-dd').
        Útil quando o DataFrame contém múltiplas datas (get_ettj_historico).
        Se None, usa todas as datas presentes.
    eixo_x : str
        Coluna a usar no eixo X: 'dias_corridos' (padrão) ou 'dias_uteis'.
    figsize : tuple
        Tamanho da figura matplotlib. Padrão: (12, 6).
    **kwargs
        Parâmetros adicionais passados para plt.plot() (ex: lw=2, color='blue').

    Exemplos
    --------
    >>> # Uma curva, uma data
    >>> df = get_ettj("09/04/2026", curva="PRE")
    >>> plot_ettj(df)

    >>> # Duas curvas sobrepostas
    >>> df = get_ettj("09/04/2026", curva=["PRE", "DIC"])
    >>> plot_ettj(df)

    >>> # Filtrar curva específica de DataFrame com múltiplas curvas
    >>> plot_ettj(df, curva="PRE")

    >>> # Usar dias úteis no eixo X
    >>> plot_ettj(df, eixo_x="dias_uteis")

    >>> # Série histórica — plota todas as datas sobrepostas
    >>> df_hist = get_ettj_historico("01/03/2026", "09/04/2026", curva="PRE")
    >>> plot_ettj(df_hist)
    """
    df = ettj.copy()

    # Validar colunas obrigatórias
    ausentes = {"curva", "taxa", eixo_x} - set(df.columns)
    if ausentes:
        raise ValueError(
            f"DataFrame não contém as colunas necessárias: {ausentes}. "
            "Use o DataFrame retornado por get_ettj()."
        )

    # Filtrar por curva
    if curva is not None:
        curvas_lista = [curva] if isinstance(curva, str) else list(curva)
        curvas_lista = [c.upper().strip() for c in curvas_lista]
        df = df[df["curva"].isin(curvas_lista)]
        if df.empty:
            raise ValueError(f"Curva(s) {curvas_lista} não encontrada(s) no DataFrame.")

    # Filtrar por data
    if data is not None and "refdate" in df.columns:
        from datetime import datetime as _dt
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                data_ts = pd.Timestamp(_dt.strptime(data.strip(), fmt))
                break
            except ValueError:
                continue
        else:
            raise ValueError(
                f"Formato de data não reconhecido: '{data}'. "
                "Use 'dd/mm/yyyy' ou 'yyyy-mm-dd'."
            )
        df = df[df["refdate"] == data_ts]
        if df.empty:
            raise ValueError(f"Data '{data}' não encontrada no DataFrame.")

    curvas_presentes = sorted(df["curva"].unique())
    n_curvas = len(curvas_presentes)
    n_datas  = df["refdate"].nunique() if "refdate" in df.columns else 1

    # Montar título
    curvas_titulo  = ", ".join(curvas_presentes) if n_curvas <= 4 else f"{n_curvas} curvas"
    if "refdate" in df.columns and n_datas == 1:
        data_titulo = pd.to_datetime(df["refdate"].iloc[0]).strftime("%d/%m/%Y")
        titulo = f"ETTJ — {curvas_titulo} — {data_titulo}"
    elif n_datas > 1:
        titulo = f"ETTJ — {curvas_titulo} — {n_datas} datas"
    else:
        titulo = f"ETTJ — {curvas_titulo}"

    label_x = "Dias Corridos" if eixo_x == "dias_corridos" else "Dias Úteis"

    plt.figure(figsize=figsize)

    if "refdate" in df.columns and n_datas > 1 and n_curvas == 1:
        # Série histórica de uma curva: uma linha por data
        for data_ref, grupo in df.groupby("refdate"):
            label = pd.to_datetime(data_ref).strftime("%d/%m/%Y")
            g = grupo.sort_values(eixo_x)
            plt.plot(g[eixo_x], g["taxa"] * 100, label=label, **kwargs)

    elif "refdate" in df.columns and n_datas > 1 and n_curvas > 1:
        # Múltiplas datas e curvas: agrupamento por curva+data
        for (data_ref, c), grupo in df.groupby(["refdate", "curva"]):
            label = f"{c} — {pd.to_datetime(data_ref).strftime('%d/%m/%Y')}"
            g = grupo.sort_values(eixo_x)
            plt.plot(g[eixo_x], g["taxa"] * 100, label=label, **kwargs)

    else:
        # Uma data, uma ou mais curvas: uma linha por curva
        for c, grupo in df.groupby("curva"):
            desc  = grupo["descricao"].iloc[0] if "descricao" in grupo.columns else ""
            label = f"{c} ({desc})" if desc and desc != c else c
            g = grupo.sort_values(eixo_x)
            plt.plot(g[eixo_x], g["taxa"] * 100, label=label, **kwargs)

    plt.title(titulo)
    plt.xlabel(label_x)
    plt.ylabel("Taxa (% a.a.)", rotation=0, labelpad=60)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()
