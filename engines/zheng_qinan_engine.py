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
        """郑钦安核心方库——火神派全方，逐证细化"""
        formulas = []
        ext_texts = " ".join(e["text"] for e in extended)

        def _add(f: str):
            """去重添加：按方剂名首词（如「四逆汤」）去重，注解不同时追加"""
            name = f.split("（")[0].strip()
            for existing in formulas:
                if existing.split("（")[0].strip() == name:
                    return
            formulas.append(f)

        if yin_yang == "阴证":
            # === 少阴寒化主干 ===
            _add("四逆汤（少阴寒化·回阳救逆第一方）")

            # 阴盛格阳系列
            if "下利清谷" in ext_texts or "完谷不化" in ext_texts:
                _add("通脉四逆汤（阴盛格阳于上·证见身反不恶寒面赤）")
            if "面赤" in ext_texts and ("手足厥冷" in ext_texts or "手足逆冷" in ext_texts):
                _add("白通汤（阴盛戴阳·下利脉微面赤）")
            if ("烦躁" in ext_texts or "但欲寐" in ext_texts) and "下利" in ext_texts:
                _add("茯苓四逆汤（阳虚烦躁·阴阳两伤）")

            # 阳虚表寒
            if "发热" in ext_texts and ("恶寒" in ext_texts or "手足厥冷" in ext_texts):
                _add("麻黄附子细辛汤（太少两感·阳虚外寒）")
            if "头痛" in ext_texts and ("恶寒" in ext_texts or "畏寒" in ext_texts):
                _add("麻黄附子细辛汤（寒中少阴头痛）")
            if "背恶寒" in ext_texts:
                _add("附子汤（少阴病背恶寒·阳虚寒湿）")

            # 阳虚水泛
            if "浮肿" in ext_texts or "水肿" in ext_texts:
                _add("真武汤（阳虚水泛·小便不利四肢沉重）")
            if "小便不利" in ext_texts and "浮肿" not in ext_texts:
                _add("苓桂术甘汤（阳虚水停·心下逆满）")
            if "振振欲擗地" in ext_texts or "头眩" in ext_texts:
                _add("真武汤（阳虚水泛上冲）")

            # 阳虚汗出
            if "自汗" in ext_texts or "大汗出" in ext_texts or "漏汗" in ext_texts:
                _add("桂枝加附子汤（阳虚漏汗·表虚不固）")

            # 血虚寒厥
            if ("手足厥冷" in ext_texts or "手足逆冷" in ext_texts) and "下利清谷" not in ext_texts:
                _add("当归四逆汤（血虚寒厥·手足厥寒脉细）")
            if "寒疝" in ext_texts or "少腹冷痛" in ext_texts:
                _add("当归四逆加吴茱萸生姜汤（血虚寒凝厥阴）")

            # 中焦虚寒
            if "纳呆" in ext_texts or "食不下" in ext_texts or "大便溏" in ext_texts:
                if "呕吐" in ext_texts:
                    _add("吴茱萸汤（肝胃虚寒·呕而胸满）")
                _add("桂附理中汤（中焦虚寒·理中加桂附）")
            if "胃痛" in ext_texts or "腹痛喜按" in ext_texts:
                _add("小建中汤（中焦虚寒腹痛）")
                _add("大建中汤（中焦虚寒重证）" if "呕" in ext_texts else "")
                formulas = [f for f in formulas if f]
            if "呕" in ext_texts and "四逆" in ext_texts:
                _add("附子理中汤（中焦虚寒呕吐）")

            # 阴虚阳浮（阴证假热——火神派标志性辨证）
            if "面赤" in ext_texts or "咽干" in ext_texts or "烦躁" in ext_texts:
                _add("潜阳丹（阴虚阳浮·上热下寒·火不归元）")
            if "咽痛" in ext_texts:
                _add("封髓丹（阴火上冲咽痛·纳气归肾）")
            if "口舌生疮" in ext_texts or "牙龈肿痛" in ext_texts:
                _add("潜阳丹合封髓丹（虚火上炎·引火归元）")

            # 肺寒
            if "咳" in ext_texts or "喘" in ext_texts:
                _add("甘草干姜汤（肺中虚冷·吐涎沫）")

            # 四肢拘急
            if "四肢拘急" in ext_texts or "转筋" in ext_texts:
                _add("芍药甘草附子汤（阳虚筋急）")

            # 失血亡阳
            if "吐血" in ext_texts or "便血" in ext_texts or "崩漏" in ext_texts:
                _add("甘草干姜汤（温摄止血·不摄血者温其阳）")

        elif yin_yang == "阳证":
            _add("白虎汤（阳明经证·四大证）")

            # 阳明腑实
            if "谵语" in ext_texts or "发狂" in ext_texts:
                _add("大承气汤（阳明腑实·痞满燥实）")
            if "便秘" in ext_texts or "大便不通" in ext_texts:
                _add("调胃承气汤（阳明燥结）")
            if "热结旁流" in ext_texts:
                _add("大承气汤（热结旁流·通因通用）")

            # 气津两伤
            if "大汗出" in ext_texts and "大烦渴" in ext_texts:
                _add("白虎加人参汤（阳明热盛伤津）")
            if "口渴" in ext_texts and "小便不利" in ext_texts:
                _add("猪苓汤（阴虚水热互结）")
            if "小便短赤" in ext_texts:
                _add("导赤散（心火下移小肠）")

            # 协热下利
            if "下利" in ext_texts or "泄泻" in ext_texts:
                _add("葛根黄芩黄连汤（协热下利·表未解而下利）")
            if "热利" in ext_texts and "后重" in ext_texts:
                _add("白头翁汤（厥阴热利·下重便脓血）")

            # 少阴热化
            if "心烦" in ext_texts or "不得卧" in ext_texts or "失眠" in ext_texts:
                _add("黄连阿胶汤（少阴热化·心中烦不得卧）")
            if ("心烦" in ext_texts or "不得卧" in ext_texts) and "小便不利" in ext_texts:
                _add("猪苓汤（阴虚水热·心烦不眠）")

            # 胸膈郁热
            if "胸中烦" in ext_texts or ("心烦" in ext_texts and "懊憹" in ext_texts):
                _add("栀子豉汤（胸膈郁热·虚烦不眠）")

            # 少阳枢机不利
            if "口苦" in ext_texts or "咽干" in ext_texts or "目眩" in ext_texts:
                _add("小柴胡汤（少阳枢机不利）")
            if "胸胁苦满" in ext_texts:
                _add("大柴胡汤（少阳阳明合病）")

            # 热入血室 / 蓄血
            if "谵语" in ext_texts and "发热" in ext_texts:
                _add("桃核承气汤（热入血室·其人如狂）")
            if "发狂" in ext_texts:
                _add("抵当汤（下焦蓄血·发狂）")

            # 黄疸
            if "黄疸" in ext_texts or "身黄" in ext_texts:
                formulas.append("茵陈蒿汤（阳明湿热发黄）")

            # 结胸
            if "心下痛" in ext_texts or "结胸" in ext_texts:
                formulas.append("大陷胸汤（热实结胸·心下硬痛）")

        elif yin_yang == "平（阴阳信号对等，需结合扩展辨证）":
            if yangxu:
                formulas.append("四逆汤（阳虚为主·兼有假热）")
                if "面赤" in ext_texts:
                    formulas.append("潜阳丹（阴盛逼阳上浮·火不归元）")
                if "咽痛" in ext_texts:
                    formulas.append("封髓丹（阴火上冲咽痛）")
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

    def get_full_fangku(self) -> str:
        """展示郑钦安全部可用方剂库（按阴证/阳证分类）"""
        lines = []
        lines.append("=== 郑钦安火神派方剂全库 ===")
        lines.append("")
        lines.append("【阴证方剂】（以四逆汤为基，随证加减）")
        lines.append("  少阴主干: 四逆汤、四逆加人参汤、茯苓四逆汤")
        lines.append("  阴盛格阳: 通脉四逆汤、白通汤、白通加猪胆汁汤")
        lines.append("  阳虚表寒: 麻黄附子细辛汤、麻黄附子甘草汤、附子汤")
        lines.append("  阳虚水泛: 真武汤、苓桂术甘汤")
        lines.append("  阳虚漏汗: 桂枝加附子汤")
        lines.append("  血虚寒厥: 当归四逆汤、当归四逆加吴茱萸生姜汤")
        lines.append("  中焦虚寒: 理中汤、桂附理中汤、附子理中汤、小建中汤、大建中汤、吴茱萸汤")
        lines.append("  虚阳浮越: 潜阳丹、封髓丹、潜阳丹合封髓丹")
        lines.append("  肺寒/失血: 甘草干姜汤")
        lines.append("  阳虚筋急: 芍药甘草附子汤")
        lines.append("")
        lines.append("【阳证方剂】（以白虎/承气为基，随证加减）")
        lines.append("  阳明经证: 白虎汤、白虎加人参汤")
        lines.append("  阳明腑实: 大承气汤、小承气汤、调胃承气汤")
        lines.append("  协热下利: 葛根黄芩黄连汤")
        lines.append("  厥阴热利: 白头翁汤")
        lines.append("  少阴热化: 黄连阿胶汤")
        lines.append("  阴虚水热: 猪苓汤、导赤散")
        lines.append("  胸膈郁热: 栀子豉汤")
        lines.append("  少阳枢机: 小柴胡汤、大柴胡汤")
        lines.append("  热入血室: 桃核承气汤、抵当汤")
        lines.append("  阳明发黄: 茵陈蒿汤")
        lines.append("  结胸: 大陷胸汤")
        lines.append("")
        lines.append("共 40+ 方，按郑钦安阴阳辨证体系逐一索引。")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhengQinAnEngine()
    print(f"已加载: 三问 {len(engine._sanwen_map)} 项, 扩展 {len(engine._extended_map)} 项")
    print()

    # 模拟阴证1: 少阴寒化+下利清谷
    test_yin_1 = ["za_kou_buke", "za_she_run", "za_mai_wu_li",
                  "za_hanre_eweihan", "za_sz_ju_leng", "za_ebian_xia_li_qing_gu"]
    print("--- 阴证测试1: 少阴寒化+下利清谷 ---")
    r1 = engine.diagnose(test_yin_1)
    print(engine.format_result(r1))
    print()

    # 模拟阴证2: 戴阳+烦躁 (白通汤/茯苓四逆汤)
    test_yin_2 = ["za_kou_buke", "za_mai_wu_li", "za_sz_ju_leng",
                  "za_ebian_xia_li_qing_gu", "za_tou_mian_chi", "za_shen_fan_zao"]
    print("--- 阴证测试2: 戴阳+烦躁 ---")
    r2 = engine.diagnose(test_yin_2)
    print(engine.format_result(r2))
    print()

    # 模拟阴证3: 太少两感 (麻黄附子细辛汤)
    test_yin_3 = ["za_kou_buke", "za_mai_wu_li", "za_hanre_fare",
                  "za_hanre_eweihan", "za_tou_tong"]
    print("--- 阴证测试3: 太少两感 ---")
    r3 = engine.diagnose(test_yin_3)
    print(engine.format_result(r3))
    print()

    # 模拟阴证4: 虚阳浮越 (潜阳丹/封髓丹)
    test_yin_4 = ["za_kou_buke", "za_she_run", "za_mai_wu_li",
                  "za_tou_mian_chi", "za_yan_tong",
                  "za_shen_fan_zao", "za_yin_bu_yu_yin"]
    print("--- 阴证测试4: 虚阳浮越·咽痛面赤 ---")
    r4 = engine.diagnose(test_yin_4)
    print(engine.format_result(r4))
    print()

    # 模拟阳证1: 少阴热化·心烦不寐
    test_yang_1 = ["za_ke_xi_leng_yin", "za_she_gan", "za_mai_you_li",
                   "za_hanre_fare", "za_shen_fan_zao", "za_shen_bu_mei",
                   "za_xiong_xin_fan"]
    print("--- 阳证测试1: 少阴热化·心烦不寐 ---")
    r5 = engine.diagnose(test_yang_1)
    print(engine.format_result(r5))
    print()

    # 模拟阳证2: 阳明腑实+谵语
    test_yang_2 = ["za_ke_xi_leng_yin", "za_mai_you_li", "za_hanre_fare",
                   "za_shen_chan_yu", "za_ebian_bianmi",
                   "za_hanre_wuhan_buere"]
    print("--- 阳证测试2: 阳明腑实+谵语 ---")
    r6 = engine.diagnose(test_yang_2)
    print(engine.format_result(r6))
    print()

    # 展示全方库
    print(engine.get_full_fangku())
