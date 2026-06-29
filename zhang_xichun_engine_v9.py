#!/usr/bin/env python3
"""
张锡纯气机升降辨证引擎 v9
基于决策树五步辨证流程 + v7脉案数据（772案，含关前→寸部映射）

五步辨证漏斗：
  第一步：辨气机升降 —— 下陷/上逆/中性，锁定方池方向
  第二步：脉诊虚实寒热 —— 有力无力（真假有力）、浮沉表里、数迟寒热
  第三步：左右对比定脏腑 —— 右>左降逆、左>右平肝、弦脉细分
  第四步：尺部定根虚里证神 —— 尺部候根、虚里候神，决预后
  第五步：方证锁定 —— 综合评分，输出推荐方剂

原著依据：《医学衷中参西录》决策树 v2.0
数据来源：pulse_cases_v7.json（772案全量，含关前→寸部映射）
"""

import json, os, sys
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# ===================== 方池定义 =====================

# 自创方——升陷类
XIAXIAN_FORMULAS = {
    "升陷汤": {
        "indications": ["大气下陷", "气短不足以息", "努力呼吸似喘", "脉沉迟微弱", "关前尤甚"],
        "composition": "生黄芪、知母、桔梗、柴胡、升麻",
        "tier": "primary"
    },
    "回阳升陷汤": {
        "indications": ["大气下陷", "心肺阳虚", "身冷", "背紧", "恶寒"],
        "composition": "生黄芪、干姜、当归身、桂枝炭、甘草",
        "tier": "variant"
    },
    "理郁升陷汤": {
        "indications": ["大气下陷", "气分郁结", "胸中满痛", "胁胀", "经络湮淤"],
        "composition": "生黄芪、知母、当归身、桂枝尖、柴胡、乳香、没药",
        "tier": "variant"
    },
    "醒脾升陷汤": {
        "indications": ["大气下陷", "脾气虚极", "小便不禁"],
        "composition": "生黄芪、白术、桑寄生、川断、萸肉、龙骨、牡蛎、川萆薢、甘草",
        "tier": "variant"
    },
}

# 自创方——镇逆类
SHANGNI_FORMULAS = {
    "参赭镇气汤": {
        "indications": ["冲气上冲", "阴分虚甚", "喘逆迫促", "阴阳两虚"],
        "composition": "野台参、生赭石、生芡实、生山药、萸肉、清半夏、茯苓",
        "tier": "primary"
    },
    "镇逆汤": {
        "indications": ["冲胃并逆", "呕吐", "胃气上逆", "呃逆"],
        "composition": "生赭石、清半夏、生姜、竹茹等",
        "tier": "variant"
    },
    "寒降汤": {
        "indications": ["吐衄", "脉洪滑", "因热胃气不降"],
        "composition": "生赭石、清半夏、瓜蒌仁、生杭芍、竹茹、牛蒡子、粉甘草",
        "tier": "conditional"
    },
    "温降汤": {
        "indications": ["吐衄", "脉虚濡", "脉迟", "因寒胃气不降"],
        "composition": "生赭石、清半夏、干姜、白术等",
        "tier": "conditional"
    },
    "清降汤": {
        "indications": ["吐衄", "阴分亏损"],
        "composition": "生赭石、清半夏等",
        "tier": "conditional"
    },
    "保元寒降汤": {
        "indications": ["吐衄", "气分虚甚"],
        "composition": "生赭石、野台参、生地黄等",
        "tier": "conditional"
    },
    "保元清降汤": {
        "indications": ["吐衄", "下元虚损"],
        "composition": "生赭石、野台参、生芡实等",
        "tier": "conditional"
    },
    "秘红丹": {
        "indications": ["吐衄", "肝郁", "多怒"],
        "composition": "川大黄、油肉桂、生赭石",
        "tier": "conditional"
    },
    "薯蓣纳气汤": {
        "indications": ["阴虚不纳气", "喘逆"],
        "composition": "生山药、大熟地、萸肉、柿霜饼等",
        "tier": "variant"
    },
    "滋培汤": {
        "indications": ["虚劳喘逆", "饮食减少"],
        "composition": "生山药、于术、广陈皮等",
        "tier": "variant"
    },
}

# 仲景方——张锡纯六经气化视角
ZHONGJING_FORMULAS = {
    "桂枝汤": {"indications": ["太阳中风", "关前浮关后弱", "阳浮阴弱"], "category": "太阳"},
    "麻黄汤": {"indications": ["太阳伤寒", "无汗", "脉浮紧"], "category": "太阳"},
    "白虎汤": {"indications": ["阳明热", "脉洪滑", "大热"], "category": "阳明"},
    "大承气汤": {"indications": ["阳明腑实", "大便燥结", "脉沉实"], "category": "阳明"},
    "小柴胡汤": {"indications": ["少阳枢机不利", "胸胁苦满"], "category": "少阳"},
    "理中汤": {"indications": ["太阴中焦虚寒"], "category": "太阴"},
    "四逆汤": {"indications": ["少阴寒化", "脉沉微"], "category": "少阴"},
    "黄连阿胶汤": {"indications": ["少阴热化", "阴虚阳浮"], "category": "少阴"},
    "乌梅丸": {"indications": ["厥阴气机逆乱", "寒热错杂"], "category": "厥阴"},
}

ALL_ZXC_SELF = set(XIAXIAN_FORMULAS.keys()) | set(SHANGNI_FORMULAS.keys())


# ===================== 力度分级量尺 =====================
FORCE_GRADE = {
    "偏虚": {"level": 1, "desc": "力稍弱，尚清晰可辨"},
    "弱": {"level": 2, "desc": "弱脉——沉位+软，按之无力"},
    "微弱": {"level": 3, "desc": "微+弱递进——极虚似有似无+沉位无力"},
    "极微弱": {"level": 4, "desc": "脉力极虚，几不可触"},
    "无脉": {"level": 5, "desc": "重按至骨亦无搏动"},
}

# 升陷汤命中条件：寸部脉力 >= 微弱(level 3) 且位置 = 沉
SHENGXIAN_CUN_FORCE_THRESHOLD = 3

# ===================== 决策树规则集 =====================

# 第一步：气机升降症状关键词
SINKING_KEYWORDS = [
    "短气", "不足以息", "努力呼吸", "气息将停", "气短不足以息",
    "呼气困难", "气短", "呼吸有声不肩息", "下坠",
    "乏力", "神昏健忘", "声颤身动", "寒热往来",
    "常常呵欠", "肢体痿废", "二便不禁",
]

COUNTERFLOW_KEYWORDS = [
    "气上冲", "冲气上冲", "上逆", "呃逆", "呕逆",
    "呕吐", "头胀", "胸满", "吸气困难", "肩息",
    "哕气", "腹中膨闷", "头目眩晕",
    "大便燥结",  # 胃气不降，传送失职
    "饮食不下", "阻塞饮食",
]

# 第二步：脉象规则
PULSE_FORCE_TRUE_STRONG = ["洪", "滑"]  # 真有力需洪滑兼具
PULSE_FORCE_FAKE_STRONG = ["弦硬", "弦直", "弦长有力"]  # 假有力——弦直无起伏
PULSE_FORCE_WEAK = ["弱", "微", "细", "无力", "虚", "濡", "沉弱", "微弱"]
PULSE_GEMAI_DANGER = ["革脉", "大而不洪", "有力不滑", "外硬中空"]  # 革脉——阴阳离绝

PULSE_FLOAT = ["浮", "浮弦", "浮芤", "浮而无力"]
PULSE_SINK = ["沉", "沉迟", "沉细", "沉弱"]

PULSE_RAPID = ["数", "数近", "至数"]  # 数脉
PULSE_SLOW = ["迟", "迟缓"]  # 迟脉

# 第三步：左右对比规则
RIGHT_GREATER_LEFT = ["右脉弦硬而长", "右大于左", "右脉>左脉", "右脉弦硬有力长"]
LEFT_GREATER_RIGHT = ["左脉弦硬", "左大于右", "左脉>右脉", "左脉弦硬有力长"]

XUAN_MAI_MAP = {
    "左脉弦细无力": {"direction": "升陷", "mechanism": "肝血虚、大气下陷"},
    "左脉弦硬有力长": {"direction": "镇逆+滋阴", "mechanism": "肝肾阴亏、阴虚不能潜阳"},
    "左脉弦细硬_右脉濡沉": {"direction": "化饮健脾", "mechanism": "湿痰留饮，中焦气化不足"},
    "右脉弦细无力": {"direction": "健脾+疏肝", "mechanism": "土为木伤、脾胃失运"},
    "右脉弦硬有力长": {"direction": "镇冲降胃", "mechanism": "冲气上冲、胃气不降"},
    "左右脉弦细无力": {"direction": "双补气血", "mechanism": "气血两亏、阴阳两虚"},
    "左右脉弦硬有力长": {"direction": "滋阴平肝", "mechanism": "阴分有亏、肝木过盛"},
    "左脉平和微无力_右脉弦似有力": {"direction": "滋肾降冲", "mechanism": "肾阴虚致冲气挟痰上冲"},
    "弦无力：重按微弦无力": {"direction": "补升", "mechanism": "久病气化已衰，忌破气理气"},
}

# 第四步：尺部虚里规则
CHI_ROOT_DANGER = [
    "尺脉无根", "重按即无", "尺部按之即无", "两尺无根",
    "尺脉甚弱", "尺部不起"
]

XULI_DANGER = [
    "虚里大动", "左乳下动脉大动", "周身脉管皆大动"
]


class ZhangXiChunEngineV9:
    """v9引擎：五步决策树 + v7脉案数据"""

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = os.path.join(_THIS_DIR, "pulse_cases_v7.json")
        self.cases = []
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                self.cases = json.load(f)
        self._build_case_index()

    def _build_case_index(self):
        """构建脉案关键词索引，加速匹配"""
        self._section_index = defaultdict(list)
        for c in self.cases:
            self._section_index[c.get("section", "?")].append(c)

    def diagnose(self,
                 symptoms: str = "",
                 pulse_left: Optional[Dict] = None,
                 pulse_right: Optional[Dict] = None,
                 pulse_overall: Optional[List] = None,
                 tongue: str = "",
                 additional: str = "",
                 cun_force_level: int = 0,
                 chi_root: str = "") -> Dict:
        """
        五步辨证主函数

        Args:
            symptoms: 主诉/症状文本
            pulse_left: 左手脉象 {"overall": "...", "cun": "...", "guan": "...", "chi": "..."}
            pulse_right: 右手脉象
            pulse_overall: 三部总看脉象描述列表
            tongue: 舌象
            additional: 其他体征
            cun_force_level: 寸部力度量尺 (0=未知, 1=偏虚, 2=弱, 3=微弱, 4=极微弱, 5=无脉)
            chi_root: 尺部根情况 ("有根"/"无根"/"")
        """
        chain = []
        all_text = self._build_text(symptoms, pulse_left, pulse_right, pulse_overall)

        # ===== 第一步：辨气机升降 =====
        qi_result = self._step1_qi_direction(symptoms, all_text, chain)

        # ===== 第二步：脉诊虚实寒热 =====
        pulse_result = self._step2_pulse_diagnosis(all_text, cun_force_level, chain)

        # ===== 第三步：左右对比定脏腑 =====
        lr_result = self._step3_left_right(pulse_left, pulse_right, all_text, chain)

        # ===== 第四步：尺部虚里 =====
        root_result = self._step4_root_prognosis(pulse_left, pulse_right, all_text,
                                                  chi_root, chain)

        # ===== 第五步：方证锁定 =====
        formula_result = self._step5_formula_lock(
            qi_result, pulse_result, lr_result, root_result,
            symptoms, all_text, tongue, additional, chain
        )

        # ===== v7脉案匹配（辅助参考） =====
        case_matches = self._match_v7_cases(all_text, qi_result, formula_result)

        return {
            "qi_direction": qi_result,
            "pulse_diagnosis": pulse_result,
            "left_right": lr_result,
            "root_prognosis": root_result,
            "formula_recommendations": formula_result,
            "v7_case_matches": case_matches[:5],
            "chain": chain,
            "summary": self._build_summary(qi_result, formula_result, chain),
        }

    def _build_text(self, symptoms, pulse_left, pulse_right, pulse_overall) -> str:
        parts = [symptoms]
        if pulse_overall:
            parts.extend(pulse_overall)
        if pulse_left:
            parts.append(str(pulse_left))
        if pulse_right:
            parts.append(str(pulse_right))
        return " ".join(parts)

    # ===== 第一步 =====
    def _step1_qi_direction(self, symptoms: str, all_text: str, chain: List[str]) -> Dict:
        """辨气机升降：下陷/上逆/中性"""
        n_sink = sum(1 for kw in SINKING_KEYWORDS if kw in all_text)
        n_flow = sum(1 for kw in COUNTERFLOW_KEYWORDS if kw in all_text)

        # 大气下陷特有鉴别：呼气难 vs 吸气难
        exhale_diff = any(w in all_text for w in ["呼气难", "呼气困难"])
        inhale_diff = any(w in all_text for w in ["吸气难", "吸气困难", "肩息"])

        result = {
            "direction": "neutral",
            "sink_count": n_sink,
            "flow_count": n_flow,
            "exhale_difficulty": exhale_diff,
            "inhale_difficulty": inhale_diff,
        }

        if n_sink > 0 and n_flow == 0:
            result["direction"] = "sinking"
            result["pool"] = "升陷类方池"
            result["candidate_formulas"] = list(XIAXIAN_FORMULAS.keys())
            chain.append(
                f"【第一步·辨气机】检出{n_sink}项下陷症状，无上逆症状 → 判定为「大气下陷」→ 升陷类方池"
            )
        elif n_flow > 0 and n_sink == 0:
            result["direction"] = "counterflow"
            result["pool"] = "镇逆类方池"
            result["candidate_formulas"] = list(SHANGNI_FORMULAS.keys())
            chain.append(
                f"【第一步·辨气机】检出{n_flow}项上逆症状，无下陷症状 → 判定为「气机上逆」→ 镇逆类方池"
            )
        elif n_sink > 0 and n_flow > 0:
            result["direction"] = "mixed"
            result["pool"] = "升陷+镇逆全方池"
            result["candidate_formulas"] = (
                list(XIAXIAN_FORMULAS.keys()) + list(SHANGNI_FORMULAS.keys())
            )
            chain.append(
                f"【第一步·辨气机】下陷{n_sink}项 + 上逆{n_flow}项 → 判定为「升降失调」→ 全方池"
            )
        else:
            result["direction"] = "neutral"
            result["pool"] = "需进一步辨证"
            result["candidate_formulas"] = []
            chain.append("【第一步·辨气机】无明显升降偏倾 → 需进一步辨证")

        # 呼气/吸气困难关键鉴别
        if exhale_diff and not inhale_diff:
            chain.append("  ⚠ 鉴别要点：呼气困难 → 支持大气下陷（与气逆之喘吸气难相反）")
        elif inhale_diff:
            chain.append("  ⚠ 鉴别要点：吸气困难/肩息 → 支持气逆之喘")

        return result

    # ===== 第二步 =====
    def _step2_pulse_diagnosis(self, all_text: str, cun_force_level: int,
                                chain: List[str]) -> Dict:
        """脉诊虚实寒热"""
        result = {
            "force_type": "unknown",  # true_strong / fake_strong / weak / gemai
            "float_sink": "unknown",
            "speed": "unknown",
            "cun_force_level": cun_force_level,
            "warning": "",
        }

        # 革脉优先检测
        if any(kw in all_text for kw in PULSE_GEMAI_DANGER):
            result["force_type"] = "gemai"
            result["warning"] = "革脉——阴阳离绝之险！禁峻下，先收敛固脱（萸肉龙骨类）"
            chain.append("【第二步·脉诊】⚠ 检出革脉特征（大而不洪+有力不滑）→ 阴阳离绝之险 → 禁峻下，急收敛固脱")
            return result

        # 辨有力真假
        has_hong = any(w in all_text for w in ["洪", "洪滑", "洪滑有力"])
        has_hua = any(w in all_text for w in ["滑", "滑而有力"])
        has_xian_ying = any(w in all_text for w in PULSE_FORCE_FAKE_STRONG)

        if has_hong and has_hua:
            result["force_type"] = "true_strong"
            chain.append("【第二步·脉诊】三部总按：洪滑兼具（波涛叠涌+累累如贯珠）→ 真有力，实热实证")
        elif has_xian_ying and not has_hong:
            result["force_type"] = "fake_strong"
            result["warning"] = "假有力——弦直无起伏无滑润，阴虚阳浮。忌峻攻！"
            chain.append("【第二步·脉诊】弦硬但无洪滑之象 → 假有力（阴虚阳浮）→ 滋阴潜阳，忌峻攻")
        elif any(w in all_text for w in PULSE_FORCE_WEAK):
            result["force_type"] = "weak"
            chain.append("【第二步·脉诊】三部总按无力 → 虚证，补益为主")

        # 浮沉
        if any(w in all_text for w in PULSE_FLOAT):
            result["float_sink"] = "float"
            chain.append("  └ 浮脉 → 表证或阴虚阳浮")
        elif any(w in all_text for w in PULSE_SINK):
            result["float_sink"] = "sink"
            chain.append("  └ 沉脉 → 里证或大气下陷")

        # 数迟
        if any(w in all_text for w in PULSE_RAPID):
            rapid_is_strong = result["force_type"] == "true_strong"
            result["speed"] = "rapid"
            if not rapid_is_strong:
                result["warning"] = result.get("warning", "") + "数而无力→大补元气，忌寒凉"
                chain.append("  └ 数而无力 → 虚（大补元气，忌寒凉）")
            else:
                chain.append("  └ 数而有力 → 真热")
        elif any(w in all_text for w in PULSE_SLOW):
            result["speed"] = "slow"
            chain.append("  └ 迟脉 → 寒积或大气下陷（大气下陷时脉仍可迟）")

        # 力度量尺评估
        if cun_force_level >= SHENGXIAN_CUN_FORCE_THRESHOLD:
            chain.append(f"  └ 寸部力度量尺：level {cun_force_level} → 达到升陷汤命中阈值")
        return result

    # ===== 第三步 =====
    def _step3_left_right(self, pulse_left, pulse_right, all_text: str,
                           chain: List[str]) -> Dict:
        """左右对比定脏腑"""
        result = {
            "asymmetry": "balanced",  # right_greater / left_greater / balanced
            "xuan_mai_match": "",
            "mechanism": "",
        }

        # 弦脉匹配（最高频组合）
        xuan_text = ""
        left_overall = pulse_left.get("overall", "") if pulse_left else ""
        right_overall = pulse_right.get("overall", "") if pulse_right else ""
        combined = f"{left_overall} {right_overall} {all_text}"

        for pattern, info in XUAN_MAI_MAP.items():
            # 简化匹配
            keys = pattern.replace("_", " ").split()
            if all(k in combined for k in keys if k):
                result["xuan_mai_match"] = pattern
                result["mechanism"] = info["mechanism"]
                result["direction"] = info["direction"]
                chain.append(f"【第三步·左右脏腑】弦脉匹配：{pattern} → {info['mechanism']} → 治则：{info['direction']}")
                break

        # 右 > 左
        if any(kw in all_text for kw in RIGHT_GREATER_LEFT):
            result["asymmetry"] = "right_greater"
            chain.append("  └ 右脉 > 左脉 → 冲气上冲、胃气不降 → 镇逆降胃")
        elif any(kw in all_text for kw in LEFT_GREATER_RIGHT):
            result["asymmetry"] = "left_greater"
            chain.append("  └ 左脉 > 右脉 → 肝阳上亢、阴虚火旺 → 平肝滋阴")

        # 弦硬 vs 弦无力鉴别
        if "弦硬" in combined and "弦无力" not in combined:
            chain.append("  └ 弦硬（假有力，肝木横恣）→ 治当镇降")
        elif "弦无力" in combined:
            chain.append("  └ 弦无力（真无力，气化已衰）→ 治当补升，忌破气理气")

        return result

    # ===== 第四步 =====
    def _step4_root_prognosis(self, pulse_left, pulse_right, all_text: str,
                               chi_root: str, chain: List[str]) -> Dict:
        """尺部定根，虚里证神"""
        result = {
            "chi_status": "unknown",  # rooted / rootless / weak
            "xuli_status": "unknown",
            "danger": False,
            "warning": "",
        }

        # 尺部候根
        if chi_root == "有根" or "尺脉有根" in all_text or "尺部重按有力" in all_text:
            result["chi_status"] = "rooted"
            chain.append("【第四步·尺部虚里】尺脉有根（重按有力）→ 可治")
        elif chi_root == "无根" or any(kw in all_text for kw in CHI_ROOT_DANGER):
            result["chi_status"] = "rootless"
            result["danger"] = True
            result["warning"] = "尺脉无根——肝肾虚极，阴阳不维，急防虚脱！"
            chain.append(f"【第四步·尺部虚里】⚠ {result['warning']}")
        elif "尺脉甚弱" in all_text:
            result["chi_status"] = "weak"
            chain.append("【第四步·尺部虚里】尺脉甚弱 → 阳升而阴不能应")
        else:
            chain.append("【第四步·尺部虚里】尺部情况未明确 → 建议触诊确认")

        # 虚里候神
        if any(kw in all_text for kw in XULI_DANGER):
            result["xuli_status"] = "abnormal"
            result["danger"] = True
            if not result["warning"]:
                result["warning"] = "虚里大动——冲气挟大气上逆"
            chain.append(f"  ⚠ 虚里大动 + 脉弦长 → 冲气上冲明确信号 → 急收敛固脱")
        else:
            chain.append("  └ 虚里未见异常搏动 → 大气尚盛")

        return result

    # ===== 第五步 =====
    def _step5_formula_lock(self, qi_result, pulse_result, lr_result, root_result,
                             symptoms: str, all_text: str, tongue: str,
                             additional: str, chain: List[str]) -> Dict:
        """方证锁定——综合评分"""
        scores: Dict[str, float] = {}

        qi_dir = qi_result.get("direction", "neutral")

        # 大气下陷 → 升陷类池内评分
        if qi_dir in ("sinking", "mixed"):
            self._score_xiaxian_pool(scores, all_text, symptoms, pulse_result)

        # 气机上逆 → 镇逆类池内评分
        if qi_dir in ("counterflow", "mixed"):
            self._score_shangni_pool(scores, all_text, symptoms, pulse_result)

        # 中性 → 全自创方评分 + 仲景方参考
        if qi_dir == "neutral" or not scores:
            self._score_all_pools(scores, all_text, symptoms, pulse_result, qi_result)

        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]

        if ranked:
            top_name, top_score = ranked[0]
            chain.append(
                f"【第五步·方证锁定】综合评分：{' > '.join(f'{n}({s:.1f})' for n, s in ranked)}"
            )
            chain.append(f"  ★ 推荐方剂：{top_name}（评分 {top_score:.1f}）")
        else:
            chain.append("【第五步·方证锁定】未匹配到特定方剂，请补充脉象、舌苔等信息")

        return {
            "rankings": ranked,
            "top_formula": ranked[0][0] if ranked else "",
            "top_score": ranked[0][1] if ranked else 0,
        }

    def _score_xiaxian_pool(self, scores, all_text, symptoms, pulse_result):
        """升陷类方评分"""
        # 升陷汤——基础大气下陷
        base_score = 0
        if any(kw in all_text for kw in ["气短不足以息", "气息将停", "努力呼吸"]):
            base_score += 5
        if any(kw in all_text for kw in ["脉沉迟微弱", "关前尤甚", "寸部微弱", "两寸微弱"]):
            base_score += 5
        if pulse_result.get("cun_force_level", 0) >= SHENGXIAN_CUN_FORCE_THRESHOLD:
            base_score += 5
        if pulse_result.get("float_sink") == "sink":
            base_score += 2
        if base_score > 0:
            scores["升陷汤"] = scores.get("升陷汤", 0) + base_score

        # 回阳升陷汤——兼心肺阳虚
        if any(kw in all_text for kw in ["身冷", "背紧", "恶寒", "心肺阳虚"]):
            scores["回阳升陷汤"] = scores.get("回阳升陷汤", 0) + 8

        # 理郁升陷汤——兼气分郁结
        if any(kw in all_text for kw in ["胸中满痛", "胁胀", "气分郁结", "经络湮淤"]):
            scores["理郁升陷汤"] = scores.get("理郁升陷汤", 0) + 8

        # 醒脾升陷汤——兼脾气虚极
        if any(kw in all_text for kw in ["小便不禁", "脾气虚"]):
            scores["醒脾升陷汤"] = scores.get("醒脾升陷汤", 0) + 8

    def _score_shangni_pool(self, scores, all_text, symptoms, pulse_result):
        """镇逆类方评分"""
        # 参赭镇气汤——冲气上冲+阴分虚
        if any(kw in all_text for kw in ["冲气上冲", "阴阳两虚", "喘逆迫促"]):
            scores["参赭镇气汤"] = scores.get("参赭镇气汤", 0) + 8

        # 薯蓣纳气汤——阴虚不纳气
        if "阴虚不纳气" in all_text or "不纳气" in all_text:
            scores["薯蓣纳气汤"] = scores.get("薯蓣纳气汤", 0) + 8

        # 滋培汤——虚劳喘逆
        if any(kw in all_text for kw in ["虚劳喘逆", "饮食减少"]):
            scores["滋培汤"] = scores.get("滋培汤", 0) + 6

        # 镇逆汤——冲胃并逆
        if any(kw in all_text for kw in ["呕吐", "胃气上逆", "呃逆"]):
            scores["镇逆汤"] = scores.get("镇逆汤", 0) + 6

        # 吐衄系列
        if any(kw in all_text for kw in ["吐衄", "吐血", "衄血", "咳血"]):
            if pulse_result.get("force_type") == "true_strong":
                scores["寒降汤"] = scores.get("寒降汤", 0) + 8
            elif pulse_result.get("speed") == "slow" or pulse_result.get("force_type") == "weak":
                scores["温降汤"] = scores.get("温降汤", 0) + 8
            if "阴分亏损" in all_text:
                scores["清降汤"] = scores.get("清降汤", 0) + 6
            if "气分虚甚" in all_text:
                scores["保元寒降汤"] = scores.get("保元寒降汤", 0) + 6
            if any(kw in all_text for kw in ["肝郁", "多怒"]):
                scores["秘红丹"] = scores.get("秘红丹", 0) + 6

    def _score_all_pools(self, scores, all_text, symptoms, pulse_result, qi_result):
        """全方池评分（方向中性时）"""
        self._score_xiaxian_pool(scores, all_text, symptoms, pulse_result)
        self._score_shangni_pool(scores, all_text, symptoms, pulse_result)

    def _match_v7_cases(self, all_text: str, qi_result: Dict, formula_result: Dict) -> List[Dict]:
        """匹配v7脉案数据"""
        if not self.cases:
            return []
        matches = []
        keywords = set()
        for kw in SINKING_KEYWORDS + COUNTERFLOW_KEYWORDS:
            if kw in all_text:
                keywords.add(kw)

        top_formula = formula_result.get("rankings", [])
        top_names = {n for n, _ in top_formula[:3]}

        for c in self.cases:
            score = 0
            # 方剂名匹配
            if c.get("section", "") in top_names:
                score += 3
            # 症状关键词匹配
            raw = c.get("pulse_raw", "")
            for kw in keywords:
                if kw in raw:
                    score += 2
            # 位置匹配
            if c.get("position_detail"):
                score += 1
            if score > 0:
                matches.append({
                    "id": c["id"],
                    "section": c.get("section", ""),
                    "score": score,
                    "pulse_summary": raw[:150],
                    "has_position_detail": bool(c.get("position_detail")),
                })

        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def _build_summary(self, qi_result, formula_result, chain) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("张锡纯气机升降辨证引擎 v9")
        lines.append("五步决策树 + v7脉案数据 (772案)")
        lines.append("=" * 60)
        lines.append("")
        for step in chain:
            lines.append(step)
        return "\n".join(lines)

    def format_result(self, result: Dict) -> str:
        """格式化输出"""
        lines = [result.get("summary", "")]
        lines.append("")
        rankings = result.get("formula_recommendations", {}).get("rankings", [])
        if rankings:
            lines.append("【方剂推荐】")
            for i, (name, score) in enumerate(rankings):
                is_self = "【自创方】" if name in ALL_ZXC_SELF else ""
                is_zhongjing = "【仲景方】" if name in ZHONGJING_FORMULAS else ""
                marker = "★" if i == 0 else f" {i}."
                lines.append(f"  {marker} {name} (评分 {score:.1f}) {is_self}{is_zhongjing}")

        # v7脉案匹配
        case_matches = result.get("v7_case_matches", [])
        if case_matches:
            lines.append("")
            lines.append("【v7脉案参考】")
            for cm in case_matches[:3]:
                pd_flag = " [含位置映射]" if cm["has_position_detail"] else ""
                lines.append(f"  · {cm['id']} | {cm['section']} | {cm['pulse_summary'][:100]}...{pd_flag}")

        # 警示
        pulse_rs = result.get("pulse_diagnosis", {})
        root_rs = result.get("root_prognosis", {})
        warnings = []
        for rs in [pulse_rs, root_rs]:
            w = rs.get("warning", "")
            if w:
                warnings.append(w)
        if warnings:
            lines.append("")
            lines.append("【⚠ 警示】")
            for w in warnings:
                lines.append(f"  {w}")

        return "\n".join(lines)


# ===================== 测试 =====================
if __name__ == "__main__":
    engine = ZhangXiChunEngineV9()
    print(f"已加载 {len(engine.cases)} 条脉案（v7全量）")
    print("=" * 60)

    tests = [
        ("测试1·大气下陷经典案", {
            "symptoms": "气短不足以息，努力呼吸似喘",
            "pulse_left": {},
            "pulse_right": {},
            "pulse_overall": ["脉沉迟微弱，关前尤甚"],
        }),
        ("测试2·冲气上冲吐衄案", {
            "symptoms": "吐血，衄血，胃气上逆",
            "pulse_overall": ["脉洪滑而长，上入鱼际，因热而胃气不降"],
        }),
        ("测试3·升降失调", {
            "symptoms": "气短，时有气上冲，呃逆",
            "pulse_overall": ["左脉弦硬，右脉沉弱"],
        }),
        ("测试4·寸部力度量尺", {
            "symptoms": "短气，乏力",
            "pulse_overall": ["两寸微弱，不起"],
            "cun_force_level": 3,
        }),
        ("测试5·虚里大动危证", {
            "symptoms": "心慌，气上冲",
            "pulse_overall": ["周身六脉弦硬，虚里大动"],
        }),
    ]

    for title, params in tests:
        result = engine.diagnose(**params)
        print(f"\n{title}")
        print(engine.format_result(result))
