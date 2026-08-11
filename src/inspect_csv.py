import pandas as pd
for f in ['curvas_rendimiento.csv','metricas_rendimiento.csv']:
    print('\nFILE', f)
    df = pd.read_csv(f)
    print(df.head().to_string(index=False))
    print('columns=', list(df.columns))
    print('shape=', df.shape)
