# -*- coding: utf-8 -*-
import pandas as pd # type: ignore

pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_rows',100)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',1000)

def get_table(main_table): #pragma: no cover
    table_names, sub_table_names = [], []
    dados, dados2 = [], []
    tabela = pd.DataFrame()
    for i,row in enumerate(main_table.find_all('td')):
        if "tabelaTitulo" in str(row) and 'rowspan' in str(row):
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif "tabelaTitulo" in str(row) and 'colspan="1"' in str(row):
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif "tabelaTitulo" in str(row) and 'colspan="2"' in str(row):
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif "tabelaItem" in str(row):
            sub_table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))

        elif "tabelaConteudo1" in str(row):
            dados.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            if len(dados)==len(table_names):
                tabela = pd.concat([tabela, pd.DataFrame(dados).T])
                dados = []
        elif "tabelaConteudo2" in str(row):
            dados2.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            if len(dados2)==len(table_names):
                tabela = pd.concat([tabela, pd.DataFrame(dados2).T])
                dados2 = []
      
    table_names_part1 = [table_names[i+1] if table_names[i]=='' else table_names[i] for i in range(len(table_names)-1)]
    table_names_part2 = table_names_part1 + [table_names_part1[-1]]
    
    new_column_names = table_names_part2
    new_sub_table_names = [x+str(i) if sub_table_names.count(x)==2 else x for i,x in enumerate(sub_table_names)]
    colunas = [i + ' ' + j for i, j in zip(new_column_names[1:], new_sub_table_names)]
    colunas = [new_column_names[0]] + colunas
    colunas = [x.split('(')[0].split(')')[0].strip() for x in colunas]
    tabela.columns = colunas
    
    for i, col in enumerate(tabela.columns.tolist()):
        if i==0:
            tabela[col] = tabela[col].astype(int)
        else:
            tabela[col] = pd.to_numeric(tabela[col].str.replace(",","."))
    return tabela