#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v1
方法：辨气机升降。大气下陷→升陷类方；气逆不降→镇逆降气类方。
输入：勾选的症状ID列表
输出：升降判定 + 推荐方剂
"""

import json
import os
from typing import Dict, List

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v1.json")


class ZhangXiChunEngine:
    """张锡纯引擎：大气下陷 vs 气机上逆 → 方药锁定"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # 映射：id → {text, direction?, maps_to?}
        self._item_map: Dict[str, Dict] = {}
        self._build_maps()

    def _build_maps(self):
        for section in self.data["step1_升降判定"]["sections"]:
            sec_id = section["id"]
            for item in section.get("items", []):
                # section ZXC_A1 = 大气下陷, ZXC_A2 = 气机上逆
                direction = "大气下陷" if "A1" in sec_id else "气机上逆"
                self._item_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "direction": direction,
                    "maps_to": item.get("maps_to", ""),
                }
        for section in self.data["step2_脉象判定"]["sections"]:
            sec_id = section["id"]
            # ZXC_B1 = 升陷脉, ZXC_B2 = 镇逆脉
            direction = "大气下陷" if "B1" in sec_id else "气机上逆"
            for item in section.get("items", []):
                self._item_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "direction": direction,
                    "maps_to": "",
                }
        for section in self.data["step3_兼证细化"]["sections"]:
            sec_id = section["id"]
            # ZXC_C1 = 升陷兼证, ZXC_C2 = 镇逆兼证
            direction = "大气下陷" if "C1" in sec_id else "气机上逆"
            for item in section.get("items", []):
                self._item_map[item["id"]] = {
                    "text": item.get("text", ""),
                    "direction": direction,
                    "maps_to": item.get("maps_to", ""),
                }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """判定升降 + 推荐方剂"""
        xiaxian_items: List[Dict] = []
        shangni_items: List[Dict] = []
        xiaxian_fangs: Dict[str, int] = {}
        shangni_fangs: Dict[str, int] = {}

        for sid in checked_ids:
            item = self._item_map.get(sid)
            if not item:
                continue

            direction = item["direction"]
            maps_to = item["maps_to"]

            if direction == "大气下陷":
                xiaxian_items.append(item)
                if maps_to:
                    xiaxian_fangs[maps_to] = xiaxian_fangs.get(maps_to, 0) + 1
            elif direction == "气机上逆":
                shangni_items.append(item)
                if maps_to:
                    shangni_fangs[maps_to] = shangni_fangs.get(maps_to, 0) + 1

        # 判定
        xiaxian_score = len(xiaxian_items)
        shangni_score = len(shangni_items)

        if xiaxian_score > shangni_score:
            result = "大气下陷"
            formulas = sorted(xiaxian_fangs.items(), key=lambda x: x[1], reverse=True)
            if not formulas:
                formulas = [("升陷汤", 1)]
        elif shangni_score > xiaxian_score:
            result = "气机上逆"
            formulas = sorted(shangni_fangs.items(), key=lambda x: x[1], reverse=True)
            if not formulas:
                formulas = [("参赭镇气汤", 1)]
        else:
            result = "无法判定（升降信号不足或对等）"
            formulas = []

        return {
            "judgment": result,
            "xiaxian_score": xiaxian_score,
            "shangni_score": shangni_score,
            "xiaxian_items": [i["text"] for i in xiaxian_items],
            "shangni_items": [i["text"] for i in shangni_items],
            "formulas": formulas
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 张锡纯气机升降辨证结果 ===")
        lines.append(f"判定: {result['judgment']}")
        lines.append(f"  下陷信号: {result['xiaxian_score']}  |  上逆信号: {result['shangni_score']}")
        lines.append("")

        if result["xiaxian_items"]:
            lines.append(f"【大气下陷症状】({len(result['xiaxian_items'])} 项)")
            for t in result["xiaxian_items"]:
                lines.append(f"  - {t}")

        if result["shangni_items"]:
            lines.append(f"【气机上逆症状】({len(result['shangni_items'])} 项)")
            for t in result["shangni_items"]:
                lines.append(f"  - {t}")

        if result["formulas"]:
            lines.append(f"\n【推荐方剂】")
            for f, c in result["formulas"]:
                lines.append(f"  → {f} (信号 {c})")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngine()
    print(f"已加载 {len(engine._item_map)} 项")

    # 模拟大气下陷
    test_xiaxian = ["zxc_xiaxian_qi_duan", "zxc_xiaxian_xiong_men",
                    "zxc_xiaxian_fa_li", "zxc_mai_ruo", "zxc_sx_han"]
    r = engine.diagnose(test_xiaxian)
    print(engine.format_result(r))
    print("\n" + "="*50 + "\n")

    # 模拟气机上逆
    test_shangni = ["zxc_shangni_ou_tu", "zxc_shangni_ke_chuan",
                    "zxc_shangni_qi_ni", "zxc_mai_xian",
                    "zxc_zn_xin_fan", "zxc_zn_qi_ni"]
    r2 = engine.diagnose(test_shangni)
    print(engine.format_result(r2))
