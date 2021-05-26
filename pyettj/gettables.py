# -*- coding: utf-8 -*-
import pandas as pd # type: ignore

pd.set_option('display.float_format', lambda x: '%.5f' % x)
pd.set_option('display.max_rows',100)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',1000)

def get_fourth_table(main_table):
    count=0
    dias_corridos, iene, spread_libor_eur_usd, libor = [], [], [], []
    table_names, sub_table_names = [], []
    for i,row in enumerate(main_table.find_all('td')):
        if i <= 3:
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif i >= 4 and i <= 6:
             sub_table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        else:     
            count+=1
            if count==1: dias_corridos.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==2: iene.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==3: spread_libor_eur_usd.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==4: 
                libor.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
                count=0
            
    all_data = [dias_corridos, iene, spread_libor_eur_usd, libor]
    final_table = pd.DataFrame(columns=table_names)
    for i, col in enumerate(final_table.columns.tolist()):
        if i==0:
            final_table[col] = all_data[i]
            final_table[col] = final_table[col].astype(int)
        else:
            final_table[col] = all_data[i]
            final_table[col] = pd.to_numeric(final_table[col].str.replace(",","."))
    return final_table

def get_third_table(main_table):
    count=0
    dias_corridos, usd, ibrx50 = [], [], []
    ibov, taxa_di_igpm, taxa_di_ipca = [], [], []
    taxa_ajuste_pre_252, taxa_ajuste_pre_360, taxa_ajuste_cupom = [], [], []
    table_names, sub_table_names = [], []
    for i,row in enumerate(main_table.find_all('td')):
        if i <= 7:
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif i >= 8 and i <= 15:
             sub_table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        else:     
            count+=1
            if count==1: dias_corridos.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==2: usd.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==3: ibrx50.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==4: ibov.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==5: taxa_di_igpm.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==6: taxa_di_ipca.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==7: taxa_ajuste_pre_252.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==8: taxa_ajuste_pre_360.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==9: 
                taxa_ajuste_cupom.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
                count=0
                
    new_cols, i = [table_names[0]], 0
    for col in table_names[1:]:
        if 'ajuste pré' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        else:
            new_cols.append( col+' '+sub_table_names[i])
            i+=1
            
    all_data = [dias_corridos, usd, ibrx50, ibov, taxa_di_igpm,
                taxa_di_ipca, taxa_ajuste_pre_252, taxa_ajuste_pre_360, taxa_ajuste_cupom]
    final_table = pd.DataFrame(columns=new_cols)
    for i, col in enumerate(final_table.columns.tolist()):
        if i==0:
            final_table[col] = all_data[i]
            final_table[col] = final_table[col].astype(int)
        else:
            final_table[col] = all_data[i]
            final_table[col] = pd.to_numeric(final_table[col].str.replace(",","."))
    return final_table

def get_second_table(main_table):
    count=0
    dias_corridos, taxa_di_eur, taxa_252_tbf_pre = [], [], []
    taxa_360_tbf_pre, taxa_252_tr_pre, taxa_360_tr_pre = [], [], []
    taxa_dolar_di, taxa_cupom_cambial, taxa_cupom_limpo = [], [], []
    table_names, sub_table_names = [], []
    for i,row in enumerate(main_table.find_all('td')):
        if i <= 6:
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif i >= 7 and i <= 14:
             sub_table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        else:     
            count+=1
            if count==1: dias_corridos.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==2: taxa_di_eur.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==3: taxa_252_tbf_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==4: taxa_360_tbf_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==5: taxa_252_tr_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==6: taxa_360_tr_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==7: taxa_dolar_di.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==8: taxa_cupom_cambial.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==9: 
                taxa_cupom_limpo.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
                count=0
                
    new_cols, i = [table_names[0]], 0
    for col in table_names[1:]:
        if 'eur' in col.lower(): new_cols.append( col+' '+sub_table_names[i])
        elif 'tbf' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        elif 'tr' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        else:
            i+=1
            new_cols.append( col+' '+sub_table_names[i])
            
    all_data = [dias_corridos, taxa_di_eur, taxa_252_tbf_pre, taxa_360_tbf_pre, taxa_252_tr_pre,
                taxa_360_tr_pre, taxa_dolar_di, taxa_cupom_cambial, taxa_cupom_limpo]
    final_table = pd.DataFrame(columns=new_cols)
    for i, col in enumerate(final_table.columns.tolist()):
        if i==0:
            final_table[col] = all_data[i]
            final_table[col] = final_table[col].astype(int)
        else:
            final_table[col] = all_data[i]
            final_table[col] = pd.to_numeric(final_table[col].str.replace(",","."))
    return final_table

def get_first_table(main_table):
    count=0
    dias_corridos, taxa_252_pre_di, taxa_360_pre_di = [], [], []
    taxa_selic_pre, taxa_252_di_tr, taxa_360_di_tr = [], [], []
    taxa_252_dolar_pre, taxa_360_dolar_pre, eur = [], [], []
    table_names, sub_table_names = [], []
    for i,row in enumerate(main_table.find_all('td')):
        if i <= 5:
            table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        elif i >= 6 and i <= 13:
             sub_table_names.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
        else:     
            count+=1
            if count==1: dias_corridos.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==2: taxa_252_pre_di.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==3: taxa_360_pre_di.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==4: taxa_selic_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==5: taxa_252_di_tr.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==6: taxa_360_di_tr.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==7: taxa_252_dolar_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==8: taxa_360_dolar_pre.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
            elif count==9: 
                eur.append(row.text.strip().replace('\r',' ').replace('\n',' ').replace('  ',' '))
                count=0

    new_cols, i = [table_names[0]], 0
    for col in table_names[1:]:
        if 'di x pré' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        elif 'selic' in col.lower(): new_cols.append( col+' '+sub_table_names[i])
        elif 'tr' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        elif 'dólar' in col.lower():
            new_cols.append( col+' '+sub_table_names[i])
            new_cols.append( col+' '+sub_table_names[i+1])
            i+=2
        else:
            i+=1
            new_cols.append( col+' '+sub_table_names[i])
            
    all_data = [dias_corridos, taxa_252_pre_di, taxa_360_pre_di, taxa_selic_pre, taxa_252_di_tr,
                taxa_360_di_tr, taxa_252_dolar_pre, taxa_360_dolar_pre, eur]
    final_table = pd.DataFrame(columns=new_cols)
    for i, col in enumerate(final_table.columns.tolist()):
        if i==0:
            final_table[col] = all_data[i]
            final_table[col] = final_table[col].astype(int)
        else:
            final_table[col] = all_data[i]
            final_table[col] = pd.to_numeric(final_table[col].str.replace(",","."))
    return final_table