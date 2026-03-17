# -*- coding: utf-8 -*-
"""
Testes para o módulo HJM (Heath-Jarrow-Morton)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ajustar path para imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "pyettj"))

from pyettj.HJM import ModeloHJM, ParametrosOtimizacao

# ============================================================================
# FIXTURES (Dados de teste reutilizáveis)
# ============================================================================


@pytest.fixture
def dados_taxas_simulados():
    """
    Gera DataFrame de taxas simuladas para testes
    """
    np.random.seed(42)
    datas = pd.date_range(start="2023-01-01", periods=500, freq="B")
    vertices = [21, 42, 63, 126, 252, 504, 756, 1260]

    taxas = pd.DataFrame(
        np.random.randn(len(datas), len(vertices)) * 0.01 + 0.10,
        index=datas,
        columns=[v for v in vertices],
    )
    return taxas


@pytest.fixture
def modelo_calibrado(dados_taxas_simulados):
    """
    Cria e calibra um modelo HJM para testes
    """
    modelo = ModeloHJM(convencao_dias=252, verbose=0)
    vertices_calibracao = [21, 63, 126, 252]
    modelo.calibrar(dados_taxas_simulados, vertices_calibracao)
    return modelo


# ============================================================================
# TESTES DE INICIALIZAÇÃO
# ============================================================================


class TestInicializacao:
    """Testes para inicialização do ModeloHJM"""

    def test_criar_modelo_padrao(self):
        """Testa criação com parâmetros padrão"""
        modelo = ModeloHJM()
        assert modelo.convencao_dias == 252
        assert modelo.verbose == 0
        assert modelo.calibrado is False

    def test_criar_modelo_customizado(self):
        """Testa criação com parâmetros customizados"""
        modelo = ModeloHJM(convencao_dias=253, verbose=1)
        assert modelo.convencao_dias == 253
        assert modelo.verbose == 1

    def test_modelo_nao_calibrado(self):
        """Testa que modelo recém-criado não está calibrado"""
        modelo = ModeloHJM()
        assert modelo.calibrado is False
        assert modelo.parametros is None
        assert modelo.pca is None


# ============================================================================
# TESTES DE CALIBRAÇÃO
# ============================================================================


class TestCalibracao:
    """Testes para calibração do modelo"""

    def test_calibrar_sucesso(self, dados_taxas_simulados):
        """Testa calibração bem-sucedida"""
        modelo = ModeloHJM(convencao_dias=252, verbose=0)
        vertices = [21, 63, 126, 252]

        resultado = modelo.calibrar(dados_taxas_simulados, vertices)

        assert modelo.calibrado is True
        assert modelo.parametros is not None
        assert modelo.pca is not None
        assert resultado is modelo  # method chaining

    def test_calibrar_vertices_dias(self, dados_taxas_simulados):
        """Testa que vértices são armazenados em dias"""
        modelo = ModeloHJM(convencao_dias=252)
        vertices = [21, 63, 126, 252]
        modelo.calibrar(dados_taxas_simulados, vertices)

        assert modelo.vertices_dias == vertices
        assert modelo.vertices_ano is not None
        assert len(modelo.vertices_ano) == len(vertices)

    def test_calibrar_vertices_convertidos(self, dados_taxas_simulados):
        """Testa conversão de dias para anos"""
        modelo = ModeloHJM(convencao_dias=252)
        vertices = [21, 63, 126, 252]
        modelo.calibrar(dados_taxas_simulados, vertices)

        esperado_ano = np.array(vertices) / 252
        assert np.allclose(modelo.vertices_ano, esperado_ano)

    def test_calibrar_parametros_shape(self, dados_taxas_simulados):
        """Testa shape dos parâmetros calibrados"""
        modelo = ModeloHJM(convencao_dias=252)
        vertices = [21, 63, 126, 252]
        modelo.calibrar(dados_taxas_simulados, vertices)

        assert modelo.parametros.shape[0] == 4  # alpha, beta, gamma, delta
        assert modelo.parametros.shape[1] == modelo.num_componentes

    def test_calibrar_pca_variancia(self, dados_taxas_simulados):
        """Testa que PCA tem variância explicada"""
        modelo = ModeloHJM(convencao_dias=252)
        vertices = [21, 63, 126, 252]
        modelo.calibrar(dados_taxas_simulados, vertices)

        assert "variação explicada (%)" in modelo.pca.columns
        assert "soma acum. (%)" in modelo.pca.columns
        assert modelo.pca["soma acum. (%)"].iloc[-1] > 90  # Pelo menos 90%

    def test_calibrar_sem_colunas(self, dados_taxas_simulados):
        """Testa erro quando colunas não existem"""
        modelo = ModeloHJM(convencao_dias=252)
        vertices = [9999, 8888]  # Colunas que não existem

        with pytest.raises(ValueError) as excinfo:
            modelo.calibrar(dados_taxas_simulados, vertices)

        assert "Nenhuma coluna de vértice encontrada" in str(excinfo.value)


# ============================================================================
# TESTES DE APLICAÇÃO DE CHOQUES
# ============================================================================


class TestAplicarChoques:
    """Testes para aplicação de choques"""

    def test_aplicar_choques_sucesso(self, modelo_calibrado):
        """Testa aplicação de choques bem-sucedida"""
        resultado = modelo_calibrado.aplicar_choques(
            data_choque="2023-01-01", vertices_choques_dias=[21, 63, 126], hp_dias=10
        )

        assert isinstance(resultado, pd.DataFrame)
        assert not resultado.empty
        assert len(resultado.columns) == 3  # T0, T+HP, HJM

    def test_aplicar_choques_modelo_nao_calibrado(self, dados_taxas_simulados):
        """Testa erro ao aplicar choques sem calibrar"""
        modelo = ModeloHJM(convencao_dias=252)

        with pytest.raises(ValueError) as excinfo:
            modelo.aplicar_choques(
                data_choque="2023-01-01", vertices_choques_dias=[21, 63, 126]
            )

        assert "calibrado" in str(excinfo.value).lower()

    def test_aplicar_choques_retornar_detalhes(self, modelo_calibrado):
        """Testa aplicação de choques com detalhes"""
        resultado = modelo_calibrado.aplicar_choques(
            data_choque="2023-01-01",
            vertices_choques_dias=[21, 63, 126],
            hp_dias=10,
            retornar_detalhes=True,
        )

        assert isinstance(resultado, dict)
        assert "curva" in resultado
        assert "choques_observados" in resultado
        assert "choques_modelo" in resultado
        assert "xi" in resultado

    def test_aplicar_choques_vertices_dias(self, modelo_calibrado):
        """Testa que vértices são passados em dias"""
        resultado = modelo_calibrado.aplicar_choques(
            data_choque="2023-01-01", vertices_choques_dias=[21, 63, 126], hp_dias=10
        )

        assert len(resultado) == len(modelo_calibrado.taxas.columns)


# ============================================================================
# TESTES DE SERIALIZAÇÃO JSON
# ============================================================================


class TestSerializacao:
    """Testes para salvar/carregar modelo"""

    def test_salvar_e_carregar(self, modelo_calibrado, tmp_path):
        """Testa salvar e carregar modelo"""
        caminho = tmp_path / "modelo_teste.json"

        # Salvar
        modelo_calibrado.salvar(caminho)
        assert caminho.exists()

        # Carregar
        modelo_carregado = ModeloHJM.carregar(caminho, verbose=0)

        # Verificar integridade
        assert modelo_carregado.calibrado == modelo_calibrado.calibrado
        assert modelo_carregado.convencao_dias == modelo_calibrado.convencao_dias
        assert modelo_carregado.num_componentes == modelo_calibrado.num_componentes
        assert np.allclose(
            modelo_carregado.parametros.values, modelo_calibrado.parametros.values
        )

    def test_resumo(self, modelo_calibrado):
        """Testa método de resumo"""
        resumo = modelo_calibrado.resumo()

        assert isinstance(resumo, dict)
        assert resumo["status"] == "Calibrado"
        assert "vertices_dias" in resumo
        assert "variancia_explicada" in resumo
        assert "n_componentes" in resumo


# ============================================================================
# TESTES DE CLASSES AUXILIARES
# ============================================================================


class TestClassesAuxiliares:
    """Testes para classes auxiliares"""

    def test_parametros_otimizacao_vetor(self):
        """Testa conversão para vetor"""
        params = ParametrosOtimizacao(
            alpha=np.array([0.1, 0.2]),
            beta=np.array([0.3, 0.4]),
            gamma=np.array([0.5, 0.6]),
            delta=np.array([0.7, 0.8]),
        )

        vetor = params.para_vetor()
        assert len(vetor) == 8  # 4 parâmetros × 2 componentes

    def test_parametros_otimizacao_de_vetor(self):
        """Testa criação a partir de vetor"""
        vetor = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
        params = ParametrosOtimizacao.de_vetor(vetor, n_comp=2)

        assert len(params.alpha) == 2
        assert len(params.beta) == 2
        assert len(params.gamma) == 2
        assert len(params.delta) == 2

    def test_parametros_otimizacao_validacao(self):
        """Testa validação de tamanhos iguais"""
        with pytest.raises(AssertionError):
            ParametrosOtimizacao(
                alpha=np.array([0.1, 0.2]),
                beta=np.array([0.3]),  # Tamanho diferente
                gamma=np.array([0.5, 0.6]),
                delta=np.array([0.7, 0.8]),
            )

    def test_resultado_calibracao_variancia(self, modelo_calibrado):
        """Testa propriedade variancia_explicada"""
        resultado = modelo_calibrado.obter_resultado_calibracao()

        assert isinstance(resultado.variancia_explicada, float)
        assert resultado.variancia_explicada > 0
        assert resultado.variancia_explicada <= 100


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Testes para casos extremos"""

    def test_hp_dias_grande(self, modelo_calibrado):
        """Testa holding period muito grande"""
        with pytest.raises(ValueError) as excinfo:
            modelo_calibrado.aplicar_choques(
                data_choque="2023-01-01",
                vertices_choques_dias=[21, 63, 126],
                hp_dias=1000,  # Muito grande
            )

        assert "dias a frente não encontrada" in str(excinfo.value)

    def test_vertices_vazios(self, dados_taxas_simulados):
        """Testa calibração com vértices vazios"""
        modelo = ModeloHJM(convencao_dias=252)

        with pytest.raises(ValueError):
            modelo.calibrar(dados_taxas_simulados, [])


# ============================================================================
# TESTE DE INTEGRAÇÃO
# ============================================================================


class TestIntegracao:
    """Testes de integração completa"""

    def test_fluxo_completo(self, dados_taxas_simulados, tmp_path):
        """Testa fluxo completo: calibrar → salvar → carregar → aplicar choques"""
        # 1. Criar e calibrar
        modelo1 = ModeloHJM(convencao_dias=252, verbose=0)
        modelo1.calibrar(dados_taxas_simulados, [21, 63, 126, 252])

        # 2. Salvar
        caminho = tmp_path / "modelo_completo.json"
        modelo1.salvar(caminho)

        # 3. Carregar
        modelo2 = ModeloHJM.carregar(caminho, verbose=0)
        modelo2.taxas = dados_taxas_simulados

        # 4. Aplicar choques
        resultado1 = modelo1.aplicar_choques(
            data_choque="2023-01-01", vertices_choques_dias=[21, 63, 126], hp_dias=10
        )

        resultado2 = modelo2.aplicar_choques(
            data_choque="2023-01-01", vertices_choques_dias=[21, 63, 126], hp_dias=10
        )

        # 5. Verificar que resultados são iguais
        pd.testing.assert_frame_equal(resultado1, resultado2)
