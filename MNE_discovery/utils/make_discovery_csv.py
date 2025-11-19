import pandas as pd


def finrep_discovery_csv (data, df_finrep, df_others, path):
    # --- FIN_REP ---
    df = df_finrep [['ID', 'NAME', 'LINK', 'REFYEAR']].copy()
    df ['TYPE'] = 'FIN_REP'
    df.rename(columns = {'LINK': 'SRC'}, inplace = True)
    df = df [['ID', 'NAME', 'TYPE', 'SRC', 'REFYEAR']]

    # FIN_REP update
    for _, row in df.iterrows():
        mask = (data ['ID'] == row ['ID']) & (data ['TYPE'] == 'FIN_REP')
        data.loc [mask, 'SRC'] = row ['SRC']
        if pd.notna(row ['REFYEAR']):
            data.loc [mask, 'REFYEAR'] = row ['REFYEAR']

    # --- OTHERS ---
    df_others = df_others [['ID', 'NAME', 'LINK', 'REFYEAR']].drop_duplicates().copy()
    df_others.rename(columns = {'LINK': 'SRC'}, inplace = True)

    for (id_val, name), group in df_others.groupby(['ID', 'NAME']):
        links = group [['SRC', 'REFYEAR']].drop_duplicates().values.tolist()
        mask = (data ['ID'] == id_val) & (data ['TYPE'] == 'OTHER')
        rows_to_update = data [mask].head(6).index

        for i, idx in enumerate(rows_to_update):
            if i < len(links):
                src_val, refyear_val = links [i]
                data.at [idx, 'SRC'] = src_val
                if pd.notna(refyear_val):
                    data.at [idx, 'REFYEAR'] = refyear_val
            else:
                # remaining others empty
                data.at [idx, 'SRC'] = ''
                data.at [idx, 'REFYEAR'] = pd.NA

    # Update the REFYEAR column to Int64 type (integer supporting NaN values).
    data ['REFYEAR'] = data ['REFYEAR'].astype('Int64')

    # final csv output
    data.to_csv(path, sep = ';', index = False)
    print("Updated and Saved: ", path)
