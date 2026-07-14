#!/usr/bin/env python3
"""
曹颖甫方证对应辨证匹配引擎 v2（纯仲景方库）
方法：经方实验，方证对应。症状→方剂直接映射。
     v2：全部对接仲景基座。
"""

import json, os, sys
from typing import Dict, List

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
sys.path.insert(0, os.path.join(_OUTPUT_DIR, ".."))
from formula_utils import is_zhongjing


def extract_formula_name(raw: str) -> str:
    import re
    raw = raw.strip()
    raw = re.sub(r'[（(].*?[）)]', '', raw)
    raw = re.sub(r'【.*?】', '', raw)
    return raw.strip()

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "曹颖甫方证对应勾选表_v1.json")


class CaoYingFuEngine:
    """曹颖甫引擎：方证对应。每项症状直接映射一方。"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        self._skills = self._load_skills("cyf_skills_v1.json")
        for section in self.data.get("checklist", {}).get("sections", []):
            for item in section.get("items", []):
                self._id_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "fang": item.get("方", ""),
                }

    def _load_skills(self, filename: str) -> dict:
        path = os.path.join(_OUTPUT_DIR, filename)
        if not os.path.exists(path):
            return {}
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        skill_map = {}
        for item in data:
            if "_meta" in item:
                continue
            core = extract_formula_name(item.get("formula", ""))
            skill_map[core] = item
        return skill_map

    def _match_skill(self, formula_name: str) -> dict:
        core = extract_formula_name(formula_name)
        return self._skills.get(core)

    def diagnose(self, checked_ids: List[str]) -> Dict:
        fang_hits: Dict[str, List[str]] = {}
        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info:
                continue
            fang = info["fang"]
            text = info["text"]
            if fang:
                fang_hits.setdefault(fang, []).append(text)

        ranked = sorted(fang_hits.items(), key=lambda x: len(x[1]), reverse=True)
        return {
            "formulas": [(f, syms) for f, syms in ranked],
            "total_checked": len(checked_ids),
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 曹颖甫经方实验辨证结果（纯仲景方） ===")
        lines.append(f"命中症状: {sum(len(syms) for _, syms in result['formulas'])}/{result['total_checked']}")
        lines.append("")
        if result["formulas"]:
            lines.append("【方证对应】")
            for fang, syms in result["formulas"]:
                tag = "【非仲景方】" if not is_zhongjing(fang) else ""
                lines.append(f"  → {fang} {tag}")
                for s in syms:
                    lines.append(f"      ∟ {s}")
                skill = self._match_skill(fang)
                if skill:
                    lines.append(f"      【Skill蒸馏 {skill['id']}】{skill.get('group','')}")
                    lines.append(f"        基础方: {skill['base']}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = CaoYingFuEngine()
    print(f"已加载 {len(engine._id_map)} 项")
    r = engine.diagnose(["cyf_t_xbq_wh", "cyf_x_xlkm"])
    print(engine.format_result(r))
