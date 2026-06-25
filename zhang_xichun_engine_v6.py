#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v6
辨证流程（还原《医学衷中参西录》实际诊治逻辑 + 六经气化对接仲景全库）：
  第一步：辨气机升降（大气下陷 OR 气机上逆）—— 确定方向，锁定自创方候选池
  第二步：脉象佐证 —— 在方向内确认寒热虚实
  第三步：舌象参合 —— 在方向内进一步锁定
  第四步：兼证细化 —— 精确到具体自创方
  第五步：六经气化映射 —— 对接仲景全库（v3版：30首），张锡纯六经气化视角解读
"""

import json, os, sys
from typing import Dict, List, Tuple

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_OUTPUT = os.path.join(os.path.dirname(_OUTPUT_DIR), "output")
sys.path.insert(0, _PARENT_OUTPUT)
from formula_utils import is_zhongjing, SELF_CREATED

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v3.json")

# 张锡纯自创方（勾选表中实际使用，来源《医学衷中参西录》）
ZHANG_XC_SELF = [
    "升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤",
    "参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "加味麦门冬汤"
]

# 升陷类方池 vs 镇逆类方池
XIAXIAN_POOL = {"升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤"}
SHANGNI_POOL = {"参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "加味麦门冬汤"}

# 仲景方池——v3版从原著核实张锡纯实际使用的30首仲景方
ZHONGJING_POOL = {
    # 太阳 (8首)
    "桂枝汤", "麻黄汤", "葛根汤", "小青龙汤", "大青龙汤",
    "麻杏甘石汤", "越婢汤", "桃核承气汤",
    # 阳明 (10首)
    "白虎汤", "白虎加人参汤", "大承气汤", "小承气汤", "调胃承气汤",
    "大陷胸汤", "小陷胸汤", "栀子豉汤", "竹叶石膏汤", "茵陈蒿汤",
    # 少阳 (2首)
    "小柴胡汤", "大柴胡汤",
    # 太阴 (1首)
    "理中汤",
    # 少阴 (8首)
    "四逆汤", "通脉四逆汤", "白通汤", "真武汤", "附子汤",
    "黄连阿胶汤", "炙甘草汤", "猪苓汤",
    # 厥阴 (3首)
    "乌梅丸", "白头翁汤", "吴茱萸汤",
    # 金匮 (4首)
    "肾气丸", "下瘀血汤", "泻心汤", "麦门冬汤",
}


class ZhangXiChunEngine:
    """张锡纯引擎 v6：先判升降→自创方池 + 六经气化→仲景方池30首，双轨合一评分"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        for step_key in ["step1_升降判定", "step2_脉象判定", "step3_舌诊", "step4_兼证细化",
                         "step5_六经方证映射"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item.get("text", ""),
                        "maps_to": item.get("maps_to", ""),
                        "step": step_key,
                        "direction": item.get("direction", ""),
                        "hardcoded": item.get("hardcoded", False),
                        "zxc_note": item.get("zxc_note", ""),
                        "source": item.get("source", ""),
                    }
        self._section_map = {}
        for step_key in ["step5_六经方证映射"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                self._section_map[section["id"]] = {
                    "label": section.get("label", ""),
                    "zxc_interpretation": section.get("zxc_interpretation", ""),
                }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """张锡纯实际辨证流程：升降→脉→舌→兼证→六经气化（双轨合一）"""
        chain = []

        # ===== 第一步：辨气机升降 =====
        xiaxian_items = []
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
        pulse_fang = {}
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
                chain.append(f"  → 脉证指向（自创）：{'、'.join(pulse_fang.keys())}")

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
                chain.append(f"  → 舌证指向（自创）：{'、'.join(tongue_fang.keys())}")

        # ===== 第四步：兼证细化 =====
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
                chain.append(f"  → 兼证锁定（自创）：{'、'.join(jianzheng_fang.keys())}")

        # ===== 第五步：六经气化映射 → 仲景方池 =====
        zhongjing_fang = {}  # formula -> count
        zhongjing_items = []  # (text, maps_to, zxc_note, source)
        jing_used = set()  # 命中的经

        for sid in checked_ids:
            info = self._id_map.get(sid)
            if not info or info["step"] != "step5_六经方证映射":
                continue
            zhongjing_items.append((info["text"], info["maps_to"], info.get("zxc_note", ""), info.get("source", "")))
            if info["maps_to"] and info["maps_to"] in ZHONGJING_POOL:
                zhongjing_fang[info["maps_to"]] = zhongjing_fang.get(info["maps_to"], 0) + 1
                # 推断该方属于哪条经：按id前缀匹配
                parts = sid.split("_")
                if len(parts) >= 2:
                    prefix = parts[0] + "_" + parts[1]
                    for sec_id in self._section_map:
                        if sec_id.lower() == prefix.upper():
                            jing_used.add(sec_id)

        if zhongjing_items:
            chain.append(f"第五步·六经气化映射：{len(zhongjing_items)}项六经症状勾选（仲景方池30首）")
            for text, fang, note, src in zhongjing_items[:5]:
                extra = f" ({note})" if note else ""
                src_str = f" [{src}]" if src else ""
                chain.append(f"  └ {text} → {fang}{extra}{src_str}")
            if len(zhongjing_items) > 5:
                chain.append(f"  └ ...共{len(zhongjing_items)}项")
            if zhongjing_fang:
                chain.append(f"  → 六经指向（仲景）：{'、'.join(zhongjing_fang.keys())}")

            # 添加张锡纯六经气化解读
            for sec_id in jing_used:
                sec_data = self._section_map.get(sec_id, {})
                if sec_data.get("zxc_interpretation"):
                    chain.append(f"  ★ 张锡纯解读：{sec_data['zxc_interpretation'][:80]}...")

        # ===== 综合评分：自创方（方向池内）+ 仲景方（六经证池） =====
        scores: Dict[str, Dict] = {}  # {fang: {"score": int, "type": "自创"/"仲景", "jing": str}}
        for text, fang in xiaxian_items + shangni_items:
            if fang and fang in pool:
                s = scores.setdefault(fang, {"score": 0, "type": "自创", "jing": ""})
                s["score"] += 3
        for fang, n in pulse_fang.items():
            s = scores.setdefault(fang, {"score": 0, "type": "自创", "jing": ""})
            s["score"] += 2 * n
        for fang, n in tongue_fang.items():
            s = scores.setdefault(fang, {"score": 0, "type": "自创", "jing": ""})
            s["score"] += 2 * n
        for fang, n in jianzheng_fang.items():
            s = scores.setdefault(fang, {"score": 0, "type": "自创", "jing": ""})
            s["score"] += 1 * n
        for fang, n in zhongjing_fang.items():
            s = scores.setdefault(fang, {"score": 0, "type": "仲景", "jing": ""})
            s["score"] += 3 * n

        ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)

        if ranked:
            chain.append(f"\n综合评分（双轨合一）：")
            for fang, info in ranked:
                tag = "【自创】" if info["type"] == "自创" else "【仲景】"
                chain.append(f"  {fang} (评分:{info['score']}) {tag}")
            top_fang = ranked[0][0]
            top_type = ranked[0][1]["type"]
            chain.append(f"\n→ 最终推荐：{top_fang}（{top_type}）")

        return {
            "direction": direction,
            "pool_size": len(pool),
            "xiaxian_items": [t for t, _ in xiaxian_items],
            "shangni_items": [t for t, _ in shangni_items],
            "pulse_texts": pulse_texts,
            "tongue_texts": tongue_texts,
            "jianzheng_texts": jianzheng_texts,
            "zhongjing_items": [t for t, _, _, _ in zhongjing_items],
            "formulas": ranked,
            "chain": chain,
        }

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 张锡纯气机升降辨证结果（v6 自创方+仲景方双轨合一 30首）===")
        lines.append("")
        lines.append("【辨证链】")
        for step in result["chain"]:
            lines.append(f"  {step}")
        lines.append("")
        lines.append(f"【结论】气机模式：{result['direction']}（自创方池{result['pool_size']}方）")
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
        if result["zhongjing_items"]:
            lines.append(f"  六经症状：{'、'.join(result['zhongjing_items'][:6])}")
            if len(result["zhongjing_items"]) > 6:
                lines.append(f"    ...共{len(result['zhongjing_items'])}项")
        if result["formulas"]:
            lines.append(f"\n【方剂推荐（自创+仲景双轨排名）】")
            for fang, info in result["formulas"]:
                score = info["score"]
                tag = "【自创方】" if info["type"] == "自创" else "【仲景方】"
                marker = "★" if result["formulas"].index((fang, info)) == 0 else "  └"
                lines.append(f"  {marker} {fang} (评分:{score}) {tag}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngine()
    print(f"已加载 {len(engine._id_map)} 项（含六经方证映射，仲景方池{len(ZHONGJING_POOL)}首）")
    print("=" * 60)

    print("测试1（纯自创方向）: 气短 + 脉沉弱 + 舌淡白 → 升陷汤")
    test1 = ["zxc_xiaxian_qi_duan", "zxc_mai_chen_ruo", "zxc_she_dan_bai"]
    r1 = engine.diagnose(test1)
    print(engine.format_result(r1))
    print()

    print("=" * 60)
    print("测试2（仲景方向 - 小柴胡汤）: 口苦咽干目眩 + 胸胁苦满 + 脉弦")
    test2 = ["zxc_shaoyang_kou_ku_yan_gan_mu_xuan", "zxc_shaoyang_xiong_lei_ku_man",
             "zxc_shaoyang_mai_xian", "zxc_shaoyang_mo_mo_bu_yu_yin_shi"]
    r2 = engine.diagnose(test2)
    print(engine.format_result(r2))
    print()

    print("=" * 60)
    print("测试3（新增仲景方 - 小青龙汤）: 咳喘白痰 + 干呕 + 脉弦紧")
    test3 = ["zxc_taiyang_xiaoqing_ke_chuan", "zxc_taiyang_xiaoqing_tan_bai",
             "zxc_taiyang_xiaoqing_ke_gan_ou", "zxc_taiyang_xiaoqing_mai_xian_jin"]
    r3 = engine.diagnose(test3)
    print(engine.format_result(r3))
    print()

    print("=" * 60)
    print("测试4（新增仲景方 - 白虎加人参汤）: 大渴引饮不解 + 口燥渴 + 脉洪大无力")
    test4 = ["zxc_yangming_baihu_renshen_da_ke", "zxc_yangming_baihu_renshen_kou_ke",
             "zxc_yangming_baihu_renshen_mai_hong_wu_li"]
    r4 = engine.diagnose(test4)
    print(engine.format_result(r4))
    print()

    print("=" * 60)
    print("测试5（新增仲景方 - 炙甘草汤）: 脉结代 + 心动悸")
    test5 = ["zxc_shaoyin_zhigancao_mai_jie_dai", "zxc_shaoyin_zhigancao_xin_dong_ji"]
    r5 = engine.diagnose(test5)
    print(engine.format_result(r5))
    print()

    print("=" * 60)
    print("测试6（新增仲景方 - 肾气丸）: 虚劳腰痛 + 小便不利 + 脉虚弱")
    test6 = ["zxc_jingui_shenqi_xu_lao_yao_tong", "zxc_jingui_shenqi_xiao_bian_bu_li",
             "zxc_jingui_shenqi_mai_xi_ruo"]
    r6 = engine.diagnose(test6)
    print(engine.format_result(r6))
    print()

    print("=" * 60)
    print("测试7（双轨合一）: 气短乏力 + 发热恶风汗出 + 脉沉弱 → 升陷汤 vs 桂枝汤")
    test7 = ["zxc_xiaxian_qi_duan", "zxc_xiaxian_fa_li", "zxc_mai_chen_ruo",
             "zxc_taiyang_fa_re_wu_feng", "zxc_taiyang_han_chu"]
    r7 = engine.diagnose(test7)
    print(engine.format_result(r7))
