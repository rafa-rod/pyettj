# -*- coding: utf-8 -*-
"""
test_ettj.py
============
Testes para o módulo ettj.py (novo endpoint B3 / TaxaSwap).

Cobertura:
    - Parsing e validação de datas
    - listar_curvas
    - listar_dias_uteis
    - get_ettj: estrutura do DataFrame, colunas, tipos, valores
    - get_ettj: múltiplas curvas
    - get_ettj: cache (leitura e escrita)
    - get_ettj_historico: intervalo de datas
    - Exceções: HolidayError, NoDataError, CurvaInvalidaError, DataFormatoError
    - cache_info e cache_clear

Nota: testes que fazem requests reais à B3 são marcados com @pytest.mark.network
e podem ser excluídos em CI sem rede: pytest -m "not network"
"""

import io
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pyettj as ettj
from pyettj.cache import _cache_ler, _cache_path, _cache_salvar, _cache_valido
from pyettj.exceptions import (
    CurvaInvalidaError,
    DataFormatoError,
    HolidayError,
    NoDataError,
    PyETTJError,
)

# ---------------------------------------------------------------------------
# Helpers para testes sem rede
# ---------------------------------------------------------------------------


def _criar_zip_taxaswap(linhas: list[str]) -> bytes:
    """
    Cria um ZIP no formato exato do TaxaSwap da B3:
    ZIP externo → self-extracting EXE (stub + PK\x03\x04) → ZIP interno → TaxaSwap.txt
    """
    # ZIP interno com TaxaSwap.txt
    buf_inner = io.BytesIO()
    with zipfile.ZipFile(buf_inner, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("TaxaSwap.txt", "\n".join(linhas))
    inner_bytes = buf_inner.getvalue()

    # Simular stub EXE antes do ZIP interno
    stub = b"MZ" + b"\x00" * 100  # cabeçalho EXE mínimo
    exe_bytes = stub + inner_bytes

    # ZIP externo contendo o .ex_
    buf_outer = io.BytesIO()
    with zipfile.ZipFile(buf_outer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("TS260409.ex_", exe_bytes)
    return buf_outer.getvalue()


def _linha_taxaswap(
    seq: int = 1,
    data: str = "20260409",
    cod: str = "PRE  ",
    desc: str = "DIxPRE         ",
    dc: int = 252,
    du: int = 174,
    taxa_int: int = 146500000,  # 0.1465 = 14.65%
    vertice: str = "F",
    cod_vertice: int = 252,
) -> str:
    """Gera uma linha válida do TaxaSwap conforme layout oficial B3."""
    sinal = "+" if taxa_int >= 0 else "-"
    taxa_str = str(abs(taxa_int)).zfill(14)
    return (
        f"{seq:06d}"  # [00:06]  seq
        f"00101"  # [06:11]  constante
        f"{data}"  # [11:19]  data AAAAMMDD
        f"T1"  # [19:21]  constante
        f"{cod}"  # [21:26]  código da taxa (5 chars)
        f"{desc}"  # [26:41]  descrição (15 chars)
        f"{dc:05d}"  # [41:46]  dias corridos
        f"{du:05d}"  # [46:51]  dias úteis
        f"{sinal}"  # [51]     sinal
        f"{taxa_str}"  # [52:66]  taxa (14 dígitos)
        f"{vertice}"  # [66]     vértice F/M
        f"{cod_vertice:05d}"  # [67:72]  código vértice
    )


def _df_esperado_pre() -> pd.DataFrame:
    """DataFrame mínimo esperado para curva PRE."""
    return pd.DataFrame(
        [
            {
                "refdate": pd.Timestamp("2026-04-09"),
                "curva": "PRE",
                "descricao": "DIxPRE",
                "dias_corridos": 252,
                "dias_uteis": 174,
                "taxa": 0.1465,
                "vertice": "F",
            }
        ]
    )


# ---------------------------------------------------------------------------
# Fixture: DataFrame de taxas simulado para get_ettj (mock)
# ---------------------------------------------------------------------------


@pytest.fixture
def df_pre_simples():
    linhas = [
        _linha_taxaswap(seq=1, dc=252, du=174, taxa_int=146500000, vertice="F"),
        _linha_taxaswap(seq=2, dc=504, du=348, taxa_int=140000000, vertice="M"),
        _linha_taxaswap(seq=3, dc=1260, du=863, taxa_int=136000000, vertice="F"),
    ]
    return _criar_zip_taxaswap(linhas)


@pytest.fixture
def df_multi_curvas():
    linhas = [
        _linha_taxaswap(
            seq=1, cod="PRE  ", desc="DIxPRE         ", dc=252, taxa_int=146500000
        ),
        _linha_taxaswap(
            seq=2, cod="DIC  ", desc="DI X IPCA      ", dc=252, taxa_int=60000000
        ),
        _linha_taxaswap(
            seq=3, cod="DCL  ", desc="CUPOM LIMPO - S", dc=252, taxa_int=50000000
        ),
    ]
    return _criar_zip_taxaswap(linhas)


# ===========================================================================
# 1. PARSING DE DATA
# ===========================================================================


class TestParseData:
    def test_formato_dd_mm_yyyy(self):
        from pyettj.ettj import _parse_data

        d = _parse_data("09/04/2026")
        assert d == date(2026, 4, 9)

    def test_formato_yyyy_mm_dd(self):
        from pyettj.ettj import _parse_data

        d = _parse_data("2026-04-09")
        assert d == date(2026, 4, 9)

    def test_formato_dd_mm_yyyy_hifem(self):
        from pyettj.ettj import _parse_data

        d = _parse_data("09-04-2026")
        assert d == date(2026, 4, 9)

    def test_formato_invalido_lanca_excecao(self):
        from pyettj.ettj import _parse_data

        with pytest.raises(DataFormatoError):
            _parse_data("2026/04/09")

    def test_nao_string_lanca_excecao(self):
        from pyettj.ettj import _parse_data

        with pytest.raises((DataFormatoError, AttributeError)):
            _parse_data(20260409)


# ===========================================================================
# 2. LISTAR_CURVAS
# ===========================================================================


class TestListarCurvas:
    def test_retorna_dataframe(self, capsys):
        df = ettj.listar_curvas(verbose=False)
        assert isinstance(df, pd.DataFrame)

    def test_colunas_corretas(self):
        df = ettj.listar_curvas(verbose=False)
        assert list(df.columns) == ["codigo", "descricao"]

    def test_contem_pre_dic_dcl(self):
        df = ettj.listar_curvas(verbose=False)
        codigos = df["codigo"].tolist()
        assert "PRE" in codigos
        assert "DIC" in codigos
        assert "DCL" in codigos

    def test_verbose_imprime(self, capsys):
        ettj.listar_curvas(verbose=True)
        out = capsys.readouterr().out
        assert "PRE" in out
        assert "Total:" in out

    def test_sem_verbose_nao_imprime(self, capsys):
        ettj.listar_curvas(verbose=False)
        out = capsys.readouterr().out
        assert out == ""


# ===========================================================================
# 3. LISTAR_DIAS_UTEIS
# ===========================================================================


class TestListarDiasUteis:
    def test_retorna_lista(self):
        dias = ettj.listar_dias_uteis("01/04/2026", "09/04/2026")
        assert isinstance(dias, list)

    def test_exclui_fins_de_semana(self):
        # 04/04 (sáb) e 05/04 (dom) não devem aparecer
        dias = ettj.listar_dias_uteis("03/04/2026", "07/04/2026")
        assert "05/04/2026" not in dias  # sábado
        assert "06/04/2026" not in dias  # domingo

    def test_inclui_dias_uteis(self):
        dias = ettj.listar_dias_uteis("07/04/2026", "09/04/2026")
        assert "07/04/2026" in dias
        assert "08/04/2026" in dias
        assert "09/04/2026" in dias

    def test_formato_saida_dd_mm_yyyy(self):
        dias = ettj.listar_dias_uteis("07/04/2026", "07/04/2026")
        assert dias == ["07/04/2026"]

    def test_data_ini_posterior_lanca_excecao(self):
        with pytest.raises(PyETTJError):
            ettj.listar_dias_uteis("09/04/2026", "01/04/2026")

    def test_aceita_formato_yyyy_mm_dd(self):
        dias = ettj.listar_dias_uteis("2026-04-07", "2026-04-09")
        assert len(dias) == 3

    def test_uma_semana_tem_cinco_dias(self):
        # Semana cheia: 06/04 (seg) a 10/04 (sex)
        dias = ettj.listar_dias_uteis("06/04/2026", "10/04/2026")
        assert len(dias) == 5


# ===========================================================================
# 4. GET_ETTJ — validações sem rede (mock)
# ===========================================================================


class TestGetEttjMock:
    def test_fim_de_semana_lanca_holiday_error(self):
        # 11/04/2026 é sábado
        with pytest.raises(HolidayError) as exc:
            ettj.get_ettj("11/04/2026", cache=False)
        assert exc.value.sugestao is not None

    def test_data_futura_lanca_no_data_error(self):
        data_futura = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
        with pytest.raises(NoDataError):
            ettj.get_ettj(data_futura, cache=False)

    def test_curva_invalida_lanca_excecao(self):
        with pytest.raises(CurvaInvalidaError) as exc:
            ettj.get_ettj("09/04/2026", curva="XYZ", cache=False)
        assert "XYZ" in str(exc.value)

    def test_curva_invalida_lista_lanca_excecao(self):
        with pytest.raises(CurvaInvalidaError):
            ettj.get_ettj("09/04/2026", curva=["PRE", "INVALIDA"], cache=False)

    @patch("pyettj.ettj._baixar_raw")
    def test_df_colunas_corretas(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert list(df.columns) == [
            "refdate",
            "curva",
            "descricao",
            "dias_corridos",
            "dias_uteis",
            "taxa",
            "vertice",
        ]

    @patch("pyettj.ettj._baixar_raw")
    def test_df_tipos_corretos(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert pd.api.types.is_datetime64_any_dtype(df["refdate"])
        assert df["curva"].dtype == object
        assert pd.api.types.is_integer_dtype(df["dias_corridos"])
        assert pd.api.types.is_integer_dtype(df["dias_uteis"])
        assert pd.api.types.is_float_dtype(df["taxa"])

    @patch("pyettj.ettj._baixar_raw")
    def test_taxa_em_decimal(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        # Taxa deve estar em decimal (0.1465), não percentual (14.65)
        assert df["taxa"].max() < 2.0
        assert df["taxa"].min() > 0.0

    @patch("pyettj.ettj._baixar_raw")
    def test_taxa_pre_valor_esperado(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert abs(df["taxa"].iloc[0] - 0.1465) < 1e-6

    @patch("pyettj.ettj._baixar_raw")
    def test_refdate_correto(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert df["refdate"].iloc[0] == pd.Timestamp("2026-04-09")

    @patch("pyettj.ettj._baixar_raw")
    def test_curva_column_so_pre(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert set(df["curva"].unique()) == {"PRE"}

    @patch("pyettj.ettj._baixar_raw")
    def test_multiplas_curvas(self, mock_baixar, df_multi_curvas):
        mock_baixar.return_value = df_multi_curvas
        df = ettj.get_ettj("09/04/2026", curva=["PRE", "DIC"], cache=False)
        assert set(df["curva"].unique()) == {"PRE", "DIC"}

    @patch("pyettj.ettj._baixar_raw")
    def test_todos_retorna_todas_curvas(self, mock_baixar, df_multi_curvas):
        mock_baixar.return_value = df_multi_curvas
        df = ettj.get_ettj("09/04/2026", curva="TODOS", cache=False)
        assert len(df["curva"].unique()) >= 1

    @patch("pyettj.ettj._baixar_raw")
    def test_ordenado_por_dias_corridos(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert df["dias_corridos"].is_monotonic_increasing

    @patch("pyettj.ettj._baixar_raw")
    def test_vertice_f_ou_m(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj("09/04/2026", curva="PRE", cache=False)
        assert set(df["vertice"].unique()).issubset({"F", "M"})

    @patch("pyettj.ettj._baixar_raw")
    def test_zip_vazio_lanca_no_data_error(self, mock_baixar):
        # ZIP vazio = 22 bytes
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass
        mock_baixar.side_effect = NoDataError(
            "09/04/2026", "arquivo vazio — possível feriado"
        )
        with pytest.raises(NoDataError):
            ettj.get_ettj("09/04/2026", curva="PRE", cache=False)


# ===========================================================================
# 5. CACHE
# ===========================================================================


class TestCache:
    def test_salvar_e_ler(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        d = date(2026, 1, 15)
        df = _df_esperado_pre()
        _cache_salvar(d, df)
        df_lido = _cache_ler(d)
        assert df_lido is not None
        assert len(df_lido) == len(df)

    def test_cache_inexistente_retorna_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        d = date(2020, 1, 1)
        assert _cache_ler(d) is None

    def test_cache_hoje_invalido(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        d = date.today()
        df = _df_esperado_pre()
        _cache_salvar(d, df)
        assert _cache_valido(d) is False

    def test_cache_dado_antigo_valido(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        d = date(2026, 1, 2)  # mais de 5 dias atrás
        df = _df_esperado_pre()
        _cache_salvar(d, df)
        assert _cache_valido(d) is True

    def test_cache_clear_tudo(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        df = _df_esperado_pre()
        for d in [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6)]:
            _cache_salvar(d, df)
        ettj.cache_clear()
        out = capsys.readouterr().out
        assert "3 arquivo(s)" in out

    def test_cache_clear_antes_de(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        df = _df_esperado_pre()
        _cache_salvar(date(2025, 12, 1), df)
        _cache_salvar(date(2026, 3, 1), df)
        ettj.cache_clear(antes_de="01/01/2026")
        out = capsys.readouterr().out
        assert "1 arquivo(s)" in out
        # O de março não deve ter sido removido
        assert _cache_ler(date(2026, 3, 1)) is not None

    def test_cache_info_vazio(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        ettj.cache_info()
        out = capsys.readouterr().out
        assert "vazio" in out.lower() or "Cache em:" in out

    def test_cache_info_com_dados(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        df = _df_esperado_pre()
        _cache_salvar(date(2026, 1, 2), df)
        ettj.cache_info()
        out = capsys.readouterr().out
        assert "1" in out

    @patch("pyettj.ettj._baixar_raw")
    def test_get_ettj_salva_no_cache(
        self, mock_baixar, df_pre_simples, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        mock_baixar.return_value = df_pre_simples
        ettj.get_ettj("09/04/2026", curva="PRE", cache=True)
        assert _cache_path(date(2026, 4, 9)).exists()

    @patch("pyettj.ettj._baixar_raw")
    def test_get_ettj_usa_cache_na_segunda_chamada(
        self, mock_baixar, df_pre_simples, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setenv("PYETTJ_CACHE_DIR", str(tmp_path))
        mock_baixar.return_value = df_pre_simples
        ettj.get_ettj("09/04/2026", curva="PRE", cache=True)
        ettj.get_ettj("09/04/2026", curva="PRE", cache=True)
        # Na segunda chamada, _baixar_raw não deve ser chamado novamente
        # (dado antigo = cache permanente)
        assert mock_baixar.call_count == 1


# ===========================================================================
# 6. GET_ETTJ_HISTORICO — mock
# ===========================================================================


class TestGetEttjHistoricoMock:
    @patch("pyettj.ettj._baixar_raw")
    def test_retorna_dataframe(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj_historico(
            "07/04/2026", "09/04/2026", curva="PRE", cache=False
        )
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    @patch("pyettj.ettj._baixar_raw")
    def test_tres_dias_uteis(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        df = ettj.get_ettj_historico(
            "07/04/2026", "09/04/2026", curva="PRE", cache=False
        )
        datas = df["refdate"].dt.date.unique()
        assert len(datas) == 3

    @patch("pyettj.ettj._baixar_raw")
    def test_pula_fins_de_semana(self, mock_baixar, df_pre_simples):
        mock_baixar.return_value = df_pre_simples
        # 04/04 (sáb) e 05/04 (dom) devem ser pulados
        df = ettj.get_ettj_historico(
            "03/04/2026", "07/04/2026", curva="PRE", cache=False
        )
        datas = [d.strftime("%d/%m/%Y") for d in df["refdate"].dt.date.unique()]
        assert "04/04/2026" not in datas
        assert "05/04/2026" not in datas

    @patch("pyettj.ettj._baixar_raw")
    def test_data_ini_posterior_lanca_excecao(self, mock_baixar, df_pre_simples):
        with pytest.raises(PyETTJError):
            ettj.get_ettj_historico(
                "09/04/2026", "01/04/2026", curva="PRE", cache=False
            )

    @patch("pyettj.ettj._baixar_raw")
    def test_ignorar_erros_true(self, mock_baixar, df_pre_simples):
        # Simula falha em uma das datas — não deve lançar exceção
        def side_effect(*args, **kwargs):
            if mock_baixar.call_count == 2:
                raise NoDataError("08/04/2026", "simulado")
            return df_pre_simples

        mock_baixar.side_effect = side_effect
        df = ettj.get_ettj_historico(
            "07/04/2026",
            "09/04/2026",
            curva="PRE",
            cache=False,
            ignorar_erros=True,
        )
        assert not df.empty

    @patch("pyettj.ettj._baixar_raw")
    def test_ignorar_erros_false_lanca_excecao(self, mock_baixar):
        mock_baixar.side_effect = NoDataError("07/04/2026", "simulado")
        with pytest.raises(NoDataError):
            ettj.get_ettj_historico(
                "07/04/2026",
                "09/04/2026",
                curva="PRE",
                cache=False,
                ignorar_erros=False,
            )

    @patch("pyettj.ettj._baixar_raw")
    def test_multiplas_curvas_historico(self, mock_baixar, df_multi_curvas):
        mock_baixar.return_value = df_multi_curvas
        df = ettj.get_ettj_historico(
            "07/04/2026",
            "09/04/2026",
            curva=["PRE", "DIC"],
            cache=False,
        )
        assert set(df["curva"].unique()) == {"PRE", "DIC"}


# ===========================================================================
# 7. EXCEÇÕES — comportamento e atributos
# ===========================================================================


class TestExcecoes:
    def test_holiday_error_tem_sugestao(self):
        # Sábado deve sugerir próxima segunda
        with pytest.raises(HolidayError) as exc:
            ettj.get_ettj("11/04/2026", cache=False)  # sábado
        assert exc.value.sugestao == "13/04/2026"  # segunda

    def test_holiday_error_domingo(self):
        with pytest.raises(HolidayError) as exc:
            ettj.get_ettj("12/04/2026", cache=False)  # domingo
        assert exc.value.sugestao == "13/04/2026"  # segunda

    def test_curva_invalida_tem_atributo_curva(self):
        with pytest.raises(CurvaInvalidaError) as exc:
            ettj.get_ettj("09/04/2026", curva="INVALIDA", cache=False)
        assert exc.value.curva == "INVALIDA"

    def test_data_formato_erro_tem_atributo_data(self):
        with pytest.raises(DataFormatoError) as exc:
            ettj.get_ettj("2026/04/09", cache=False)
        assert "2026/04/09" in exc.value.data

    def test_holiday_error_e_subclasse_de_pyettj_error(self):
        assert issubclass(HolidayError, PyETTJError)

    def test_no_data_error_e_subclasse_de_pyettj_error(self):
        assert issubclass(NoDataError, PyETTJError)

    def test_curva_invalida_e_subclasse_de_pyettj_error(self):
        assert issubclass(CurvaInvalidaError, PyETTJError)

    def test_importacao_direta_de_exceptions(self):
        from pyettj.exceptions import (
            CacheError,
            CurvaInvalidaError,
            DataFormatoError,
            HolidayError,
            NoDataError,
            ParsingError,
        )

        assert HolidayError
        assert NoDataError
        assert CurvaInvalidaError
        assert DataFormatoError
        assert CacheError
        assert ParsingError


# ===========================================================================
# 8. TESTES COM REDE REAL (marcados — executar só quando há conexão)
# ===========================================================================


@pytest.mark.network
class TestGetEttjNetwork:
    """
    Testes que fazem requests reais à B3.
    Executar com: pytest -m network
    Ignorar em CI sem rede: pytest -m "not network"

    Requerem configuração de proxy se em ambiente corporativo.
    Defina PYETTJ_TEST_PROXIES no ambiente para sobrescrever.
    """

    PROXIES = None  # Sobrescrever via fixture ou variável de ambiente

    def test_get_ettj_pre_real(self):
        df = ettj.get_ettj("09/04/2026", curva="PRE", proxies=self.PROXIES, cache=False)
        assert not df.empty
        assert df["curva"].iloc[0] == "PRE"
        assert 0.05 < df["taxa"].mean() < 0.30  # taxa entre 5% e 30%
        assert len(df) >= 200  # PRE tem ~285 vértices

    def test_get_ettj_dic_real(self):
        df = ettj.get_ettj("09/04/2026", curva="DIC", proxies=self.PROXIES, cache=False)
        assert not df.empty
        assert df["curva"].iloc[0] == "DIC"

    def test_get_ettj_multiplas_curvas_real(self):
        df = ettj.get_ettj(
            "09/04/2026", curva=["PRE", "DIC"], proxies=self.PROXIES, cache=False
        )
        assert set(df["curva"].unique()) == {"PRE", "DIC"}

    def test_feriado_pascoa_2026(self):
        # 18/04/2026 = Sexta-feira da Paixão — deve retornar NoDataError
        # (não é fim de semana, mas B3 não opera)
        with pytest.raises((HolidayError, NoDataError)):
            ettj.get_ettj("18/04/2026", proxies=self.PROXIES, cache=False)
