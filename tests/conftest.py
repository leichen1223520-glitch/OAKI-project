"""
conftest.py — pytest 全局配置与共用 fixture

确保测试从项目根目录运行，中文字符正常显示。
"""
import sys
import os

# 将项目根目录添加到 Python 路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
