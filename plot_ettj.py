import matplotlib.pyplot as plt; plt.style.use('fivethirtyeight')

def plot(ettj, curva, data):
    ettj_ = ettj.copy()
    data = pd.to_datetime(data).strftime("%d/%m/%Y")
    ettj_ = ettj_[ettj_.Data==data]
    ettj_.index = ettj_[ettj.columns[0]]
    ettj_ = ettj_[[curva]]
    ettj_.plot()
    plt.title('Curva - '+curva)
    plt.xticks(rotation=45)
    plt.xlabel('Maturidade (dias)')
    plt.ylabel('Taxa (%)  ',rotation=0, labelpad=50)
    plt.tight_layout()
    plt.legend('')
    plt.show()

import pandas as pd
ettj = pd.read_excel("C:\\Users\\rrafa\\Desktop\\pyettj\\exemplo\\ettj.xlsx", index_col=0)
curvas = ettj.columns.tolist()[1:]
curva = curvas[2]
data = "2021/05/18"

plot(ettj, curva, data)
