"""
src.preprocessing — 数据预处理模块

子模块：
  docx_parser         解析 41 座设施个厂资料 (.docx)
  energy_stats_parser 解析 46 厂能耗药耗统计报告 (.docx)
  pipeline            端到端预处理管道（Step 1–4）
"""
from .docx_parser import parse_all_plants, parse_plant_docx, PlantEquipmentData
from .energy_stats_parser import parse_energy_report, PlantEnergyRecord
from .pipeline import run_pipeline

__all__ = [
    "parse_all_plants",
    "parse_plant_docx",
    "PlantEquipmentData",
    "parse_energy_report",
    "PlantEnergyRecord",
    "run_pipeline",
]
