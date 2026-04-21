from . import version

# ETTJ — funções principais
from .ettj import (
    get_ettj,
    get_ettj_historico,
    listar_curvas,
    listar_dias_uteis,
    CURVAS_DISPONIVEIS,
)

# ANBIMA e modelos
from .modelo_ettj import get_ettj_anbima, svensson, calibrar_curva_svensson

# HJM
from .HJM import ModeloHJM, ParametrosOtimizacao, ResultadoCalibracao

# Plot
from .plot_ettj import plot_ettj

# Cache
from .cache import cache_info, cache_clear, set_cache_dir

# Exceções — expostas para quem quiser fazer tratamento granular
from .exceptions import (
    PyETTJError,
    DataNotAvailableError,
    HolidayError,
    NoDataError,
    CurvaInvalidaError,
    DataFormatoError,
    ConnectionError,
    ProxyAuthError,
    ServerUnavailableError,
    TimeoutError,
    ParsingError,
    CacheError,
)

__version__ = version.__version__
__author__  = "Rafael Rodrigues, rafa-rod @ GitHub"

__all__ = [
    # Versão
    "__version__",
    "__author__",
    # ETTJ
    "get_ettj",
    "get_ettj_historico",
    "listar_curvas",
    "listar_dias_uteis",
    "CURVAS_DISPONIVEIS",
    # ANBIMA
    "get_ettj_anbima",
    # Plot
    "plot_ettj",
    # Cache
    "cache_info",
    "cache_clear",
    "set_cache_dir",
    # Modelos
    "svensson",
    "calibrar_curva_svensson",
    "ModeloHJM",
    "ParametrosOtimizacao",
    "ResultadoCalibracao",
    # Exceções
    "PyETTJError",
    "DataNotAvailableError",
    "HolidayError",
    "NoDataError",
    "CurvaInvalidaError",
    "DataFormatoError",
    "ConnectionError",
    "ProxyAuthError",
    "ServerUnavailableError",
    "TimeoutError",
    "ParsingError",
    "CacheError",
]
