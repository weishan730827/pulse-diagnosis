#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v8
仅使用《医学衷中参西录》医方篇33门177首方剂
三层辨证漏斗：
  第一步：辨气机升降（下陷/上逆/中性）
  第二步：33门症状路由（门类定位）
  第三步：门内方证匹配（症状→方剂）

原著依据：《医学衷中参西录》医方篇33门，15749行全文检索
"""

import json, os
from typing import Dict, List

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v4.json")

# 气机升降专用方池
XIAXIAN_POOL = {"升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤"}
SHANGNI_POOL = {"参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "清降汤",
                "保元寒降汤", "保元清降汤", "秘红丹", "薯蓣纳气汤", "滋培汤"}


class ZhangXiChunEngineV8:
    """v8引擎：纯33门177首，无仲景外引"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._build_section_map()

    def _build_section_map(self):
        self.sections = {}
        for key, val in self.data.items():
            if key.startswith("s_") and isinstance(val, dict) and "formulas" in val:
                self.sections[key] = val

    def _clean_name(self, raw_name: str) -> str:
        """去除编号前缀 '1．寒降汤' → '寒降汤'"""
        return raw_name.split("．", 1)[-1] if "．" in raw_name else raw_name

    def diagnose(self, symptom_text: str) -> Dict:
        chain = []

        # 第一步：辨气机升降
        qi_direction = self._judge_qi_direction(symptom_text, chain)

        # 第二步：症状→门类路由
        section_scores = self._match_sections(symptom_text, chain)

        # 第三步：门内方证匹配
        formula_scores = self._match_formulas(symptom_text, section_scores, qi_direction, chain)

        return {
            "qi_direction": qi_direction,
            "formula_scores": formula_scores,
            "chain": chain,
        }

    def _judge_qi_direction(self, text: str, chain: List[str]) -> str:
        sinking_signs = ["短气", "不足以息", "努力呼吸", "气息将停", "气短不足以息"]
        counterflow_signs = ["喘逆", "气上冲", "呕逆", "呃逆", "上逆", "冲气上干",
                            "冲脉逆气", "胃气上逆", "胆火上冲", "胃气不降", "气不降"]

        n_sink = sum(1 for s in sinking_signs if s in text)
        n_flow = sum(1 for s in counterflow_signs if s in text)

        if n_sink > 0 and n_flow == 0:
            chain.append("【第一步·辨气机】判定为「大气下陷」→ 升陷类方")
            return "sinking"
        elif n_flow > 0 and n_sink == 0:
            chain.append("【第一步·辨气机】判定为「气机上逆」→ 镇降类方")
            return "counterflow"
        elif n_sink > 0 and n_flow > 0:
            chain.append("【第一步·辨气机】判定为「升降失调」→ 升陷+镇降并见")
            return "mixed"
        else:
            chain.append("【第一步·辨气机】无明显升降偏倾 → 直接门类匹配")
            return "neutral"

    def _match_sections(self, text: str, chain: List[str]) -> Dict[str, float]:
        # 33门关键词
        section_keywords = {
            "s_01_阴虚劳热": ["虚劳", "羸瘦", "劳瘵", "脉数", "脉弦数", "肌肤甲错", "阴虚作热"],
            "s_02_阳虚": ["阳虚", "阳分衰惫", "畏寒", "四肢不温"],
            "s_03_大气下陷": ["大气下陷", "气短不足以息", "气息将停"],
            "s_04_喘息": ["喘逆", "喘促", "不纳气", "肺肾两虚"],
            "s_05_痰饮": ["痰涎", "饮邪", "生痰", "痰盛", "痰气郁结"],
            "s_06_肺病": ["肺痈", "肺痿", "劳嗽", "肺虚", "肺损", "肺中腐烂"],
            "s_07_吐衄": ["吐血", "衄血", "咳血", "痰中带血", "下血", "瘀血膈上", "吐衄", "便下血"],
            "s_08_心病": ["怔忡", "惊悸", "心中", "怔冲"],
            "s_09_癫狂": ["癫狂", "失心", "神志", "思虑过度"],
            "s_10_痫风": ["痫风", "抽搐"],
            "s_11_小儿风证": ["小儿", "初生", "急惊风", "绵风"],
            "s_12_中风": ["中风", "偏枯", "脑充血", "不遂", "历节风", "破伤后", "上盛下虚",
                          "脉弦长有力", "头重目眩", "神昏健忘", "昏仆", "血压过高"],
            "s_13_痿废": ["痿废", "痹木"],
            "s_14_膈食": ["膈食", "噎膈", "反胃"],
            "s_15_呕吐": ["呕吐", "呕", "闻药气"],
            "s_16_霍乱": ["霍乱", "吐泻转筋"],
            "s_17_泄泻": ["泄泻", "完谷不化", "肠滑", "大便滑泻", "滑泻"],
            "s_18_痢": ["痢", "下痢", "里急后重", "噤口痢", "热痢", "脓血"],
            "s_19_燥结": ["燥结", "大便燥结", "宿食结"],
            "s_20_消渴": ["消渴"],
            "s_21_癃闭": ["小便不利", "小便不通", "水肿", "臌胀", "小便滴沥"],
            "s_22_淋浊": ["淋", "血淋", "膏淋", "气淋", "石淋", "砂淋", "白浊", "遗精", "溺血"],
            "s_23_伤寒": ["伤寒", "无汗", "表证未罢", "有汗"],
            "s_24_温病": ["温病", "表里俱热", "肌肤壮热", "感冒", "湿温", "憎寒壮热", "头疼",
                          "周身", "脉浮", "骨节酸疼", "恶寒无汗"],
            "s_25_伤寒温病同用": ["阳明", "石膏", "结胸"],
            "s_26_瘟疫": ["瘟疫", "发斑疹", "头面肿疼", "阳毒"],
            "s_27_疟疾": ["疟", "久疟"],
            "s_28_肢体疼痛": ["肝郁脾弱", "胁下掀疼", "腿疼", "臂疼", "腰疼", "气血凝滞",
                            "肝气不舒"],
            "s_29_女科": ["经闭", "月事不调", "血崩", "带下", "滑胎", "恶阻", "产难",
                         "乳少", "产后", "倒经", "血海虚寒", "阴挺", "室女", "恶露不尽", "妇人"],
            "s_30_眼科": ["眼", "目睛", "目翳", "云翳", "赤脉络目", "羞明", "瞳散"],
            "s_31_咽喉": ["咽喉"],
            "s_32_牙疳": ["牙疳"],
            "s_33_疮科": ["疮疡", "瘰疬", "杨梅疮", "瘰", "化脓生肌", "红肿疮疡"],
        }

        scores = {}
        for sec_key, keywords in section_keywords.items():
            score = sum(2.0 if kw in text else 0 for kw in keywords)
            if score > 0:
                scores[sec_key] = score

        scored = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top = scored[:3]
        if top:
            names = []
            for sk, sc in top:
                title = self.sections.get(sk, {}).get("title", sk)
                names.append(f"{title}({sc:.0f}分)")
            chain.append(f"【第二步·门类定位】{' → '.join(names)}")
        return scores

    def _match_formulas(self, text: str, section_scores: Dict[str, float],
                        qi_direction: str, chain: List[str]) -> Dict[str, float]:
        formula_scores = {}

        # 气机升降优先锁方
        if qi_direction in ("sinking", "mixed"):
            if "气短不足以息" in text or "气息将停" in text:
                formula_scores["升陷汤"] = formula_scores.get("升陷汤", 0) + 5
            if "心冷" in text or "背紧" in text or "恶寒" in text:
                formula_scores["回阳升陷汤"] = formula_scores.get("回阳升陷汤", 0) + 5
            if "经络湮淤" in text or "气分郁结" in text:
                formula_scores["理郁升陷汤"] = formula_scores.get("理郁升陷汤", 0) + 5
            if "小便不禁" in text:
                formula_scores["醒脾升陷汤"] = formula_scores.get("醒脾升陷汤", 0) + 5

        if qi_direction in ("counterflow", "mixed"):
            if "阴阳两虚" in text or "喘逆迫促" in text:
                formula_scores["参赭镇气汤"] = formula_scores.get("参赭镇气汤", 0) + 5
            if "阴虚不纳气" in text:
                formula_scores["薯蓣纳气汤"] = formula_scores.get("薯蓣纳气汤", 0) + 5
            if "虚劳喘逆" in text or "饮食减少" in text:
                formula_scores["滋培汤"] = formula_scores.get("滋培汤", 0) + 3
            if "呕吐" in text or "胃气上逆" in text:
                formula_scores["镇逆汤"] = formula_scores.get("镇逆汤", 0) + 4
            if "吐血" in text or "衄血" in text or "吐衄" in text:
                if "脉洪" in text or "脉滑" in text:
                    formula_scores["寒降汤"] = formula_scores.get("寒降汤", 0) + 5
                elif "脉虚" in text or "脉濡" in text or "脉迟" in text:
                    formula_scores["温降汤"] = formula_scores.get("温降汤", 0) + 5
                elif "阴分亏损" in text:
                    formula_scores["清降汤"] = formula_scores.get("清降汤", 0) + 4
                elif "气分虚甚" in text:
                    formula_scores["保元寒降汤"] = formula_scores.get("保元寒降汤", 0) + 4
                elif "肝郁" in text or "多怒" in text:
                    formula_scores["秘红丹"] = formula_scores.get("秘红丹", 0) + 4

        # 门内方证匹配
        top_sections = sorted(section_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        kw_pairs = [
            ("咳嗽", "咳嗽"), ("喘促", "喘促"), ("发热", "发热"),
            ("吐血", "吐血"), ("衄血", "衄血"), ("咳血", "咳血"),
            ("吐衄", "吐衄"), ("怔忡", "怔忡"), ("惊悸", "惊悸"), ("不眠", "不眠"),
            ("泄泻", "泄泻"), ("下痢", "下痢"),
            ("小便不利", "小便不利"), ("小便不通", "小便不通"),
            ("水肿", "水肿"), ("淋", "淋"), ("消渴", "消渴"), ("燥渴", "燥渴"),
            ("经闭", "经闭"), ("月事不调", "月事不调"),
            ("血崩", "血崩"), ("带下", "带下"),
            ("中风", "中风"), ("痿废", "痿废"), ("呕吐", "呕吐"),
        ]

        for sec_key, sec_score in top_sections:
            sec_weight = sec_score * 0.2
            sec_data = self.sections.get(sec_key, {})
            for f in sec_data.get("formulas", []):
                raw_name = f["name"]
                name = self._clean_name(raw_name)
                indication = f["indication"]
                match_score = sum(1.0 for kw, kw_ind in kw_pairs
                                  if kw in text and kw_ind in indication)
                if match_score > 0:
                    formula_scores[name] = formula_scores.get(name, 0) + match_score + sec_weight

        ranked = sorted(formula_scores.items(), key=lambda x: x[1], reverse=True)
        if ranked:
            top3 = ranked[:3]
            chain.append(f"【第三步·方证匹配】{'、'.join(f'{n}({s:.1f})' for n, s in top3)}")
        else:
            chain.append("【第三步·方证匹配】未匹配到特定方剂，请细化症状")
        return formula_scores

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("张锡纯辨证引擎 v8 —— 《医学衷中参西录》33门")
        lines.append("=" * 60)
        lines.append("")
        for step in result["chain"]:
            lines.append(step)
        lines.append("")

        ranked = sorted(result["formula_scores"].items(), key=lambda x: x[1], reverse=True)
        if ranked:
            lines.append("【方剂推荐】")
            for i, (fang, score) in enumerate(ranked[:5]):
                marker = "★" if i == 0 else f" {i}."
                lines.append(f"  {marker} {fang}（评分 {score:.1f}）")
        else:
            lines.append("【方剂推荐】暂无匹配，请补充脉象、舌苔等辨证信息。")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngineV8()
    print(f"已加载 {len(engine.sections)} 门、"
          f"{sum(len(s.get('formulas',[])) for s in engine.sections.values())} 首方剂")
    print("（全部出自《医学衷中参西录》医方篇，无外引）")
    print("=" * 60)

    tests = [
        ("测试1·大气下陷", "病人气短不足以息，努力呼吸似喘，脉沉迟微弱"),
        ("测试2·吐衄热证", "吐血、衄血，脉洪滑而长，上入鱼际，因热而胃气不降"),
        ("测试3·吐衄虚寒", "吐衄，脉虚濡而迟，饮食停滞胃口"),
        ("测试4·虚劳喘逆", "虚劳喘逆，饮食减少，兼咳嗽"),
        ("测试5·阴虚咳喘", "虚劳发热，喘嗽，脉数而弱"),
        ("测试6·心悸失眠", "心中怔忡，惊悸不眠，兼心下停有痰饮"),
        ("测试7·内中风", "内中风，脉弦长有力，上盛下虚，头目眩晕"),
        ("测试8·经闭劳嗽", "妇女经闭不行，食少劳嗽，阴虚作热"),
        ("测试9·温病初起", "温病初得，头疼，周身骨节酸疼，肌肤壮热，脉浮滑"),
        ("测试10·消渴", "消渴，口燥渴，饮不解渴"),
    ]
    for title, text in tests:
        r = engine.diagnose(text)
        print(f"\n{title}: {text}")
        print(engine.format_result(r))
