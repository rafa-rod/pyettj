#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import linalg, optimize


def _numpy_para_json(obj: np.ndarray) -> Dict[str, Any]:
    """Converte array numpy para formato JSON serializável"""
    return {
        "__type__": "numpy.ndarray",
        "data": obj.tolist(),
        "dtype": str(obj.dtype),
        "shape": obj.shape,
    }


def _json_para_numpy(dct: Dict[str, Any]) -> Union[np.ndarray, Dict[str, Any]]:
    """Converte dict JSON de volta para numpy array"""
    if "__type__" in dct and dct["__type__"] == "numpy.ndarray":
        return np.array(dct["data"], dtype=dct["dtype"]).reshape(dct["shape"])
    return dct


def _dataframe_para_json(df: pd.DataFrame) -> Dict[str, Any]:
    """Converte DataFrame para formato JSON serializável"""
    return {
        "__type__": "pandas.DataFrame",
        "data": df.to_dict(),
        "index": df.index.tolist(),
        "columns": df.columns.tolist(),
    }


def _json_para_dataframe(dct: Dict[str, Any]) -> Union[pd.DataFrame, Dict[str, Any]]:
    """Converte dict JSON de volta para DataFrame"""
    if "__type__" in dct and dct["__type__"] == "pandas.DataFrame":
        df = pd.DataFrame(dct["data"])
        df.index = dct["index"]
        df.columns = dct["columns"]
        return df
    return dct


def _timestamp_para_json(ts: Optional[pd.Timestamp]) -> Optional[str]:
    """Converte Timestamp para string ISO"""
    if ts is None:
        return None
    return ts.isoformat()


def _json_para_timestamp(s: Optional[str]) -> Optional[pd.Timestamp]:
    """Converte string ISO de volta para Timestamp"""
    if s is None:
        return None
    return pd.Timestamp(s)


class HJMEncoder(json.JSONEncoder):
    """Encoder personalizado para serialização JSON do modelo HJM"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return _numpy_para_json(obj)
        if isinstance(obj, pd.DataFrame):
            return _dataframe_para_json(obj)
        if isinstance(obj, pd.Timestamp):
            return _timestamp_para_json(obj)
        if isinstance(obj, np.generic):
            return obj.item()
        return super().default(obj)


def _object_hook(dct: Dict[str, Any]) -> Any:
    """Hook para desserialização JSON do modelo HJM"""
    if "__type__" in dct:
        if dct["__type__"] == "numpy.ndarray":
            return _json_para_numpy(dct)
        if dct["__type__"] == "pandas.DataFrame":
            return _json_para_dataframe(dct)
    return dct


@dataclass
class ParametrosOtimizacao:
    """Parâmetros otimizados do modelo"""

    alpha: np.ndarray
    beta: np.ndarray
    gamma: np.ndarray
    delta: np.ndarray

    def __post_init__(self):
        assert (
            len(self.alpha) == len(self.beta) == len(self.gamma) == len(self.delta)
        ), "Todos os parâmetros devem ter o mesmo tamanho"

    def para_vetor(self) -> np.ndarray:
        """Converte parâmetros para vetor único"""
        return np.concatenate([self.alpha, self.beta, self.gamma, self.delta])

    @classmethod
    def de_vetor(cls, x: np.ndarray, n_comp: int) -> "ParametrosOtimizacao":
        """Cria parâmetros a partir de vetor único"""
        indices_divisao = np.arange(n_comp, n_comp * 4, n_comp)
        alpha, beta, gamma, delta = np.split(x, indices_divisao)
        return cls(alpha=alpha, beta=beta, gamma=gamma, delta=delta)

    def para_dataframe(self, n_fatores: int) -> pd.DataFrame:
        """Converte para DataFrame legível"""
        return pd.DataFrame(
            {
                "alpha": self.alpha,
                "beta": self.beta,
                "gamma": self.gamma,
                "delta": self.delta,
            },
            index=[f"fator {i + 1}" for i in range(n_fatores)],
        ).T

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict serializável"""
        return {
            "alpha": self.alpha.tolist(),
            "beta": self.beta.tolist(),
            "gamma": self.gamma.tolist(),
            "delta": self.delta.tolist(),
        }

    @classmethod
    def de_dict(cls, dct: Dict[str, Any]) -> "ParametrosOtimizacao":
        """Cria a partir de dict"""
        return cls(
            alpha=np.array(dct["alpha"]),
            beta=np.array(dct["beta"]),
            gamma=np.array(dct["gamma"]),
            delta=np.array(dct["delta"]),
        )


@dataclass
class ResultadoCalibracao:
    """Resultado da calibração"""

    parametros: pd.DataFrame
    pca: pd.DataFrame
    num_componentes: int
    vertices_dias: List[int]
    sigma_funcional: np.ndarray
    mu_funcional: np.ndarray
    sucesso: bool = True
    data_calibracao: Optional[pd.Timestamp] = None

    @property
    def variancia_explicada(self) -> float:
        """Propriedade calculada"""
        return float(self.pca.iloc[: self.num_componentes, 0].sum())

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict serializável"""
        return {
            "parametros": _dataframe_para_json(self.parametros),
            "pca": _dataframe_para_json(self.pca),
            "num_componentes": self.num_componentes,
            "vertices_dias": self.vertices_dias,
            "sigma_funcional": self.sigma_funcional.tolist(),
            "mu_funcional": self.mu_funcional.tolist(),
            "sucesso": self.sucesso,
            "data_calibracao": _timestamp_para_json(self.data_calibracao),
        }

    @classmethod
    def de_dict(cls, dct: Dict[str, Any]) -> "ResultadoCalibracao":
        """Cria a partir de dict"""
        return cls(
            parametros=_json_para_dataframe(dct["parametros"]),
            pca=_json_para_dataframe(dct["pca"]),
            num_componentes=dct["num_componentes"],
            vertices_dias=dct["vertices_dias"],
            sigma_funcional=np.array(dct["sigma_funcional"]),
            mu_funcional=np.array(dct["mu_funcional"]),
            sucesso=dct["sucesso"],
            data_calibracao=_json_para_timestamp(dct["data_calibracao"]),
        )


class ModeloHJM:
    """
    Classe para implementação do modelo Heath-Jarrow-Morton (HJM)
    Formato do DataFrame 'taxas':
    -----------------------------
    - Índice: datas (pd.DatetimeIndex)
    - Colunas: vértices em DIAS (int ou float)
      Ex: [21, 63, 126, 252, 504, ...]
    """

    VERBOSE_LEVELS: ClassVar[Dict[str, int]] = {
        "silencioso": 0,
        "basico": 1,
        "detalhado": 2,
    }

    VERSAO_MODELO: ClassVar[str] = "1.0.0"

    def __init__(self, convencao_dias: int = 252, verbose: int = 0):
        self.convencao_dias = convencao_dias
        self.verbose = verbose
        self.parametros: Optional[pd.DataFrame] = None
        self.pca: Optional[pd.DataFrame] = None
        self.vertices_dias: Optional[List[int]] = None
        self.vertices_ano: Optional[np.ndarray] = None
        self._taxas: Optional[pd.DataFrame] = None
        self.num_componentes: Optional[int] = None
        self.sigma_funcional: Optional[np.ndarray] = None
        self.mu_funcional: Optional[np.ndarray] = None
        self.sigma_t: Optional[np.ndarray] = None
        self._parametros_obj: Optional[ParametrosOtimizacao] = None
        self.calibrado: bool = False
        self._historico: List[Dict[str, Any]] = []
        self._data_calibracao: Optional[pd.Timestamp] = None
        self._metadata: Dict[str, Any] = {
            "versao": self.VERSAO_MODELO,
            "criado_em": pd.Timestamp.now().isoformat(),
        }

    def _log(self, mensagem: str, nivel: int = 1) -> None:
        """Método de logging interno"""
        if self.verbose >= nivel:
            print(f"[HJM] {mensagem}")

    @property
    def taxas(self) -> Optional[pd.DataFrame]:
        return self._taxas

    @taxas.setter
    def taxas(self, df: Optional[pd.DataFrame]) -> None:
        if df is None:
            self._taxas = None
            return
        taxas = df.copy()
        if pd.api.types.is_integer_dtype(taxas.columns):
            taxas.columns = self._padronizar_colunas(
                taxas.columns, self.convencao_dias
            )
        self._taxas = taxas

    @staticmethod
    def _dias_para_anos(
        vertices_dias: Union[List[int], np.ndarray], convencao_dias: int
    ) -> np.ndarray:
        """
        Converte vértices de dias para anos

        Parâmetros:
        -----------
        vertices_dias : List[int] ou np.ndarray
            Vértices em dias
        convencao_dias : int
            Convenção de dias úteis

        Retorna:
        --------
        np.ndarray
            Vértices em anos
        """
        return np.array(vertices_dias) / convencao_dias

    @staticmethod
    def _sigma_parametrico(
        x: np.ndarray,
        vertices_ano: np.ndarray,
        n_comp: int = 3,
        retorna_mu: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """Calcula a função de volatilidade paramétrica"""
        assert len(x) % 4 == 0, "Vetor x deve ter tamanho múltiplo de 4"

        split_indices = np.arange(n_comp, n_comp * 4, n_comp)
        alpha, beta, gamma, delta = np.split(x, split_indices)

        alpha = alpha.reshape(1, -1)
        beta = beta.reshape(1, -1)
        gamma = gamma.reshape(1, -1)
        delta = delta.reshape(1, -1)

        vertices = np.array(vertices_ano).reshape((-1, 1))

        sigma = (alpha + beta * vertices) * np.exp(gamma * vertices) + delta

        if retorna_mu:
            alpha, beta, gamma, delta = (
                alpha.flatten(),
                beta.flatten(),
                gamma.flatten(),
                delta.flatten(),
            )

            with np.errstate(divide="ignore", invalid="ignore"):
                termo1 = delta * vertices
                termo2 = np.where(
                    gamma != 0, beta / gamma * vertices * np.exp(gamma * vertices), 0
                )
                termo3 = np.where(
                    gamma != 0,
                    (alpha / gamma - beta / gamma**2) * (np.exp(gamma * vertices) - 1),
                    alpha * vertices,
                )

            mu = (sigma * (termo1 + termo2 + termo3)).sum(axis=1)
            sigma = sigma, mu

        return sigma

    @staticmethod
    def _chute_inicial(
        sigma: np.ndarray,
        pos_beta: int,
        vertice_beta: float,
        pos_alpha: int = 0,
        pos_delta: int = -1,
        gamma_0: float = np.log(0.5),
    ) -> np.ndarray:
        """Gera chute inicial para otimização dos parâmetros"""
        assert (sigma.ndim == 2) and len(sigma) >= np.max(
            [pos_alpha, pos_beta, pos_delta]
        )

        delta_0 = sigma[pos_delta, :]
        alpha_0 = sigma[pos_alpha] - delta_0
        gamma_0_array = np.full_like(alpha_0, gamma_0)

        if pos_beta > 1:
            beta_0 = (
                np.exp(-gamma_0_array * vertice_beta) * (sigma[pos_beta, :] - delta_0)
                - alpha_0
            ) / vertice_beta
        else:
            beta_0 = (
                np.exp(-gamma_0_array * vertice_beta) * (delta_0) - alpha_0
            ) / vertice_beta

        return np.concatenate((alpha_0, beta_0, gamma_0_array, delta_0))

    @staticmethod
    def _obter_svd(correl: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Decomposição em valores singulares da matriz de correlação"""
        assert correl.isnull().sum().sum() == 0
        U, D, V = np.linalg.svd(correl)
        assert np.allclose(np.matmul(U, np.diag(D)).dot(V), correl)
        assert np.allclose(U, V.T)
        return U, D, V

    @staticmethod
    def obter_data_valida(
        data: Union[str, datetime.date, pd.Timestamp], datas_validas: pd.DatetimeIndex
    ) -> pd.Timestamp:
        """
        Ajusta a data para um valor válido na série temporal

        Retorna:
        --------
        pd.Timestamp
            Data válida encontrada no índice
        """
        if not isinstance(data, pd.Timestamp):
            data = pd.to_datetime(data)

        if not isinstance(datas_validas, pd.DatetimeIndex):
            datas_validas = pd.to_datetime(datas_validas)

        data_normalized = data.normalize()
        datas_normalized = datas_validas.normalize()

        data_max = datas_normalized.max()

        while data_normalized not in datas_normalized:
            data_normalized += datetime.timedelta(days=1)
            if data_normalized > data_max:
                data_normalized = data_max
                break

        mask = datas_normalized == data_normalized
        if mask.any():
            return datas_validas[mask][0]
        else:
            return pd.to_datetime(data_normalized)

    @staticmethod
    def _padronizar_colunas(
        colunas_df: List[str | int | float], convencao_dias: int
    ) -> List[float]:
        """
        Padroniza colunas do DataFrame para float
        """
        colunas_padronizadas = []
        for col in colunas_df:
            dias = int(col)
            anos = dias / convencao_dias
            colunas_padronizadas.append(float(anos))
        return pd.Index(colunas_padronizadas)

    def calibrar(
        self, taxas: pd.DataFrame, vertices_calibracao: List[int]
    ) -> "ModeloHJM":
        """
        Calibra o modelo HJM

        Parâmetros:
        -----------
        taxas : pd.DataFrame
            Série histórica de taxas
            - Índice: datas (pd.DatetimeIndex)
            - Colunas: vértices em DIAS (ex: [21, 63, 126, 252, ...])
        vertices_calibracao : List[int]
            Lista de vértices para calibração (SEMPRE EM DIAS)
            Ex: [21, 63, 126, 252]

        Retorna:
        --------
        self : ModeloHJM
            Permite method chaining
        """
        self._log("Iniciando calibração...", nivel=1)
        self.taxas = taxas.copy()

        self.vertices_dias = vertices_calibracao
        self.vertices_ano = self._dias_para_anos(
            vertices_calibracao, self.convencao_dias
        )

        self._log(f"Vértices (dias): {self.vertices_dias}", nivel=2)
        self._log(f"Vértices (anos): {self.vertices_ano}", nivel=2)

        colunas_existentes = [v for v in self.vertices_ano if v in self.taxas.columns]
        print(f"colunas_existentes {colunas_existentes}")

        if len(colunas_existentes) == 0:
            raise ValueError(
                f"Nenhuma coluna de vértice encontrada no DataFrame de taxas.\n"
                f"Vértices procurados: {vertices_calibracao}\n"
                f"Colunas disponíveis: {list(taxas.columns)}"
            )

        if len(colunas_existentes) < len(self.vertices_ano):
            faltantes = set(self.vertices_ano) - set(colunas_existentes)
            self._log(f"Aviso: Colunas não encontradas: {faltantes}", nivel=1)

        taxas_filtrado = self.taxas[colunas_existentes]

        diff_taxas = taxas_filtrado.diff().dropna()
        diff_taxas_norm = (diff_taxas - diff_taxas.mean()).divide(diff_taxas.std())

        correl = diff_taxas_norm.corr()
        U, D, V = self._obter_svd(correl)

        d_prop = D / D.sum()
        self.pca = pd.DataFrame(d_prop * 100, columns=["variação explicada (%)"])
        self.pca["soma acum. (%)"] = np.cumsum(self.pca.iloc[:, 0])
        self.pca.index = ["PC {}".format(i + 1) for i in range(self.pca.shape[0])]
        self.pca = self.pca.head(16)

        if self.num_componentes is None:
            acumulado = self.pca.iloc[:, 1].values
            mask_95 = acumulado >= 95
            if mask_95.any():
                self.num_componentes = int(
                    np.arange(1, len(acumulado) + 1)[mask_95].min()
                )
            else:
                self.num_componentes = 3
                self._log(
                    "Aviso: 95% de variância não atingido. Usando 3 componentes.",
                    nivel=1,
                )

        self._log(f"Número de componentes: {self.num_componentes}", nivel=1)

        self.sigma_t = np.matmul(U, np.diag(np.sqrt(D * self.convencao_dias))) * (
            diff_taxas.std().values
        )
        self.sigma_t = self.sigma_t[:, : self.num_componentes]

        x0_pre = self._chute_inicial(self.sigma_t, 3, 1.0, 0, -1, np.log(0.5))

        def funcao_residuos(x):
            sigma_calc = self._sigma_parametrico(
                x, self.vertices_ano, n_comp=self.num_componentes
            )
            return (sigma_calc - self.sigma_t).ravel()

        self._log("Executando otimização...", nivel=1)
        resultados_otimizacao = optimize.least_squares(
            funcao_residuos, x0=x0_pre, max_nfev=10**4, verbose=0
        )

        if not resultados_otimizacao.success:
            raise RuntimeError("Falha na otimização dos parâmetros HJM")

        x_otimizado = resultados_otimizacao.x

        self.sigma_funcional, self.mu_funcional = self._sigma_parametrico(
            x_otimizado, self.vertices_ano, n_comp=self.num_componentes, retorna_mu=True
        )

        params_obj = ParametrosOtimizacao.de_vetor(x_otimizado, self.num_componentes)
        self._parametros_obj = params_obj
        self.parametros = params_obj.para_dataframe(self.num_componentes)

        self.calibrado = True
        self._data_calibracao = pd.Timestamp.now()

        self._historico.append(
            {
                "acao": "calibracao",
                "data": self._data_calibracao.isoformat(),
                "vertices_dias": vertices_calibracao,
                "n_componentes": self.num_componentes,
            }
        )

        self._log("Calibração concluída com sucesso!", nivel=1)

        return self

    def obter_resultado_calibracao(self) -> ResultadoCalibracao:
        """Retorna objeto completo com resultados"""
        if not self.calibrado:
            raise ValueError("Modelo não foi calibrado ainda")

        return ResultadoCalibracao(
            parametros=self.parametros,
            pca=self.pca,
            num_componentes=self.num_componentes,
            vertices_dias=self.vertices_dias,
            sigma_funcional=self.sigma_funcional,
            mu_funcional=self.mu_funcional,
            sucesso=True,
            data_calibracao=self._data_calibracao,
        )

    def _calcular_choques_interno(
        self,
        choques_observados: np.ndarray,
        vertices_ano: np.ndarray,
        hp: float,
        vertices_saida_ano: Optional[np.ndarray] = None,
        retorna_xi: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """
        MÉTODO INTERNO: Calcula choques usando o modelo calibrado
        """
        if not self.calibrado:
            raise ValueError("Modelo precisa ser calibrado antes de calcular choques")

        assert len(choques_observados) == len(vertices_ano)

        if vertices_saida_ano is None:
            vertices_saida_ano = vertices_ano

        x_param = self._parametros_obj.para_vetor()

        sigma, mu = self._sigma_parametrico(
            x_param, vertices_ano, n_comp=self.num_componentes, retorna_mu=True
        )

        v = choques_observados - hp * mu
        pinv_sigma = linalg.pinv(sigma)
        xi = np.matmul(pinv_sigma, v) / np.sqrt(hp)

        sigma, mu = self._sigma_parametrico(
            x_param, vertices_saida_ano, n_comp=self.num_componentes, retorna_mu=True
        )

        resultado = hp * mu + np.sqrt(hp) * np.matmul(sigma, xi)

        if retorna_xi:
            return resultado, xi

        return resultado

    def aplicar_choques(
        self,
        data_choque: Union[str, datetime.date, pd.Timestamp],
        vertices_choques_dias: List[int],
        hp_dias: int = 10,
        choques_observados: Optional[np.ndarray] = None,
        retornar_detalhes: bool = False,
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Aplica choques na curva de taxas
        """
        if not self.calibrado:
            raise ValueError("Modelo precisa ser calibrado antes de aplicar choques")

        if self.taxas is None:
            raise ValueError("Dados de taxas não disponíveis")

        if not isinstance(self.taxas.index, pd.DatetimeIndex):
            self.taxas.index = pd.to_datetime(self.taxas.index)

        data_choque_ts = self.obter_data_valida(data_choque, self.taxas.index)

        self._log(f"Data do choque ajustada para: {data_choque_ts}", nivel=2)

        try:
            loc1 = self.taxas.index.get_loc(data_choque_ts)
        except KeyError:
            self._log(
                "Data não encontrada exatamente, buscando posição mais próxima...",
                nivel=2,
            )
            index_values = self.taxas.index.to_numpy(dtype="datetime64[ns]")
            data_choque_np = np.datetime64(data_choque_ts.to_datetime64())
            loc1 = np.searchsorted(index_values, data_choque_np)
            if loc1 >= len(self.taxas):
                loc1 = len(self.taxas) - 1
            if loc1 < 0:
                loc1 = 0

        loc2 = loc1 + hp_dias

        if loc2 >= self.taxas.shape[0]:
            raise ValueError(
                f"Data para {hp_dias} dias a frente não encontrada. "
                f"loc1={loc1}, loc2={loc2}, total={self.taxas.shape[0]}"
            )

        if choques_observados is None:
            self._log("Calculando choques observados automaticamente...", nivel=2)
            choques_series = self.taxas.iloc[loc2].values - self.taxas.iloc[loc1].values
            choques_series = pd.Series(choques_series, index=self.taxas.columns)

            colunas_df = self._padronizar_colunas(
                choques_series.index, self.convencao_dias
            )
            choques_series.index = colunas_df

            choques_observados = []
            for v_dias in vertices_choques_dias:
                col_proxima = min(colunas_df, key=lambda x: abs(x - v_dias))
                choques_observados.append(choques_series[col_proxima])
            choques_observados = np.array(choques_observados)

        vertices_choques_ano = self._dias_para_anos(
            vertices_choques_dias, self.convencao_dias
        )
        vertices_saida_ano = self._dias_para_anos(
            self._padronizar_colunas(self.taxas.columns, self.convencao_dias),
            self.convencao_dias,
        )

        choques_modelo = self._calcular_choques_interno(
            choques_observados=choques_observados,
            vertices_ano=vertices_choques_ano,
            hp=hp_dias / self.convencao_dias,
            vertices_saida_ano=vertices_saida_ano,
            retorna_xi=retornar_detalhes,
        )

        if retornar_detalhes:
            choques_modelo, xi = choques_modelo
        else:
            xi = None

        taxa_modelada = choques_modelo + self.taxas.iloc[loc2].values

        resultado = pd.DataFrame(
            {
                f"T0 ({self.taxas.index[loc1].strftime('%Y-%m-%d')})": self.taxas.iloc[
                    loc1
                ].values,
                f"T{hp_dias} ({self.taxas.index[loc2].strftime('%Y-%m-%d')})": self.taxas.iloc[
                    loc2
                ].values,
                f"HJM ({self.taxas.index[loc2].strftime('%Y-%m-%d')})": taxa_modelada,
            },
            index=self.taxas.columns,
        )

        self._historico.append(
            {
                "acao": "aplicacao_choques",
                "data": pd.Timestamp.now().isoformat(),
                "data_choque": str(data_choque_ts.date()),
                "vertices_dias": vertices_choques_dias,
                "hp_dias": hp_dias,
            }
        )

        if retornar_detalhes:
            return {
                "curva": resultado,
                "choques_observados": choques_observados,
                "choques_modelo": choques_modelo,
                "xi": xi,
                "vertices_choques_dias": vertices_choques_dias,
            }

        return resultado

    def para_dict(self) -> Dict[str, Any]:
        """Converte o modelo para dict serializável em JSON"""
        return {
            "versao": self.VERSAO_MODELO,
            "metadata": self._metadata,
            "config": {"convencao_dias": self.convencao_dias, "verbose": self.verbose},
            "estado": {
                "calibrado": self.calibrado,
                "num_componentes": self.num_componentes,
                "vertices_dias": self.vertices_dias,
                "data_calibracao": _timestamp_para_json(self._data_calibracao),
            },
            "parametros": self._parametros_obj.para_dict()
            if self._parametros_obj
            else None,
            "pca": _dataframe_para_json(self.pca) if self.pca is not None else None,
            "sigma_funcional": self.sigma_funcional.tolist()
            if self.sigma_funcional is not None
            else None,
            "mu_funcional": self.mu_funcional.tolist()
            if self.mu_funcional is not None
            else None,
            "historico": self._historico,
        }

    @classmethod
    def de_dict(cls, dct: Dict[str, Any]) -> "ModeloHJM":
        """Cria modelo a partir de dict desserializado"""
        versao_arquivo = dct.get("versao", "1.0.0")
        if versao_arquivo != cls.VERSAO_MODELO:
            print(
                f"Aviso: Versão do arquivo ({versao_arquivo}) difere da versão atual ({cls.VERSAO_MODELO})"
            )

        modelo = cls(
            convencao_dias=dct["config"]["convencao_dias"],
            verbose=dct["config"].get("verbose", 0),
        )

        modelo._metadata = dct.get("metadata", {})
        modelo.calibrado = dct["estado"]["calibrado"]
        modelo.num_componentes = dct["estado"]["num_componentes"]
        modelo.vertices_dias = dct["estado"]["vertices_dias"]
        modelo.vertices_ano = cls._dias_para_anos(
            modelo.vertices_dias, modelo.convencao_dias
        )
        modelo._data_calibracao = _json_para_timestamp(dct["estado"]["data_calibracao"])

        if dct["parametros"] is not None:
            modelo._parametros_obj = ParametrosOtimizacao.de_dict(dct["parametros"])
            modelo.parametros = modelo._parametros_obj.para_dataframe(
                modelo.num_componentes
            )

        if dct["pca"] is not None:
            modelo.pca = _json_para_dataframe(dct["pca"])

        if dct["sigma_funcional"] is not None:
            modelo.sigma_funcional = np.array(dct["sigma_funcional"])

        if dct["mu_funcional"] is not None:
            modelo.mu_funcional = np.array(dct["mu_funcional"])

        modelo._historico = dct.get("historico", [])

        return modelo

    def salvar(self, caminho: Union[str, Path], indent: int = 2) -> None:
        """Salva o modelo calibrado em arquivo JSON"""
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)

        dados = self.para_dict()

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, cls=HJMEncoder, indent=indent, ensure_ascii=False)

        self._log(f"Modelo salvo em {caminho}", nivel=1)

    @classmethod
    def carregar(cls, caminho: Union[str, Path], verbose: int = 0) -> "ModeloHJM":
        """Carrega modelo calibrado de arquivo JSON"""
        caminho = Path(caminho)

        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f, object_hook=_object_hook)

        modelo = cls.de_dict(dados)
        modelo.verbose = verbose

        if verbose >= 1:
            print(f"[HJM] Modelo carregado de {caminho}")
            print(f"[HJM] {modelo}")

        return modelo

    def resumo(self) -> Dict[str, Any]:
        """Resumo rápido do modelo"""
        if not self.calibrado:
            return {"status": "Não calibrado", "convencao_dias": self.convencao_dias}

        variancia_explicada = None
        if self.pca is not None:
            variancia_explicada = float(self.pca.iloc[: self.num_componentes, 0].sum())

        return {
            "status": "Calibrado",
            "vertices_dias": self.vertices_dias,
            "vertices_ano": self.vertices_ano.tolist()
            if self.vertices_ano is not None
            else None,
            "n_componentes": self.num_componentes,
            "convencao_dias": self.convencao_dias,
            "variancia_explicada": variancia_explicada,
            "data_calibracao": _timestamp_para_json(self._data_calibracao),
        }

    def __repr__(self) -> str:
        status = "calibrado" if self.calibrado else "não calibrado"
        n_vertices = len(self.vertices_dias) if self.vertices_dias is not None else 0
        return (
            f"ModeloHJM("
            f"convencao_dias={self.convencao_dias}, "
            f"vertices={n_vertices}, "
            f"n_comp={self.num_componentes}, "
            f"status={status})"
        )

    def __str__(self) -> str:
        return self.__repr__()
