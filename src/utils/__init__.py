"""
src.utils — 工具函数模块

子模块：
  carbon_factors    电网/药剂/污泥处置碳排放因子查询
  validators        模型输入参数合理性校验
  report_generator  计算结果报告生成（文字/CSV/汇总）
"""
from .carbon_factors import (
    GWP_CH4, GWP_N2O,
    get_grid_ef, PROVINCIAL_GRID_EF,
    get_chemical_ef, CHEMICAL_EF,
    get_sludge_ef, SLUDGE_DISPOSAL_EF,
)
from .validators import validate_model_input, validate_batch, ValidationResult
from .report_generator import (
    generate_text_report,
    generate_csv_report,
    generate_summary_table,
)

__all__ = [
    "GWP_CH4", "GWP_N2O",
    "get_grid_ef", "PROVINCIAL_GRID_EF",
    "get_chemical_ef", "CHEMICAL_EF",
    "get_sludge_ef", "SLUDGE_DISPOSAL_EF",
    "validate_model_input", "validate_batch", "ValidationResult",
    "generate_text_report", "generate_csv_report", "generate_summary_table",
]
