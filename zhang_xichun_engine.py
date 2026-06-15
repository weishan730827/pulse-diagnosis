#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v2（对接仲景基座+自创升陷汤系列）
方法："大气下陷→升提 / 气逆→降逆"二分法，症状→方证。
     v2：方剂对接仲景基座，自创方标注附录。
"""

import json, os, sys
from typing import Dict, List

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
from formula_utils import is_zhongjing, SELF_CREATED

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v1.json")

# 张锡纯自创方
ZHANG_XC_SELF = ["升陷汤", "回阳升陷汤", "理郁升陷汤", "参赭镇气汤", "镇逆汤", "寒降汤", "温降汤"]


class ZhangXiChunEngine:
    """张锡纯引擎：气机升降二分法"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        for step in ["step1_升降判定", "step2_脉象判定", "step3_兼证细化"]:
            for section in self.data.get(step, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item.get("text", ""),
                        "maps_to": item.get("maps_to", ""),
                        "step": step,
                    }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        xiaxian_hits = []
        shangni_hits = []
        fang_hits: Dict[str, int] = {}
        pulse_hits = []

        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info:
                continue
            text = info["text"]
            maps_to = info["maps_to"]
            step = info["step"]

            if step == "step1_升降判定":
                if "xiaxian" in sid:
                    xiaxian_hits.append(text)
                elif "shangni" in sid:
                    shangni_hits.append(text)
                if maps_to:
                    fang_hits[maps_to] = fang_hits.get(maps_to, 0) + 2
            elif step == "step2_脉象判定":
                pulse_hits.append(text)
            elif step == "step3_兼证细化":
                if maps_to:
                    fang_hits[maps_to] = fang_hits.get(maps_to, 0) + 1

        pattern = ""
        if xiaxian_hits and not shangni_hits:
            pattern = "大气下陷"
        elif shangni_hits and not xiaxian_hits:
            pattern = "气机冲逆"
        elif xiaxian_hits and shangni_hits:
            pattern = "升降失调（陷逆同病）"
        else:
            pattern = "升降待判"

        ranked = sorted(fang_hits.items(), key=lambda x: x[1], reverse=True)

        return {
            "pattern": pattern,
            "xiaxian_hits": xiaxian_hits,
            "shangni_hits": shangni_hits,
            "pulse_hits": pulse_hits,
            "formulas": ranked,
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 张锡纯气机升降辨证结果（v2 仲景基座+自创方附录） ===")
        lines.append(f"气机模式: {result['pattern']}")
        lines.append("")
        if result["xiaxian_hits"]:
            lines.append(f"【下陷症状】({len(result['xiaxian_hits'])} 项)")
            for s in result["xiaxian_hits"]:
                lines.append(f"  ↓ {s}")
        if result["shangni_hits"]:
            lines.append(f"\n【上逆症状】({len(result['shangni_hits'])} 项)")
            for s in result["shangni_hits"]:
                lines.append(f"  ↑ {s}")
        if result["formulas"]:
            lines.append(f"\n【方剂推荐】")
            for fang, score in result["formulas"]:
                tag = "【自创方附录】" if fang in ZHANG_XC_SELF else ""
                lines.append(f"  → {fang} {tag}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngine()
    print(f"已加载 {len(engine._id_map)} 项")
    test = ["zxc_xiaxian_qi_duan", "zxc_xiaxian_xiong_men", "zxc_xiaxian_fa_li"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
