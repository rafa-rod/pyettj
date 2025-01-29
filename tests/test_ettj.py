# -*- coding: utf-8 -*-
import pytest, sys

sys.path.append("./src/pyettj")

from ettj import get_ettj, plot_ettj, listar_dias_uteis
from modelo_ettj import get_ettj_anbima, svensson

data = "27/03/2023"

class TestClass():

    def test_ettj(self):
        self.ettj_dataframe = get_ettj(data)
        self.curvas = self.ettj_dataframe.columns.tolist()[1:]
        self.curva = self.curvas[2] #selic
        return self.ettj_dataframe, self.curva

    def test_listar_dias_uteis(self):
        de = "2021/05/13"
        ate = data
        datas = listar_dias_uteis(de, ate)
        with pytest.raises(Exception) as error4:
            de = 12
            ate = "2021/05/13"
            datas = listar_dias_uteis(de, ate)
        assert str(error4.value) == "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
        with pytest.raises(Exception) as error5:
            de = "13/05/2021"
            ate = 34
            datas = listar_dias_uteis(de, ate)
        assert str(error5.value) == "O parametro data deve ser em formato string, exemplo: '18/05/2021'"

    def test_plot_ettj(self):
        self.ettj_dataframe, self.curva = self.test_ettj()
        plot_ettj(self.ettj_dataframe.drop(self.ettj_dataframe.columns[0],axis=1), self.curva, data)

    def test_raises(self):
        with pytest.raises(Exception) as error1:
            get_ettj(18)
        assert str(error1.value) == "O parametro data deve ser em formato string, exemplo: '18/05/2021'"
        with pytest.raises(Exception) as error2:
            get_ettj("teste")
        assert str(error2.value) == "O parametro data deve ser em formato string, exemplo: '18/05/2021'" 

    def test_svensson(self):
        taxa = svensson(0.13, 0.03, 0.03, 0.03, 1.97, 0.93, 1/252)
        assert round(taxa,2) == 0.16

    def get_ettj_anbima(self):
        data = "28/03/2023"
        parametros_curva, ettj, taxa, erros = get_ettj_anbima(data)
        assert not parametros_curva.empty
        assert not ettj.empty
        assert not taxa.empty
        assert not erros.empty

    def test_ettj2(self):
        data = "15/09/2022"
        curva = "pre"
        ettj_pre = get_ettj(data, curva)
        assert not ettj_pre.empty

TestClass()