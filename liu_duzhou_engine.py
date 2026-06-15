#!/usr/bin/env python3
"""
刘渡舟十论分诊辨证匹配引擎 v1
方法：十维过筛——表里→寒热→虚实→气血→津液→脏腑→经络→六经→病邪→禀赋
输入：勾选的症状ID列表
输出：六经锁定 + 方证推荐
"""

import json
import os
from typing import Dict, List

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "刘渡舟十论分诊辨证勾选表_v1.json")


class LiuDuZhouEngine:
    """刘渡舟引擎：十维过筛 → 六经锁定 → 方证"""

    # 六经与关键症状/脏腑的映射
    JING_FANG = {
        "太阳经": "麻黄汤/桂枝汤/大青龙汤/小青龙汤/五苓散/桃核承气汤",
        "阳明经": "白虎汤/承气汤系列/茵陈蒿汤/栀子豉汤",
        "少阳经": "小柴胡汤/大柴胡汤/柴胡桂枝干姜汤/柴胡加龙骨牡蛎汤",
        "太阴经": "理中汤/桂枝人参汤/厚朴生姜半夏甘草人参汤",
        "少阴经": "四逆汤/真武汤/附子汤/黄连阿胶汤/猪苓汤",
        "厥阴经": "乌梅丸/当归四逆汤/吴茱萸汤/干姜黄芩黄连人参汤",
    }

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self._id_map: Dict[str, Dict] = {}
        self._build_maps()

    def _build_maps(self):
        for step_key in ["step1_十论框架", "step2_脏腑经络", "step3_病邪禀赋"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item["text"],
                        "section": section["id"],
                        "label": section["label"],
                    }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        hits = []
        jing_hits: Dict[str, int] = {}  # 六经名 → 命中数
        zangfu_hits: List[str] = []
        biaoli = None
        hanre = None
        xushi = None
        qixue: List[str] = []
        jinye: List[str] = []
        bingxie: List[str] = []

        for sid in checked_ids:
            item = self._id_map.get(sid)
            if not item:
                continue
            hits.append(item)

            sid_upper = sid.upper()
            text = item["text"]

            # 表里
            if sid.startswith("ldz_bl_"):
                biaoli = text
            # 寒热
            elif sid.startswith("ldz_hr_"):
                hanre = text
            # 虚实
            elif sid.startswith("ldz_xs_"):
                xushi = text
            # 气血
            elif sid.startswith("ldz_qx_"):
                qixue.append(text)
            # 津液
            elif sid.startswith("ldz_jy_"):
                jinye.append(text)
            # 脏腑
            elif sid.startswith("ldz_zf_"):
                zangfu_hits.append(text)
            # 经络/六经
            elif sid.startswith("ldz_jl_"):
                for jing_name in ["太阳经", "阳明经", "少阳经", "太阴经", "少阴经", "厥阴经"]:
                    if jing_name in text:
                        jing_hits[jing_name] = jing_hits.get(jing_name, 0) + 1
            # 病邪
            elif sid.startswith("ldz_bx_"):
                bingxie.append(text)

        # 六经锁定：取命中数最高的
        if jing_hits:
            locked_jing = max(jing_hits, key=jing_hits.get)
            formulas = self.JING_FANG.get(locked_jing, "无对应方")
        else:
            locked_jing = "无法锁定（请在Step2中勾选六经项）"
            formulas = "无"

        return {
            "locked_jing": locked_jing,
            "biaoli": biaoli,
            "hanre": hanre,
            "xushi": xushi,
            "qixue": qixue,
            "jinye": jinye,
            "zangfu": zangfu_hits,
            "bingxie": bingxie,
            "jing_hits": jing_hits,
            "formulas": formulas,
            "total_hits": len(hits)
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 刘渡舟十论分诊辨证结果 ===")
        lines.append(f"六经锁定: {result['locked_jing']}")
        lines.append("")

        if result["biaoli"]:
            lines.append(f"【表里定位】{result['biaoli']}")
        if result["hanre"]:
            lines.append(f"【寒热定性】{result['hanre']}")
        if result["xushi"]:
            lines.append(f"【虚实判定】{result['xushi']}")
        if result["qixue"]:
            lines.append(f"【气血】{'、'.join(result['qixue'])}")
        if result["jinye"]:
            lines.append(f"【津液】{'、'.join(result['jinye'])}")
        if result["zangfu"]:
            lines.append(f"【脏腑】{'、'.join(result['zangfu'])}")
        if result["bingxie"]:
            lines.append(f"【病邪】{'、'.join(result['bingxie'])}")

        if result["jing_hits"]:
            lines.append(f"\n【六经信号分布】")
            for j, c in sorted(result["jing_hits"].items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {j}: {c} 次")

        lines.append(f"\n【候选方剂】{result['formulas']}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = LiuDuZhouEngine()
    print(f"已加载 {len(engine._id_map)} 项")

    # 模拟太阳表寒实证
    test = ["ldz_bl_biao", "ldz_hr_han", "ldz_xs_shi",
            "ldz_qx_qi_ni", "ldz_zf_fei", "ldz_jl_taiyang", "ldz_bx_feng", "ldz_bx_han"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
