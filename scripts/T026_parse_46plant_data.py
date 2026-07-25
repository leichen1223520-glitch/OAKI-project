#!/usr/bin/env python3
"""T026: Parse 46-plant monthly panel data - corrected version"""
import xlrd, pandas as pd, numpy as np, hashlib, os

RAW_XLS = 'data/raw/02-11 2026年数据汇总（污水厂）(更新到6月）.xls'
OUT_DIR = 'data/processed'; os.makedirs(OUT_DIR, exist_ok=True)

def plant_hash(name):
    return 'plt_' + hashlib.sha256(name.encode()).hexdigest()[:8]

wb = xlrd.open_workbook(RAW_XLS)

MONTHS_12 = [f'{m}月' for m in range(1,13)]

def parse_sheet(wb, sname, has_design_cap=False):
    sh = wb.sheet_by_name(sname)
    header = sh.row_values(1)
    # Find FIRST occurrence of each month column (skip duplicates / 水量 section)
    month_col_idx = {}
    for i, v in enumerate(header):
        sv = str(v).strip()
        if sv in MONTHS_12 and sv not in month_col_idx:
            month_col_idx[sv] = i  # first occurrence only

    records = []
    for r in range(2, sh.nrows):
        row = sh.row_values(r)
        if not row[0]: continue
        try: seq = int(float(row[0]))
        except: continue
        name = str(row[3]).strip()
        design = None
        if has_design_cap:
            try:
                v = float(row[4])
                if 0.1 < v < 500: design = v
            except: pass
        rec = {'seq':seq, 'plant_id':plant_hash(name), 'plant_alias':f'P{seq:03d}', 'design_cap_wan_m3d':design}
        for mname, ci in month_col_idx.items():
            try:
                val = float(row[ci])
                if val == 0 and mname in ['7月','8月','9月','10月','11月','12月']:
                    val = np.nan  # Future months = NaN
            except: val = np.nan
            rec[mname] = val
        records.append(rec)
    return pd.DataFrame(records)

sheet_map = {
    '处理量': ('Q_wan_m3', True),
    'COD进水':('COD_in_mgL', False), 'TN进水':('TN_in_mgL',False),
    'TP进水': ('TP_in_mgL', False),  'AD进水':('NH4_in_mgL',False), 'SS进水':('SS_in_mgL',False),
    'COD出水':('COD_out_mgL',False), 'TN出水':('TN_out_mgL',False),
    'TP出水': ('TP_out_mgL',False),  'AD出水':('NH4_out_mgL',False),'SS出水':('SS_out_mgL',False),
}

base = None
for sname,(vname,has_cap) in sheet_map.items():
    df = parse_sheet(wb, sname, has_cap)
    id_cols = ['seq','plant_id','plant_alias','design_cap_wan_m3d']
    mcols = [c for c in MONTHS_12 if c in df.columns]
    dl = df[id_cols+mcols].melt(id_vars=id_cols, var_name='month', value_name=vname)
    if base is None: base = dl
    else: base = base.merge(dl[['plant_id','month',vname]], on=['plant_id','month'], how='left')
    print(f"{sname}: {df['plant_id'].nunique()} plants -> {vname}: {dl[vname].notna().sum()} valid")

# Clean
base['month_num'] = base['month'].str.replace('月','').astype(float).astype(int)
base['year'] = 2026
base['data_source'] = '[真实活动数据]'
base['note'] = '浓度数据(mg/L)+水量(万m³/月)，无GHG直接测量'
base = base[base['month_num'].between(1,6)].copy()  # Jan-Jun 2026 (valid data)
base = base.sort_values(['seq','month_num']).reset_index(drop=True)
base['data_complete'] = base[['Q_wan_m3','COD_in_mgL','TN_in_mgL','NH4_in_mgL']].notna().all(axis=1)

print(f"\nFinal: {len(base)} rows, {base.plant_id.nunique()} plants, {base['data_complete'].sum()} complete rows")
print(base[['plant_alias','month','Q_wan_m3','COD_in_mgL','TN_in_mgL','NH4_in_mgL','COD_out_mgL','TN_out_mgL']].head(8).to_string())

# Numeric stats
numeric_cols = [c for c in base.columns if base[c].dtype in [float, 'float64']]
stats = base[numeric_cols].describe()
print("\nStats:\n", stats[['Q_wan_m3','COD_in_mgL','TN_in_mgL','NH4_in_mgL','COD_out_mgL','TN_out_mgL']].to_string())

base.to_csv(f'{OUT_DIR}/panel_46plants_2026_v1.csv', index=False)
base.to_parquet(f'{OUT_DIR}/panel_46plants_2026_v1.parquet', index=False)
print(f"\nSaved to {OUT_DIR}/")
