#!/usr/bin/env python3
"""
曹颖甫方证对应匹配引擎 v1
方法：方证对应——有是证用是方。每个症状组合直接映射经方。
输入：勾选的症状ID列表
输出：匹配经方列表（按命中次数排序）
"""

import json
import os
from typing import Dict, List, Tuple, Optional

# --- 方证数据库路径 ---
_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "曹颖甫方证对应勾选表_v1.json")


class CaoYingFuEngine:
    """曹颖甫引擎：症状ID → 方名 直接映射"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # 构建 ID → (症状文本, 方名列表) 的索引
        self.symptom_map: Dict[str, Tuple[str, List[str]]] = {}
        self._build_index()

    def _build_index(self):
        """遍历所有症状条目，建立ID到方名的索引"""
        for section in self.data["checklist"]["sections"]:
            for item in section.get("items", []):
                sid = item["id"]
                fang_str = item.get("方", "")
                fangs = self._parse_fangs(fang_str)
                self.symptom_map[sid] = (item["text"], fangs)

    @staticmethod
    def _parse_fangs(fang_str: str) -> List[str]:
        """解析方名字符串，处理 '/', '→', 括号等"""
        if not fang_str or fang_str == "需结合其他症状":
            return []

        fangs = []
        # 拆分 "桂枝汤/麻黄汤" 和 "白虎汤/R参白虎汤"
        for part in fang_str.replace("R", "人").split("/"):
            part = part.strip()
            # 去掉括号注释：如 "温病（非太阳）"
            if "（" in part:
                part = part.split("（")[0].strip()
            if part and part not in ("非太阳",):
                fangs.append(part)

        return fangs

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """
        输入勾选的症状ID列表，返回辨证结果。

        曹颖甫核心逻辑：症状组合直接映射经方，但需区分：
        - 特异性权重：单方映射(原方原量) > 多方交叉映射
        - 若有单方100%命中症状组，直接锁定该方
        """
        fang_counter: Dict[str, Dict] = {}  # fang_name → {score, symptoms, specificity}
        unmatched = []

        for sid in checked_ids:
            if sid not in self.symptom_map:
                unmatched.append(sid)
                continue

            text, fangs = self.symptom_map[sid]
            # 特异性权重：单方=3 多方=1（单方映射症状是更确定的指征）
            specificity = 3 if len(fangs) == 1 else 1
            for f in fangs:
                if f not in fang_counter:
                    fang_counter[f] = {"fang": f, "score": 0, "symptoms": [], "specific_count": 0}
                fang_counter[f]["score"] += specificity
                if specificity == 3:
                    fang_counter[f]["specific_count"] += 1
                fang_counter[f]["symptoms"].append({"id": sid, "text": text, "specific": specificity == 3})

        # 按得分降序排列（特异性加权优先）
        ranked = sorted(fang_counter.values(), key=lambda x: (x["score"], x["specific_count"]), reverse=True)

        return {
            "matched_formulas": ranked,
            "unmatched_ids": unmatched,
            "total_checked": len(checked_ids),
            "total_matched": len(checked_ids) - len(unmatched)
        }

    def format_result(self, result: Dict) -> str:
        """将诊断结果格式化为可读文本"""
        lines = []
        lines.append(f"=== 曹颖甫方证对应辨证结果 ===")
        lines.append(f"勾选症状: {result['total_checked']} 项，命中: {result['total_matched']} 项")
        lines.append("")

        if result["matched_formulas"]:
            lines.append("【匹配经方】（按特异性加权排序）")
            for i, entry in enumerate(result["matched_formulas"], 1):
                marker = "【首选】" if i == 1 else ""
                lines.append(f"  {i}. {marker}{entry['fang']} (得分 {entry['score']}，特异性 {entry['specific_count']} 项)")
                for sym in entry["symptoms"]:
                    tag = "●" if sym.get("specific") else "○"
                    lines.append(f"     {tag} [{sym['id']}] {sym['text']}")
        else:
            lines.append("【无匹配经方】")

        if result["unmatched_ids"]:
            lines.append(f"\n【未匹配ID】({len(result['unmatched_ids'])} 项)")
            for uid in result["unmatched_ids"]:
                lines.append(f"  - {uid}")

        return "\n".join(lines)


# --- 自检 ---
if __name__ == "__main__":
    engine = CaoYingFuEngine()
    print(f"已加载 {len(engine.symptom_map)} 条症状-方证映射")

    # 模拟：勾选 "恶寒发热 + 无汗 + 身痛" 和 "恶风 + 汗出 + 发热"
    test_ids = [
        "cyf_ch_eweihan_fare_wuhan",   # → 麻黄汤
        "cyf_ch_efeng_hf_fare",        # → 桂枝汤
        "cyf_t_txq_tong",              # → 桂枝汤/麻黄汤
        "cyf_ch_dare_dahan_dake",      # → 白虎汤
    ]
    result = engine.diagnose(test_ids)
    print(engine.format_result(result))
