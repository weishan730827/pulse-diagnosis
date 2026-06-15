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
    # 张锡纯
    "升陷汤": {"indications": "大气下陷·气短不足以息", "author": "张锡纯《医学衷中参西录》"},
    "回阳升陷汤": {"indications": "大气下陷·阳虚", "author": "张锡纯"},
    "理郁升陷汤": {"indications": "大气下陷·气郁", "author": "张锡纯"},
    "参赭镇气汤": {"indications": "气机上逆·喘促", "author": "张锡纯"},
    "镇逆汤": {"indications": "气机上逆·呕逆", "author": "张锡纯"},
    "寒降汤": {"indications": "寒逆呕吐", "author": "张锡纯"},
    "温降汤": {"indications": "温中降逆", "author": "张锡纯"},
}
