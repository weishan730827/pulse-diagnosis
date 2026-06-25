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

# 各家自创方附录（仅勾选表/引擎中实际使用方，来源原著）
SELF_CREATED = {
    # ===== 郑钦安自创方（火神派核心方）=====
    "潜阳丹": {"indications": "虚阳浮越·火不归元·上热下寒", "author": "郑钦安《医理真传》"},
    "封髓丹": {"indications": "阴火上冲·咽痛·纳气归肾", "author": "郑钦安《医理真传》"},
    "桂附理中汤": {"indications": "中焦虚寒·理中加桂附", "author": "郑钦安（理中汤加味）"},
    "附子理中汤": {"indications": "中焦虚寒·呕吐", "author": "郑钦安（理中汤加附子）"},
    "导赤散": {"indications": "心火下移小肠·小便短赤", "author": "钱乙·郑钦安引用"},

    # ===== 张锡纯自创方（勾选表中实际使用的9方）=====
    "升陷汤": {"indications": "大气下陷·气短不足以息·努力呼吸似喘", "author": "张锡纯《医学衷中参西录》治大气下陷方"},
    "回阳升陷汤": {"indications": "大气下陷兼心肺阳虚·畏寒", "author": "张锡纯《医学衷中参西录》"},
    "理郁升陷汤": {"indications": "大气下陷兼气分郁结·胸痛", "author": "张锡纯《医学衷中参西录》"},
    "醒脾升陷汤": {"indications": "大气下陷兼脾气虚极下陷·小便不禁", "author": "张锡纯《医学衷中参西录》"},
    "参赭镇气汤": {"indications": "阴阳两虚·喘促咳逆·气逆上冲", "author": "张锡纯《医学衷中参西录》治喘息方"},
    "镇逆汤": {"indications": "胃气上逆·呕哕·心烦", "author": "张锡纯《医学衷中参西录》治呕吐方"},
    "寒降汤": {"indications": "吐血衄血·脉洪滑而长·因热胃气不降", "author": "张锡纯《医学衷中参西录》治吐衄方"},
    "温降汤": {"indications": "吐血衄血·脉虚濡而迟·因寒胃气不降", "author": "张锡纯《医学衷中参西录》治吐衄方"},
    "加味麦门冬汤": {"indications": "经行吐衄·倒经", "author": "张锡纯《医学衷中参西录》治女科方"},
}
