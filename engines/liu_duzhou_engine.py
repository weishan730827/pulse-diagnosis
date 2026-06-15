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
    """刘渡舟引擎：十维过筛 → 六经锁定 → 方证（维度逐层缩小）"""

    # 六经基础方阵
    JING_FANG = {
        "太阳经": ["麻黄汤", "桂枝汤", "大青龙汤", "小青龙汤", "五苓散", "桃核承气汤", "桂枝加葛根汤"],
        "阳明经": ["白虎汤", "大承气汤", "调胃承气汤", "茵陈蒿汤", "栀子豉汤", "白虎加人参汤"],
        "少阳经": ["小柴胡汤", "大柴胡汤", "柴胡桂枝干姜汤", "柴胡加龙骨牡蛎汤"],
        "太阴经": ["理中汤", "桂枝人参汤", "厚朴生姜半夏甘草人参汤", "小建中汤"],
        "少阴经": ["四逆汤", "真武汤", "附子汤", "黄连阿胶汤", "猪苓汤", "白通汤"],
        "厥阴经": ["乌梅丸", "当归四逆汤", "吴茱萸汤", "干姜黄芩黄连人参汤"],
    }

    # 表里+寒热+虚实 → 六经方向指引
    DIMENSION_JING = {
        ("表", "寒", "实"): "太阳经",
        ("表", "寒", "虚"): "太阳经",  # 表虚→桂枝汤类仍在太阳
        ("表", "热", "实"): "太阳经",  # 表热→麻杏甘石汤在太阳
        ("里", "热", "实"): "阳明经",
        ("里", "热", "虚"): "少阴经",  # 阴虚内热→黄连阿胶汤
        ("里", "寒", "实"): "厥阴经",  # 寒实→四逆类
        ("里", "寒", "虚"): "少阴经",
        ("半表半里", "热", "实"): "少阳经",
        ("半表半里", "寒", "虚"): "厥阴经",
    }

    # 维度缩小后的方证精准匹配
    NARROWED_FANG = {
        ("太阳经", "表", "寒", "实"): ["麻黄汤", "小青龙汤"],
        ("太阳经", "表", "寒", "虚"): ["桂枝汤", "桂枝加葛根汤"],
        ("太阳经", "表", "热", "实"): ["大青龙汤"],
        ("阳明经", "里", "热", "实"): ["白虎汤", "大承气汤", "调胃承气汤"],
        ("少阳经", "半表半里", "热", "实"): ["小柴胡汤", "大柴胡汤"],
        ("少阴经", "里", "寒", "虚"): ["四逆汤", "真武汤", "附子汤"],
        ("少阴经", "里", "热", "虚"): ["黄连阿胶汤", "猪苓汤"],
        ("太阴经", "里", "寒", "虚"): ["理中汤", "桂枝人参汤"],
        ("厥阴经", "里", "寒", "实"): ["当归四逆汤", "吴茱萸汤"],
        ("厥阴经", "半表半里", "寒", "虚"): ["乌梅丸", "干姜黄芩黄连人参汤"],
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
        """十维顺序过筛：表里→寒热→虚实→六经→方证缩小"""
        hits = []
        jing_hits: Dict[str, int] = {}
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
            text = item["text"]

            if sid.startswith("ldz_bl_"):
                # 表里（单选，取第一个命中即可）
                if biaoli is None:
                    biaoli = text
            elif sid.startswith("ldz_hr_"):
                if hanre is None:
                    hanre = text
            elif sid.startswith("ldz_xs_"):
                if xushi is None:
                    xushi = text
            elif sid.startswith("ldz_qx_"):
                qixue.append(text)
            elif sid.startswith("ldz_jy_"):
                jinye.append(text)
            elif sid.startswith("ldz_zf_"):
                zangfu_hits.append(text)
            elif sid.startswith("ldz_jl_"):
                for jing_name in ["太阳经", "阳明经", "少阳经", "太阴经", "少阴经", "厥阴经"]:
                    if jing_name in text:
                        jing_hits[jing_name] = jing_hits.get(jing_name, 0) + 1
            elif sid.startswith("ldz_bx_"):
                bingxie.append(text)

        # --- 维度过筛：三核心维度提取 ---
        def _shorten(label: str) -> str:
            """截取首字作为类型：表/里/半 或 寒/热 或 虚/实"""
            if not label:
                return ""
            if "表里夹杂" in label:
                return "夹杂"
            if "寒热错杂" in label:
                return "错杂"
            if "真热假寒" in label:
                return "热"
            if "虚实夹杂" in label:
                return "夹杂"
            return label[0] if label else ""

        bl = _shorten(biaoli)
        hr = _shorten(hanre)
        xs = _shorten(xushi)

        # --- 六经锁定：优先用维度推断 ---
        dimension_jing = self.DIMENSION_JING.get((bl, hr, xs))
        if dimension_jing:
            locked_jing = dimension_jing
        elif jing_hits:
            locked_jing = max(jing_hits, key=jing_hits.get)
        else:
            locked_jing = "无法锁定"

        # --- 方证精准缩小 ---
        narrowed = self.NARROWED_FANG.get((locked_jing, bl, hr, xs))
        if narrowed:
            formulas = narrowed
        elif locked_jing in self.JING_FANG:
            formulas = self.JING_FANG[locked_jing][:3]  # 兜底：取前三方
        else:
            formulas = ["无法推荐"]

        # --- 特殊兼证微调 ---
        if "瘀" in " ".join(qixue):
            if "桃核承气汤" in self.JING_FANG.get(locked_jing, []):
                formulas.insert(0, "桃核承气汤（血瘀）")
        if "水" in " ".join(jinye) or "湿" in " ".join(jinye):
            if locked_jing == "太阳经" and "五苓散" not in " ".join(formulas):
                formulas.append("五苓散（水湿）")

        return {
            "locked_jing": locked_jing,
            "biaoli": bl,
            "hanre": hr,
            "xushi": xs,
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

        if result["formulas"]:
            lines.append(f"\n【推荐方剂】（维度过筛后）")
            for f in result["formulas"]:
                lines.append(f"  → {f}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = LiuDuZhouEngine()
    print(f"已加载 {len(engine._id_map)} 项")

    # 模拟太阳表寒实证
    test = ["ldz_bl_biao", "ldz_hr_han", "ldz_xs_shi",
            "ldz_qx_qi_ni", "ldz_zf_fei", "ldz_jl_taiyang", "ldz_bx_feng", "ldz_bx_han"]
    r = engine.diagnose(test)
    print(engine.format_result(r))
