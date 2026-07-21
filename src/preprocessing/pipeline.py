"""
pipeline.py — 数据预处理主管道

执行流程：
  Step 1  解析 41 座设施个厂资料 (.docx) → facilities_equipment.{csv,json}
  Step 2  解析 46 厂能耗药耗统计报告   → facilities_energy_stats.{csv,json}
  Step 3  合并两张表（按厂名模糊匹配） → facilities_merged.{csv,json}
  Step 4  生成汇总统计                  → pipeline_summary.json

用法：
    python -m src.preprocessing.pipeline
    或：
    from src.preprocessing.pipeline import run_pipeline
    result = run_pipeline()
"""
from __future__ import annotations

import json
import csv
import re
from pathlib import Path
from typing import List, Dict, Optional

from .docx_parser import parse_all_plants, to_records as equip_to_records
from .energy_stats_parser import parse_energy_report, save_records as save_energy


# ─── 模糊匹配工具 ────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """归一化厂名（去除空格、标点、常见后缀）以便匹配"""
    name = re.sub(r'\s+', '', name)
    name = re.sub(r'（.*?）|\(.*?\)', '', name)
    name = re.sub(r'[一二三四五六七八九十]期$', '', name)
    name = name.replace('水质净化厂', '厂').replace('污水处理厂', '厂')
    return name


def _fuzzy_match(name_a: str, name_b: str) -> bool:
    na, nb = _normalize_name(name_a), _normalize_name(name_b)
    # 完全包含关系
    if na in nb or nb in na:
        return True
    # 公共前缀 ≥ 3 字
    common = 0
    for a, b in zip(na, nb):
        if a == b:
            common += 1
        else:
            break
    return common >= 3


def merge_tables(equip_records: List[dict],
                 energy_records: List[dict]) -> List[dict]:
    """将设备数据与能耗统计按厂名模糊合并"""
    merged = []
    energy_matched = set()

    for eq in equip_records:
        row = dict(eq)
        row['notes'] = '; '.join(eq.get('notes', []))

        for i, en in enumerate(energy_records):
            if i in energy_matched:
                continue
            if _fuzzy_match(eq['plant_name'], en['plant_name']):
                # 合并能耗字段
                for k, v in en.items():
                    if k not in ('plant_name', 'source_file') and v is not None:
                        row[f'energy_{k}'] = v
                energy_matched.add(i)
                row['match_status'] = 'matched'
                break
        else:
            row['match_status'] = 'equipment_only'

        merged.append(row)

    # 添加只在能耗报告中出现的厂站
    for i, en in enumerate(energy_records):
        if i not in energy_matched:
            row = {f'energy_{k}': v for k, v in en.items()}
            row['plant_name'] = en['plant_name']
            row['match_status'] = 'energy_only'
            merged.append(row)

    return merged


def _summary_stats(equip_records, energy_records, merged) -> dict:
    """生成管道摘要统计"""
    blower_ok = sum(1 for r in equip_records if r.blower_power_kw)
    do_ok = sum(1 for r in equip_records if r.do_aerobic_min)
    matched = sum(1 for r in merged if r.get('match_status') == 'matched')
    energy_total = sum(
        r.get('energy_water_volume_10km3', 0) or 0 for r in merged
    )

    return {
        "equipment_files_parsed": len(equip_records),
        "energy_records_parsed": len(energy_records),
        "merged_rows": len(merged),
        "matched_rows": matched,
        "blower_power_extracted": blower_ok,
        "do_extracted": do_ok,
        "mbr_plants": sum(1 for r in equip_records if r.has_mbr),
        "drying_plants": sum(1 for r in equip_records if r.has_drying),
        "total_water_volume_10km3": round(energy_total, 2),
    }


def run_pipeline(
    equip_dir: str = "data/raw/41座设施各厂资料",
    energy_file: str = (
        "data/raw/深圳市46座污水处理厂2025.10-2026.03能耗药耗统计分析及节能降耗建议"
        "_规模工艺完善版.docx"
    ),
    output_dir: str = "data/processed",
) -> dict:
    """运行完整预处理管道，返回摘要统计 dict"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Step 1: 解析设备文件
    print("Step 1: 解析 41 座设施个厂资料…")
    equip_plants = parse_all_plants(equip_dir)
    equip_dicts = equip_to_records(equip_plants)

    json_path = f"{output_dir}/facilities_equipment.json"
    csv_path = f"{output_dir}/facilities_equipment.csv"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(equip_dicts, f, ensure_ascii=False, indent=2)

    flat_keys = [k for k in equip_dicts[0].keys() if k != "notes"] if equip_dicts else []
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=flat_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(equip_dicts)
    print(f"  ✓ {len(equip_dicts)} 条设备记录 → {json_path}")

    # Step 2: 解析能耗报告
    print("Step 2: 解析 46 厂能耗药耗统计报告…")
    energy_records = parse_energy_report(energy_file)
    save_energy(
        energy_records,
        json_path=f"{output_dir}/facilities_energy_stats.json",
        csv_path=f"{output_dir}/facilities_energy_stats.csv",
    )
    print(f"  ✓ {len(energy_records)} 条能耗记录")

    energy_dicts = [
        {k: v for k, v in vars(r).items()} if hasattr(r, '__dict__') else r
        for r in energy_records
    ]
    # dataclass → dict
    from dataclasses import asdict as _asdict
    energy_dicts = [_asdict(r) for r in energy_records]

    # Step 3: 合并
    print("Step 3: 合并两张表…")
    merged = merge_tables(equip_dicts, energy_dicts)
    merged_path = f"{output_dir}/facilities_merged.json"
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    if merged:
        all_keys = list(merged[0].keys())
        with open(f"{output_dir}/facilities_merged.csv", "w",
                  newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(merged)
    print(f"  ✓ {len(merged)} 条合并记录 → {merged_path}")

    # Step 4: 摘要
    summary = _summary_stats(equip_plants, energy_records, merged)
    summary_path = f"{output_dir}/pipeline_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 管道完成：")
    for k, v in summary.items():
        print(f"   {k}: {v}")

    return summary


if __name__ == "__main__":
    run_pipeline()
