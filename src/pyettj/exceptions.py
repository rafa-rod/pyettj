"""
exceptions.py
=============
Hierarquia de exceções do pyettj.

Importação direta:
    from pyettj.exceptions import HolidayError, NoDataError, CurvaInvalidaError
"""

from __future__ import annotations
from typing import Optional


class PyETTJError(Exception):
    """Exceção base do pyettj. Captura qualquer erro do pacote."""


# ---------------------------------------------------------------------------
# Erros de disponibilidade de dados
# ---------------------------------------------------------------------------

class DataNotAvailableError(PyETTJError):
    """Sem dados para a data solicitada."""

    def __init__(self, data: str, motivo: str = ""):
        self.data = data
        self.motivo = motivo
        msg = f"Sem dados para {data}"
        if motivo:
            msg += f": {motivo}"
        super().__init__(msg)


class HolidayError(DataNotAvailableError):
    """Data solicitada é feriado, fim de semana ou não-útil no calendário ANBIMA.

    Atributos
    ---------
    sugestao : str | None
        Próximo dia útil sugerido no formato dd/mm/yyyy.
    """

    def __init__(self, data: str, sugestao: Optional[str] = None):
        self.sugestao = sugestao
        motivo = "feriado ou final de semana"
        if sugestao:
            motivo += f". Sugestão: {sugestao}"
        super().__init__(data, motivo)


class NoDataError(DataNotAvailableError):
    """Dia útil sem dados publicados pela B3.

    Causas comuns:
    - Dado ainda não publicado (pregão recente)
    - Data futura
    - Feriado não coberto pelo calendário local
    """


# ---------------------------------------------------------------------------
# Erros de conexão / rede
# ---------------------------------------------------------------------------

class ConnectionError(PyETTJError):
    """Falha de rede, proxy ou DNS."""


class ProxyAuthError(ConnectionError):
    """Proxy requer autenticação (HTTP 407)."""


class ServerUnavailableError(ConnectionError):
    """Servidor da B3 indisponível (HTTP 5xx)."""


class TimeoutError(ConnectionError):
    """Timeout na requisição HTTP."""


# ---------------------------------------------------------------------------
# Erros de parse / formato
# ---------------------------------------------------------------------------

class ParsingError(PyETTJError):
    """Arquivo baixado com sucesso mas não foi possível parsear.

    Indica mudança de layout no arquivo TaxaSwap da B3.

    Atributos
    ---------
    data : str
        Data do arquivo que falhou.
    """

    def __init__(self, msg: str, data: str = ""):
        self.data = data
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Erros de parâmetro
# ---------------------------------------------------------------------------

class CurvaInvalidaError(PyETTJError):
    """Código de curva não reconhecido no catálogo CURVAS_DISPONIVEIS.

    Atributos
    ---------
    curva : str
        Código inválido informado pelo usuário.
    """

    def __init__(self, curva: str):
        self.curva = curva
        super().__init__(
            f"Curva '{curva}' não encontrada. "
            "Use listar_curvas() para ver as opções disponíveis."
        )


class DataFormatoError(PyETTJError):
    """Formato de data não reconhecido.

    Formatos aceitos: 'dd/mm/yyyy' ou 'yyyy-mm-dd'.
    """

    def __init__(self, data: str):
        self.data = data
        super().__init__(
            f"Formato de data não reconhecido: '{data}'. "
            "Use 'dd/mm/yyyy' ou 'yyyy-mm-dd'."
        )


# ---------------------------------------------------------------------------
# Erros de cache
# ---------------------------------------------------------------------------

class CacheError(PyETTJError):
    """Falha ao ler ou escrever no cache local.

    Causas comuns: sem permissão de escrita, disco cheio.
    """
