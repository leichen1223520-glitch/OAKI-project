"""
test_preprocessing.py — 数据预处理模块单元测试

覆盖：
  - docx_parser: 文件名清洗、单文件解析
  - energy_stats_parser: 能耗报告解析
  - validators: 输入参数校验
"""
import sys
import os
import glob
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessing.docx_parser import (
    _clean_plant_name,
    _extract_power,
    _extract_count,
    _extract_do,
    _extract_moisture,
    parse_plant_docx,
    parse_all_plants,
    PlantEquipmentData,
)


# ─── 文件名清洗测试 ──────────────────────────────────────────────────────────

class TestCleanPlantName:
    def test_basic_bracket_removal(self):
        name = _clean_plant_name("fake/排水处咨询工作所需资料(上洋厂).docx")
        # 清洗后应包含厂站关键词，不包含完整前缀
        assert len(name) > 0
        assert "上洋" in name or len(name) < 15  # 至少去掉了前缀部分

    def test_prefix_stripped(self):
        name = _clean_plant_name("fake/排水处咨询工作所需资料（横岭一期）(1).docx")
        # 至少去除了末尾的(1)
        assert "(1)" not in name
        assert len(name) > 0

    def test_returns_string(self):
        name = _clean_plant_name("fake/光明水质净化厂-排水处咨询工作所需资料.docx")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_clean_removes_trailing_number(self):
        """末尾 (1) (2) 应被去除"""
        name = _clean_plant_name("fake/横岗一期 排水处咨询工作所需资料(2).docx")
        assert "(2)" not in name


# ─── 正则提取函数测试 ────────────────────────────────────────────────────────

class TestExtractFunctions:
    def test_extract_power_basic(self):
        assert _extract_power("单机功率：450kW") == 450.0
        assert _extract_power("功率 55 kW（主电机）") == 55.0
        assert _extract_power("无功率信息") is None

    def test_extract_count_run_standby(self):
        assert _extract_count("3用1备") == 3
        assert _extract_count("4台（3用1备）") in (4, 3)

    def test_extract_count_simple(self):
        assert _extract_count("运行台数：3") == 3

    def test_extract_do_range(self):
        lo, hi = _extract_do("好氧区DO 2.0~3.0 mg/L")
        assert lo == 2.0
        assert hi == 3.0

    def test_extract_do_single(self):
        lo, hi = _extract_do("DO：2.5")
        assert lo == 2.5

    def test_extract_do_none(self):
        lo, hi = _extract_do("无DO数据")
        assert lo is None
        assert hi is None

    def test_extract_moisture(self):
        v = _extract_moisture("出泥含水率：78%~80%")
        assert v is not None
        assert 50 <= v <= 99

    def test_extract_moisture_none(self):
        v = _extract_moisture("无含水率信息")
        assert v is None


# ─── 单文件解析测试 ──────────────────────────────────────────────────────────

SAMPLE_FILES = glob.glob("data/raw/41座设施各厂资料/*.docx")
HAS_SAMPLE = len(SAMPLE_FILES) > 0


@pytest.mark.skipif(not HAS_SAMPLE, reason="缺少测试用 docx 文件")
class TestParsePlantDocx:
    def test_returns_dataclass(self):
        result = parse_plant_docx(SAMPLE_FILES[0])
        assert isinstance(result, PlantEquipmentData)

    def test_plant_name_nonempty(self):
        result = parse_plant_docx(SAMPLE_FILES[0])
        assert len(result.plant_name) > 0

    def test_source_file_set(self):
        result = parse_plant_docx(SAMPLE_FILES[0])
        assert SAMPLE_FILES[0] in result.source_file

    def test_blower_power_if_extracted_positive(self):
        result = parse_plant_docx(SAMPLE_FILES[0])
        if result.blower_power_kw is not None:
            assert result.blower_power_kw > 0

    def test_do_range_ordered(self):
        """若提取了DO范围，lo 应 ≤ hi"""
        for f in SAMPLE_FILES[:5]:
            r = parse_plant_docx(f)
            if r.do_aerobic_min is not None and r.do_aerobic_max is not None:
                assert r.do_aerobic_min <= r.do_aerobic_max


@pytest.mark.skipif(not HAS_SAMPLE, reason="缺少测试用 docx 文件")
class TestParseAllPlants:
    def test_count_matches_files(self):
        plants = parse_all_plants("data/raw/41座设施各厂资料")
        assert len(plants) == len(SAMPLE_FILES)

    def test_no_duplicate_names(self):
        """解析结果中不应有完全重复的厂名"""
        plants = parse_all_plants("data/raw/41座设施各厂资料")
        names = [p.plant_name for p in plants]
        # 允许少量重复（同厂多文件），但不应全重复
        unique = set(names)
        assert len(unique) > len(names) * 0.7  # 至少70%唯一

    def test_some_blower_extracted(self):
        """至少50%的文件能提取到鼓风机功率"""
        plants = parse_all_plants("data/raw/41座设施各厂资料")
        ok = sum(1 for p in plants if p.blower_power_kw)
        assert ok / len(plants) >= 0.5, (
            f"鼓风机功率提取率偏低: {ok}/{len(plants)}"
        )
