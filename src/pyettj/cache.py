"""
cache.py
========
Gerenciamento de cache local para o pyettj.

O cache salva o TaxaSwap completo (todas as curvas) em CSV por data,
evitando downloads repetidos de séries históricas.

Estrutura em disco:
    {PYETTJ_CACHE_DIR}/TS/
        2026-04-09.csv
        2026-04-08.csv
        ...

Configuração:
    - Diretório padrão : ~/.pyettj/cache/TS/
    - Variável de ambiente PYETTJ_CACHE_DIR sobrescreve o padrão
      ex: PYETTJ_CACHE_DIR=/dados/mercado/pyettj

Política de TTL:
    - Data de hoje           → nunca usa cache (sempre baixa fresco)
    - Dado recente (≤ 5 dias) → cache válido por 4 horas
    - Dado antigo (> 5 dias)  → cache permanente (dado imutável)
"""

from __future__ import annotations

import os
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from pyettj.exceptions import CacheError


# ---------------------------------------------------------------------------
# Diretório de cache
# ---------------------------------------------------------------------------

def _cache_dir() -> Path:
    """Retorna o diretório de cache, respeitando PYETTJ_CACHE_DIR."""
    custom = os.environ.get("PYETTJ_CACHE_DIR")
    if custom:
        base = Path(custom)
    else:
        base = Path.home() / ".pyettj" / "cache"
    return base / "TS"


def _cache_path(d: date) -> Path:
    """Retorna o caminho do arquivo CSV para uma data específica."""
    return _cache_dir() / f"{d.isoformat()}.csv"


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------

def _cache_valido(d: date) -> bool:
    """Verifica se o cache para a data d está válido conforme política de TTL."""
    path = _cache_path(d)
    if not path.exists():
        return False

    hoje = date.today()

    # Data de hoje ou futura: nunca usar cache
    if d >= hoje:
        return False

    dias_atras = (hoje - d).days

    # Dado antigo (> 5 dias): cache permanente
    if dias_atras > 5:
        return True

    # Dado recente (≤ 5 dias): válido por 4 horas
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return (datetime.now() - mtime).total_seconds() < 4 * 3600
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Leitura e escrita
# ---------------------------------------------------------------------------

def _cache_ler(d: date) -> Optional[pd.DataFrame]:
    """
    Lê o DataFrame completo do cache para a data d.
    Retorna None se o arquivo não existir ou estiver corrompido.
    """
    path = _cache_path(d)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["refdate"])
        return df
    except Exception as e:
        warnings.warn(
            f"[pyettj] Cache corrompido para {d.isoformat()}, "
            f"será rebaixado: {e}",
            stacklevel=4,
        )
        try:
            path.unlink()
        except OSError:
            pass
        return None


def _cache_salvar(d: date, df: pd.DataFrame) -> None:
    """
    Salva o DataFrame completo no cache para a data d.
    Falhas de escrita emitem warning mas não interrompem o fluxo.
    """
    path = _cache_path(d)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    except Exception as e:
        warnings.warn(
            f"[pyettj] Não foi possível salvar cache para {d.isoformat()}: {e}",
            stacklevel=4,
        )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def cache_info() -> None:
    """
    Exibe estatísticas do cache local.

    Exemplo de output:
        [pyettj] Cache em: C:\\Users\\rrafa\\.pyettj\\cache\\TS
        [pyettj] Datas em cache : 45
        [pyettj] Tamanho total  : 4.2 MB
        [pyettj] Mais antiga    : 02/01/2026
        [pyettj] Mais recente   : 09/04/2026
    """
    cache = _cache_dir()
    print(f"[pyettj] Cache em: {cache}")

    if not cache.exists():
        print("[pyettj] Cache vazio (diretório não existe).")
        return

    arquivos = sorted(cache.glob("*.csv"))
    if not arquivos:
        print("[pyettj] Cache vazio.")
        return

    total_bytes = sum(f.stat().st_size for f in arquivos)
    total_mb    = total_bytes / 1_048_576

    # Datas a partir dos nomes de arquivo
    datas = []
    for f in arquivos:
        try:
            datas.append(date.fromisoformat(f.stem))
        except ValueError:
            pass

    print(f"[pyettj] Datas em cache : {len(arquivos)}")
    print(f"[pyettj] Tamanho total  : {total_mb:.1f} MB")
    if datas:
        print(f"[pyettj] Mais antiga    : {min(datas).strftime('%d/%m/%Y')}")
        print(f"[pyettj] Mais recente   : {max(datas).strftime('%d/%m/%Y')}")


def cache_clear(antes_de: Optional[str] = None) -> None:
    """
    Remove arquivos do cache local.

    Parâmetros
    ----------
    antes_de : str, opcional
        Data no formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
        Se informada, remove apenas arquivos com data anterior a este valor.
        Se None (padrão), remove todo o cache.

    Exemplos
    --------
    >>> cache_clear()                        # remove tudo
    >>> cache_clear(antes_de="01/01/2026")   # remove só dados antigos
    """
    cache = _cache_dir()
    if not cache.exists():
        print("[pyettj] Cache já está vazio.")
        return

    # Determinar data limite
    limite: Optional[date] = None
    if antes_de is not None:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                from datetime import datetime as _dt
                limite = _dt.strptime(antes_de.strip(), fmt).date()
                break
            except ValueError:
                continue
        if limite is None:
            raise ValueError(
                f"Formato de data não reconhecido: '{antes_de}'. "
                "Use 'dd/mm/yyyy' ou 'yyyy-mm-dd'."
            )

    arquivos = sorted(cache.glob("*.csv"))
    removidos = 0

    for f in arquivos:
        try:
            d = date.fromisoformat(f.stem)
        except ValueError:
            continue

        if limite is None or d < limite:
            try:
                f.unlink()
                removidos += 1
            except OSError as e:
                warnings.warn(f"[pyettj] Não foi possível remover {f.name}: {e}")

    if antes_de:
        print(f"[pyettj] {removidos} arquivo(s) removido(s) anteriores a {antes_de}.")
    else:
        print(f"[pyettj] Cache limpo — {removidos} arquivo(s) removido(s).")
