import pandas as pd, numpy as np
df = pd.read_csv('gage data.txt', sep='\t')
dims = ['C5','C15','C6','C4','C8','C10_L','C10_R','C11']
for d in dims:
    if d not in df.columns:
        continue
    m = df[d].dropna().astype(float)
    sr = df[df['Dimension']==d].iloc[0]
    utol = float(sr['Upper Tol'])
    ltol = float(sr['Lower Tol'])
    avg = m.mean()
    std = m.std()
    usl = avg + utol
    lsl = avg + ltol
    data_span = m.max() - m.min()
    tol_span = usl - lsl
    ratio = tol_span / data_span if data_span > 0 else 0
    print(f"{d}: avg={avg:.8f} std={std:.2e} utol={utol} ltol={ltol}")
    print(f"   usl={usl:.8f} lsl={lsl:.8f} tol_span={tol_span:.6f} data_span={data_span:.2e} ratio={ratio:.1f}")
