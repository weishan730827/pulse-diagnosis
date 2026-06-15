#!/usr/bin/env python3
"""
姚梅龄脉学辨证匹配引擎 v2
方法：纯脉诊辨证。知医邦28脉10维量化全量输入→分层分析→病机推演。
      本引擎为桥接层——接收知医邦脉诊量化表的输出，按姚梅龄三层解析法：
      病位（表/里/半表半里）→ 病性（寒/热/虚/实）→ 病势（进退/缓急）
      v2新增：复合脉解析（浮数→表热、沉迟→里寒等）覆盖浮沉单脉寒热空白。
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from itertools import combinations

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "姚梅龄脉学辨证勾选表_v1.json")


class YaoMeiLingEngine:
    """姚梅龄引擎：脉诊三层解析（v2 复合脉）"""

    # 28脉 → 病位/病性的映射规则（单脉）
    PULSE_BINGWEI = {
        "浮": "表", "沉": "里",
        "弦": "半表半里（兼）", "滑": "里（痰/食/热）",
        "细": "里（血虚/阴虚）", "弱": "里（气虚/阳虚）",
        "洪": "里（气分热盛）", "大": "里",
        "数": "里（热）", "迟": "里（寒）",
        "紧": "表/里（寒/痛）", "涩": "里（血瘀/精亏）",
        "结": "里（阴寒/气血瘀滞）", "代": "里（脏气衰微）",
        "促": "里（阳热亢盛）",
    }

    PULSE_BINGXING = {
        "浮": {"寒": 0, "热": 0, "虚": 0, "实": 0},
        "沉": {"寒": 0, "热": 0, "虚": 0, "实": 0},
        "数": {"热": 2, "虚": -1},
        "迟": {"寒": 2, "虚": 1},
        "洪": {"热": 3, "实": 1},
        "细": {"虚": 2, "热": -1},
        "弱": {"虚": 3},
        "滑": {"实": 2, "热": 1},
        "涩": {"虚": 1, "实": 1},
        "弦": {"实": 2, "寒": 0, "热": 0},
        "紧": {"寒": 3, "实": 1},
        "结": {"寒": 1, "虚": 1},
        "代": {"虚": 3},
        "促": {"热": 2},
        "大": {"实": 2, "热": 0},
    }

    # 复合脉解析：两脉组合→病位+病性
    COMPOUND_RULES: Dict[Tuple[str, ...], Dict] = {
        # 浮脉复合
        ("浮", "紧"): {"bingwei": "表", "han": 3, "re": 0, "xu": 0, "shi": 1, "desc": "浮紧→表寒（太阳伤寒）"},
        ("浮", "数"): {"bingwei": "表", "han": 0, "re": 3, "xu": 0, "shi": 1, "desc": "浮数→表热（风热犯表）"},
        ("浮", "缓"): {"bingwei": "表", "han": 1, "re": 0, "xu": 1, "shi": 0, "desc": "浮缓→表虚（太阳中风）"},
        ("浮", "滑"): {"bingwei": "表", "han": 0, "re": 1, "xu": 0, "shi": 1, "desc": "浮滑→表有痰热"},
        ("浮", "弱"): {"bingwei": "表", "han": 0, "re": 0, "xu": 2, "shi": 0, "desc": "浮弱→表虚卫外不固"},
        ("浮", "细"): {"bingwei": "表", "han": 0, "re": 0, "xu": 2, "shi": 0, "desc": "浮细→表虚血弱"},
        # 沉脉复合
        ("沉", "迟"): {"bingwei": "里", "han": 3, "re": 0, "xu": 1, "shi": 0, "desc": "沉迟→里寒"},
        ("沉", "数"): {"bingwei": "里", "han": 0, "re": 3, "xu": 0, "shi": 1, "desc": "沉数→里热"},
        ("沉", "细"): {"bingwei": "里", "han": 0, "re": 0, "xu": 2, "shi": 0, "desc": "沉细→里虚（血弱）"},
        ("沉", "弱"): {"bingwei": "里", "han": 0, "re": 0, "xu": 3, "shi": 0, "desc": "沉弱→里虚（气弱）"},
        ("沉", "弦"): {"bingwei": "里", "han": 0, "re": 0, "xu": 0, "shi": 2, "desc": "沉弦→里实（气滞/水饮）"},
        ("沉", "滑"): {"bingwei": "里", "han": 0, "re": 1, "xu": 0, "shi": 2, "desc": "沉滑→里实（痰/食/热）"},
        ("沉", "洪"): {"bingwei": "里", "han": 0, "re": 3, "xu": 0, "shi": 2, "desc": "沉洪→里热盛"},
        ("沉", "紧"): {"bingwei": "里", "han": 3, "re": 0, "xu": 0, "shi": 1, "desc": "沉紧→里寒痛"},
        # 弦脉复合
        ("弦", "数"): {"bingwei": "半表半里", "han": 0, "re": 2, "xu": 0, "shi": 1, "desc": "弦数→少阳郁热"},
        ("弦", "细"): {"bingwei": "半表半里", "han": 0, "re": 0, "xu": 2, "shi": 0, "desc": "弦细→肝血不足"},
        ("弦", "滑"): {"bingwei": "里", "han": 0, "re": 1, "xu": 0, "shi": 2, "desc": "弦滑→肝胆湿热/痰火"},
        # 数脉复合
        ("数", "滑"): {"bingwei": "里", "han": 0, "re": 3, "xu": 0, "shi": 1, "desc": "滑数→痰热"},
        ("数", "细"): {"bingwei": "里", "han": 0, "re": 1, "xu": 2, "shi": 0, "desc": "细数→阴虚内热"},
    }

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def diagnose(self, pulse_data: Dict[str, List[str]], aux_symptoms: Optional[List[str]] = None) -> Dict:
        """
        pulse_data: {"左寸": ["细", "弱"], "左关": ["弦"], "右尺": ["沉"]}
        aux_symptoms: 辅助问诊勾选ID列表
        """
        # 收集所有脉象
        all_pulses = []
        for pos, pulses in pulse_data.items():
            for p in pulses:
                all_pulses.append({"position": pos, "pulse": p})

        # Layer 0: 复合脉解析（优先于单脉累加）
        compound_findings = self._analyze_compounds(all_pulses)

        # Layer 1: 病位（单脉+复合脉叠加）
        biaoli_score = {"表": 0, "里": 0, "半表半里": 0}
        # 复合脉贡献
        for cf in compound_findings:
            bw = cf.get("bingwei", "里")
            if bw in biaoli_score:
                biaoli_score[bw] += 2  # 复合脉权重加倍
        # 单脉贡献
        for entry in all_pulses:
            bw = self.PULSE_BINGWEI.get(entry["pulse"], "里")
            for loc in bw.split("/"):
                loc = loc.strip()
                if "兼" not in loc and loc in biaoli_score:
                    biaoli_score[loc] += 1
                elif "兼" in loc:
                    biaoli_score["半表半里"] += 1

        bingwei = max(biaoli_score, key=biaoli_score.get)

        # Layer 2: 病性（单脉+复合脉叠加）
        bingxing = {"寒": 0, "热": 0, "虚": 0, "实": 0}
        # 复合脉贡献
        for cf in compound_findings:
            bingxing["寒"] += cf.get("han", 0)
            bingxing["热"] += cf.get("re", 0)
            bingxing["虚"] += cf.get("xu", 0)
            bingxing["实"] += cf.get("shi", 0)
        # 单脉贡献
        for entry in all_pulses:
            bx = self.PULSE_BINGXING.get(entry["pulse"], {})
            for k, v in bx.items():
                bingxing[k] += v

        # 病性判定
        hanre = "寒" if bingxing["寒"] > bingxing["热"] else "热" if bingxing["热"] > bingxing["寒"] else "平"
        xushi = "虚" if bingxing["虚"] > bingxing["实"] else "实" if bingxing["实"] > bingxing["虚"] else "虚实夹杂"

        # Layer 3: 病势
        bingshi = self._judge_bingshi(all_pulses)

        # 方证推荐
        formulas = self._recommend(bingwei, hanre, xushi)

        return {
            "pulse_count": len(all_pulses),
            "pulse_detail": all_pulses,
            "compound_findings": compound_findings,
            "bingwei": bingwei,
            "bingwei_scores": biaoli_score,
            "bingxing_scores": bingxing,
            "han_re": hanre,
            "xu_shi": xushi,
            "bingshi": bingshi,
            "formulas": formulas
        }

    def _analyze_compounds(self, all_pulses: List[Dict]) -> List[Dict]:
        """扫描同部复合脉（同position的两两组合）"""
        findings = []
        # 按部位分组
        pos_pulses: Dict[str, List[str]] = {}
        for e in all_pulses:
            pos_pulses.setdefault(e["position"], []).append(e["pulse"])

        seen = set()
        for pos, pulses in pos_pulses.items():
            for combo in combinations(sorted(pulses), 2):
                key = tuple(combo)
                if key in self.COMPOUND_RULES and key not in seen:
                    rule = self.COMPOUND_RULES[key]
                    findings.append({
                        "position": pos,
                        "pulses": list(key),
                        **rule,
                    })
                    seen.add(key)
        return findings

    def _judge_bingshi(self, all_pulses: List[Dict]) -> str:
        """判定病势：进退缓急"""
        pulses = [e["pulse"] for e in all_pulses]
        if any(p in ("结", "代", "促") for p in pulses):
            return "急（节律异常，病情紧迫）"
        if any(p in ("洪", "数", "大") for p in pulses):
            return "进（邪气亢盛，病势发展）"
        if any(p in ("沉", "弱", "细", "涩") for p in pulses):
            return "缓（正气不足，病势缠绵）"
        return "待定"

    def _recommend(self, bingwei: str, hanre: str, xushi: str) -> List[str]:
        formulas = []
        if bingwei == "表" and xushi == "实":
            formulas.append("麻黄汤（表寒实证）" if hanre == "寒" else "银翘散（表热实证）")
        elif bingwei == "表" and xushi == "虚":
            formulas.append("桂枝汤（表虚证）")
        elif bingwei == "里" and xushi == "虚":
            formulas.append("四逆汤（里虚寒）" if hanre == "寒" else "黄连阿胶汤（里虚热）")
        elif bingwei == "里" and xushi == "实":
            formulas.append("大承气汤（里实热）" if hanre == "热" else "四逆汤（里实寒）")
        elif bingwei == "半表半里":
            formulas.append("小柴胡汤（半表半里）")
        return formulas

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 姚梅龄脉学辨证结果（v2 复合脉） ===")
        lines.append(f"脉象数: {result['pulse_count']} 项")
        lines.append(f"病位: {result['bingwei']}  |  寒热: {result['han_re']}  |  虚实: {result['xu_shi']}")
        lines.append(f"病势: {result['bingshi']}")
        lines.append("")

        # 复合脉发现
        if result.get("compound_findings"):
            lines.append("【复合脉解析】")
            for cf in result["compound_findings"]:
                pulses_str = " + ".join(cf["pulses"])
                lines.append(f"  {cf['position']} {pulses_str} → {cf['desc']}")

        lines.append("【脉象明细】")
        for e in result["pulse_detail"]:
            lines.append(f"  {e['position']} → {e['pulse']}")

        lines.append(f"\n【病性分值】寒={result['bingxing_scores']['寒']} 热={result['bingxing_scores']['热']} 虚={result['bingxing_scores']['虚']} 实={result['bingxing_scores']['实']}")

        if result["formulas"]:
            lines.append(f"\n【推荐方剂】")
            for f in result["formulas"]:
                lines.append(f"  → {f}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = YaoMeiLingEngine()

    # 模拟少阴脉象: 沉细微弱
    test_pulse = {
        "左寸": ["沉", "细"],
        "左关": ["沉", "弦"],
        "左尺": ["沉", "弱"],
        "右寸": ["沉"],
        "右关": ["弱"],
        "右尺": ["沉", "弱"],
    }
    r = engine.diagnose(test_pulse)
    print(engine.format_result(r))
