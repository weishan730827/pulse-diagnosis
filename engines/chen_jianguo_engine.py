#!/usr/bin/env python3
"""
陈建国三部九候脉诊辨证匹配引擎 v2（对接仲景基座）
方法：18格脉签名（左右寸关尺×浮中沉）→ 组合匹配 → 方证输出。
     v2：方剂全部对接仲景基座（温胆汤→小陷胸汤）。
"""

import json
import os
import sys
from typing import Dict, List, Tuple

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
from formula_utils import is_zhongjing

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "陈建国三部九候脉诊辨证勾选表_v1.json")


class ChenJianGuoEngine:
    """陈建国引擎：18格脉签名 → 仲景方证映射"""

    GRID_NAMES = {
        "cjq_cun_zuo_fu": "左寸浮", "cjq_cun_zuo_zhong": "左寸中", "cjq_cun_zuo_chen": "左寸沉",
        "cjq_cun_you_fu": "右寸浮", "cjq_cun_you_zhong": "右寸中", "cjq_cun_you_chen": "右寸沉",
        "cjq_guan_zuo_fu": "左关浮", "cjq_guan_zuo_zhong": "左关中", "cjq_guan_zuo_chen": "左关沉",
        "cjq_guan_you_fu": "右关浮", "cjq_guan_you_zhong": "右关中", "cjq_guan_you_chen": "右关沉",
        "cjq_chi_zuo_fu": "左尺浮", "cjq_chi_zuo_zhong": "左尺中", "cjq_chi_zuo_chen": "左尺沉",
        "cjq_chi_you_fu": "右尺浮", "cjq_chi_you_zhong": "右尺中", "cjq_chi_you_chen": "右尺沉",
    }

    SIGNATURE_MAP = {
        "左寸浮细+左关沉弦+左尺沉弱": "柴胡桂枝干姜汤",
        "右寸浮紧+右关沉": "麻黄汤",
        "右寸浮大+右关沉紧+右尺沉弱": "桂枝汤",
        "左寸浮+右寸浮+左尺沉": "小青龙汤",
        "右寸浮数+右关沉弱+右尺沉细": "竹叶石膏汤",
        "右关洪大+右尺沉": "白虎汤",
        "右关沉实+左关弦": "大承气汤",
        "左关弦大+右关沉": "大柴胡汤",
        "左关弦细+右关弦+左尺沉": "小柴胡汤",
        "左关弦+右关弦+右寸沉": "柴胡加龙骨牡蛎汤",
        "左寸沉弱+左关沉弦+左尺沉弱": "四逆散",
        "左寸沉细+左关沉弦+左尺沉弱": "当归四逆汤",
        "右尺沉弱+左尺沉弱": "四逆汤",
        "左尺沉细+右尺沉细+左寸浮": "黄连阿胶汤",
        "左寸沉+右寸沉+左尺浮": "真武汤",
        "右关沉弱+左关沉+右尺沉": "理中汤",
        "右关沉弱+右寸沉": "桂枝人参汤",
        "左关弦细+右关弦+左尺沉细": "乌梅丸",
        "左关弦紧+左尺沉弱": "吴茱萸汤",
        "左寸浮滑+右寸浮滑+左尺沉": "半夏泻心汤",
        "右关沉弱+右寸滑+左关弦": "半夏厚朴汤",
        "左关沉弦+右关沉滑": "小陷胸汤",
        "左尺沉弱+右关沉": "肾气丸",
        "左寸沉+右寸浮+右关滑": "苓桂术甘汤",
    }

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._sig_len_map = {fang: len(sig.split("+"))
                             for sig, fang in self.SIGNATURE_MAP.items()}

    def diagnose(self, grid_values: Dict[str, str]) -> Dict:
        signature_parts = []
        for grid_id, pulse in grid_values.items():
            if pulse and grid_id in self.GRID_NAMES:
                signature_parts.append(f"{self.GRID_NAMES[grid_id]}{pulse}")
        raw_sig = "+".join(signature_parts)
        matched_fangs: Dict[str, float] = {}
        for sig, fang in self.SIGNATURE_MAP.items():
            sig_terms = sig.split("+")
            hits = sum(1 for term in sig_terms if term in raw_sig)
            if hits > 0:
                coverage = hits / len(sig_terms)
                matched_fangs[fang] = coverage
        ranked = sorted(matched_fangs.items(),
                       key=lambda x: (x[1], self._sig_len_map.get(x[0], 0)),
                       reverse=True)
        bilateral = self._bilateral_analysis(grid_values)
        return {
            "grid_signature": raw_sig,
            "filled_positions": len(grid_values),
            "matched_formulas": ranked,
            "bilateral": bilateral,
        }

    def _bilateral_analysis(self, grid_values):
        pairs = [
            ("左寸", "cjq_cun_zuo_fu", "cjq_cun_zuo_zhong", "cjq_cun_zuo_chen",
             "右寸", "cjq_cun_you_fu", "cjq_cun_you_zhong", "cjq_cun_you_chen"),
            ("左关", "cjq_guan_zuo_fu", "cjq_guan_zuo_zhong", "cjq_guan_zuo_chen",
             "右关", "cjq_guan_you_fu", "cjq_guan_you_zhong", "cjq_guan_you_chen"),
            ("左尺", "cjq_chi_zuo_fu", "cjq_chi_zuo_zhong", "cjq_chi_zuo_chen",
             "右尺", "cjq_chi_you_fu", "cjq_chi_you_zhong", "cjq_chi_you_chen"),
        ]
        findings = []
        for pos_left, lf_id, lz_id, lc_id, pos_right, rf_id, rz_id, rc_id in pairs:
            left_pulses = set()
            right_pulses = set()
            for gid, val in grid_values.items():
                if gid in (lf_id, lz_id, lc_id) and val:
                    left_pulses.add(val)
                if gid in (rf_id, rz_id, rc_id) and val:
                    right_pulses.add(val)
            if not left_pulses and not right_pulses:
                continue
            if left_pulses and not right_pulses:
                findings.append(f"{pos_left}有脉（{'/'.join(left_pulses)}），{pos_right}未填")
            elif right_pulses and not left_pulses:
                findings.append(f"{pos_right}有脉（{'/'.join(right_pulses)}），{pos_left}未填")
            elif left_pulses != right_pulses:
                findings.append(f"{pos_left}（{'/'.join(left_pulses)}）≠ {pos_right}（{'/'.join(right_pulses)}）")
        return {"findings": findings, "summary": "左右均衡" if not findings else f"共 {len(findings)} 处左右不均衡"}

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 陈建国三部九候脉诊辨证结果（仲景方库） ===")
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
        if result.get("bilateral", {}).get("findings"):
            lines.append(f"\n【左右对比】{result['bilateral']['summary']}")
            for f in result["bilateral"]["findings"]:
                lines.append(f"  ⇄ {f}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ChenJianGuoEngine()
    test_grid = {
        "cjq_cun_zuo_chen": "细",
        "cjq_guan_zuo_chen": "弦",
        "cjq_chi_zuo_chen": "弱",
        "cjq_guan_you_chen": "弱",
    }
    r = engine.diagnose(test_grid)
    print(engine.format_result(r))
