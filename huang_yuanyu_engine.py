#!/usr/bin/env python3
"""
黄元御一气周流辨证匹配引擎 v1
方法：中气为轴，四维为轮。中气判定→左升右降→方药锁定。
输入：勾选的症状ID列表
输出：中气判定 + 升陷判定 + 推荐方剂
"""

import json
import os
from typing import Dict, List

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "黄元御一气周流辨证勾选表_v1.json")


class HuangYuanYuEngine:
    """黄元御引擎：一气周流，中气→四维→方药"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self._id_map: Dict[str, Dict] = {}
        self._build_maps()

    def _build_maps(self):
        for step_key in ["step1_中气轴心", "step2_四维升降", "step3_方药映射"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item.get("text", ""),
                        "section_id": section.get("id", ""),
                    }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        zhongqi: List[str] = []
        left_lu: List[str] = []
        right_lu: List[str] = []
        transition: List[str] = []
        fangzheng: List[str] = []

        for sid in checked_ids:
            item = self._id_map.get(sid)
            if not item:
                continue
            text = item["text"]
            sec = item["section_id"]

            if "A1" in sec:          # 中气
                zhongqi.append(text)
            elif "B1" in sec:        # 左路
                left_lu.append(text)
            elif "B2" in sec:        # 右路
                right_lu.append(text)
            elif "B3" in sec:        # 过渡
                transition.append(text)
            elif "C1" in sec:        # 方证
                fangzheng.append(text)

        # 中气判定
        if zhongqi:
            zhongqi_status = "中气不运" if any("脾虚" in t or "胃逆" in t for t in zhongqi) else "中气待查"
        else:
            zhongqi_status = "未勾选中气项（黄元御体系要求优先判定中气）"

        # 升陷判定
        if len(left_lu) > len(right_lu):
            sheng_jiang = "左路升发不足（肝木不升/肾水不温为主）"
        elif len(right_lu) > len(left_lu):
            sheng_jiang = "右路肃降不足（肺金不降/心火不下为主）"
        else:
            sheng_jiang = "左右均衡"

        # 方药推荐
        formulas = []
        ext_text = " ".join(zhongqi + left_lu + right_lu + transition)
        if "脾虚" in ext_text or "便溏" in ext_text:
            formulas.append("苓桂术甘汤（健脾利水）")
        if "肝" in ext_text and ("郁" in ext_text or "胁痛" in ext_text):
            formulas.append("四逆散（疏肝理气）")
        if "胃" in ext_text and ("逆" in ext_text or "呕" in ext_text):
            formulas.append("旋覆代赭汤（降逆和胃）")
        if "肺" in ext_text and ("逆" in ext_text or "咳" in ext_text):
            formulas.append("泻白散（清肺降气）")
        if "心" in ext_text and "烦" in ext_text:
            formulas.append("黄连阿胶汤（交通心肾）")

        return {
            "zhongqi_status": zhongqi_status,
            "zhongqi_items": zhongqi,
            "sheng_jiang": sheng_jiang,
            "left_items": left_lu,
            "right_items": right_lu,
            "transition_items": transition,
            "fangzheng_items": fangzheng,
            "formulas": formulas
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 黄元御一气周流辨证结果 ===")
        lines.append(f"中气判定: {result['zhongqi_status']}")
        lines.append(f"升降判定: {result['sheng_jiang']}")
        lines.append("")

        if result["zhongqi_items"]:
            lines.append(f"【中气症状】({len(result['zhongqi_items'])} 项)")
            for t in result["zhongqi_items"]:
                lines.append(f"  - {t}")
        if result["left_items"]:
            lines.append(f"\n【左路（肝木升发+肾水）】({len(result['left_items'])} 项)")
            for t in result["left_items"]:
                lines.append(f"  - {t}")
        if result["right_items"]:
            lines.append(f"\n【右路（肺金肃降+心火）】({len(result['right_items'])} 项)")
            for t in result["right_items"]:
                lines.append(f"  - {t}")
        if result["formulas"]:
            lines.append(f"\n【推荐方剂】")
            for f in result["formulas"]:
                lines.append(f"  → {f}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = HuangYuanYuEngine()
    print(f"已加载 {len(engine._id_map)} 项")

    test = ["hyy_zq_pi_xu", "hyy_zl_le_gan_yu", "hyy_yl_fe_qi_ni",
            "hyy_gd_bu_tong", "hyy_fz_xiang", "hyy_fz_gan_yu", "hyy_fz_wei_ni"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
