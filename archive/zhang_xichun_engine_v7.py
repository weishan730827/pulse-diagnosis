#!/usr/bin/env python3
"""
张锡纯气机升降辨证匹配引擎 v7
完整辨证体系：三层漏斗
  第一步~第四步：辨气机升降（自创方9首 + 仲景方先判）
  第五步：门类归属（33门症状路由）
  第六步：门内方证匹配（177首自创方 + 36首仲景方）
  
原著依据：《医学衷中参西录》医方篇33门，15749行全文检索
"""

import json, os
from typing import Dict, List, Tuple, Set

_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "张锡纯气机升降辨证勾选表_v4.json")

# 升陷类9首（v2已验证）
XIAXIAN_POOL = {"升陷汤", "回阳升陷汤", "理郁升陷汤", "醒脾升陷汤"}
SHANGNI_POOL = {"参赭镇气汤", "镇逆汤", "寒降汤", "温降汤", "清降汤",
                "保元寒降汤", "保元清降汤", "秘红丹", "薯蓣纳气汤", "滋培汤"}

# 仲景方池v4（36首，从原著核实）
ZHONGJING_POOL = {
    "桂枝汤", "麻黄汤", "小青龙汤", "大青龙汤", "葛根汤",
    "桂枝加附子汤", "桂枝加厚朴杏子汤", "五苓散",
    "白虎汤", "白虎加人参汤", "大承气汤", "小承气汤", "调胃承气汤",
    "栀子豉汤", "茵陈蒿汤", "猪苓汤", "麻子仁丸", "蜜煎导方",
    "小柴胡汤", "大柴胡汤",
    "理中汤",
    "四逆汤", "通脉四逆汤", "白通汤", "真武汤", "附子汤",
    "黄连阿胶汤", "桃花汤", "炙甘草汤",
    "乌梅丸", "白头翁汤", "当归四逆汤",
    "肾气丸", "下瘀血汤", "桂枝茯苓丸", "当归芍药散"
}


class ZhangXiChunEngineV7:
    """v7引擎：33门全覆盖，三层辨证漏斗"""

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._build_section_map()
        self._build_symptom_index()

    def _build_section_map(self):
        """构建门类-方剂映射"""
        self.sections = {}  # section_key -> {"title": ..., "formulas": [...]}
        for key, val in self.data.items():
            if key.startswith("s_") and isinstance(val, dict) and "formulas" in val:
                self.sections[key] = val

    def _build_symptom_index(self):
        """构建症状-方剂反向索引"""
        self.symptom_to_formulas = {}
        for sec_key, sec_data in self.sections.items():
            for f in sec_data.get("formulas", []):
                name = f["name"]
                indication = f["indication"]
                # Extract key symptoms from indication text
                symptoms = self._extract_symptoms(indication)
                for sym in symptoms:
                    if sym not in self.symptom_to_formulas:
                        self.symptom_to_formulas[sym] = []
                    self.symptom_to_formulas[sym].append((name, sec_key))

    def _extract_symptoms(self, text: str) -> Set[str]:
        """从适应症文本提取关键症状词"""
        keywords = [
            "喘", "嗽", "咳嗽", "发热", "脉数", "脉虚", "脉弦", "脉洪", "脉滑", "脉沉", "脉细", "脉微",
            "脉迟", "脉浮", "脉弱", "饮食减少", "羸弱", "羸瘦", "自汗", "盗汗", "咳逆",
            "吐血", "衄血", "咳血", "痰", "心悸", "怔忡", "不眠", "惊悸",
            "呕吐", "泄泻", "下痢", "里急后重", "腹疼", "小便不利", "小便不通",
            "水肿", "淋", "消渴", "燥渴", "大便燥结", "恶寒", "头痛", "身疼",
            "气短", "不足以息", "满闷", "胸胁胀满", "胁疼", "腰疼", "腿疼", "臂疼",
            "经闭", "月事不调", "血崩", "带下", "滑胎", "恶阻", "产难", "乳少",
            "中风", "偏枯", "痿废", "麻木", "抽掣", "痉", "痫风",
            "眼", "目睛", "咽喉", "牙疳", "疮疡", "瘰疬",
            "舌苔白", "舌苔黄", "苔白", "苔黄", "上盛下虚", "上鱼际"
        ]
        found = set()
        for kw in keywords:
            if kw in text:
                found.add(kw)
        return found

    def diagnose(self, symptom_text: str) -> Dict:
        """
        基于症状文本进行辨证。
        输入：患者症状描述文本
        输出：辨证链 + 方剂推荐
        """
        chain = []
        matched_sections = {}  # section_key -> formula_list

        # Step1: 辨气机升降
        qi_direction = self._judge_qi_direction(symptom_text, chain)

        # Step2: 症状→门类匹配
        section_scores = self._match_sections(symptom_text, chain)

        # Step3: 门内方证匹配
        formula_scores = self._match_formulas(symptom_text, section_scores, qi_direction, chain)

        # Step4: 仲景方补充匹配
        zhongjing_scores = self._match_zhongjing(symptom_text, chain)

        return {
            "qi_direction": qi_direction,
            "section_scores": section_scores,
            "formula_scores": formula_scores,
            "zhongjing_scores": zhongjing_scores,
            "chain": chain,
        }

    def _judge_qi_direction(self, text: str, chain: List[str]) -> str:
        """辨气机升降"""
        sinking_signs = ["短气", "不足以息", "努力呼吸", "气息将停", "气短不足以息"]
        counterflow_signs = ["喘逆", "气上冲", "呕逆", "呃逆", "上逆", "冲气上干",
                            "冲脉逆气", "胃气上逆", "胆火上冲", "胃气不降", "气不降"]

        n_sink = sum(1 for s in sinking_signs if s in text)
        n_flow = sum(1 for s in counterflow_signs if s in text)

        if n_sink > 0 and n_flow == 0:
            chain.append("【第一步·辨升降】判定为「大气下陷」（升陷类）")
            return "sinking"
        elif n_flow > 0 and n_sink == 0:
            chain.append("【第一步·辨升降】判定为「气机上逆」（镇降类）")
            return "counterflow"
        elif n_sink > 0 and n_flow > 0:
            chain.append("【第一步·辨升降】判定为「升降失调」（升陷+镇降并见）")
            return "mixed"
        else:
            chain.append("【第一步·辨升降】无明显升降异常 → 直接按门类匹配")
            return "neutral"

    def _match_sections(self, text: str, chain: List[str]) -> Dict[str, float]:
        """症状→门类路由评分"""
        # 门类关键词映射
        section_keywords = {
            "s_01_阴虚劳热": ["虚劳", "羸瘦", "劳瘵", "脉数", "脉弦数", "肌肤甲错", "阴虚作热"],
            "s_02_阳虚": ["阳虚", "阳分衰惫", "畏寒", "四肢不温"],
            "s_03_大气下陷": ["大气下陷", "气短不足以息", "气息将停"],
            "s_04_喘息": ["喘逆", "喘促", "不纳气", "肺肾两虚"],
            "s_05_痰饮": ["痰涎", "饮邪", "生痰", "痰盛", "痰气郁结"],
            "s_06_肺病": ["肺痈", "肺痿", "肺结核", "劳嗽", "肺虚", "肺损", "肺中腐烂"],
            "s_07_吐衄": ["吐血", "衄血", "咳血", "痰中带血", "下血", "瘀血膈上", "吐衄", "便下血"],
            "s_08_心病": ["怔忡", "惊悸", "心中", "怔冲"],
            "s_09_癫狂": ["癫狂", "失心", "神志", "神明", "思虑过度"],
            "s_10_痫风": ["痫风", "抽搐"],
            "s_11_小儿风证": ["小儿", "初生", "急惊风", "绵风"],
            "s_12_中风": ["中风", "偏枯", "脑充血", "不遂", "历节风", "破伤后", "上盛下虚", "脉弦长有力",
                          "头重目眩", "神昏健忘", "昏仆", "血压过高"],
            "s_13_痿废": ["痿废", "痹木", "偏枯"],
            "s_14_膈食": ["膈食", "噎膈", "反胃"],
            "s_15_呕吐": ["呕吐", "呕", "闻药气"],
            "s_16_霍乱": ["霍乱", "吐泻转筋", "痧证"],
            "s_17_泄泻": ["泄泻", "完谷不化", "肠滑", "大便滑泻", "滑泻"],
            "s_18_痢": ["痢", "下痢", "里急后重", "噤口痢", "热痢", "脓血"],
            "s_19_燥结": ["燥结", "大便燥结", "宿食结"],
            "s_20_消渴": ["消渴"],
            "s_21_癃闭": ["小便不利", "小便不通", "水肿", "臌胀", "小便滴沥"],
            "s_22_淋浊": ["淋", "血淋", "膏淋", "气淋", "石淋", "砂淋", "白浊", "遗精", "溺血"],
            "s_23_伤寒": ["伤寒", "无汗", "有汗", "表证未罢"],
            "s_24_温病": ["温病", "表里俱热", "肌肤壮热", "感冒", "湿温", "憎寒壮热", "头疼", "周身", "脉浮",
                          "骨节酸疼", "恶寒无汗", "表里俱觉发热"],
            "s_25_伤寒温病同用": ["阳明", "石膏", "承气", "结胸", "白虎"],
            "s_26_瘟疫": ["瘟疫", "发斑疹", "头面肿疼", "阳毒"],
            "s_27_疟疾": ["疟", "久疟"],
            "s_28_肢体疼痛": ["肝郁脾弱", "胁下掀疼", "腿疼", "臂疼", "腰疼", "气血凝滞", "肝气不舒"],
            "s_29_女科": ["经闭", "月事不调", "血崩", "带下", "滑胎", "恶阻", "产难", "乳少",
                         "产后", "倒经", "血海虚寒", "阴挺", "室女", "恶露不尽", "妇人"],
            "s_30_眼科": ["眼", "目睛", "目翳", "云翳", "赤脉络目", "羞明", "瞳散"],
            "s_31_咽喉": ["咽喉", "喉"],
            "s_32_牙疳": ["牙疳"],
            "s_33_疮科": ["疮疡", "瘰疬", "杨梅疮", "瘰", "化脓生肌", "红肿疮疡"]
        }

        scores = {}
        for sec_key, keywords in section_keywords.items():
            score = sum(2.0 if kw in text else 0 for kw in keywords)
            if score > 0:
                scores[sec_key] = score

        # Sort by score descending
        scored = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_sections = scored[:3]

        if top_sections:
            sec_names = []
            for sk, sc in top_sections:
                title = self.sections.get(sk, {}).get("title", sk)
                sec_names.append(f"{title}({sc:.0f}分)")
            chain.append(f"【第二步·门类定位】{' → '.join(sec_names)}")

        return scores

    def _match_formulas(self, text: str, section_scores: Dict[str, float],
                        qi_direction: str, chain: List[str]) -> Dict[str, float]:
        """门内方证匹配"""
        formula_scores = {}

        # 先看气机升降 → 直接锁定升降方池
        if qi_direction in ("sinking", "mixed"):
            pool = XIAXIAN_POOL
            if "气短不足以息" in text or "气息将停" in text:
                formula_scores["升陷汤"] = formula_scores.get("升陷汤", 0) + 5
            if "心冷" in text or "背紧" in text or "恶寒" in text:
                formula_scores["回阳升陷汤"] = formula_scores.get("回阳升陷汤", 0) + 5
            if "经络湮淤" in text or "气分郁结" in text:
                formula_scores["理郁升陷汤"] = formula_scores.get("理郁升陷汤", 0) + 5
            if "小便不禁" in text:
                formula_scores["醒脾升陷汤"] = formula_scores.get("醒脾升陷汤", 0) + 5

        if qi_direction in ("counterflow", "mixed"):
            pool = SHANGNI_POOL
            if "阴阳两虚" in text or "喘逆迫促" in text:
                formula_scores["参赭镇气汤"] = formula_scores.get("参赭镇气汤", 0) + 5
            if "阴虚不纳气" in text:
                formula_scores["薯蓣纳气汤"] = formula_scores.get("薯蓣纳气汤", 0) + 5
            if "虚劳喘逆" in text or "饮食减少" in text:
                formula_scores["滋培汤"] = formula_scores.get("滋培汤", 0) + 3
            if "呕吐" in text or "胃气上逆" in text:
                formula_scores["镇逆汤"] = formula_scores.get("镇逆汤", 0) + 4
            if "吐血" in text or "衄血" in text:
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

        # Then match within top sections
        top_sections = sorted(section_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        for sec_key, sec_score in top_sections:
            sec_weight = sec_score * 0.2
            sec_data = self.sections.get(sec_key, {})
            for f in sec_data.get("formulas", []):
                raw_name = f["name"]
                # Clean number prefix like "1．寒降汤" → "寒降汤"
                name = raw_name.split("．", 1)[-1] if "．" in raw_name else raw_name
                indication = f["indication"]
                # Simple keyword matching
                match_score = 0
                kw_pairs = [
                    ("咳嗽", "咳嗽"), ("喘促", "喘促"), ("发热", "发热"),
                    ("吐血", "吐血"), ("衄血", "衄血"), ("咳血", "咳血"),
                    ("吐衄", "吐衄"), ("心悸", "怔忡"), ("不眠", "不眠"),
                    ("怔忡", "怔忡"), ("惊悸", "惊悸"),
                    ("泄泻", "泄泻"), ("下痢", "下痢"),
                    ("小便不利", "小便不利"), ("小便不通", "小便不通"),
                    ("水肿", "水肿"), ("淋", "淋"),
                    ("消渴", "消渴"), ("燥渴", "燥渴"),
                    ("经闭", "经闭"), ("月事不调", "月事不调"),
                    ("血崩", "血崩"), ("带下", "带下"),
                    ("中风", "中风"), ("痿废", "痿废"),
                    ("呕吐", "呕吐"),
                ]
                for kw, kw_ind in kw_pairs:
                    if kw in text and kw_ind in indication:
                        match_score += 1
                if match_score > 0:
                    old = formula_scores.get(name, 0)
                    formula_scores[name] = old + match_score + sec_weight

        # Sort
        ranked = sorted(formula_scores.items(), key=lambda x: x[1], reverse=True)
        if ranked:
            top3 = ranked[:3]
            clean_names = [n.split("．", 1)[-1] if "．" in n else n for n, _ in top3]
            chain.append(f"【第三步·方证匹配】{'、'.join(f'{n}({s:.1f})' for n, s in zip(clean_names, [s for _, s in top3]))}")
        else:
            chain.append("【第三步·方证匹配】未匹配到特定方剂，请细化症状")

        return formula_scores

    def _match_zhongjing(self, text: str, chain: List[str]) -> Dict[str, float]:
        """仲景方补充匹配（六经视角）"""
        zhongjing_keywords = {
            "桂枝汤": ["发热", "恶风", "汗出", "脉浮"],
            "麻黄汤": ["无汗", "恶寒", "脉浮紧", "身疼", "腰痛", "骨节疼痛", "喘"],
            "小青龙汤": ["咳喘", "痰稀", "干呕", "外寒内饮"],
            "大青龙汤": ["不汗出", "烦躁", "脉浮紧"],
            "葛根汤": ["项背强", "无汗", "恶风"],
            "五苓散": ["小便不利", "微热消渴", "水入即吐"],
            "白虎汤": ["大热", "大汗", "大渴", "脉洪大"],
            "白虎加人参汤": ["大渴", "口燥渴", "心烦", "背微恶寒", "时时恶风"],
            "大承气汤": ["大便硬", "腹满", "谵语", "潮热"],
            "栀子豉汤": ["心中懊憹", "烦热", "胸中窒"],
            "茵陈蒿汤": ["发黄", "小便不利", "腹满"],
            "小柴胡汤": ["寒热往来", "胸胁苦满", "口苦", "咽干", "目眩", "默默不欲饮食", "心烦喜呕"],
            "大柴胡汤": ["呕不止", "心下急", "郁郁微烦", "热结在里"],
            "理中汤": ["下利", "腹痛", "不渴", "太阴虚寒"],
            "四逆汤": ["四肢厥冷", "下利清谷", "脉微欲绝", "恶寒倦卧"],
            "真武汤": ["小便不利", "四肢沉重", "腹痛", "下利", "阳虚水泛"],
            "附子汤": ["身痛", "骨节痛", "脉沉", "口中和", "背恶寒"],
            "黄连阿胶汤": ["心烦", "不寐", "心中烦", "不得卧"],
            "桃花汤": ["下利", "便脓血", "日久不愈"],
            "炙甘草汤": ["脉结代", "心动悸"],
            "乌梅丸": ["蛔厥", "久利", "寒热错杂", "呕吐蛔虫", "消渴", "心中疼热"],
            "白头翁汤": ["热利下重", "下利", "欲饮水"],
            "当归四逆汤": ["手足厥寒", "脉细欲绝", "血虚寒厥"],
            "肾气丸": ["腰痛", "少腹拘急", "小便不利", "消渴", "虚劳"],
            "下瘀血汤": ["瘀血", "腹痛", "经水不利"],
            "桂枝茯苓丸": ["癥病", "妇人"],
            "当归芍药散": ["腹痛", "妇人", "腹中诸疾痛"]
        }

        scores = {}
        for fang, keywords in zhongjing_keywords.items():
            match_count = sum(1 for kw in keywords if kw in text)
            if match_count >= 1:
                scores[fang] = match_count * 3

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if ranked:
            top3 = ranked[:3]
            chain.append(f"【第四步·仲景方补充】{'、'.join(f'{n}({s})' for n, s in top3)}")

        return scores

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("张锡纯辨证引擎 v7 —— 33门全覆盖")
        lines.append("=" * 60)
        lines.append("")

        for step in result["chain"]:
            lines.append(step)
        lines.append("")

        lines.append("【推荐结果】")
        lines.append(f"  气机方向：{result['qi_direction']}")

        # Merge self-created and zhongjing
        all_scores = {}
        for k, v in result.get("formula_scores", {}).items():
            all_scores[k] = (v, "自创")
        for k, v in result.get("zhongjing_scores", {}).items():
            old = all_scores.get(k, (0, "仲景"))
            all_scores[k] = (old[0] + v, "仲景" if old[1] == "仲景" else "自创")

        ranked = sorted(all_scores.items(), key=lambda x: x[1][0], reverse=True)
        if ranked:
            lines.append(f"\n  【方剂排名（自创+仲景）】")
            for i, (fang, (score, ftype)) in enumerate(ranked[:5]):
                marker = "★ 首选" if i == 0 else f"  {i}."
                tag = "【自创】" if ftype == "自创" else "【仲景】"
                clean_name = fang.split("．", 1)[-1] if "．" in fang else fang
                lines.append(f"  {marker} {clean_name} (评分:{score:.1f}) {tag}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = ZhangXiChunEngineV7()

    print("=" * 60)
    print("张锡纯辨证引擎 v7 测试")
    print(f"已加载 {len(engine.sections)} 门、{sum(len(s.get('formulas',[])) for s in engine.sections.values())} 首自创方")
    print(f"仲景方池：{len(ZHONGJING_POOL)} 首")
    print("=" * 60)

    tests = [
        ("测试1·纯大气下陷", "病人气短不足以息，努力呼吸似喘，脉沉迟微弱"),
        ("测试2·吐血（胃气上逆热证）", "吐血、衄血，脉洪滑而长，上入鱼际，因热而胃气不降"),
        ("测试3·吐衄虚寒", "吐衄，脉虚濡而迟，饮食停滞胃口"),
        ("测试4·虚劳喘逆", "虚劳喘逆，饮食减少，兼咳嗽"),
        ("测试5·阴虚咳喘", "虚劳发热，喘嗽，脉数而弱"),
        ("测试6·心悸失眠", "心中怔忡，惊悸不眠，兼心下停有痰饮"),
        ("测试7·中风", "内中风，脉弦长有力，上盛下虚，头目眩晕"),
        ("测试8·妇科经闭", "妇女经闭不行，食少劳嗽，阴虚作热"),
        ("测试9·伤寒温病", "温病初得，头疼，周身骨节酸疼，肌肤壮热，脉浮滑"),
        ("测试10·消渴", "消渴，糖尿病，口燥渴"),
    ]

    for title, text in tests:
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"症状：{text}")
        r = engine.diagnose(text)
        print(engine.format_result(r))
