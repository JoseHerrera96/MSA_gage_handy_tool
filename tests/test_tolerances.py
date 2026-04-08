import pandas as pd
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
    tol_range = utol - ltol
    usl = avg + tol_range * 0.1
    lsl = avg - tol_range * 0.1
    print(f"{d}: avg={avg:.8f}  utol={utol}  ltol={ltol}")
    print(f"   tol_range={tol_range:.6f}  10%={tol_range*0.1:.8f}")
    print(f"   USL line = avg+10% = {usl:.8f}")
    print(f"   LSL line = avg-10% = {lsl:.8f}")
    print(f"   data range: {m.min():.8f} - {m.max():.8f}")
    print(f"   gap USL-datamax = {usl - m.max():.8f}")
    print(f"   gap datamin-LSL = {m.min() - lsl:.8f}")
    print()
