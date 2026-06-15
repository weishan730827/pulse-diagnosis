#!/usr/bin/env python3
"""
胡希恕六经八纲辨证匹配引擎 v2
方法：病位×病性×症候群 三步递进锁定 —— 替代v1"撒豆子计分"
Step1: 八纲定位 → 病位(表/里/半表半里) × 病性(阳/阴) → 六经锁定
Step2: 六经限定 —— 仅搜索已锁定六经内的细化症状
Step3: Jaccard聚类 —— 在锁定六经的方证内做覆盖度排序
"""

import json
import os
from typing import Dict, List, Tuple, Set

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "胡希恕辨证勾选表_v1.json")

# 病位×病性 → 六经映射表
BINGWEI_BINGXING_MAP = {
    ("表证", "阳证"): "太阳病",
    ("表证", "阴证"): "少阴病",
    ("里证", "阳证"): "阳明病",
    ("里证", "阴证"): "太阴病",
    ("半表半里", "阳证"): "少阳病",
    ("半表半里", "阴证"): "厥阴病",
}


class HuXiShuEngine:
    """胡希恕引擎：六经八纲三步递进"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # 八纲定位项
        self._bagang_items: Dict[str, Dict] = {}
        # 六经细化项 {jing_name: {id: item}}
        self._jing_items: Dict[str, Dict[str, Dict]] = {}
        # 脉象映射
        self._pulse_map: Dict[str, str] = {}

        self._build_maps()

    def _build_maps(self):
        # Step1 八纲
        for section in self.data["step1_八纲定位"]["sections"]:
            for item in section["items"]:
                self._bagang_items[item["id"]] = {
                    "text": item["text"],
                    "maps_to": item["maps_to"],
                    "tags": item["tags"],
                }

        # Step2 六经细化
        step2 = self.data["step2_六经细化"]
        for jing_name, jing_data in step2.items():
            if jing_name == "description":
                continue
            self._jing_items[jing_name] = {}
            for item in jing_data["细分"]:
                self._jing_items[jing_name][item["id"]] = {
                    "text": item["text"],
                    "label": item.get("label", ""),
                    "maps_to": item.get("maps_to", ""),
                }

        # Step3 脉象映射
        self._pulse_map = self.data["step3_脉象确认"].get("mapping", {})

    def _extract_bagang_scores(self, checked_ids: List[str]) -> Dict[str, int]:
        """Step1: 统计病位×病性得分"""
        scores = {"表证": 0, "里证": 0, "半表半里": 0, "阳证": 0, "阴证": 0}

        for sid in checked_ids:
            item = self._bagang_items.get(sid)
            if item:
                for tag in item["tags"]:
                    if tag in scores:
                        scores[tag] += 1

        return scores

    def _lock_liujing(self, bagang_scores: Dict[str, int]) -> List[Tuple[str, float]]:
        """根据病位×病性分数锁定六经（按置信度排序）"""
        candidates: List[Tuple[str, float]] = []

        for (bw, bx), jing in BINGWEI_BINGXING_MAP.items():
            bw_score = bagang_scores.get(bw, 0)
            bx_score = bagang_scores.get(bx, 0)
            if bw_score > 0 and bx_score > 0:
                confidence = (bw_score + bx_score) / 2
                candidates.append((jing, confidence))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def _collect_jing_items(self, checked_ids: List[str], locked_jing: str) -> List[Dict]:
        """Step2: 在锁定的六经内收集细化症状"""
        items = []
        jing_pool = self._jing_items.get(locked_jing, {})

        for sid in checked_ids:
            item = jing_pool.get(sid)
            if item:
                items.append(item)

        return items

    def _jaccard_rank(self, jing_items: List[Dict], locked_jing: str) -> List[Tuple[str, float]]:
        """
        Step3: Jaccard聚类——在锁定六经内，对每条细化项的maps_to做覆盖度排序
        每条细化项可能映射到一个方证（如"TY_sw_1"→"麻黄汤证"）
        统计每个方证被勾选的细化项覆盖了多少，按Jaccard覆盖度排序
        """
        jing_pool = self._jing_items.get(locked_jing, {})

        # 该六经所有方证集合
        all_fangs: Dict[str, Set[str]] = {}  # fang -> set of item_ids
        for item_id, item in jing_pool.items():
            maps_to = item.get("maps_to", "")
            if maps_to:
                # 一个方证可能对应多个细化项
                if maps_to not in all_fangs:
                    all_fangs[maps_to] = set()
                all_fangs[maps_to].add(item_id)

        # 已勾选的item_id集合
        checked_item_ids = set()
        for item in jing_items:
            # 反向查找item_id
            for iid, i in jing_pool.items():
                if i["text"] == item["text"]:
                    checked_item_ids.add(iid)
                    break

        # Jaccard相似度: |checked ∩ fang_items| / |fang_items|
        ranked: List[Tuple[str, float]] = []
        for fang, fang_ids in all_fangs.items():
            intersection = checked_item_ids & fang_ids
            union = fang_ids  # 用方证覆盖的item数做分母
            if union:
                jaccard = len(intersection) / len(union)
                if jaccard > 0:
                    ranked.append((fang, jaccard))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """三步递进诊断"""
        # Step 1: 八纲定位
        bagang_scores = self._extract_bagang_scores(checked_ids)
        jing_candidates = self._lock_liujing(bagang_scores)

        if not jing_candidates:
            return {
                "status": "无法锁定六经",
                "bagang_scores": bagang_scores,
                "jing_candidates": [],
                "locked_jing": None,
                "jing_items": [],
                "formulas": [],
            }

        locked_jing = jing_candidates[0][0]

        # Step 2: 六经限定 → 收集细化症状
        jing_items = self._collect_jing_items(checked_ids, locked_jing)

        # Step 3: Jaccard聚类
        formulas = self._jaccard_rank(jing_items, locked_jing)

        return {
            "status": "success",
            "bagang_scores": bagang_scores,
            "jing_candidates": jing_candidates,
            "locked_jing": locked_jing,
            "jing_items": [i["text"] for i in jing_items],
            "jing_item_details": jing_items,
            "formulas": formulas,
        }

    def format_result(self, result: Dict) -> str:
        lines = ["=== 胡希恕六经八纲辨证结果 ==="]

        if result["status"] == "无法锁定六经":
            lines.append("状态: 八纲信号不足，无法锁定六经")
            lines.append(f"八纲得分: {result['bagang_scores']}")
            return "\n".join(lines)

        lines.append("")
        lines.append("【Step1: 八纲定位】")
        lines.append(f"  病位: 表={result['bagang_scores'].get('表证',0)}  里={result['bagang_scores'].get('里证',0)}  半表半里={result['bagang_scores'].get('半表半里',0)}")
        lines.append(f"  病性: 阳={result['bagang_scores'].get('阳证',0)}  阴={result['bagang_scores'].get('阴证',0)}")
        lines.append(f"  六经候选: {', '.join(f'{j}({c:.1f})' for j, c in result['jing_candidates'])}")

        lines.append(f"\n【Step2: 六经锁定 → {result['locked_jing']}】")
        if result["jing_items"]:
            for i, detail in enumerate(result["jing_item_details"], 1):
                label = detail.get("label", "")
                text = detail["text"]
                lines.append(f"  {i}. {text}  [{label}]")
        else:
            lines.append("  (该六经内无细化症状命中)")

        lines.append(f"\n【Step3: Jaccard聚类方证匹配】")
        if result["formulas"]:
            for fang, score in result["formulas"]:
                pct = f"{score*100:.0f}%"
                bar = "█" * int(score * 20) if score > 0 else ""
                lines.append(f"  {fang}: {pct} {bar}")
        else:
            lines.append("  (未匹配到方证)")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = HuXiShuEngine()

    # 测试1: 太阳伤寒 → 锁定太阳病 → 麻黄汤
    print("=" * 60)
    print("测试1: 太阳伤寒 (恶寒发热+无汗+身疼)")
    test1 = [
        "biaozheng_etaiyang",  # 表+阳 → 太阳
        "TY_sw_1",             # 恶寒发热+无汗+身疼 → 麻黄汤
    ]
    r1 = engine.diagnose(test1)
    print(engine.format_result(r1))

    print()
    print("=" * 60)
    print("测试2: 少阴寒化 (脉沉细+但欲寐+手足厥冷+下利)")
    test2 = [
        "biaozheng_eshaoyin",  # 表+阴 → 少阴
        "SY_bb_1",             # 手足厥冷+下利清谷+脉微细 → 四逆汤
    ]
    r2 = engine.diagnose(test2)
    print(engine.format_result(r2))

    print()
    print("=" * 60)
    print("测试3: 阳明经证 (大热+大汗+大渴+脉洪大)")
    test3 = [
        "lizheng_eyangming",   # 里+阳 → 阳明
        "YM_jz_1",             # 大热大汗大渴脉洪大 → 白虎汤
    ]
    r3 = engine.diagnose(test3)
    print(engine.format_result(r3))
