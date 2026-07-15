#!/usr/bin/env python3
"""
胡希恕八纲六经辨证匹配引擎 v2（纯仲景方库）
方法：先定八纲（表里阴阳寒热虚实）→再定六经→方证对应。
     v2：纯仲景方，胡老本就不改经方。
"""

import json, os, sys
from typing import Dict, List

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_OUTPUT_DIR, ".."))
from formula_utils import is_zhongjing

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "胡希恕辨证勾选表_v1.json")
SKILLS_PATH = os.path.join(_OUTPUT_DIR, "hu_xishu_skills_v1.json")


class HuXiShuEngine:
    """胡希恕引擎：八纲→六经→方证对应。全仲景方。"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        # step1 八纲定位
        for section in self.data.get("step1_八纲定位", {}).get("sections", []):
            for item in section.get("items", []):
                self._id_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "maps_to": item.get("maps_to", ""),
                    "tags": item.get("tags", []),
                    "step": "八纲",
                }
        # step2 六经细化
        for jing, jing_data in self.data.get("step2_六经细化", {}).items():
            if jing == "description":
                continue
            for item in jing_data.get("细分", []):
                self._id_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "maps_to": item.get("maps_to", ""),
                    "label": item.get("label", ""),
                    "jing": jing,
                    "step": "六经",
                }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        bagang_hits: Dict[str, List[str]] = {}
        liujing_hits: Dict[str, List[str]] = {}
        fangzheng_hits: Dict[str, str] = {}

        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info:
                continue
        self._skills = self._load_skills()

    def _load_skills(self) -> dict:
        if not os.path.exists(SKILLS_PATH):
            return {}
        with open(SKILLS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        skill_map = {}
        for item in data:
            if "_meta" in item:
                continue
            formula_raw = item.get("formula", "")
            core_name = formula_raw.split("（")[0].split("(")[0].strip()
            skill_map[core_name] = item
        return skill_map

    def _match_skill(self, formula_name: str) -> dict:
        return self._skills.get(formula_name)

    def diagnose(self, checked_ids: List[str]) -> Dict:
        bagang_hits: Dict[str, List[str]] = {}
        liujing_hits: Dict[str, List[str]] = {}
        fangzheng_hits: Dict[str, str] = {}

        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info:
                continue
            if info["step"] == "八纲":
                target = info["maps_to"]
                if target:
                    bagang_hits.setdefault(target, []).append(info["text"])
            elif info["step"] == "六经":
                jing = info.get("jing", "未知")
                liujing_hits.setdefault(jing, []).append(info["text"])
                maps_to = info.get("maps_to", "")
                if maps_to:
                    fangzheng_hits.setdefault(maps_to, info.get("label", ""))

        # 锁定六经
        primary_jing = max(liujing_hits, key=lambda k: len(liujing_hits[k])) if liujing_hits else "待定"
        primary_bagang = max(bagang_hits, key=lambda k: len(bagang_hits[k])) if bagang_hits else "待定"

        return {
            "bagang": bagang_hits,
            "primary_bagang": primary_bagang,
            "liujing": liujing_hits,
            "primary_jing": primary_jing,
            "fangzheng": fangzheng_hits,
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 胡希恕八纲六经辨证结果（纯仲景方） ===")
        lines.append(f"八纲定位: {result['primary_bagang']}")
        lines.append(f"六经锁定: {result['primary_jing']}")
        lines.append("")

        if result["bagang"]:
            lines.append("【八纲分布】")
            for b, syms in result["bagang"].items():
                lines.append(f"  {b}: {len(syms)} 症")

        if result["liujing"]:
            lines.append(f"\n【六经细化】({result['primary_jing']} 为主)")
            for j, syms in result["liujing"].items():
                lines.append(f"  [{j}]")
                for s in syms:
                    lines.append(f"    ✓ {s[:50]}...")

        if result["fangzheng"]:
            lines.append(f"\n【方证锁定】")
            for fang, label in result["fangzheng"].items():
                lines.append(f"  → {fang}（{label}）")
                skill = self._match_skill(fang)
                if skill:
                    lines.append(f"    【Skill蒸馏 {skill['id']}】{skill['group']}")
                    lines.append(f"      辨证逻辑: {skill['core_logic']}")
                    lines.append(f"      基础方药: {skill['base']}")
                    if skill.get("if_then"):
                        for rule in skill["if_then"]:
                            lines.append(f"        · {rule['if']} → {rule['then']}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = HuXiShuEngine()
    print(f"已加载 {len(engine._id_map)} 项")
    test = ["biaozheng_etaiyang", "TY_sw_1", "TY_sw_2"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
