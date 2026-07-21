"""
energy_stats_parser.py — 解析深圳46座污水处理厂能耗药耗统计报告

提取各厂站的：
  - 厂站名称、设计规模、工艺类型
  - 半年处理水量、平均负荷率
  - 综合吨水电耗
  - COD削减电耗
  - 碳源单耗、除磷药剂单耗
"""
from __future__ import annotations

import re
import json
import csv
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from pathlib import Path

try:
    from docx import Document
except ImportError:
    raise ImportError("请安装 python-docx: pip install python-docx")


@dataclass
class PlantEnergyRecord:
    plant_name: str = ""
    design_scale_10kmd: Optional[float] = None   # 设计规模 万m³/d
    scale_group: str = ""                          # 规模分组
    process_group: str = ""                        # 工艺分组
    water_volume_10km3: Optional[float] = None    # 半年处理水量 万m³
    load_rate_pct: Optional[float] = None          # 平均负荷率 %
    unit_elec_kwh_m3: Optional[float] = None      # 吨水电耗 kWh/m³
    cod_reduction_elec: Optional[float] = None    # COD削减电耗 kWh/kgCOD
    carbon_dose_kg_10km3: Optional[float] = None  # 碳源单耗 kg/万m³
    pac_dose_kg_10km3: Optional[float] = None     # 除磷药剂单耗 kg/万m³
    dewater_dose_kg_10km3: Optional[float] = None # 脱水药剂单耗 kg/万m³
    is_high_consumer: bool = False                 # 高耗能标记
    source_file: str = ""


def _parse_float(text: str) -> Optional[float]:
    """解析含逗号的数字字符串"""
    text = text.replace(',', '').strip()
    try:
        return float(text)
    except ValueError:
        return None


def parse_energy_report(filepath: str) -> List[PlantEnergyRecord]:
    """
    解析 46 厂能耗药耗统计报告，提取厂站级数据表（Table 3）。
    Returns list of PlantEnergyRecord.
    """
    records: List[PlantEnergyRecord] = []
    doc = Document(filepath)

    # Table 3 通常是各厂站明细（厂站名称 | 设计规模 | 规模分组 | 工艺分组 | 处理水量 | ...）
    for table in doc.tables:
        if not table.rows:
            continue
        header = [c.text.strip() for c in table.rows[0].cells]
        # 识别厂站明细表：含"厂站名称"列
        if '厂站名称' not in header:
            continue

        col_map = {h: i for i, h in enumerate(header)}

        for row in table.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if not cells[0] or cells[0] == '':
                continue

            rec = PlantEnergyRecord(
                plant_name=cells[0],
                source_file=str(filepath),
            )

            # 按列映射
            def get(col_name: str) -> str:
                idx = col_map.get(col_name)
                return cells[idx] if idx is not None and idx < len(cells) else ''

            rec.design_scale_10kmd = _parse_float(get('设计规模(万m³/d)'))
            rec.scale_group = get('规模分组')
            rec.process_group = get('工艺分组')

            # 水量列：可能是"处理水量(万m³)"或"半年处理水量(万m³)"
            wv = get('处理水量(万m³)') or get('半年处理水量(万m³)')
            rec.water_volume_10km3 = _parse_float(wv)

            lr = get('平均负荷率(%)') or get('负荷率(%)')
            if lr and lr != '-':
                rec.load_rate_pct = _parse_float(lr)

            rec.unit_elec_kwh_m3 = _parse_float(get('吨水电耗(kWh/m³)'))
            rec.cod_reduction_elec = _parse_float(get('COD削减电耗(kWh/kgCOD)'))
            rec.carbon_dose_kg_10km3 = _parse_float(get('碳源单耗(kg/万m³)'))
            rec.pac_dose_kg_10km3 = _parse_float(
                get('除磷药剂单耗(kg/万m³)') or get('除磷单耗(kg/万m³)')
            )
            rec.dewater_dose_kg_10km3 = _parse_float(get('脱水药剂单耗(kg/万m³)'))

            records.append(rec)

    return records


def save_records(records: List[PlantEnergyRecord],
                 json_path: str = "data/processed/facilities_energy_stats.json",
                 csv_path: str = "data/processed/facilities_energy_stats.csv") -> None:
    dicts = [asdict(r) for r in records]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dicts, f, ensure_ascii=False, indent=2)

    if dicts:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=dicts[0].keys())
            writer.writeheader()
            writer.writerows(dicts)


if __name__ == "__main__":
    import sys
    fpath = sys.argv[1] if len(sys.argv) > 1 else \
        "data/raw/深圳市46座污水处理厂2025.10-2026.03能耗药耗统计分析及节能降耗建议_规模工艺完善版.docx"

    records = parse_energy_report(fpath)
    print(f"解析到 {len(records)} 条厂站记录")

    save_records(records)
    print("已写入 data/processed/facilities_energy_stats.{json,csv}")

    if records:
        print(f"\n示例（前3条）：")
        for r in records[:3]:
            print(f"  {r.plant_name}  规模={r.design_scale_10kmd}万m³/d  "
                  f"工艺={r.process_group}  吨水电耗={r.unit_elec_kwh_m3} kWh/m³")
