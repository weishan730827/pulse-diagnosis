#!/usr/bin/env python3
"""
郑钦安阴阳辨证匹配引擎 v1
方法：三问定阴阳→阳证/阴证方库。渴饮/舌象/脉象锁定阴阳大方向，
      然后扩展辨证细化方证选择。
输入：勾选的症状ID列表
输出：阴阳判定 + 推荐方剂
"""

import json
import os
from typing import Dict, List, Tuple

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "郑钦安阴阳辨证勾选表_v1.json")


class ZhengQinAnEngine:
    """郑钦安引擎：阴阳二分 → 方证推荐"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # 核心三问：渴饮/舌象/脉象 的阴阳方向
        self._sanwen_map: Dict[str, str] = {}       # id → direction (阴证/阳证)
        self._extended_map: Dict[str, str] = {}       # id → 症状文本（扩展项）
        self._yangxu_signals: List[str] = []          # 阳虚专项信号

        self._build_maps()

    def _build_maps(self):
        """构建各项索引"""
        # Step1: 核心三问
        for section in self.data["step1_核心三问"]["sections"]:
            for item in section.get("items", []):
                direction = item.get("direction", "")
                if direction:
                    self._sanwen_map[item["id"]] = direction

        # Step2: 扩展辨证
        for section in self.data["step2_扩展辨证"]["sections"]:
            for item in section.get("items", []):
                self._extended_map[item["id"]] = item["text"]

        # 阳虚信号
        self._yangxu_signals = self.data.get("yangxu_signals", {}).get("items", [])

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """
        辨证逻辑：
        1. 核心三问中有信号的项 → 统计 yin_count vs yang_count
        2. 如果三问信号明确 → 直接定阴阳
        3. 扩展症状辅助验证 → 推荐相应方剂
        """
        yin_count = 0
        yang_count = 0
        sanwen_detail: List[Dict] = []

        for sid in checked_ids:
            if sid in self._sanwen_map:
                d = self._sanwen_map[sid]
                if "阴" in d:
                    yin_count += 1
                else:
                    yang_count += 1
                sanwen_detail.append({"id": sid, "direction": d})

        # 阴阳判定
        if yin_count > yang_count:
            yin_yang = "阴证"
        elif yang_count > yin_count:
            yin_yang = "阳证"
        elif yin_count == 0 and yang_count == 0:
            yin_yang = "无法判定（三问信号不足）"
        else:
            yin_yang = "平（阴阳信号对等，需结合扩展辨证）"

        # 扩展症状收集
        extended_hits = []
        for sid in checked_ids:
            if sid in self._extended_map:
                extended_hits.append({"id": sid, "text": self._extended_map[sid]})

        # 阳虚信号统计（直接匹配，避免逗号/标点导致漏检）
        yangxu_hits = []
        def _norm(s: str) -> str:
            """去除所有非关键标点，统一用于模糊匹配"""
            for ch in "，。、；：（）　 ,.;:()":
                s = s.replace(ch, "")
            return s

        norm_texts = {_norm(eh["text"]): eh["text"] for eh in extended_hits}

        for signal in self._yangxu_signals:
            norm_signal = _norm(signal)
            for norm_t, raw_t in norm_texts.items():
                if norm_signal in norm_t or any(
                    part in norm_t for part in norm_signal.split("/") if part
                ):
                    if raw_t not in yangxu_hits:
                        yangxu_hits.append(raw_t)
                    break

        # 方证推荐
        formulas = self._recommend_formulas(yin_yang, extended_hits, yangxu_hits)

        return {
            "yin_yang": yin_yang,
            "yin_count": yin_count,
            "yang_count": yang_count,
            "sanwen_detail": sanwen_detail,
            "extended_hits": extended_hits,
            "yangxu_signals": yangxu_hits,
            "formulas": formulas,
            "total_checked": len(checked_ids)
        }

    def _recommend_formulas(self, yin_yang: str, extended: List[Dict], yangxu: List[str]) -> List[str]:
        """根据阴阳判定 + 扩展症状推荐方剂（郑钦安核心方库）"""
        formulas = []
        ext_texts = " ".join(e["text"] for e in extended)

        if yin_yang == "阴证":
            formulas.append("四逆汤（少阴寒化主方）")

            # 阴盛格阳
            if "下利清谷" in ext_texts or "完谷不化" in ext_texts:
                formulas.append("通脉四逆汤（阴盛格阳于上）")
            if "面赤" in ext_texts and (
                "手足厥冷" in ext_texts or "手足逆冷" in ext_texts
            ):
                formulas.append("白通汤（阴盛戴阳）")

            # 阳虚水泛
            if "浮肿" in ext_texts or "水肿" in ext_texts:
                formulas.append("真武汤（阳虚水泛）")
            if "小便不利" in ext_texts and "浮肿" not in ext_texts:
                formulas.append("苓桂术甘汤（阳虚水停）")

            # 阳虚漏汗
            if "自汗" in ext_texts or "大汗出" in ext_texts:
                formulas.append("桂枝加附子汤（阳虚漏汗）")

            # 血虚寒厥
            if ("手足厥冷" in ext_texts or "手足逆冷" in ext_texts) and \
               "下利清谷" not in ext_texts:
                formulas.append("当归四逆汤（血虚寒厥）")

            # 中焦虚寒
            if yangxu and ("纳呆" in ext_texts or "食不下" in ext_texts or "大便溏" in ext_texts):
                formulas.append("桂附理中汤（中焦虚寒）")
            if "但欲寐" in ext_texts:
                formulas.append("四逆汤加人参（少阴寒化伤津）")
            if "腹痛喜按" in ext_texts:
                formulas.append("小建中汤（中焦虚寒腹痛）")

            # 阴虚阳浮（阴证基础上的假热）
            if "面赤" in ext_texts or "咽干" in ext_texts:
                formulas.append("潜阳丹（阴虚阳浮，上热下寒）")
            if "咽痛" in ext_texts:
                formulas.append("封髓丹（阴火上冲咽痛）")

        elif yin_yang == "阳证":
            formulas.append("白虎汤（阳明经证）")

            # 阳明腑实
            if "谵语" in ext_texts or "发狂" in ext_texts:
                formulas.append("大承气汤（阳明腑实）")
            if "便秘" in ext_texts or "大便不通" in ext_texts:
                formulas.append("调胃承气汤（阳明燥结）")

            # 阴虚水热
            if "小便短赤" in ext_texts or "小便不利" in ext_texts:
                if "心烦" in ext_texts:
                    formulas.append("猪苓汤（阴虚水热互结）")
                else:
                    formulas.append("五苓散（膀胱气化不利）")

            # 少阴热化
            if "心烦" in ext_texts or "不得卧" in ext_texts:
                formulas.append("黄连阿胶汤（少阴热化）")

            # 协热下利
            if "下利" in ext_texts or "拉肚子" in ext_texts:
                formulas.append("葛根黄芩黄连汤（协热下利）")

            # 少阳枢机不利
            if "口苦" in ext_texts or "咽干" in ext_texts:
                formulas.append("小柴胡汤（少阳枢机不利）")

            # 热入血室
            if "谵语" in ext_texts and "发热" in ext_texts:
                formulas.append("桃核承气汤（热入血室）")

        elif yin_yang == "平（阴阳信号对等，需结合扩展辨证）":
            # 阴阳对等时靠扩展症状区分
            if yangxu:
                formulas.append("四逆汤（阳虚为主，兼有假热）")
                if "面赤" in ext_texts:
                    formulas.append("潜阳丹（阴盛逼阳上浮）")
            else:
                if "发热" in ext_texts:
                    formulas.append("白虎加人参汤（气津两伤）")
                if "脉有力" in ext_texts or "脉数" in ext_texts:
                    formulas.append("调胃承气汤（阳明初结）")

        return formulas

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 郑钦安阴阳辨证结果 ===")
        lines.append(f"阴阳判定: {result['yin_yang']}")
        lines.append(f"  阴证信号: {result['yin_count']}  |  阳证信号: {result['yang_count']}")
        lines.append("")

        if result["sanwen_detail"]:
            lines.append("【核心三问命中】")
            for d in result["sanwen_detail"]:
                lines.append(f"  - [{d['id']}] → {d['direction']}")

        if result["extended_hits"]:
            lines.append(f"\n【扩展症状】({len(result['extended_hits'])} 项)")
            for e in result["extended_hits"]:
                lines.append(f"  - {e['text']}")

        if result["yangxu_signals"]:
            lines.append(f"\n【阳虚专项信号命中】({len(result['yangxu_signals'])} 项)")
            for s in result["yangxu_signals"]:
                lines.append(f"  - {s}")

        if result["formulas"]:
            lines.append(f"\n【推荐方剂】")
            for f in result["formulas"]:
                lines.append(f"  → {f}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhengQinAnEngine()
    print(f"已加载: 三问 {len(engine._sanwen_map)} 项, 扩展 {len(engine._extended_map)} 项")

    # 模拟阴证
    test_yin = ["za_kou_buke", "za_she_run", "za_mai_wu_li",
                "za_hanre_eweihan", "za_sz_ju_leng", "za_ebian_xia_li_qing_gu"]
    result = engine.diagnose(test_yin)
    print(engine.format_result(result))
    print("\n" + "="*50 + "\n")

    # 模拟阳证
    test_yang = ["za_ke_xi_leng_yin", "za_she_gan", "za_mai_you_li",
                 "za_hanre_fare", "za_shen_chan_yu"]
    result2 = engine.diagnose(test_yang)
    print(engine.format_result(result2))
