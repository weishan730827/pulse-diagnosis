#!/usr/bin/env python3
"""
刘渡舟方证辨证匹配引擎 v2（纯仲景方库）
方法：主症→兼症→方证锁定。以"抓主证"为核心，强调方证对应。
     v2：方剂直接对接仲景基座。
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
from formula_utils import is_zhongjing


class LiuDuZhouEngine:
    """刘渡舟引擎：抓主证→方证锁定。全部经方。"""

    # 主证→方剂映射（伤寒论127方精选）
    JING_FANG: Dict[str, List[Tuple[str, str]]] = {
        "发热恶寒": [("麻黄汤", "太阳伤寒"), ("桂枝汤", "太阳中风")],
        "往来寒热": [("小柴胡汤", "半表半里"), ("柴胡桂枝干姜汤", "少阳兼太阴")],
        "大渴": [("白虎加人参汤", "阳明经证"), ("五苓散", "膀胱蓄水")],
        "潮热": [("大承气汤", "阳明腑实"), ("调胃承气汤", "阳明燥结")],
        "下利": [("葛根黄芩黄连汤", "协热下利"), ("理中汤", "太阴虚寒"),
               ("四逆汤", "少阴下利"), ("白头翁汤", "厥阴热利")],
        "心下痞": [("半夏泻心汤", "寒热错杂"), ("大黄黄连泻心汤", "热痞"),
                  ("生姜泻心汤", "水饮食滞"), ("甘草泻心汤", "胃气虚")],
        "呕吐": [("小半夏汤", "痰饮呕逆"), ("吴茱萸汤", "肝胃虚寒"),
                ("小柴胡汤", "少阳呕"), ("大柴胡汤", "少阳阳明呕")],
        "胸胁苦满": [("小柴胡汤", "少阳"), ("大柴胡汤", "少阳阳明")],
        "结胸": [("大陷胸汤", "热实结胸"), ("小陷胸汤", "小结胸")],
        "喘": [("麻黄汤", "风寒束表"), ("麻杏甘石汤", "肺热喘"),
              ("小青龙汤", "外寒内饮"), ("射干麻黄汤", "寒饮郁肺")],
        "身黄": [("茵陈蒿汤", "湿热发黄"), ("栀子柏皮汤", "热重于湿"),
                ("麻黄连轺赤小豆汤", "瘀热在里")],
        "四逆": [("四逆汤", "少阴寒化"), ("当归四逆汤", "血虚寒厥"),
                ("四逆散", "阳郁四逆"), ("通脉四逆汤", "阴盛格阳")],
        "心烦": [("栀子豉汤", "胸膈郁热"), ("黄连阿胶汤", "少阴热化"),
                ("调胃承气汤", "胃热上扰")],
        "腹痛": [("小建中汤", "中焦虚寒"), ("大承气汤", "阳明腑实"),
                ("桂枝加芍药汤", "太阴腹痛"), ("大黄附子汤", "寒实内结")],
        "小便不利": [("五苓散", "蓄水"), ("猪苓汤", "水热互结"),
                    ("真武汤", "阳虚水泛"), ("肾气丸", "肾气不足")],
    }

    # 兼症→细化方证
    NARROWED_FANG: Dict[str, List[Tuple[str, str]]] = {
        "汗出": [("桂枝汤", "表虚"), ("白虎加人参汤", "热迫津出"), ("四逆加人参汤", "亡阳")],
        "无汗": [("麻黄汤", "风寒束表"), ("葛根汤", "项背强几几")],
        "口渴": [("白虎加人参汤", "里热伤津"), ("猪苓汤", "阴虚水热"), ("五苓散", "气化不利")],
        "口苦": [("小柴胡汤", "少阳郁热"), ("大柴胡汤", "少阳阳明")],
        "咽干": [("桔梗汤", "少阴咽痛"), ("猪肤汤", "少阴阴虚")],
        "但欲寐": [("四逆汤", "少阴寒化"), ("麻黄附子细辛汤", "太少两感")],
        "大便硬": [("大承气汤", "阳明腑实"), ("小承气汤", "阳明轻证"), ("麻子仁丸", "脾约")],
        "手足厥冷": [("四逆汤", "少阴寒化"), ("当归四逆汤", "血虚寒凝"), ("四逆散", "阳郁")],
    }

    def diagnose(self, main_symptoms: List[str], side_symptoms: Optional[List[str]] = None) -> Dict:
        side_symptoms = side_symptoms or []
        primary_matches: Dict[str, List[str]] = {}
        for sym in main_symptoms:
            for key, formulas in self.JING_FANG.items():
                if sym in key or key in sym:
                    for fang, rationale in formulas:
                        primary_matches.setdefault(fang, []).append(f"{sym}→{rationale}")

        secondary_matches: Dict[str, List[str]] = {}
        for sym in side_symptoms:
            for key, formulas in self.NARROWED_FANG.items():
                if sym in key or key in sym:
                    for fang, rationale in formulas:
                        secondary_matches.setdefault(fang, []).append(f"{sym}→{rationale}")

        # 交叉评分
        fang_score: Dict[str, int] = {}
        for fang in primary_matches:
            fang_score[fang] = len(primary_matches[fang]) * 2
            if fang in secondary_matches:
                fang_score[fang] += len(secondary_matches[fang])

        for fang in secondary_matches:
            if fang not in fang_score:
                fang_score[fang] = len(secondary_matches[fang])

        ranked = sorted(fang_score.items(), key=lambda x: x[1], reverse=True)
        return {
            "main_symptoms": main_symptoms,
            "side_symptoms": side_symptoms,
            "primary_matches": primary_matches,
            "secondary_matches": secondary_matches,
            "ranked_formulas": ranked,
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 刘渡舟方证辨证结果（纯仲景经方） ===")
        if result["main_symptoms"]:
            lines.append(f"主症: {'、'.join(result['main_symptoms'])}")
        if result["side_symptoms"]:
            lines.append(f"兼症: {'、'.join(result['side_symptoms'])}")
        lines.append("")

        if result["ranked_formulas"]:
            lines.append("【方证推荐】")
            for fang, score in result["ranked_formulas"]:
                rationales = set()
                for r in result["primary_matches"].get(fang, []):
                    rationales.add(r)
                for r in result["secondary_matches"].get(fang, []):
                    rationales.add(r)
                for r in rationales:
                    lines.append(f"  → {fang}  ({r})")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = LiuDuZhouEngine()
    r = engine.diagnose(["发热恶寒", "喘"], ["无汗", "口渴"])
    print(engine.format_result(r))
