#!/usr/bin/env python3
"""
陈建国三部九候脉诊辨证匹配引擎 v1
方法：18格脉签名（左右寸关尺×浮中沉）→ 组合匹配 → 方证输出
输入：list of (grid_id, pulse_type) tuples
输出：匹配的脉签名 + 推荐方剂
"""

import json
import os
from typing import Dict, List, Tuple

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "陈建国三部九候脉诊辨证勾选表_v1.json")


class ChenJianGuoEngine:
    """陈建国引擎：18格脉签名 → 方证映射"""

    # 18个脉位标准名
    GRID_NAMES = {
        "cjq_cun_zuo_fu": "左寸浮", "cjq_cun_zuo_zhong": "左寸中", "cjq_cun_zuo_chen": "左寸沉",
        "cjq_cun_you_fu": "右寸浮", "cjq_cun_you_zhong": "右寸中", "cjq_cun_you_chen": "右寸沉",
        "cjq_guan_zuo_fu": "左关浮", "cjq_guan_zuo_zhong": "左关中", "cjq_guan_zuo_chen": "左关沉",
        "cjq_guan_you_fu": "右关浮", "cjq_guan_you_zhong": "右关中", "cjq_guan_you_chen": "右关沉",
        "cjq_chi_zuo_fu": "左尺浮", "cjq_chi_zuo_zhong": "左尺中", "cjq_chi_zuo_chen": "左尺沉",
        "cjq_chi_you_fu": "右尺浮", "cjq_chi_you_zhong": "右尺中", "cjq_chi_you_chen": "右尺沉",
    }

    # 标准脉签名 → 方证（从陈建国体系提取）
    SIGNATURE_MAP = {
        "左寸浮细+左关沉弦+左尺沉弱": "柴胡桂枝干姜汤",
        "右寸浮数+右关沉弱+右尺沉细": "竹叶石膏汤",
        "右寸浮大+右关沉紧+右尺沉弱": "桂枝汤",
        "左寸沉弱+左关沉弦+左尺沉弱": "四逆散",
        "右寸浮滑+右关沉弱+右尺沉细": "半夏泻心汤",
        "左寸沉细+左关沉弦+左尺沉弱": "当归四逆汤",
        "左关弦大+右关沉": "大柴胡汤",
        "右寸浮紧+右关沉": "麻黄汤",
    }

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def diagnose(self, grid_values: Dict[str, str]) -> Dict:
        """
        输入：{grid_id: pulse_type}  例如：{"cjq_cun_zuo_fu": "细", "cjq_guan_zuo_chen": "弦", ...}
        """
        # 构建简化签名：只取有值的非空位
        signature_parts = []
        for grid_id, pulse in grid_values.items():
            if pulse and grid_id in self.GRID_NAMES:
                signature_parts.append(f"{self.GRID_NAMES[grid_id]}{pulse}")

        raw_sig = "+".join(signature_parts)

        # 匹配标准签名
        matched_fangs: Dict[str, float] = {}
        for sig, fang in self.SIGNATURE_MAP.items():
            sig_terms = sig.split("+")
            hits = sum(1 for term in sig_terms if term in raw_sig)
            if hits > 0:
                coverage = hits / len(sig_terms)
                matched_fangs[fang] = coverage

        ranked = sorted(matched_fangs.items(), key=lambda x: x[1], reverse=True)

        return {
            "grid_signature": raw_sig,
            "filled_positions": len(grid_values),
            "matched_formulas": ranked
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 陈建国三部九候脉诊辨证结果 ===")
        lines.append(f"脉签名: {result['grid_signature']}")
        lines.append(f"已填脉位: {result['filled_positions']}/18")
        lines.append("")

        if result["matched_formulas"]:
            lines.append("【方证匹配】")
            for fang, coverage in result["matched_formulas"]:
                pct = f"{coverage*100:.0f}%"
                lines.append(f"  → {fang} (覆盖度 {pct})")
        else:
            lines.append("【未匹配到标准签名，需手动辨证】")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ChenJianGuoEngine()

    # 模拟：左寸细、左关弦、左尺弱 → 应匹配 当归四逆汤/四逆散
    test_grid = {
        "cjq_cun_zuo_chen": "细",
        "cjq_guan_zuo_chen": "弦",
        "cjq_chi_zuo_chen": "弱",
        "cjq_guan_you_chen": "弱",
    }
    r = engine.diagnose(test_grid)
    print(engine.format_result(r))
