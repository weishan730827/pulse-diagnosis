#!/usr/bin/env python3
"""
郑钦安阴阳辨证匹配引擎 v2（对接仲景基座+自创方附录）
方法：三问定阴阳→阳证/阴证方库。渴饮/舌象/脉象锁定阴阳大方向，
      然后扩展辨证细化方证选择。
      v2：方剂主体对接仲景基座，保留6个自创方为附录。
输入：勾选的症状ID列表
输出：阴阳判定 + 推荐方剂
"""

import json
import os
import sys
from typing import Dict, List, Tuple

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _OUTPUT_DIR)
sys.path.insert(0, os.path.join(_OUTPUT_DIR, ".."))
from formula_utils import is_zhongjing, SELF_CREATED


def extract_formula_name(raw: str) -> str:
    import re
    raw = raw.strip()
    raw = re.sub(r'[（(].*?[）)]', '', raw)
    raw = re.sub(r'【.*?】', '', raw)
    return raw.strip()

CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "郑钦安阴阳辨证勾选表_v1.json")

# 郑钦安自创方附录（不在仲景153方中但属火神派核心方）
ZHEN_QN_SELF = ["潜阳丹", "封髓丹", "桂附理中汤", "附子理中汤", "导赤散"]


class ZhengQinAnEngine:
    """郑钦安引擎：阴阳二分 → 方证推荐。主方对接仲景基座，自创方标注附录。"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._sanwen_map: Dict[str, str] = {}
        self._extended_map: Dict[str, str] = {}
        self._yangxu_signals: List[str] = []
        self._build_maps()
        self._skills = self._load_skills("zqa_skills_v1.json")

    def _load_skills(self, filename: str) -> dict:
        path = os.path.join(_OUTPUT_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        skill_map = {}
        for item in data:
            if "_meta" in item:
                continue
            formula_raw = item.get("formula", "")
            core = extract_formula_name(formula_raw)
            skill_map[core] = item
        return skill_map

    def _match_skill(self, formula_name: str) -> dict:
        core = extract_formula_name(formula_name)
        return self._skills.get(core)

    def _build_maps(self):
        for section in self.data["step1_核心三问"]["sections"]:
            for item in section.get("items", []):
                direction = item.get("direction", "")
                if direction:
                    self._sanwen_map[item["id"]] = direction
        for section in self.data["step2_扩展辨证"]["sections"]:
            for item in section.get("items", []):
                self._extended_map[item["id"]] = item["text"]
        self._yangxu_signals = self.data.get("yangxu_signals", {}).get("items", [])

    def diagnose(self, checked_ids: List[str]) -> Dict:
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

        if yin_count > yang_count:
            yin_yang = "阴证"
        elif yang_count > yin_count:
            yin_yang = "阳证"
        elif yin_count == 0 and yang_count == 0:
            yin_yang = "无法判定（三问信号不足）"
        else:
            yin_yang = "平（阴阳信号对等，需结合扩展辨证）"

        extended_hits = []
        for sid in checked_ids:
            if sid in self._extended_map:
                extended_hits.append({"id": sid, "text": self._extended_map[sid]})

        yangxu_hits = []
        def _norm(s: str) -> str:
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
        formulas = []
        ext_texts = " ".join(e["text"] for e in extended)

        def _add(f: str):
            name = f.split("（")[0].strip()
            for existing in formulas:
                if existing.split("（")[0].strip() == name:
                    return
            formulas.append(f)

        def _tag(fang_name: str, annotation: str) -> str:
            """标注自创方"""
            if fang_name in ZHEN_QN_SELF:
                return f"{fang_name}【自创方附录】{annotation}"
            return f"{fang_name}（{annotation}）"

        if yin_yang == "阴证":
            _add(_tag("四逆汤", "少阴寒化·回阳救逆第一方"))
            if "下利清谷" in ext_texts or "完谷不化" in ext_texts:
                _add(_tag("通脉四逆汤", "阴盛格阳于上"))
            if "面赤" in ext_texts and ("手足厥冷" in ext_texts or "手足逆冷" in ext_texts):
                _add(_tag("白通汤", "阴盛戴阳·下利脉微面赤"))
            if ("烦躁" in ext_texts or "但欲寐" in ext_texts) and "下利" in ext_texts:
                _add(_tag("茯苓四逆汤", "阳虚烦躁·阴阳两伤") if is_zhongjing("茯苓四逆汤") else _tag("四逆加人参汤", "阳虚烦躁"))
            if "发热" in ext_texts and ("恶寒" in ext_texts or "手足厥冷" in ext_texts):
                _add(_tag("麻黄附子细辛汤", "太少两感·阳虚外寒"))
            if "头痛" in ext_texts and ("恶寒" in ext_texts or "畏寒" in ext_texts):
                _add(_tag("麻黄附子细辛汤", "寒中少阴头痛"))
            if "背恶寒" in ext_texts:
                _add(_tag("附子汤", "少阴病背恶寒·阳虚寒湿"))
            if "浮肿" in ext_texts or "水肿" in ext_texts:
                _add(_tag("真武汤", "阳虚水泛·小便不利四肢沉重"))
            if "小便不利" in ext_texts and "浮肿" not in ext_texts:
                _add(_tag("苓桂术甘汤", "阳虚水停·心下逆满"))
            if "振振欲擗地" in ext_texts or "头眩" in ext_texts:
                _add(_tag("真武汤", "阳虚水泛上冲"))
            if "自汗" in ext_texts or "大汗出" in ext_texts or "漏汗" in ext_texts:
                _add(_tag("桂枝加附子汤", "阳虚漏汗·表虚不固"))
            if ("手足厥冷" in ext_texts or "手足逆冷" in ext_texts) and "下利清谷" not in ext_texts:
                _add(_tag("当归四逆汤", "血虚寒厥·手足厥寒脉细"))
            if "寒疝" in ext_texts or "少腹冷痛" in ext_texts:
                _add(_tag("当归四逆加吴茱萸生姜汤", "血虚寒凝厥阴"))
            if "纳呆" in ext_texts or "食不下" in ext_texts or "大便溏" in ext_texts:
                if "呕吐" in ext_texts:
                    _add(_tag("吴茱萸汤", "肝胃虚寒·呕而胸满"))
                _add(_tag("桂附理中汤", "中焦虚寒·理中加桂附"))
            if "胃痛" in ext_texts or "腹痛喜按" in ext_texts:
                _add(_tag("小建中汤", "中焦虚寒腹痛"))
                if "呕" in ext_texts:
                    _add(_tag("大建中汤", "中焦虚寒重证"))
            if "呕" in ext_texts and "四逆" in ext_texts:
                _add(_tag("附子理中汤", "中焦虚寒呕吐"))
            if "面赤" in ext_texts or "咽干" in ext_texts or "烦躁" in ext_texts:
                _add(_tag("潜阳丹", "阴虚阳浮·上热下寒·火不归元"))
            if "咽痛" in ext_texts:
                _add(_tag("封髓丹", "阴火上冲咽痛·纳气归肾"))
            if "口舌生疮" in ext_texts or "牙龈肿痛" in ext_texts:
                _add(f"潜阳丹合封髓丹【自创方附录】（虚火上炎·引火归元）")
            if "咳" in ext_texts or "喘" in ext_texts:
                _add(_tag("甘草干姜汤", "肺中虚冷·吐涎沫"))
            if "四肢拘急" in ext_texts or "转筋" in ext_texts:
                _add(_tag("芍药甘草附子汤", "阳虚筋急"))
            if "吐血" in ext_texts or "便血" in ext_texts or "崩漏" in ext_texts:
                _add(_tag("甘草干姜汤", "温摄止血·不摄血者温其阳"))

        elif yin_yang == "阳证":
            _add(_tag("白虎汤", "阳明经证·四大证"))
            if "谵语" in ext_texts or "发狂" in ext_texts:
                _add(_tag("大承气汤", "阳明腑实·痞满燥实"))
            if "便秘" in ext_texts or "大便不通" in ext_texts:
                _add(_tag("调胃承气汤", "阳明燥结"))
            if "热结旁流" in ext_texts:
                _add(_tag("大承气汤", "热结旁流·通因通用"))
            if "大汗出" in ext_texts and "大烦渴" in ext_texts:
                _add(_tag("白虎加人参汤", "阳明热盛伤津"))
            if "口渴" in ext_texts and "小便不利" in ext_texts:
                _add(_tag("猪苓汤", "阴虚水热互结"))
            if "小便短赤" in ext_texts:
                _add(_tag("导赤散", "心火下移小肠"))
            if "下利" in ext_texts or "泄泻" in ext_texts:
                _add(_tag("葛根黄芩黄连汤", "协热下利·表未解而下利"))
            if "热利" in ext_texts and "后重" in ext_texts:
                _add(_tag("白头翁汤", "厥阴热利·下重便脓血"))
            if "心烦" in ext_texts or "不得卧" in ext_texts or "失眠" in ext_texts:
                _add(_tag("黄连阿胶汤", "少阴热化·心中烦不得卧"))
            if ("心烦" in ext_texts or "不得卧" in ext_texts) and "小便不利" in ext_texts:
                _add(_tag("猪苓汤", "阴虚水热·心烦不眠"))
            if "胸中烦" in ext_texts or ("心烦" in ext_texts and "懊憹" in ext_texts):
                _add(_tag("栀子豉汤", "胸膈郁热·虚烦不眠"))
            if "口苦" in ext_texts or "咽干" in ext_texts or "目眩" in ext_texts:
                _add(_tag("小柴胡汤", "少阳枢机不利"))
            if "胸胁苦满" in ext_texts:
                _add(_tag("大柴胡汤", "少阳阳明合病"))
            if "谵语" in ext_texts and "发热" in ext_texts:
                _add(_tag("桃核承气汤", "热入血室·其人如狂"))
            if "发狂" in ext_texts:
                _add(_tag("抵当汤", "下焦蓄血·发狂"))
            if "黄疸" in ext_texts or "身黄" in ext_texts:
                _add(_tag("茵陈蒿汤", "阳明湿热发黄"))
            if "心下痛" in ext_texts or "结胸" in ext_texts:
                _add(_tag("大陷胸汤", "热实结胸·心下硬痛"))

        elif yin_yang == "平（阴阳信号对等，需结合扩展辨证）":
            if yangxu:
                _add(_tag("四逆汤", "阳虚为主·兼有假热"))
                if "面赤" in ext_texts:
                    _add(_tag("潜阳丹", "阴盛逼阳上浮·火不归元"))
                if "咽痛" in ext_texts:
                    _add(_tag("封髓丹", "阴火上冲咽痛"))
            else:
                if "发热" in ext_texts:
                    _add(_tag("白虎加人参汤", "气津两伤"))
                if "脉有力" in ext_texts or "脉数" in ext_texts:
                    _add(_tag("调胃承气汤", "阳明初结"))

        return formulas

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 郑钦安阴阳辨证结果（v2 仲景基座+自创方附录） ===")
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
            if result["formulas"]:
                top = result["formulas"][0]
                skill = self._match_skill(top)
                if skill:
                    lines.append(f"\n【Skill蒸馏 {skill['id']}】{skill.get('group','')}")
                    lines.append(f"  辨证逻辑: {skill['core_logic'][:150]}...")
                    lines.append(f"  基础方药: {skill['base']}")
                    if skill.get("if_then"):
                        for rule in skill["if_then"][:3]:
                            lines.append(f"    · {rule['if']} → {rule['then']}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhengQinAnEngine()
    print(f"已加载: 三问 {len(engine._sanwen_map)} 项, 扩展 {len(engine._extended_map)} 项")
    print()
    test_yin = ["za_kou_buke", "za_she_run", "za_mai_wu_li",
                "za_hanre_eweihan", "za_sz_ju_leng", "za_ebian_xia_li_qing_gu"]
    print("--- 阴证测试: 少阴寒化+下利清谷 ---")
    r1 = engine.diagnose(test_yin)
    print(engine.format_result(r1))
