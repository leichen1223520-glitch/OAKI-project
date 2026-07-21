"""
M6：污泥处置碳排放子模型

干污泥量获取（三级优先级）：
  1. 台账直接给出 W_sludge (tDS/月)
  2. 湿重 × (1 - MC_sludge)
  3. 物料守恒估算（Q_in × SS_removal + 生化合成 VSS）

处置方式碳排放因子（kgCO₂eq/tDS）：
  compost_closed:       360
  compost_open:         480
  anaerobic_digestion:  100
  landfill_gas:         680
  landfill_no_gas:      950
  incineration:         980
  land_application:     120

参考文献：
- 张等 (2022)，王等 (2021)，宋等 (2020)，刘等 (2021)
- 表4-3 各处置方式 EF_disposal 先验分布参数
"""
from .params import ModelParams
from .inputs import ModelInput

# 处置方式排放因子查找表 (kgCO₂eq/tDS)
DISPOSAL_EF = {
    "compost_closed": 360.0,
    "compost_open": 480.0,
    "anaerobic_digestion": 100.0,
    "landfill_gas": 680.0,
    "landfill_no_gas": 950.0,
    "incineration": 980.0,
    "land_application": 120.0,
}


class SludgeDisposalModel:
    """
    M6：污泥处置碳排放子模型
    """

    def __init__(self, params: ModelParams):
        self.p = params

    # ─────────────────────────────────────────────────────────
    # 干污泥量确定（三级优先级）
    # ─────────────────────────────────────────────────────────

    def _get_WDS_annual(self, inp: ModelInput) -> float:
        """
        返回年干污泥量 (tDS/年)

        优先级：1. 台账 W_sludge → 2. 湿重推算 → 3. 物料守恒估算
        """
        # ── 方法1：直接台账 ───────────────────────────────────
        if inp.W_sludge is not None:
            return inp.W_sludge * 12.0  # 月均值 × 12 月

        # ── 方法2：湿重推算 ───────────────────────────────────
        if inp.W_sludge_wet is not None:
            return inp.W_sludge_wet * 12.0 * (1.0 - self.p.MC_sludge)

        # ── 方法3：物料守恒估算 ───────────────────────────────
        # SS 去除量 (kgSS/年)
        if inp.SS_in is not None and inp.SS_out is not None:
            SS_removal = max(0.0, inp.SS_in - inp.SS_out)
        else:
            # 默认进水 SS ≈ 0.8 × COD_in（工程经验值）
            SS_removal = 0.8 * inp.COD_in * 0.7  # 70% SS 去除率

        W_SS = inp.Q_in * SS_removal * 365 * 1e-6  # tSS/年

        # 生化合成 VSS (tVSS/年)
        BOD_removed = max(0.0, inp.COD_in - inp.COD_out) * self.p.f_boc
        W_VSS = self.p.Y_obs * inp.Q_in * BOD_removed * 365 * 1e-6

        # 总 DS（取最大，避免重复计算）
        W_DS = max(W_SS, W_VSS)
        return max(0.0, W_DS)

    # ─────────────────────────────────────────────────────────
    # 主接口
    # ─────────────────────────────────────────────────────────

    def calculate(self, inp: ModelInput) -> float:
        """
        计算年污泥处置碳排放 (kgCO₂eq/年)

        E_sludge = W_DS_annual × EF_disposal
        """
        W_DS = self._get_WDS_annual(inp)

        # 优先使用 params 中的 EF_disposal（支持贝叶斯率定）
        # 也可通过 inp.disposal_method 查表覆盖
        if inp.disposal_method in DISPOSAL_EF:
            EF = DISPOSAL_EF[inp.disposal_method]
        else:
            EF = self.p.EF_disposal

        # kgCO₂eq/年 = tDS/年 × kgCO₂eq/tDS
        return max(0.0, W_DS * EF)

    def get_annual_DS(self, inp: ModelInput) -> float:
        """返回年干污泥量 (tDS/年)，供集成框架展示"""
        return self._get_WDS_annual(inp)
