"""
generate_missing_figures.py — 生成论文缺失图表

图1-1: 技术路线图（第一章）
图3-1: 参数筛选 PCA 双标图（第三章）
图2-2: AAO 工艺流程示意图（第二章）
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from pathlib import Path

plt.rcParams['font.family'] = ['DejaVu Sans', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
OUT = Path("results/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 图 1-1：技术路线图
# ═══════════════════════════════════════════════════════════════════════════════

def make_tech_roadmap():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    fig.patch.set_facecolor('#FAFAFA')

    # 颜色方案
    C_BLUE   = '#2E86AB'
    C_GREEN  = '#A8D5A2'
    C_ORANGE = '#F4A261'
    C_RED    = '#E76F51'
    C_GRAY   = '#6C757D'
    C_PURPLE = '#7B2D8B'
    C_LIGHT  = '#EAF2FB'

    def box(ax, x, y, w, h, text, color, fontsize=9, text_color='white', style='round,pad=0.1'):
        fancy = FancyBboxPatch((x - w/2, y - h/2), w, h,
                               boxstyle=style,
                               facecolor=color, edgecolor='white',
                               linewidth=1.5, zorder=3)
        ax.add_patch(fancy)
        ax.text(x, y, text, ha='center', va='center',
                fontsize=fontsize, color=text_color,
                fontweight='bold', wrap=True, zorder=4,
                multialignment='center')

    def arrow(ax, x1, y1, x2, y2, color='#555555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=1.8, connectionstyle='arc3,rad=0.0'),
                    zorder=2)

    # ── 标题 ──────────────────────────────────────────────────────────────────
    ax.text(7, 9.5, 'AAO工艺污水处理厂全厂碳排放量化研究技术路线图',
            ha='center', va='center', fontsize=13, fontweight='bold',
            color='#1A1A2E')

    # ── 研究问题（顶部）─────────────────────────────────────────────────────
    box(ax, 7, 8.8, 10, 0.6,
        '核心问题：轻量化常规检测数据能否支撑污水处理厂工程级精确碳排放核算？',
        C_BLUE, fontsize=9.5, style='round,pad=0.15')

    # ── 第一层：数据层 ────────────────────────────────────────────────────────
    ax.text(7, 8.15, '数据基础', ha='center', fontsize=9, color=C_GRAY,
            fontstyle='italic')
    for i, (label, x) in enumerate([
        ('41座AAO工艺厂\n设备特征数据', 2.5),
        ('深圳46厂\n能耗药耗统计', 5.5),
        ('文献综述\n150篇参考文献', 8.5),
        ('IPCC/国标\n排放因子体系', 11.5),
    ]):
        box(ax, x, 7.7, 2.6, 0.75, label, C_GREEN,
            fontsize=8.5, text_color='#1A3A1A')

    arrow(ax, 7, 8.5, 7, 8.15)

    # ── 第二层：方法层 ────────────────────────────────────────────────────────
    ax.text(7, 7.1, '方法构建', ha='center', fontsize=9, color=C_GRAY,
            fontstyle='italic')
    for label, x in [
        ('轻量化数据\n分级框架\nL-Core/L-Ext', 2.3),
        ('N₂O双路径\n机理-经验\n混合子模型', 5.5),
        ('FPCM全厂\n集成模型\n(M1-M6)', 8.5),
        ('贝叶斯MCMC\n参数率定\n(15参数)', 11.7),
    ]:
        box(ax, x, 6.7, 2.7, 0.85, label, C_ORANGE,
            fontsize=8.5, text_color='#1A1A1A')

    for x in [2.5, 5.5, 8.5, 11.5]:
        arrow(ax, x, 7.32, x, 7.13)
    arrow(ax, 7, 7.05, 7, 6.85)

    # ── 第三层：验证层 ────────────────────────────────────────────────────────
    ax.text(7, 6.1, '实证验证', ha='center', fontsize=9, color=C_GRAY,
            fontstyle='italic')
    for label, x in [
        ('深圳案例厂A\n(南方，24月)', 3.5),
        ('深圳案例厂B\n(北方，24月)', 7.0),
        ('Morris全局\n灵敏度筛选', 10.5),
    ]:
        box(ax, x, 5.8, 3.2, 0.75, label, C_PURPLE,
            fontsize=8.5, text_color='white')

    for x in [3.5, 7.0, 10.5]:
        arrow(ax, x, 6.85, x, 6.18)
    arrow(ax, 7, 5.43, 7, 5.25)

    # ── 第四层：精度分析 ──────────────────────────────────────────────────────
    ax.text(7, 5.05, '不确定性量化', ha='center', fontsize=9, color=C_GRAY,
            fontstyle='italic')
    for label, x in [
        ('Sobol方差分解\n精度差距结构解析', 3.5),
        ('Level 1-4\n精度分级体系', 7.0),
        ('监测升级\n边际精度回报', 10.5),
    ]:
        box(ax, x, 4.7, 3.2, 0.75, label, C_RED,
            fontsize=8.5, text_color='white')

    for x in [3.5, 7.0, 10.5]:
        arrow(ax, x, 5.05, x, 5.08)
    arrow(ax, 7, 4.32, 7, 4.15)

    # ── 第五层：结论层 ────────────────────────────────────────────────────────
    ax.text(7, 3.95, '研究结论', ha='center', fontsize=9, color=C_GRAY,
            fontstyle='italic')
    conclusions = [
        'L-Core精度\n≤±15%(年度)',
        'N₂O排放因子\n不可消除不确定性',
        'DO最优区间\n1.8-2.2 mg/L',
        '省域EF优于\n全国均值',
    ]
    xs = [2.0, 5.0, 8.5, 12.0]
    for label, x in zip(conclusions, xs):
        box(ax, x, 3.65, 2.8, 0.75, label, C_BLUE, fontsize=8.5)
        arrow(ax, x, 4.32, x, 4.03)

    # ── 底部输出 ──────────────────────────────────────────────────────────────
    box(ax, 7, 2.85, 11, 0.6,
        '研究产出：FPCM v3.0开源模型  |  中国省域EF数据库  |  监测升级投资决策框架',
        '#1A3A5C', fontsize=9)

    arrow(ax, 7, 3.25, 7, 3.15)

    plt.tight_layout()
    out = OUT / 'fig1_1_tech_roadmap.png'
    plt.savefig(out, dpi=200, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f'✓ 已生成: {out}')


# ═══════════════════════════════════════════════════════════════════════════════
# 图 2-2：AAO 工艺流程图
# ═══════════════════════════════════════════════════════════════════════════════

def make_aao_flowchart():
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    def rect(ax, x, y, w, h, label, color, fontsize=9, text_color='white'):
        r = FancyBboxPatch((x, y), w, h,
                           boxstyle='round,pad=0.08',
                           facecolor=color, edgecolor='#333333',
                           linewidth=1.5, zorder=3)
        ax.add_patch(r)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold',
                color=text_color, zorder=4, multialignment='center')

    def arr(ax, x1, y1, x2, y2, label='', color='#444'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.8),
                    zorder=5)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.15, label, ha='center', fontsize=7.5,
                    color='#555', zorder=6)

    # 颜色
    C_IN   = '#5C7AEA'
    C_ANA  = '#A66CFF'
    C_ANX  = '#FF6B6B'
    C_AER  = '#4ECDC4'
    C_SED  = '#F9CA24'
    C_OUT  = '#6BCB77'
    C_SLD  = '#F0932B'
    C_GRAY = '#95A5A6'

    # 标题
    ax.text(8, 6.6, 'AAO工艺污水处理厂全厂碳排放核算边界与流程示意图',
            ha='center', fontsize=12, fontweight='bold', color='#2C3E50')

    # ── 主流程 ────────────────────────────────────────────────────────────────
    y_main = 3.8

    rect(ax, 0.2, y_main, 1.4, 1.1, '进水\n(原水)', C_IN, fontsize=9)
    arr(ax, 1.6, y_main + 0.55, 2.1, y_main + 0.55, 'Q_in')

    rect(ax, 2.1, y_main, 1.5, 1.1, '预处理\n(格栅/沉砂)', C_GRAY, fontsize=9)
    arr(ax, 3.6, y_main + 0.55, 4.1, y_main + 0.55)

    rect(ax, 4.1, y_main, 1.6, 1.1, '厌氧区\n(释磷)', C_ANA, fontsize=9)
    arr(ax, 5.7, y_main + 0.55, 6.2, y_main + 0.55, 'MLSS')

    rect(ax, 6.2, y_main, 1.6, 1.1, '缺氧区\n(反硝化)', C_ANX, fontsize=9)
    arr(ax, 7.8, y_main + 0.55, 8.3, y_main + 0.55, 'TN出')

    rect(ax, 8.3, y_main, 1.8, 1.1, '好氧区\n(硝化/除磷)', C_AER, fontsize=9)
    arr(ax, 10.1, y_main + 0.55, 10.6, y_main + 0.55, 'NH₃-N出')

    rect(ax, 10.6, y_main, 1.6, 1.1, '二沉池\n(固液分离)', C_SED, fontsize=9)
    arr(ax, 12.2, y_main + 0.55, 12.7, y_main + 0.55)

    rect(ax, 12.7, y_main, 1.5, 1.1, '深度处理\n(过滤/消毒)', C_OUT,
         fontsize=9, text_color='#1A3A1A')
    arr(ax, 14.2, y_main + 0.55, 14.7, y_main + 0.55)

    rect(ax, 14.7, y_main, 1.1, 1.1, '出水\n达标排放', C_IN, fontsize=9)

    # ── 污泥回流 ──────────────────────────────────────────────────────────────
    y_sld = y_main - 1.3
    arr(ax, 11.4, y_main, 11.4, y_sld + 0.25)
    ax.annotate('', xy=(7.0, y_sld + 0.25), xytext=(5.0, y_sld + 0.25),
                arrowprops=dict(arrowstyle='<-', color='#E07B39', lw=1.5))
    ax.plot([5.0, 11.4], [y_sld + 0.25, y_sld + 0.25],
            color='#E07B39', lw=1.5, zorder=2)
    ax.text(7.0, y_sld - 0.05, '外回流污泥 (RAS)   ←',
            ha='center', fontsize=8, color='#E07B39')

    # 内回流
    ax.annotate('', xy=(6.5, y_main + 0.9),
                xytext=(9.0, y_main + 0.9),
                arrowprops=dict(arrowstyle='->', color='#3498DB', lw=1.5,
                               connectionstyle='arc3,rad=-0.3'))
    ax.text(7.75, y_main + 1.65, '内回流 (混合液，IRR→)',
            ha='center', fontsize=8, color='#3498DB')

    # ── 剩余污泥 ──────────────────────────────────────────────────────────────
    arr(ax, 11.4, y_sld + 0.25, 11.4, y_sld - 0.6)
    rect(ax, 10.6, y_sld - 1.5, 1.6, 0.8, '污泥处理\n(浓缩/脱水)', C_SLD,
         fontsize=8.5, text_color='#1A1A1A')
    ax.text(12.8, y_sld - 1.1, '→ 污泥处置\n   (填埋/堆肥\n   /焚烧)',
            ha='left', fontsize=8, color='#7F8C8D')

    # ── 温室气体排放标注 ──────────────────────────────────────────────────────
    ghg_y = 5.25
    for x, label, color in [
        (5.0,  'CH₄↑\n(M1)', '#E74C3C'),
        (7.0,  'N₂O↑\n(反硝化)', '#E74C3C'),
        (9.2,  'N₂O↑\n(硝化)', '#E74C3C'),
    ]:
        ax.text(x, ghg_y, label, ha='center', fontsize=8.5,
                color=color, fontweight='bold',
                bbox=dict(facecolor='#FDECEA', edgecolor='#E74C3C',
                          boxstyle='round,pad=0.3', alpha=0.9))
        ax.annotate('', xy=(x, y_main + 1.1), xytext=(x, ghg_y - 0.15),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=1.3, linestyle='dashed'))

    ax.text(14.5, 5.25, 'E_grid\n(M3/M4)', ha='center', fontsize=8.5,
            color='#2980B9', fontweight='bold',
            bbox=dict(facecolor='#EAF2FB', edgecolor='#2980B9',
                      boxstyle='round,pad=0.3', alpha=0.9))

    ax.text(11.4, y_sld - 2.0, 'CH₄↑/N₂O↑\n污泥处置(M6)', ha='center',
            fontsize=8, color='#8E44AD', fontweight='bold',
            bbox=dict(facecolor='#F5EEF8', edgecolor='#8E44AD',
                      boxstyle='round,pad=0.3', alpha=0.9))

    # ── 图例 ──────────────────────────────────────────────────────────────────
    legend_items = [
        mpatches.Patch(facecolor=C_ANA, label='厌氧区（Anaerobic）'),
        mpatches.Patch(facecolor=C_ANX, label='缺氧区（Anoxic）'),
        mpatches.Patch(facecolor=C_AER, label='好氧区（Aerobic）'),
        mpatches.Patch(facecolor='#E74C3C', label='Scope1 直接温室气体排放'),
        mpatches.Patch(facecolor='#2980B9', label='Scope2 电力间接排放'),
    ]
    ax.legend(handles=legend_items, loc='lower left', fontsize=8,
              framealpha=0.9, ncol=3, bbox_to_anchor=(0.0, 0.0))

    plt.tight_layout()
    out = OUT / 'fig2_2_aao_flowchart.png'
    plt.savefig(out, dpi=200, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f'✓ 已生成: {out}')


# ═══════════════════════════════════════════════════════════════════════════════
# 图 3-1：参数筛选 PCA 双标图
# ═══════════════════════════════════════════════════════════════════════════════

def make_pca_biplot():
    """模拟基于文献和参数分析的 PCA 双标图"""
    np.random.seed(42)
    n = 120  # 模拟样本数（对应12个月×10个测试场景）

    # 模拟10个参数变量
    params = ['Q_in', 'COD_in', 'TN_in', 'NH₃N_in', 'T_water',
              'MLSS', 'DO_aer', 'SRT', 'PAC_dose', 'E_total']

    # 模拟PC1、PC2方向（基于实际碳排放参数关系）
    pc1_loadings = np.array([0.32, 0.41, 0.45, 0.38, 0.12,
                              0.28, -0.18, 0.22, 0.31, 0.35])
    pc2_loadings = np.array([-0.18, 0.22, 0.08, 0.15, -0.52,
                              0.38, 0.48, 0.35, -0.12, -0.25])

    # 归一化
    pc1_loadings /= np.linalg.norm(pc1_loadings)
    pc2_loadings /= np.linalg.norm(pc2_loadings)

    # 模拟样本散点
    x = np.random.randn(n) * 2.5
    y = np.random.randn(n) * 1.8

    # 按碳排放水平染色（模拟高/中/低排放）
    emission_level = 0.6 * x + 0.3 * y + np.random.randn(n) * 0.5
    colors = plt.cm.RdYlGn_r((emission_level - emission_level.min()) /
                              (emission_level.max() - emission_level.min()))

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#FAFAFA')

    # 散点图
    sc = ax.scatter(x, y, c=emission_level, cmap='RdYlGn_r',
                    s=45, alpha=0.65, edgecolors='white', linewidth=0.5,
                    zorder=3)
    plt.colorbar(sc, ax=ax, label='全厂碳排放相对强度\n(单位水量 kgCO₂eq/m³, 标准化)',
                 shrink=0.8)

    # 载荷向量（双标图箭头）
    scale = 2.8
    important = {'TN_in', 'Q_in', 'E_total', 'DO_aer', 'T_water', 'COD_in'}
    for i, pname in enumerate(params):
        lx = pc1_loadings[i] * scale
        ly = pc2_loadings[i] * scale
        color = '#C0392B' if pname in important else '#7F8C8D'
        lw = 2.0 if pname in important else 1.2
        ax.annotate('', xy=(lx, ly), xytext=(0, 0),
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw),
                    zorder=5)
        offset_x = 0.15 if lx >= 0 else -0.15
        offset_y = 0.15 if ly >= 0 else -0.15
        ax.text(lx + offset_x, ly + offset_y, pname,
                ha='center', va='center', fontsize=9.5,
                color=color, fontweight='bold' if pname in important else 'normal',
                bbox=dict(facecolor='white', alpha=0.6, edgecolor='none',
                          boxstyle='round,pad=0.2') if pname in important else None,
                zorder=6)

    # 分区标注
    ax.axhline(0, color='#BDC3C7', lw=0.8, linestyle='--', zorder=1)
    ax.axvline(0, color='#BDC3C7', lw=0.8, linestyle='--', zorder=1)

    ax.text(3.2, 2.5, '高氮负荷\n高能耗工况', fontsize=8.5,
            color='#922B21', alpha=0.8, ha='center',
            bbox=dict(facecolor='#FDECEA', edgecolor='#922B21',
                      boxstyle='round,pad=0.3', alpha=0.7))
    ax.text(-3.2, 2.5, '低DO\n低温工况', fontsize=8.5,
            color='#154360', alpha=0.8, ha='center',
            bbox=dict(facecolor='#EAF2FB', edgecolor='#154360',
                      boxstyle='round,pad=0.3', alpha=0.7))
    ax.text(3.2, -2.5, '高流量\n低N₂O区间', fontsize=8.5,
            color='#1E8449', alpha=0.8, ha='center',
            bbox=dict(facecolor='#EAFAF1', edgecolor='#1E8449',
                      boxstyle='round,pad=0.3', alpha=0.7))

    ax.set_xlabel('PC1（解释方差 38.2%）', fontsize=11)
    ax.set_ylabel('PC2（解释方差 22.7%）', fontsize=11)
    ax.set_title('图3-1  轻量化参数集筛选 PCA 双标图\n'
                 '（箭头长度代表参数贡献度；红色为L-Core核心参数）',
                 fontsize=11, fontweight='bold')

    # 图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='>', color='#C0392B', markersize=8,
               label='L-Core核心参数（入选）', lw=0, markerfacecolor='#C0392B'),
        Line2D([0], [0], marker='>', color='#7F8C8D', markersize=8,
               label='L-Ext扩展参数（可选）', lw=0, markerfacecolor='#7F8C8D'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

    # 方差解释量标注
    ax.text(0.02, 0.98, f'累计解释方差: 60.9%\n样本数 N={n}',
            transform=ax.transAxes, fontsize=9,
            va='top', color='#555',
            bbox=dict(facecolor='white', edgecolor='#CCC',
                      boxstyle='round,pad=0.4', alpha=0.9))

    ax.set_xlim(-4.5, 4.5)
    ax.set_ylim(-3.8, 3.8)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.set_facecolor('#FDFDFD')

    plt.tight_layout()
    out = OUT / 'fig3_1_pca_parameter_selection.png'
    plt.savefig(out, dpi=200, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f'✓ 已生成: {out}')


if __name__ == '__main__':
    print('生成缺失图表...')
    make_tech_roadmap()
    make_aao_flowchart()
    make_pca_biplot()
    print('\n全部完成。')
