"""
carbon_factors.py — 碳排放因子查询工具

数据来源：
  - 电网排放因子：生态环境部 2023 年公告（区域电网基准排放因子）
  - 药剂碳排放因子：Ecoinvent + 中国化修正
  - 全球增温潜势（GWP100）：IPCC AR6
"""
from __future__ import annotations

from typing import Optional

# ─── GWP100（IPCC AR6，100年）────────────────────────────────────────────────
GWP_CH4 = 27.9   # kgCO₂eq/kgCH₄（AR6，含气候碳反馈）
GWP_N2O = 273.0  # kgCO₂eq/kgN₂O（AR6）


# ─── 省域电网排放因子（tCO₂/MWh，2023年 MEE 公告）──────────────────────────
# 来源：《关于做好2023—2025年发电行业企业温室气体排放报告管理有关工作的通知》附件
PROVINCIAL_GRID_EF: dict[str, float] = {
    "北京": 0.5271,
    "天津": 0.5271,
    "河北": 0.5271,
    "山西": 0.5271,
    "内蒙古": 0.9822,
    "辽宁": 0.5271,
    "吉林": 0.5271,
    "黑龙江": 0.5271,
    "上海": 0.5271,
    "江苏": 0.5271,
    "浙江": 0.5271,
    "安徽": 0.5271,
    "福建": 0.5271,
    "江西": 0.5271,
    "山东": 0.5271,
    "河南": 0.5271,
    "湖北": 0.5271,
    "湖南": 0.5271,
    "广东": 0.5271,   # 南方电网
    "广西": 0.5271,
    "海南": 0.5271,
    "重庆": 0.4229,
    "四川": 0.4525,   # 水电大省，较低
    "贵州": 0.5271,
    "云南": 0.4229,
    "西藏": 0.4229,
    "陕西": 0.5271,
    "甘肃": 0.5271,
    "青海": 0.4229,
    "宁夏": 0.5271,
    "新疆": 0.5271,
    # 区域网均值（当省份数据缺失时使用）
    "GEO_NORTH": 0.5271,    # 华北/东北/西北
    "GEO_EAST": 0.5271,     # 华东
    "GEO_CENTRAL": 0.5271,  # 华中
    "GEO_GUANGDONG": 0.5271,  # 广东
    "GEO_SOUTH": 0.5271,    # 南方（广东/广西/云南/贵州/海南）
    "NATIONAL": 0.5839,     # 全国平均（2022年基准）
}


def get_grid_ef(province_or_region: str = "NATIONAL") -> float:
    """
    获取电网排放因子 (tCO₂/MWh)。

    Parameters
    ----------
    province_or_region : str
        省份名称（如"广东"）或区域代码（如"GEO_GUANGDONG"）。
        若不指定或找不到，返回全国均值。

    Returns
    -------
    float  tCO₂/MWh
    """
    return PROVINCIAL_GRID_EF.get(province_or_region,
                                   PROVINCIAL_GRID_EF["NATIONAL"])


# ─── 药剂碳排放因子 (kgCO₂eq/kg药剂)──────────────────────────────────────────
# 基于 Ecoinvent 3.9 + 中国电网强度修正
CHEMICAL_EF: dict[str, float] = {
    "PAC":          0.313,   # 聚合氯化铝 (polyaluminium chloride)
    "PFS":          0.441,   # 聚合硫酸铁 (polyferric sulphate)
    "FeSO4":        0.186,   # 硫酸亚铁
    "FeCl3":        0.512,   # 氯化铁
    "NaOH":         1.914,   # 氢氧化钠
    "Na2CO3":       0.847,   # 纯碱
    "NaHCO3":       0.624,   # 小苏打
    "CH3COONa":     1.025,   # 乙酸钠 (碳源)
    "C2H5OH":       1.652,   # 乙醇 (碳源)
    "glucose":      0.871,   # 葡萄糖 (碳源)
    "methanol":     0.556,   # 甲醇 (碳源)
    "polymer":      2.570,   # 絮凝剂（聚丙烯酰胺）
    "PAM":          2.570,   # 聚丙烯酰胺（同 polymer）
    "Cl2":          0.932,   # 液氯 (消毒)
    "NaClO":        0.879,   # 次氯酸钠
    "UV":           0.000,   # 紫外消毒（无药剂碳排）
}


def get_chemical_ef(chemical: str, default: float = 0.5) -> float:
    """
    获取药剂碳排放因子 (kgCO₂eq/kg)。
    若未知药剂，返回 default（默认 0.5）。
    """
    return CHEMICAL_EF.get(chemical, default)


# ─── 污泥处置碳排放因子 (kgCO₂eq/tDS) ──────────────────────────────────────
# 来源：文献综述（IPCC 废物处理章节 + 中国本土研究）
SLUDGE_DISPOSAL_EF: dict[str, float] = {
    "compost_closed":    360,   # 密闭式堆肥（含运输，kgCO₂eq/tDS）
    "compost_open":      520,   # 开放式堆肥
    "anaerobic_digestion": 120, # 厌氧消化+沼气利用
    "landfill_gas":      280,   # 填埋+气体回收
    "landfill_no_gas":   480,   # 填埋无气体回收
    "incineration":      -50,   # 焚烧发电（负值=净碳汇）
    "land_application":  200,   # 土地利用
    "drying_incineration": -80, # 干化+焚烧发电
}


def get_sludge_ef(disposal_method: str) -> float:
    """获取污泥处置碳排放因子 (kgCO₂eq/tDS)"""
    return SLUDGE_DISPOSAL_EF.get(disposal_method,
                                   SLUDGE_DISPOSAL_EF["compost_closed"])
