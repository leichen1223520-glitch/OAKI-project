#!/usr/bin/env python3
"""
扩展分析脚本：将深圳46厂数据从 2025.10–2026.03 延伸至 2026.06

使用前提：
  需要在 data/raw/ 目录中放入包含 2026.04–2026.06 月度数据的文件
  （参考现有文件格式：深圳市46座污水处理厂...能耗药耗统计.docx）

使用步骤：
  1. 将新数据文件（xlsx 或 docx）放入 data/raw/
  2. 从文件中读取 2026.04、2026.05、2026.06 的月度指标，填入下方 APRIL_JUNE_DATA
  3. 运行：PYTHONPATH=/path/to/project python3 notebooks/extend_to_june_2026.py

输出：
  - data/processed/fpcm_monthly_9months.csv/json（9个月完整数据）
  - data/processed/fpcm_9months_trend.csv（季节性趋势分析）
  - 终端打印对比分析报告
"""

import sys
import os
import json
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import FPCM, ModelInput, ModelParams

# ─────────────────────────────────────────────────────────────────────────────
# 广东省电网排放因子
# ─────────────────────────────────────────────────────────────────────────────
EF_GRID_GUANGDONG = 0.5271  # kgCO₂/kWh

# ─────────────────────────────────────────────────────────────────────────────
# 现有 6 个月数据（2025.10–2026.03）
# 来源：深圳市46座污水处理厂2025.10-2026.03能耗药耗统计报告 Table 1
# ─────────────────────────────────────────────────────────────────────────────
EXISTING_6MONTHS = [
    # (月份, 处理水量万m³, 用电量kWh, 碳源单耗kg/万m³, 除磷单耗kg/万m³, 脱水单耗kg/万m³)
    ("2025.10", 20105.93, 70_772_071.72, 105.64, 567.46, 79.24),
    ("2025.11", 17505.89, 69_302_847.60, 136.53, 672.38, 92.22),
    ("2025.12", 17670.66, 72_214_101.12, 157.57, 625.08, 103.28),
    ("2026.01", 17181.59, 71_938_674.02, 153.57, 716.17, 130.86),
    ("2026.02", 12534.88, 56_394_030.00, 148.25, 782.81, 159.01),
    ("2026.03", 18301.28, 73_123_542.40, 132.82, 592.74, 111.76),
]

# ─────────────────────────────────────────────────────────────────────────────
# ！！！需要填入的新数据（2026.04–2026.06）！！！
# 请从"2026年数据汇总（污水厂）(更新到6月）"文件中读取并填入以下数据
# 数据格式与 EXISTING_6MONTHS 完全相同
# ─────────────────────────────────────────────────────────────────────────────
APRIL_JUNE_DATA = [
    # 请用实际数据替换以下占位符（None 表示未填）
    # ("2026.04", 水量万m³, 用电量kWh, 碳源kg/万m³, 除磷kg/万m³, 脱水kg/万m³),
    # ("2026.05", ...),
    # ("2026.06", ...),
    # 示例格式（仅供参考，使用前删除以下三行并替换为实际数据）：
    # ("2026.04", 19500.00, 72_000_000.00, 115.00, 580.00, 88.00),
    # ("2026.05", 20000.00, 73_000_000.00, 108.00, 560.00, 82.00),
    # ("2026.06", 21000.00, 75_000_000.00, 100.00, 540.00, 78.00),
]

# ─────────────────────────────────────────────────────────────────────────────
# 月度温度（深圳典型水温，°C）
# ─────────────────────────────────────────────────────────────────────────────
MONTHLY_TEMP = {
    "2025.10": 26.0,
    "2025.11": 22.0,
    "2025.12": 17.0,
    "2026.01": 15.0,
    "2026.02": 14.0,
    "2026.03": 18.0,
    "2026.04": 22.0,  # 春季升温
    "2026.05": 25.0,  # 初夏
    "2026.06": 27.0,  # 梅雨季，水温升高
}

# 各月天数
DAYS_MAP = {
    "2025.10": 31, "2025.11": 30, "2025.12": 31,
    "2026.01": 31, "2026.02": 28, "2026.03": 31,
    "2026.04": 30, "2026.05": 31, "2026.06": 30,
}

# 深圳典型水质参数（Level 2：典型值代入）
SHENZHEN_WATER_QUALITY = {
    "COD_in": 290.0, "COD_out": 30.0,
    "TN_in": 38.0, "TN_out": 10.0,
    "NH3N_in": 30.0, "NH3N_out": 1.5,
    "TP_in": 4.5,
}


def build_monthly_input(month: str, water_vol_wan_m3: float,
                        elec_kwh: float, carbon_dose: float,
                        pac_dose: float) -> ModelInput:
    days = DAYS_MAP[month]
    Q_in = water_vol_wan_m3 * 10000 / days
    return ModelInput(
        Q_in=Q_in,
        E_total_monthly=elec_kwh,
        T_water=MONTHLY_TEMP[month],
        disposal_method="compost_closed",
        carbon_dose_monthly=carbon_dose * water_vol_wan_m3 if carbon_dose > 0 else None,
        PAC_monthly=pac_dose * water_vol_wan_m3 if pac_dose > 0 else None,
        **SHENZHEN_WATER_QUALITY,
    )


def run_fpcm_for_months(monthly_data: list, params) -> list:
    """对给定月份列表运行 FPCM，返回结果列表"""
    model = FPCM(params=params)
    results = []
    for month, vol, elec, carbon, pac, dewater in monthly_data:
        inp = build_monthly_input(month, vol, elec, carbon, pac)
        out = model.run(inp, validate=False)
        sc1 = out.E_Scope1_CO2eq / 12 / 1e3
        sc2 = out.E_Scope2_CO2eq / 12 / 1e3
        sc3 = out.E_Scope3_CO2eq / 12 / 1e3
        results.append({
            "month": month,
            "water_vol_wan_m3": vol,
            "elec_wan_kwh": elec / 1e4,
            "Scope1_tCO2": round(sc1, 1),
            "Scope2_tCO2": round(sc2, 1),
            "Scope3_tCO2": round(sc3, 1),
            "Total_tCO2": round(sc1 + sc2 + sc3, 1),
            "unit_kgCO2_m3": round(out.E_unit_kgCO2_m3, 4),
        })
    return results


def compare_6vs9_months(results_6: list, results_9: list):
    """比较6个月与9个月数据，识别新发现"""
    print("\n" + "=" * 70)
    print("  扩展分析：新增3个月（2026.04-06）带来的新发现")
    print("=" * 70)

    total_6 = sum(r["Total_tCO2"] for r in results_6)
    total_9 = sum(r["Total_tCO2"] for r in results_9)
    new_3months = sum(r["Total_tCO2"] for r in results_9[6:])

    print(f"\n原6个月总碳排放: {total_6:,.0f} tCO₂ ({total_6/10000:.2f} 万tCO₂)")
    print(f"新增3个月总碳排放: {new_3months:,.0f} tCO₂ ({new_3months/10000:.2f} 万tCO₂)")
    print(f"9个月总碳排放: {total_9:,.0f} tCO₂ ({total_9/10000:.2f} 万tCO₂)")

    # 季节性分析
    print("\n季节性规律（扩展后可见完整秋冬春夏周期）：")
    seasons = {
        "秋季(10-11月)": [r for r in results_9 if r["month"] in ("2025.10", "2025.11")],
        "冬季(12-2月)": [r for r in results_9 if r["month"] in ("2025.12", "2026.01", "2026.02")],
        "春季(3-5月)": [r for r in results_9 if r["month"] in ("2026.03", "2026.04", "2026.05")],
        "初夏(6月)": [r for r in results_9 if r["month"] in ("2026.06",)],
    }
    for season, months in seasons.items():
        if months:
            avg_unit = sum(r["unit_kgCO2_m3"] for r in months) / len(months)
            avg_total = sum(r["Total_tCO2"] for r in months) / len(months)
            print(f"  {season}: 月均碳排 {avg_total:,.0f} tCO₂, 单位 {avg_unit:.4f} kgCO₂/m³")

    # 单位碳排放趋势
    print("\n月度单位碳排放趋势（完整9个月）：")
    for r in results_9:
        bar = "█" * int(r["unit_kgCO2_m3"] * 20)
        print(f"  {r['month']}: {r['unit_kgCO2_m3']:.4f} kgCO₂/m³  {bar}")


def main():
    # 检查是否有新数据
    if not APRIL_JUNE_DATA:
        print("⚠️  2026.04–2026.06 数据尚未填入！")
        print("   请参照 APRIL_JUNE_DATA 变量的注释，填入实际月度数据后重新运行。")
        print()
        print("   当前仅重新验证6个月数据...")

        sz_params = ModelParams(EF_grid=EF_GRID_GUANGDONG)
        results_6 = run_fpcm_for_months(EXISTING_6MONTHS, sz_params)

        print("\n6个月验证结果（应与 data/processed/fpcm_monthly_46plants.csv 完全一致）：")
        print(f"{'月份':<10} {'合计(tCO₂)':>12} {'单位(kg/m³)':>12}")
        for r in results_6:
            print(f"{r['month']:<10} {r['Total_tCO2']:>12,.1f} {r['unit_kgCO2_m3']:>12.4f}")
        total = sum(r["Total_tCO2"] for r in results_6)
        print(f"{'合计':<10} {total:>12,.1f}")
        print(f"\n  6月总碳排放: {total/10000:.2f} 万tCO₂ (应为 52.83 万)")
        return

    # 有新数据时：运行完整9个月分析
    print("=" * 65)
    print("  FPCM v3.0 扩展分析 — 深圳市46座污水处理厂")
    print("  数据周期：2025.10 – 2026.06（9个月）")
    print("=" * 65)

    sz_params = ModelParams(EF_grid=EF_GRID_GUANGDONG)

    # 运行6个月（已有）
    results_6 = run_fpcm_for_months(EXISTING_6MONTHS, sz_params)

    # 运行新增3个月
    results_new3 = run_fpcm_for_months(APRIL_JUNE_DATA, sz_params)

    # 合并
    all_results = results_6 + results_new3

    # 打印完整表格
    print("\n【完整9个月月度碳排放结果】\n")
    print(f"{'月份':<10} {'水量(万m³)':>12} {'Sc1(tCO₂)':>12} {'Sc2(tCO₂)':>12} "
          f"{'Sc3(tCO₂)':>12} {'合计(tCO₂)':>12} {'单位(kg/m³)':>12}")
    print("-" * 90)
    for r in all_results:
        marker = " ◀ 新增" if r["month"] >= "2026.04" else ""
        print(f"{r['month']:<10} {r['water_vol_wan_m3']:>12,.1f} {r['Scope1_tCO2']:>12,.1f} "
              f"{r['Scope2_tCO2']:>12,.1f} {r['Scope3_tCO2']:>12,.1f} "
              f"{r['Total_tCO2']:>12,.1f} {r['unit_kgCO2_m3']:>12.4f}{marker}")
    print("-" * 90)
    total_9 = sum(r["Total_tCO2"] for r in all_results)
    vol_9 = sum(r["water_vol_wan_m3"] for r in all_results)
    print(f"{'9月合计':<10} {vol_9:>12,.1f} {'':>12} {'':>12} {'':>12} {total_9:>12,.1f}")

    # 对比分析
    compare_6vs9_months(results_6, all_results)

    # 保存结果
    os.makedirs("data/processed", exist_ok=True)

    with open("data/processed/fpcm_monthly_9months.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    with open("data/processed/fpcm_monthly_9months.csv", "w", encoding="utf-8-sig") as f:
        f.write("月份,处理水量(万m³),用电量(万kWh),Scope1(tCO₂),Scope2(tCO₂),"
                "Scope3(tCO₂),合计(tCO₂),单位碳排(kgCO₂/m³)\n")
        for r in all_results:
            f.write(f"{r['month']},{r['water_vol_wan_m3']},{r['elec_wan_kwh']},"
                    f"{r['Scope1_tCO2']},{r['Scope2_tCO2']},{r['Scope3_tCO2']},"
                    f"{r['Total_tCO2']},{r['unit_kgCO2_m3']}\n")

    print("\n\n✅ 结果已保存：")
    print("  data/processed/fpcm_monthly_9months.csv")
    print("  data/processed/fpcm_monthly_9months.json")


if __name__ == "__main__":
    main()
