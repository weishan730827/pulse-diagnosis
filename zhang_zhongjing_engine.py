#!/usr/bin/env python3
"""
张仲景六经辨证匹配引擎 v1
方法：六经提纲锁定 → 变证细化 → 方证索引。纯原文，不做发挥。
输入：勾选的症状ID列表
输出：六经归属 + 变证 + 候选方剂
"""

import json
import os
from typing import Dict, List

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张仲景六经辨证勾选表_v1.json")
SKILLS_PATH = os.path.join(_OUTPUT_DIR, "zhang_zhongjing_skills_v1.json")


class ZhangZhongJingEngine:
    """张仲景引擎：原文症状 → 六经锁定 → 方证"""

    JING_NAMES = ["太阳", "阳明", "少阳", "太阴", "少阴", "厥阴"]
    JING_PREFIX = {"zzj_ty": "太阳", "zzj_zf": "太阳", "zzj_sh": "太阳",
                   "zzj_ym": "阳明", "zzj_sy": "少阳", "zzj_tyin": "太阴",
                   "zzj_syin": "少阴", "zzj_jy": "厥阴"}

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self._id_map: Dict[str, Dict] = {}
        self._build_maps()

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

    def _build_maps(self):
        for section in self.data["step1_六经提纲"]["sections"]:
            label = section["label"]
            for item in section.get("items", []):
                sid = item["id"]
                self._id_map[sid] = {"text": item["text"], "label": label}

        for item in self.data["step2_太阳变证"]["items"]:
            self._id_map[item["id"]] = {"text": item["text"], "label": "太阳变证"}

        for item in self.data["step3_坏病兼证"]["items"]:
            self._id_map[item["id"]] = {"text": item["text"], "label": "坏病兼证"}

    def diagnose(self, checked_ids: List[str]) -> Dict:
        jing_hits: Dict[str, List[str]] = {j: [] for j in self.JING_NAMES}
        bianzheng_hits: List[str] = []
        huaibing_hits: List[str] = []
        formulas: Dict[str, int] = {}

        for sid in checked_ids:
            item = self._id_map.get(sid)
            if not item:
                continue
            text = item["text"]

            # 六经归类（按前缀）
            matched = False
            for prefix, jing_name in self.JING_PREFIX.items():
                if sid.startswith(prefix):
                    jing_hits[jing_name].append(text)
                    matched = True
                    break

            if not matched:
                if sid.startswith("zzj_bz_"):
                    bianzheng_hits.append(text)
                elif sid.startswith("zzj_hb_"):
                    huaibing_hits.append(text)

            # 提取方名（→ 后面，兼容有无括号）
            if "→" in text:
                part = text.split("→")[-1].strip()
                # 去掉括号注释
                for sep in ["（", "(", "（"]:
                    if sep in part:
                        part = part.split(sep)[0].strip()
                if part and "无明确方" not in part and "随证治" not in part:
                    formulas[part] = formulas.get(part, 0) + 1

        # --- 合病判定 ---
        scored = [(j, len(items)) for j, items in jing_hits.items() if items]
        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            locked_jing = "未锁定"
            hebing = None
            locked_items = []
        elif len(scored) >= 2 and scored[1][1] >= 1 and scored[0][1] >= 1:
            # 多个六经同时有信号 → 可能为合病
            top2 = scored[:2]
            if top2[1][1] >= top2[0][1] * 0.5:  # 次高≥最高50%才有合病价值
                hebing = f"{top2[0][0]}合{top2[1][0]}"
            else:
                hebing = None
            locked_jing = scored[0][0]
            locked_items = jing_hits[locked_jing]
        else:
            locked_jing = scored[0][0]
            hebing = None
            locked_items = jing_hits[locked_jing]

        ranked_fang = sorted(formulas.items(), key=lambda x: x[1], reverse=True)

        return {
            "locked_jing": locked_jing,
            "hebing": hebing,
            "jing_scores": {j: len(v) for j, v in jing_hits.items()},
            "locked_items": locked_items,
            "all_jing_hits": {j: v for j, v in jing_hits.items() if v},
            "bianzheng": bianzheng_hits,
            "huaibing": huaibing_hits,
            "formulas": ranked_fang
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 张仲景六经辨证结果 ===")
        if result["hebing"]:
            lines.append(f"六经锁定: {result['locked_jing']}  【合病: {result['hebing']}】")
        else:
            lines.append(f"六经锁定: {result['locked_jing']}")

        if result["locked_items"]:
            lines.append(f"\n【{result['locked_jing']}病命中症状】({len(result['locked_items'])} 项)")
            for t in result["locked_items"]:
                lines.append(f"  - {t}")

        if result["bianzheng"]:
            lines.append(f"\n【变证】({len(result['bianzheng'])} 项)")
            for t in result["bianzheng"]:
                lines.append(f"  - {t}")

        if result["huaibing"]:
            lines.append(f"\n【坏病/兼证】({len(result['huaibing'])} 项)")
            for t in result["huaibing"]:
                lines.append(f"  - {t}")

        if result["formulas"]:
            lines.append(f"\n【候选方剂】")
            for f, c in result["formulas"]:
                lines.append(f"  → {f} (命中 {c})")
                skill = self._match_skill(f)
                if skill:
                    lines.append(f"    【Skill蒸馏 {skill['id']}】{skill['group']}")
                    lines.append(f"      辨证逻辑: {skill['core_logic'][:120]}...")
                    lines.append(f"      基础方药: {skill['base']}")
                    if skill.get("if_then"):
                        for rule in skill["if_then"][:3]:
                            lines.append(f"        · {rule['if']} → {rule['then']}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangZhongJingEngine()
    print(f"已加载 {len(engine._id_map)} 项")

    # 太阳中风 → 桂枝汤
    test = ["zzj_ty_mai_fu", "zzj_ty_ehan", "zzj_zf_fare",
            "zzj_zf_hanchu", "zzj_zf_efeng", "zzj_zf_maihuan"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
