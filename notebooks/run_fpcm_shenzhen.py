#!/usr/bin/env python3
"""
Phase 6 预备：基于深圳市46座污水处理厂实际数据运行 FPCM v3.0
数据来源：深圳市46座污水处理厂2025.10-2026.03能耗药耗统计分析报告

本脚本执行：
  1. 加载实际月度运行数据（46厂汇总 + 重点厂站）
  2. 以 Level 2 模式运行 FPCM（已知：Q_in, E_total, 水质参数用深圳典型值填充）
  3. 输出全市碳排放汇总 + 各月 Scope 1/2/3 拆分
  4. 对7座高能耗重点厂站单独核算
  5. 将结果写入 data/processed/ 目录
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json
import numpy as np

from src.models import FPCM, ModelInput, ModelParams

# ─────────────────────────────────────────────────────────────
# 一、月度汇总数据（46厂，2025.10–2026.03）
# 数据来源：报告表1
# ─────────────────────────────────────────────────────────────
MONTHLY_DATA = [
    # (月份, 处理水量万m³, 用电量kWh, 碳源单耗kg/万m³, 除磷单耗kg/万m³, 脱水单耗kg/万m³)
    ("2025.10", 20105.93, 70_772_071.72, 105.64, 567.46, 79.24),
    ("2025.11", 17505.89, 69_302_847.60, 136.53, 672.38, 92.22),
    ("2025.12", 17670.66, 72_214_101.12, 157.57, 625.08, 103.28),
    ("2026.01", 17181.59, 71_938_674.02, 153.57, 716.17, 130.86),
    ("2026.02", 12534.88, 56_394_030.00, 148.25, 782.81, 159.01),
    ("2026.03", 18301.28, 73_123_542.40, 132.82, 592.74, 111.76),
]

# 深圳典型进出水水质参数（基于广东省污水处理厂设计标准及报告推算）
# COD削减量已知，用于校验
SHENZHEN_WATER_QUALITY = {
    "COD_in": 290.0,      # mg/L（城市生活污水，深圳实测中位数）
    "COD_out": 30.0,      # mg/L（一级A标准）
    "TN_in": 38.0,
    "TN_out": 10.0,
    "NH3N_in": 30.0,
    "NH3N_out": 1.5,
    "TP_in": 4.5,
}

# 月均水温（深圳季节性变化）
MONTHLY_TEMP = {
    "2025.10": 26.0,
    "2025.11": 22.0,
    "2025.12": 17.0,
    "2026.01": 15.0,
    "2026.02": 14.0,
    "2026.03": 18.0,
}

# ─────────────────────────────────────────────────────────────
# 二、重点厂站数据（报告表4）
# ─────────────────────────────────────────────────────────────
KEY_PLANTS = [
    # (名称, 设计规模万m³/d, 半年水量万m³, 吨水电耗kWh/m³, 碳源kg/万m³, 除磷kg/万m³, 工艺)
    ("布吉三期",    10.0,  585.05,  0.978, 284.30, 1246.25, "A²O/AO"),
    ("东涌",         0.3,   10.84,  0.971, 1069.19, 514.76, "A²O/AO"),
    ("罗芳",        40.0, 4109.11,  0.759,    0.00, 952.26, "含MBR"),
    ("滨河",        30.0, 4187.85,  0.694,    0.00,   0.00, "氧化沟"),
    ("埔地吓三期",   5.0,  374.32,  0.656, 349.51, 556.32, "A²O/AO"),
    ("洪湖",         5.0,  709.57,  0.636, 1164.23, 1755.46,"含MBR"),
    ("沙井三期",    20.0,  671.38,  0.603, 309.04, 1083.10, "其他复合"),
]

# ─────────────────────────────────────────────────────────────
# 三、FPCM 运行函数
# ─────────────────────────────────────────────────────────────

def build_monthly_input(month: str, water_vol_wan_m3: float,
                        elec_kwh: float, carbon_dose: float,
                        pac_dose: float) -> ModelInput:
    """
    构建月度 ModelInput（46厂汇总，以等效单厂日平均输入）
    carbon_dose: kg/万m³ → 换算为 PAC_monthly (kg/月)
    """
    # 46厂汇总→等效单月日均流量
    days = 31 if month in ("2025.10", "2025.12", "2026.01", "2026.03") else (
        28 if month == "2026.02" else 30)
    Q_in_m3d = water_vol_wan_m3 * 10000 / days  # m³/d

    # 碳源月总量 (kg/月)
    carbon_monthly = carbon_dose * water_vol_wan_m3  # kg/万m³ × 万m³

    # 除磷药剂月总量 (kg/月)，这里是脱水PAC，当作化学除磷药剂使用
    pac_monthly = pac_dose * water_vol_wan_m3

    return ModelInput(
        Q_in=Q_in_m3d,
        E_total_monthly=elec_kwh,
        T_water=MONTHLY_TEMP[month],
        disposal_method="compost_closed",
        carbon_dose_monthly=carbon_monthly if carbon_dose > 0 else None,
        PAC_monthly=pac_monthly if pac_dose > 0 else None,
        **SHENZHEN_WATER_QUALITY,
    )


def run_plant_analysis(name: str, design_scale_wan: float,
                       half_year_vol_wan: float, unit_elec: float,
                       carbon_unit: float, pac_unit: float,
                       process: str = "") -> dict:
    """对单座厂站运行 FPCM（以6个月代表值）"""
    # 半年均日流量
    Q_in = half_year_vol_wan * 10000 / 183  # m³/d（6个月≈183天）
    E_monthly = Q_in * unit_elec * 30  # kWh/月（估算）

    # 针对不同工艺调整水质参数
    wq = SHENZHEN_WATER_QUALITY.copy()
    if carbon_unit > 500:  # 高碳源单耗→C/N比可能偏低
        wq["COD_in"] = 200.0
        wq["TN_in"] = 45.0

    inp = ModelInput(
        Q_in=Q_in,
        E_total_monthly=E_monthly,
        T_water=19.0,  # 半年均温
        disposal_method="compost_closed",
        PAC_monthly=pac_unit * half_year_vol_wan / 6 if pac_unit > 0 else None,
        carbon_dose_monthly=carbon_unit * half_year_vol_wan / 6 if carbon_unit > 0 else None,
        **wq,
    )

    model = FPCM()
    out = model.run(inp)

    return {
        "name": name,
        "design_scale_wan": design_scale_wan,
        "Q_in_m3d": Q_in,
        "unit_elec_kWh_m3": unit_elec,
        "E_total_CO2eq_t": out.E_total_CO2eq / 1e3,
        "E_unit_kgCO2_m3": out.E_unit_kgCO2_m3,
        "E_Scope1_pct": out.E_Scope1_CO2eq / out.E_total_CO2eq * 100 if out.E_total_CO2eq else 0,
        "E_Scope2_pct": out.E_Scope2_CO2eq / out.E_total_CO2eq * 100 if out.E_total_CO2eq else 0,
        "E_Scope3_pct": out.E_Scope3_CO2eq / out.E_total_CO2eq * 100 if out.E_total_CO2eq else 0,
        "level": out.calculation_level,
    }


# ─────────────────────────────────────────────────────────────
# 四、主分析
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  FPCM v3.0 实际数据验证 — 深圳市46座污水处理厂")
    print("  数据周期：2025.10 – 2026.03（6个月）")
    print("=" * 65)

    model = FPCM()
    monthly_results = []

    print("\n【1】月度汇总碳排放（46厂整体）\n")
    print(f"{'月份':<10} {'水量(万m³)':>12} {'电耗(万kWh)':>12} "
          f"{'Sc1(tCO₂)':>11} {'Sc2(tCO₂)':>11} "
          f"{'Sc3(tCO₂)':>11} {'合计(tCO₂)':>12} "
          f"{'单位(kg/m³)':>12}")
    print("-" * 95)

    total_CO2 = 0.0
    for month, vol, elec, carbon, pac, dewater in MONTHLY_DATA:
        inp = build_monthly_input(month, vol, elec, carbon, pac)
        out = model.run(inp, validate=False)

        # 因模型以"年"为单位，月度结果除以12
        sc1 = out.E_Scope1_CO2eq / 12 / 1e3
        sc2 = out.E_Scope2_CO2eq / 12 / 1e3
        sc3 = out.E_Scope3_CO2eq / 12 / 1e3
        total_t = (sc1 + sc2 + sc3)
        total_CO2 += total_t

        print(f"{month:<10} {vol:>12,.1f} {elec/1e4:>12,.1f} "
              f"{sc1:>11,.1f} {sc2:>11,.1f} "
              f"{sc3:>11,.1f} {total_t:>12,.1f} "
              f"{out.E_unit_kgCO2_m3:>12.4f}")

        monthly_results.append({
            "month": month,
            "water_vol_wan_m3": vol,
            "elec_wan_kwh": elec / 1e4,
            "Scope1_tCO2": round(sc1, 1),
            "Scope2_tCO2": round(sc2, 1),
            "Scope3_tCO2": round(sc3, 1),
            "Total_tCO2": round(total_t, 1),
            "unit_kgCO2_m3": round(out.E_unit_kgCO2_m3, 4),
        })

    print("-" * 95)
    print(f"{'6月合计':<10} {sum(r['water_vol_wan_m3'] for r in monthly_results):>12,.1f} "
          f"{sum(r['elec_wan_kwh'] for r in monthly_results):>12,.1f} "
          f"{'':>11} {'':>11} {'':>11} "
          f"{total_CO2:>12,.1f}")
    avg_unit = total_CO2*1e3 / (sum(r['water_vol_wan_m3'] for r in monthly_results) * 1e4)
    print(f"\n  全周期平均单位碳排放: {avg_unit:.4f} kgCO₂eq/m³")
    print(f"  6个月总碳排放: {total_CO2/1e4:.2f} 万tCO₂eq\n")

    # ── 重点厂站分析 ─────────────────────────────────────────
    print("\n【2】高能耗重点厂站 FPCM 碳排放核算\n")
    print(f"{'厂站名称':<14} {'规模(万m³/d)':>12} {'日均流量':>10} "
          f"{'吨水电耗':>10} {'总碳排(tCO₂/a)':>14} "
          f"{'单位(kg/m³)':>12} {'Sc1%':>7} {'Sc2%':>7} {'Sc3%':>7}")
    print("-" * 100)

    plant_results = []
    for plant_data in KEY_PLANTS:
        res = run_plant_analysis(*plant_data)
        plant_results.append(res)
        print(f"{res['name']:<14} {res['design_scale_wan']:>12.1f} "
              f"{res['Q_in_m3d']:>10,.0f} "
              f"{res['unit_elec_kWh_m3']:>10.3f} "
              f"{res['E_total_CO2eq_t']:>14,.1f} "
              f"{res['E_unit_kgCO2_m3']:>12.4f} "
              f"{res['E_Scope1_pct']:>7.1f} "
              f"{res['E_Scope2_pct']:>7.1f} "
              f"{res['E_Scope3_pct']:>7.1f}")

    # ── 保存结果 ─────────────────────────────────────────────
    os.makedirs("data/processed", exist_ok=True)

    with open("data/processed/fpcm_monthly_46plants.json", "w", encoding="utf-8") as f:
        json.dump(monthly_results, f, ensure_ascii=False, indent=2)

    with open("data/processed/fpcm_key_plants.json", "w", encoding="utf-8") as f:
        json.dump(plant_results, f, ensure_ascii=False, indent=2)

    # CSV 格式输出（便于 Excel 导入）
    with open("data/processed/fpcm_monthly_46plants.csv", "w", encoding="utf-8-sig") as f:
        f.write("月份,处理水量(万m³),用电量(万kWh),Scope1(tCO₂),Scope2(tCO₂),"
                "Scope3(tCO₂),合计(tCO₂),单位碳排(kgCO₂/m³)\n")
        for r in monthly_results:
            f.write(f"{r['month']},{r['water_vol_wan_m3']},{r['elec_wan_kwh']},"
                    f"{r['Scope1_tCO2']},{r['Scope2_tCO2']},{r['Scope3_tCO2']},"
                    f"{r['Total_tCO2']},{r['unit_kgCO2_m3']}\n")

    with open("data/processed/fpcm_key_plants.csv", "w", encoding="utf-8-sig") as f:
        f.write("厂站名称,设计规模(万m³/d),日均流量(m³/d),吨水电耗(kWh/m³),"
                "年碳排放(tCO₂),单位碳排(kgCO₂/m³),Scope1%,Scope2%,Scope3%\n")
        for r in plant_results:
            f.write(f"{r['name']},{r['design_scale_wan']},{r['Q_in_m3d']:.0f},"
                    f"{r['unit_elec_kWh_m3']},{r['E_total_CO2eq_t']:.1f},"
                    f"{r['E_unit_kgCO2_m3']:.4f},{r['E_Scope1_pct']:.1f},"
                    f"{r['E_Scope2_pct']:.1f},{r['E_Scope3_pct']:.1f}\n")

    print("\n\n✅ 结果已保存：")
    print("  data/processed/fpcm_monthly_46plants.csv  （月度汇总，可导入Excel）")
    print("  data/processed/fpcm_key_plants.csv        （重点厂站，可导入Excel）")
    print("  data/processed/fpcm_monthly_46plants.json")
    print("  data/processed/fpcm_key_plants.json\n")

    return monthly_results, plant_results


if __name__ == "__main__":
    main()
