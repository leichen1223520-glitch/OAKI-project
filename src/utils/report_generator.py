"""
report_generator.py — 生成 FPCM 计算结果的文字/CSV 报告

提供：
  generate_text_report(result, inp)   → str（可打印的文字报告）
  generate_csv_report(results, path)  → 写入 CSV 文件
  generate_summary_table(results)     → dict（汇总统计）
"""
from __future__ import annotations

import csv
from typing import List, Optional, Tuple


def generate_text_report(result, inp=None, plant_name: str = "案例厂") -> str:
    """
    生成单厂 FPCM 计算结果的格式化文字报告。

    Parameters
    ----------
    result : ModelOutput
        FPCM.run() 返回值。
    inp : ModelInput, optional
        对应输入（用于显示关键参数）。
    plant_name : str
        厂站名称。

    Returns
    -------
    str  可直接打印的报告文本。
    """
    sep = "─" * 60
    lines = [
        sep,
        f"  FPCM 碳排放计算报告 — {plant_name}",
        sep,
    ]

    if inp is not None:
        lines += [
            "【输入参数】",
            f"  日均进水量       {inp.Q_in:>12,.0f}  m³/d",
            f"  月电耗           {inp.E_total_monthly:>12,.0f}  kWh/月",
            f"  进水 COD/TN/NH₃N {inp.COD_in:.0f}/{inp.TN_in:.0f}/{inp.NH3N_in:.0f} mg/L",
            f"  出水 COD/TN/NH₃N {inp.COD_out:.0f}/{inp.TN_out:.0f}/{inp.NH3N_out:.1f} mg/L",
            f"  水温             {inp.T_water:>12.1f}  °C",
            "",
        ]

    lines += [
        "【排放分项（kgCO₂eq/年）】",
        f"  Scope 1 直接排放  {result.E_Scope1_CO2eq:>14,.0f}",
        f"    ├─ CH₄          {result.E_CH4_kg * 27.9:>14,.0f}  (CH₄={result.E_CH4_kg:.1f} kg)",
        f"    └─ N₂O          {result.E_N2O_kg * 273.0:>14,.0f}  (N₂O={result.E_N2O_kg:.1f} kg)",
        f"  Scope 2 电力间接  {result.E_Scope2_CO2eq:>14,.0f}",
        f"  Scope 3 其他间接  {result.E_Scope3_CO2eq:>14,.0f}",
        f"    ├─ 药剂          {result.E_chem_CO2eq:>14,.0f}",
        f"    └─ 污泥处置      {result.E_sludge_CO2eq:>14,.0f}",
        sep,
        f"  全厂总计          {result.E_total_CO2eq:>14,.0f}  kgCO₂eq/年",
        f"  ≈ {result.E_total_CO2eq/1000:,.1f}  tCO₂eq/年",
        "",
        "【单耗指标】",
        f"  单位水量碳排放    {result.E_unit_kgCO2_m3:>12.4f}  kgCO₂eq/m³",
        f"  数据完整性级别    Level {result.calculation_level}",
        f"  估算不确定性      ±{result.uncertainty_pct:.0f}%（95% CI）",
    ]

    if result.warnings:
        lines += ["", "【计算警告】"]
        for w in result.warnings:
            lines.append(f"  ⚠  {w}")

    lines.append(sep)
    return "\n".join(lines)


def generate_csv_report(
    results: List[Tuple[str, object]],
    output_path: str = "results/fpcm_batch_results.csv",
) -> None:
    """
    将批量计算结果写入 CSV。

    Parameters
    ----------
    results : list of (plant_name, ModelOutput)
    output_path : str
    """
    if not results:
        return

    fieldnames = [
        "plant_name",
        "E_Scope1_CO2eq_kg", "E_Scope2_CO2eq_kg", "E_Scope3_CO2eq_kg",
        "E_total_CO2eq_kg", "E_total_CO2eq_t",
        "E_CH4_kg", "E_N2O_kg",
        "E_unit_kgCO2_m3",
        "calculation_level", "uncertainty_pct",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for name, r in results:
            writer.writerow({
                "plant_name": name,
                "E_Scope1_CO2eq_kg": round(r.E_Scope1_CO2eq, 0),
                "E_Scope2_CO2eq_kg": round(r.E_Scope2_CO2eq, 0),
                "E_Scope3_CO2eq_kg": round(r.E_Scope3_CO2eq, 0),
                "E_total_CO2eq_kg": round(r.E_total_CO2eq, 0),
                "E_total_CO2eq_t": round(r.E_total_CO2eq / 1000, 2),
                "E_CH4_kg": round(r.E_CH4_kg, 2),
                "E_N2O_kg": round(r.E_N2O_kg, 2),
                "E_unit_kgCO2_m3": round(r.E_unit_kgCO2_m3, 4),
                "calculation_level": r.calculation_level,
                "uncertainty_pct": r.uncertainty_pct,
            })


def generate_summary_table(results: List[Tuple[str, object]]) -> dict:
    """生成批量结果汇总统计（均值、中位数、范围等）"""
    import statistics as stats

    if not results:
        return {}

    units = [r.E_unit_kgCO2_m3 for _, r in results]
    totals_t = [r.E_total_CO2eq / 1000 for _, r in results]

    return {
        "count": len(results),
        "unit_emission_mean": round(stats.mean(units), 4),
        "unit_emission_median": round(stats.median(units), 4),
        "unit_emission_min": round(min(units), 4),
        "unit_emission_max": round(max(units), 4),
        "total_emission_mean_t": round(stats.mean(totals_t), 1),
        "total_emission_sum_t": round(sum(totals_t), 1),
    }
