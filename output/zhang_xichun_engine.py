#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v4
辨证流程（还原《医学衷中参西录》实际诊治逻辑）：
  第一步：辨气机升降（大气下陷 OR 气机上逆）—— 确定方向，锁定方剂候选池
  第二步：脉象佐证 —— 在方向内确认寒热虚实
  第三步：舌象参合 —— 在方向内进一步锁定
  第四步：兼证细化 —— 精确到具体方剂
"""

import json, os, sys
from typing import Dict, List, Tuple

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
from formula_utils import is_zhongjing, SELF_CREATED

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v1.json")

# 张锡纯自创方（勾选表中实际使用，来源《医学衷中参西录》）
ZHANG_XC_SELF = [
    "升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤",
    "参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "加味麦门冬汤"
]

# 升陷类方池 vs 镇逆类方池
XIAXIAN_POOL = {"升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤"}
SHANGNI_POOL = {"参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "加味麦门冬汤"}


class ZhangXiChunEngine:
    """张锡纯引擎：先判升降→方向内脉舌兼证锁定"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        for step_key in ["step1_升降判定", "step2_脉象判定", "step3_舌诊", "step4_兼证细化"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item.get("text", ""),
                        "maps_to": item.get("maps_to", ""),
                        "step": step_key,
                        "direction": item.get("direction", ""),
                        "hardcoded": item.get("hardcoded", False),
                    }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """张锡纯实际辨证流程：升降→脉→舌→兼证"""
        chain = []  # 辨证链日志

        # ===== 第一步：辨气机升降 =====
        xiaxian_items = []  # (text, maps_to)
        shangni_items = []

        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info or info["step"] != "step1_升降判定":
                continue
            if "xiaxian" in sid:
                xiaxian_items.append((info["text"], info["maps_to"]))
            elif "shangni" in sid:
                shangni_items.append((info["text"], info["maps_to"]))

        n_xiaxian = len(xiaxian_items)
        n_shangni = len(shangni_items)

        if n_xiaxian > 0 and n_shangni == 0:
            direction = "大气下陷"
            pool = XIAXIAN_POOL
            chain.append(f"第一步·辨升降：勾选{n_xiaxian}项下陷症状，无上逆症状 → 判定为「大气下陷」→ 升陷类方池")
        elif n_shangni > 0 and n_xiaxian == 0:
            direction = "气机冲逆"
            pool = SHANGNI_POOL
            chain.append(f"第一步·辨升降：勾选{n_shangni}项上逆症状，无下陷症状 → 判定为「气机冲逆」→ 镇逆类方池")
        elif n_xiaxian > 0 and n_shangni > 0:
            direction = "升降失调（陷逆同病）"
            pool = XIAXIAN_POOL | SHANGNI_POOL
            chain.append(f"第一步·辨升降：下陷{n_xiaxian}项 + 上逆{n_shangni}项 → 「升降失调」→ 全方池")
        else:
            direction = "升降待判"
            pool = set()
            chain.append("第一步·辨升降：未勾选升降症状 → 无法判定方向")

        # ===== 第二步：脉象佐证 =====
        pulse_fang = {}  # formula -> count
        pulse_texts = []
        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info or info["step"] != "step2_脉象判定":
                continue
            pulse_texts.append(info["text"])
            if info["maps_to"] and info["maps_to"] in pool:
                pulse_fang[info["maps_to"]] = pulse_fang.get(info["maps_to"], 0) + 1

        if pulse_texts:
            chain.append(f"第二步·脉象佐证：{', '.join(pulse_texts)}")
            if pulse_fang:
                chain.append(f"  → 脉证指向：{'、'.join(pulse_fang.keys())}")

        # ===== 第三步：舌象参合 =====
        tongue_fang = {}
        tongue_texts = []
        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info or info["step"] != "step3_舌诊":
                continue
            tongue_texts.append(f"{info['text']}({info['direction']})")
            if info["maps_to"] and info["maps_to"] in pool:
                tongue_fang[info["maps_to"]] = tongue_fang.get(info["maps_to"], 0) + 1

        if tongue_texts:
            chain.append(f"第三步·舌象参合：{'、'.join(tongue_texts)}")
            if tongue_fang:
                chain.append(f"  → 舌证指向：{'、'.join(tongue_fang.keys())}")

        # ===== 第四步：兼证细化锁定 =====
        jianzheng_fang = {}
        jianzheng_texts = []
        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info or info["step"] != "step4_兼证细化":
                continue
            jianzheng_texts.append(info["text"])
            if info["maps_to"] and info["maps_to"] in pool:
                jianzheng_fang[info["maps_to"]] = jianzheng_fang.get(info["maps_to"], 0) + 1

        if jianzheng_texts:
            chain.append(f"第四步·兼证细化：{'、'.join(jianzheng_texts)}")
            if jianzheng_fang:
                chain.append(f"  → 兼证锁定：{'、'.join(jianzheng_fang.keys())}")

        # ===== 综合评分（仅在方向池内） =====
        # 主症权重3 / 脉象权重2 / 舌诊权重2 / 兼证权重1
        scores: Dict[str, int] = {}
        for text, fang in xiaxian_items + shangni_items:
            if fang and fang in pool:
                scores[fang] = scores.get(fang, 0) + 3
        for fang, n in pulse_fang.items():
            scores[fang] = scores.get(fang, 0) + 2 * n
        for fang, n in tongue_fang.items():
            scores[fang] = scores.get(fang, 0) + 2 * n
        for fang, n in jianzheng_fang.items():
            scores[fang] = scores.get(fang, 0) + 1 * n

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if ranked:
            top_fang, top_score = ranked[0]
            chain.append(f"\n综合评分：{' > '.join(f'{f}({s})' for f, s in ranked)}")
            chain.append(f"→ 最终推荐：{top_fang}")

        return {
            "direction": direction,
            "pool_size": len(pool),
            "xiaxian_items": [t for t, _ in xiaxian_items],
            "shangni_items": [t for t, _ in shangni_items],
            "pulse_texts": pulse_texts,
            "tongue_texts": tongue_texts,
            "jianzheng_texts": jianzheng_texts,
            "formulas": ranked,
            "chain": chain,
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 张锡纯气机升降辨证结果（v4 还原《衷中参西录》辨证流程）===")
        lines.append("")
        lines.append("【辨证链】")
        for step in result["chain"]:
            lines.append(f"  {step}")
        lines.append("")
        lines.append(f"【结论】气机模式：{result['direction']}（方池{result['pool_size']}方）")
        if result["xiaxian_items"]:
            lines.append(f"  下陷症状：{'、'.join(result['xiaxian_items'])}")
        if result["shangni_items"]:
            lines.append(f"  上逆症状：{'、'.join(result['shangni_items'])}")
        if result["pulse_texts"]:
            lines.append(f"  脉象：{'、'.join(result['pulse_texts'])}")
        if result["tongue_texts"]:
            lines.append(f"  舌象：{'、'.join(result['tongue_texts'])}")
        if result["jianzheng_texts"]:
            lines.append(f"  兼证：{'、'.join(result['jianzheng_texts'])}")
        if result["formulas"]:
            lines.append(f"\n【方剂推荐】")
            for fang, score in result["formulas"]:
                tag = "【自创方】" if fang in ZHANG_XC_SELF else ""
                marker = "★" if result["formulas"].index((fang, score)) == 0 else "  └"
                lines.append(f"  {marker} {fang} (评分:{score}) {tag}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngine()
    print(f"已加载 {len(engine._id_map)} 项（含舌诊）")
    print("=" * 60)
    print("测试1: 气短 + 脉沉弱 + 舌淡白 → 升陷汤")
    test1 = ["zxc_xiaxian_qi_duan", "zxc_mai_chen_ruo", "zxc_she_dan_bai"]
    r1 = engine.diagnose(test1)
    print(engine.format_result(r1))
    print()
    print("=" * 60)
    print("测试2: 吐血 + 脉洪滑 + 舌红绛 → 寒降汤")
    test2 = ["zxc_shangni_tu_xie", "zxc_mai_hong_hua", "zxc_she_hong_jiang", "zxc_zn_tu_xue_hong_hua"]
    r2 = engine.diagnose(test2)
    print(engine.format_result(r2))
