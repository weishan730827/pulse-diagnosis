#!/usr/bin/env python3
"""
姚梅龄脉学辨证匹配引擎 v1
方法：纯脉诊辨证。知医邦28脉10维量化全量输入→分层分析→病机推演。
      本引擎为桥接层——接收知医邦脉诊量化表的输出，按姚梅龄三层解析法：
      病位（表/里/半表半里）→ 病性（寒/热/虚/实）→ 病势（进退/缓急）
"""

import json
import os
from typing import Dict, List, Optional

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "姚梅龄脉学辨证勾选表_v1.json")


class YaoMeiLingEngine:
    """姚梅龄引擎：脉诊三层解析"""

    # 28脉 → 病位/病性的映射规则
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
        "浮": {"寒": 0, "热": 0, "虚": 0, "实": 0},  # 需结合兼脉
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

        # Layer 1: 病位
        biaoli_score = {"表": 0, "里": 0, "半表半里": 0}
        for entry in all_pulses:
            bw = self.PULSE_BINGWEI.get(entry["pulse"], "里")
            for loc in bw.split("/"):
                loc = loc.strip()
                if "兼" not in loc and loc in biaoli_score:
                    biaoli_score[loc] += 1
                elif "兼" in loc:
                    biaoli_score["半表半里"] += 1

        bingwei = max(biaoli_score, key=biaoli_score.get)

        # Layer 2: 病性
        bingxing = {"寒": 0, "热": 0, "虚": 0, "实": 0}
        for entry in all_pulses:
            bx = self.PULSE_BINGXING.get(entry["pulse"], {})
            for k, v in bx.items():
                bingxing[k] += v

        # 病性判定
        hanre = "寒" if bingxing["寒"] > bingxing["热"] else "热" if bingxing["热"] > bingxing["寒"] else "平"
        xushi = "虚" if bingxing["虚"] > bingxing["实"] else "实" if bingxing["实"] > bingxing["虚"] else "虚实夹杂"

        # Layer 3: 病势（基于脉的气势）
        bingshi = self._judge_bingshi(all_pulses)

        # 方证推荐
        formulas = self._recommend(bingwei, hanre, xushi)

        return {
            "pulse_count": len(all_pulses),
            "pulse_detail": all_pulses,
            "bingwei": bingwei,
            "bingxing_scores": bingxing,
            "han_re": hanre,
            "xu_shi": xushi,
            "bingshi": bingshi,
            "formulas": formulas
        }

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
        lines.append("=== 姚梅龄脉学辨证结果 ===")
        lines.append(f"脉象数: {result['pulse_count']} 项")
        lines.append(f"病位: {result['bingwei']}")
        lines.append(f"寒热: {result['han_re']}  |  虚实: {result['xu_shi']}")
        lines.append(f"病势: {result['bingshi']}")
        lines.append("")

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
