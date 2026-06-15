"""
共享方剂工具——八家引擎统一导入，对接仲景基座。
"""
import re
from typing import Optional, List, Dict
from zhongjing_formula_base import ZhongJingFormulaBase

_base = ZhongJingFormulaBase()

def clean_name(raw: str) -> str:
    """剥离括号及之后内容，返回纯方名。不截取'/'分隔的方案。"""
    return re.split(r"[（(]", raw)[0].strip()

def is_zhongjing(raw: str) -> bool:
    """通过别名映射检查是否为仲景方"""
    return _base.get(clean_name(raw)) is not None

def get_zhongjing(raw: str) -> Optional[dict]:
    return _base.get(clean_name(raw))

def search_zhongjing(keyword: str) -> List[dict]:
    return _base.search(keyword)

def annotate(raw: str) -> str:
    """若方名在基座中，附加条文号；否则标注【非仲景方】"""
    name = clean_name(raw)
    f = _base.get(name)
    if f:
        return f"{raw}（伤寒/{f['tiaowen']}条）"
    return f"{raw}【非仲景方】"

# 各家自创方附录（不在153基座中但需保留）
SELF_CREATED = {
    # 郑钦安
    "潜阳丹": {"indications": "虚阳浮越·火不归元·上热下寒", "author": "郑钦安"},
    "封髓丹": {"indications": "阴火上冲·咽痛·纳气归肾", "author": "郑钦安"},
    "桂附理中汤": {"indications": "中焦虚寒·理中加桂附", "author": "郑钦安（理中汤加味）"},
    "附子理中汤": {"indications": "中焦虚寒·呕吐", "author": "郑钦安（理中汤加附子）"},
    "导赤散": {"indications": "心火下移小肠·小便短赤", "author": "钱乙·郑钦安引用"},
    # ========== 张锡纯自创方（按《医学衷中参西录》类目） ==========
    # ——治阴虚劳热方——
    "资生汤": {"indications": "劳瘵羸弱已甚饮食减少喘促咳嗽身热", "author": "张锡纯"},
    "十全育真汤": {"indications": "虚劳脉数肌肤甲错形体羸瘦饮食不壮筋力", "author": "张锡纯"},
    "醴泉饮": {"indications": "虚劳发热或喘或嗽脉数而弱", "author": "张锡纯"},
    "一味薯蓣饮": {"indications": "劳瘵发热或喘或嗽自汗怔忡大便滑泻", "author": "张锡纯"},
    "来复汤": {"indications": "寒温外感诸证大病瘥后不能自复虚汗淋漓或心慌怔忡", "author": "张锡纯"},
    "珠玉二宝粥": {"indications": "脾肺阴分亏损饮食懒进虚热劳嗽", "author": "张锡纯"},
    "水晶桃": {"indications": "肺肾两虚咳嗽喘逆服之既济", "author": "张锡纯"},
    "既济汤": {"indications": "大病后阴阳不相维系阳欲上脱阴欲下脱", "author": "张锡纯"},
    "镇摄汤": {"indications": "胸膈满闷脉大而弦按之似有力非真有力", "author": "张锡纯"},
    # ——治喘息方——
    "参赭镇气汤": {"indications": "阴阳两虚喘促咳逆", "author": "张锡纯"},
    "薯蓣纳气汤": {"indications": "阴虚不纳气作喘", "author": "张锡纯"},
    "滋培汤": {"indications": "虚劳喘逆饮食减少或咳嗽", "author": "张锡纯"},
    # ——治心病方——
    "定心汤": {"indications": "心虚怔忡", "author": "张锡纯"},
    "安魂汤": {"indications": "心中气血虚损兼心下停有痰饮惊悸不眠", "author": "张锡纯"},
    # ——治肺病方——
    "清金益气汤": {"indications": "肺虚少气劳热咳嗽肺痿", "author": "张锡纯"},
    "清金解毒汤": {"indications": "肺脏损烂或将成肺痈咳嗽吐脓血", "author": "张锡纯"},
    "清凉华盖饮": {"indications": "肺中腐烂浸成肺痈咳嗽胸中隐疼", "author": "张锡纯"},
    # ——治呕吐方——
    "镇逆汤": {"indications": "胃气上逆呕哕", "author": "张锡纯"},
    # ——治膈食方——
    "参赭培气汤": {"indications": "膈食（贲门癌）饮食难下", "author": "张锡纯"},
    # ——治吐衄方——
    "寒降汤": {"indications": "吐血衄血脉洪滑而长因热而胃气不降", "author": "张锡纯"},
    "温降汤": {"indications": "吐血衄血脉虚濡而迟因寒胃气不降", "author": "张锡纯"},
    "清降汤": {"indications": "因吐衄不止致阴分亏损脉象细数", "author": "张锡纯"},
    "保元寒降汤": {"indications": "吐血衄血证血脱气亦脱言语若不接续", "author": "张锡纯"},
    "秘红丹": {"indications": "肝郁多怒胃郁气逆致吐血衄血", "author": "张锡纯"},
    "二鲜饮": {"indications": "虚劳证痰中带血", "author": "张锡纯"},
    "三鲜饮": {"indications": "虚劳证痰中带血兼有虚热", "author": "张锡纯"},
    "化血丹": {"indications": "咳血/吐血/衄血二便下血", "author": "张锡纯"},
    "补络补管汤": {"indications": "咳血吐血久不愈", "author": "张锡纯"},
    # ——治消渴方——
    "玉液汤": {"indications": "消渴（糖尿病）气不布津肾虚胃燥", "author": "张锡纯"},
    "滋膵饮": {"indications": "消渴（糖尿病）渴而多饮多尿", "author": "张锡纯"},
    # ——治癃闭方——
    "宣阳汤": {"indications": "阳分虚损气弱不能宣通小便不利", "author": "张锡纯"},
    "济阴汤": {"indications": "阴分虚损血亏不能濡润小便不利", "author": "张锡纯"},
    "温通汤": {"indications": "下焦受寒小便不通", "author": "张锡纯"},
    "寒通汤": {"indications": "下焦蕴蓄实热小便不通", "author": "张锡纯"},
    # ——治淋浊方——
    "理血汤": {"indications": "血淋/溺血", "author": "张锡纯"},
    "膏淋汤": {"indications": "膏淋（乳糜尿）", "author": "张锡纯"},
    "气淋汤": {"indications": "气淋少腹下坠作疼小便涩痛", "author": "张锡纯"},
    "劳淋汤": {"indications": "劳淋遇劳即发小便淋涩", "author": "张锡纯"},
    "砂淋丸": {"indications": "砂淋（泌尿系结石）", "author": "张锡纯"},
    "清肾汤": {"indications": "肾经实热淋浊", "author": "张锡纯"},
    "澄化汤": {"indications": "小便浑浊", "author": "张锡纯"},
    # ——治痢方——
    "化滞汤": {"indications": "下痢赤白腹疼里急后重初起", "author": "张锡纯"},
    "燮理汤": {"indications": "下痢赤白腹疼", "author": "张锡纯"},
    "解毒生化丹": {"indications": "痢久郁热生毒肠中腐烂", "author": "张锡纯"},
    "天水涤肠汤": {"indications": "久痢肠中腐烂", "author": "张锡纯"},
    "通变白头翁汤": {"indications": "热痢下重腹疼及肠胃有实热", "author": "张锡纯"},
    "三宝粥": {"indications": "痢久脓血腥臭兼下焦虚惫", "author": "张锡纯"},
    # ——治泄泻方——
    "益脾饼": {"indications": "脾胃湿寒饮食减少长作泄泻完谷不化", "author": "张锡纯"},
    "扶中汤": {"indications": "泄泻久不止气血俱虚身体羸弱", "author": "张锡纯"},
    # ——治痰饮方——
    "理饮汤": {"indications": "心肺阳虚脾湿不升胃郁不降饮邪为患", "author": "张锡纯"},
    "理痰汤": {"indications": "痰涎郁塞胸膈满闷", "author": "张锡纯"},
    "龙蚝理痰汤": {"indications": "思虑生痰因痰生热神志不宁", "author": "张锡纯"},
    "健脾化痰丸": {"indications": "脾胃虚弱不能运化饮食生痰", "author": "张锡纯"},
    # ——治癫狂方——
    "调气养神汤": {"indications": "思虑过度伤其神明或癫或狂", "author": "张锡纯"},
    # ——治大气下陷方（升陷系列）——
    "升陷汤": {"indications": "大气下陷气短不足以息努力呼吸似喘", "author": "张锡纯《医学衷中参西录》"},
    "回阳升陷汤": {"indications": "大气下陷兼心肺阳虚", "author": "张锡纯"},
    "理郁升陷汤": {"indications": "大气下陷兼气分郁结经络湮淤", "author": "张锡纯"},
    "醒脾升陷汤": {"indications": "大气下陷兼脾气虚极下陷小便不禁", "author": "张锡纯"},
    # ——治气血郁滞肢体疼痛方——
    "升降汤": {"indications": "肝郁脾弱胸胁胀满不能饮食", "author": "张锡纯"},
    "培脾舒肝汤": {"indications": "肝气不舒木郁克土脾胃不能升降", "author": "张锡纯"},
    "活络效灵丹": {"indications": "气血凝滞痃癖癥瘕心腹疼痛腿疼臂疼", "author": "张锡纯"},
    "活络祛寒汤": {"indications": "经络受寒四肢发搐", "author": "张锡纯"},
    "健运汤": {"indications": "腿疼臂疼气虚", "author": "张锡纯"},
    "振中汤": {"indications": "腿疼腰疼饮食减少", "author": "张锡纯"},
    "曲直汤": {"indications": "肝虚腿疼左部脉微弱", "author": "张锡纯"},
    # ——治伤寒方——
    "麻黄加知母汤": {"indications": "伤寒无汗而喘脉紧加知母防热", "author": "张锡纯"},
    "从龙汤": {"indications": "外感痰喘服小青龙汤后未痊愈", "author": "张锡纯"},
    "通变大柴胡汤": {"indications": "伤寒温病表证未罢大便已实", "author": "张锡纯"},
    # ——治温病方——
    "清解汤": {"indications": "温病初得头痛周身骨节酸疼肌肤壮热", "author": "张锡纯"},
    "凉解汤": {"indications": "温病表里俱觉发热舌苔白黄", "author": "张锡纯"},
    "寒解汤": {"indications": "温病周身壮热心中热渴脉洪滑", "author": "张锡纯"},
    "和解汤": {"indications": "温病表里俱热时有汗出舌苔白", "author": "张锡纯"},
    "宣解汤": {"indications": "感冒久在太阳致热蓄膀胱小便赤涩", "author": "张锡纯"},
    "滋阴宣解汤": {"indications": "温病太阳未解渐入阳明阴虚不能作汗", "author": "张锡纯"},
    "滋阴清燥汤": {"indications": "温病表里俱热泄泻", "author": "张锡纯"},
    "滋阴固下汤": {"indications": "温病外感之火已消渴与泻仍不止", "author": "张锡纯"},
    # ——治伤寒温病同用方——
    "仙露汤": {"indications": "寒温阳明证表里俱热心中热嗜凉水脉象洪滑", "author": "张锡纯"},
    "石膏粳米汤": {"indications": "温病初得脉浮有力身体壮热", "author": "张锡纯"},
    "镇逆白虎汤": {"indications": "伤寒温病邪传胃腑燥渴身热白虎证俱而胃气上逆", "author": "张锡纯"},
    "白虎加人参以山药代粳米汤": {"indications": "寒温实热已入阳明白虎汤证而渴甚", "author": "张锡纯"},
    "宁嗽定喘饮": {"indications": "伤寒温病阳明大热已退咳嗽喘促", "author": "张锡纯"},
    # ——治瘟疫瘟疹方——
    "青盂汤": {"indications": "瘟疫表里俱热头面肿疼", "author": "张锡纯"},
    "清疹汤": {"indications": "小儿出疹表里俱热或烦躁引饮", "author": "张锡纯"},
    # ——治内外中风方——
    "镇肝熄风汤": {"indications": "内中风（脑充血）脉弦长有力头目眩晕脑中作疼发热", "author": "张锡纯"},
    "搜风汤": {"indications": "中风猝然昏倒", "author": "张锡纯"},
    "逐风汤": {"indications": "中风抽掣及破伤风角弓反张", "author": "张锡纯"},
    "加味补血汤": {"indications": "身形软弱肢体渐觉不遂头重目眩", "author": "张锡纯"},
    "加味黄耆五物汤": {"indications": "历节风证周身关节皆疼", "author": "张锡纯"},
    # ——治肢体痿废方——
    "振颓汤": {"indications": "痿废腿不能行手不能握", "author": "张锡纯"},
    "补偏汤": {"indications": "偏枯半身不遂", "author": "张锡纯"},
    # ——治女科方——
    "玉烛汤": {"indications": "妇女寒热往来或先寒后热汗出热解", "author": "张锡纯"},
    "理冲汤": {"indications": "妇女经闭不行或产后恶露不尽结为癥瘕", "author": "张锡纯"},
    "安冲汤": {"indications": "妇女经水行时多而且久过期不止", "author": "张锡纯"},
    "固冲汤": {"indications": "妇女血崩（功能性子宫出血）", "author": "张锡纯"},
    "温冲汤": {"indications": "妇人血海虚寒不孕", "author": "张锡纯"},
    "清带汤": {"indications": "妇女赤白带下", "author": "张锡纯"},
    "寿胎丸": {"indications": "滑胎（习惯性流产）", "author": "张锡纯"},
    "安胃饮": {"indications": "恶阻（妊娠呕吐）", "author": "张锡纯"},
    "升肝舒郁汤": {"indications": "妇女阴挺（子宫脱垂）肝气郁结", "author": "张锡纯"},
    "资生通脉汤": {"indications": "室女月闭血枯饮食减少灼热咳嗽", "author": "张锡纯"},
    # ——治疮科方——
    "消瘰丸": {"indications": "瘰疬（淋巴结结核）", "author": "张锡纯"},
    "内托生肌散": {"indications": "瘰疬疮疡破后气血亏损不能化脓生肌", "author": "张锡纯"},
    "化腐生肌散": {"indications": "疮疡已溃腐肉不脱新肉不生", "author": "张锡纯"},
    # ——杂方——
    "荡胸汤": {"indications": "寒温结胸证大便不实胸膈满闷", "author": "张锡纯"},
    "急救回阳汤": {"indications": "霍乱吐泻已极精神昏愦气息奄奄", "author": "张锡纯"},
}
