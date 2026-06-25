#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辨证施治辅助系统 v2.2（八家并列·仲景为根）
整合：张仲景（本经·六经定纲）+ 姚梅龄脉学 + 胡希恕六经八纲 + 张锡纯方证升降 + 刘渡舟十论辨证 + 曹颖甫方证对应 + 郑钦安阴阳辨证 + 知医邦量化（脉诊/舌诊）
八家并列输出 → 方证匹配 → 跨体系冲突审查 → 综合处方建议
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 加载全部数据库
# ============================================================
with open(os.path.join(BASE_DIR, "pulse_db.json"), "r", encoding="utf-8") as f:
    PULSE_DB = json.load(f)

with open(os.path.join(BASE_DIR, "fangzheng_db_v2.json"), "r", encoding="utf-8") as f:
    FANGZHENG_DB = json.load(f)

with open(os.path.join(BASE_DIR, "zhiyibang_quant.json"), "r", encoding="utf-8") as f:
    ZHIYIBANG_PULSE = json.load(f)

with open(os.path.join(BASE_DIR, "zhiyibang_tongue.json"), "r", encoding="utf-8") as f:
    ZHIYIBANG_TONGUE = json.load(f)

with open(os.path.join(BASE_DIR, "zhang_xichun_rules.json"), "r", encoding="utf-8") as f:
    ZHANGXICHUN_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "hu_xishu_rules.json"), "r", encoding="utf-8") as f:
    HUXISHU_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "yao_meiling_rules.json"), "r", encoding="utf-8") as f:
    YAOMEILING_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "zheng_qinan_rules.json"), "r", encoding="utf-8") as f:
    ZHENGQINAN_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "liu_duzhou_rules.json"), "r", encoding="utf-8") as f:
    LIUDUZHOU_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "cao_yingfu_rules.json"), "r", encoding="utf-8") as f:
    CAOYINGFU_RULES = json.load(f)

with open(os.path.join(BASE_DIR, "zhang_zhongjing_rules.json"), "r", encoding="utf-8") as f:
    ZHANGZHONGJING_RULES = json.load(f)

# ============================================================
# 1. 知医邦 28 脉 ∈ 公式计算引擎
# ============================================================
PULSE_FORMULAS = ZHIYIBANG_PULSE["28脉组合公式（分部适配版）"]

def parse_formula_weight(pulse_name):
    """解析脉象公式中各项的权重"""
    formula = PULSE_FORMULAS.get(pulse_name)
    if not formula:
        return [], []
    raw = formula.get("公式", [])
    core = []  # {} 倍加 f=2
    secondary = []  # () 倍减 f=1/2
    normal = []  # 普通 f=1
    for item in raw:
        s = item.strip()
        if s.startswith("{") and s.endswith("}"):
            core.append(s[1:-1])
        elif s.startswith("(") and s.endswith(")"):
            secondary.append(s[1:-1])
        else:
            normal.append(s)
    return core, secondary, normal


def calc_pulse_confidence(selected_options, pulse_name):
    """计算某脉象的置信度∈值（知医邦公式 v1.2）
    
    公式：∈ = (等效阳性 × e - 阴性个数) / (阳性个数 + 阴性个数 + 1.5)
    - 阳性个数 = 公式项中实际命中的维度数（未加权）
    - 倍加数 = 命中项中属于{}核心的个数（选中1个等效+2）
    - 倍减数 = 命中项中属于()次要的个数（选中1个等效+0.5）
    - 等效阳性 = 阳性个数 + 倍加数 - 0.5×倍减数
    - 阴性个数 = 公式总项数 - 阳性个数（漏项数，公式写了但没采集到）
    - e = 2.718281828（自然常数）
    - 阈值：∈ ≥ 1 脉象成立
    """
    import math
    E = math.e
    formula = PULSE_FORMULAS.get(pulse_name)
    if not formula:
        return 0.0
    core, secondary, normal = parse_formula_weight(pulse_name)
    selected_set = set(selected_options)
    
    # 统计各项选中情况
    selected_core = [c for c in core if c in selected_set]
    selected_sec = [s for s in secondary if s in selected_set]
    selected_norm = [n for n in normal if n in selected_set]
    
    # 阳性个数（原始计数，未加权）
    N_pos = len(selected_core) + len(selected_sec) + len(selected_norm)
    
    # 倍加数、倍减数
    n_double = len(selected_core)
    n_half = len(selected_sec)
    
    # 等效阳性 = 原始阳性 + 倍加(每项+1额外) - 倍减折扣(每项-0.5)
    eff_pos = N_pos + n_double - 0.5 * n_half
    
    # 阴性个数 = 公式总项数 - 阳性个数（漏项）
    total_items = len(core) + len(secondary) + len(normal)
    N_neg = total_items - N_pos
    
    # ∈ = (等效阳性 × e - 阴性) / (阳性 + 阴性 + 1.5)
    eps = (eff_pos * E - N_neg) / (N_pos + N_neg + 1.5)
    return round(eps, 2)


def zhiyibang_diagnose_28mai(selected_options):
    """输入选中的维度选项列表，输出28脉∈值排序（仅∈≥1的成立脉象）"""
    results = {}
    for pname in PULSE_FORMULAS:
        if pname.startswith("_"):
            continue
        eps = calc_pulse_confidence(selected_options, pname)
        if eps >= 1.0:
            results[pname] = eps
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


def list_zhiyibang_options():
    """列出知医邦10维度的所有选项"""
    opts = []
    # 整体维度
    overall = ZHIYIBANG_PULSE.get("整体维度（六部统一采集）", {})
    for dim_name, dim_data in overall.items():
        for key, val in dim_data.get("options", {}).items():
            opts.append((key, val["label"], "整体", dim_name))
    # 分部维度
    part = ZHIYIBANG_PULSE.get("分部维度（左右×寸关尺，仅采集异常部位）", {})
    for dim_name, dim_data in part.get("维度定义", {}).items():
        for key, val in dim_data.get("options", {}).items():
            if val.get("type") == "阳性":
                opts.append((key, val["label"], "分部", dim_name))
    return opts


# ============================================================
# 2. 舌诊辨证引擎
# ============================================================
TONGUE_ALGO = ZHIYIBANG_TONGUE.get("辨证算法", {}).get("基础证型推导", {})
TONGUE_ZONES = ZHIYIBANG_TONGUE.get("舌面分区", {}).get("可用部位", [])


def tongue_diagnose(selected_options):
    """
    输入舌诊选中的选项列表（格式：["AB", "BA", "BE", ...]），
    返回证型推导结果
    """
    results = []
    for zheng_name, formula in TONGUE_ALGO.items():
        if "∩" in formula:
            parts = [p.strip() for p in formula.split("∩")]
            if all(p in selected_options for p in parts):
                results.append(zheng_name)
        elif "∪" in formula:
            parts = [p.strip() for p in formula.split("∪")]
            if any(p in selected_options for p in parts):
                results.append(zheng_name)
        else:
            if formula.strip() in selected_options:
                results.append(zheng_name)
    return results


def get_option_meaning(code):
    """查找脉诊/舌诊选项编码的含义（脉诊优先）"""
    # 先查脉诊10维度
    overall = ZHIYIBANG_PULSE.get("整体维度（六部统一采集）", {})
    for dim_name, dim_data in overall.items():
        for key, val in dim_data.get("options", {}).items():
            if key == code:
                return val["label"]
    part = ZHIYIBANG_PULSE.get("分部维度（左右×寸关尺，仅采集异常部位）", {})
    for dim_name, dim_data in part.get("维度定义", {}).items():
        for key, val in dim_data.get("options", {}).items():
            if key == code:
                return val["label"]
    # 再查舌诊选项
    for dim_key in ["A_舌体", "B_舌苔", "C_神态", "D_舌下"]:
        dim = ZHIYIBANG_TONGUE.get("维度定义", {}).get(dim_key, {})
        if dim_key in ("C_神态", "D_舌下"):
            opts = dim.get("options", {})
            if code in opts:
                v = opts[code]
                return v if isinstance(v, str) else v.get("label", code)
        else:
            for sub in dim.get("子维度", {}).values():
                for k, v in sub.get("options", {}).items():
                    if k == code:
                        return v.get("label", code)
    return "未知"

def options_with_meaning(codes):
    """返回带含义的选项列表"""
    return [f"{c}(={get_option_meaning(c)})" for c in codes]


# ============================================================
# 3. 张锡纯用药禁忌查询
# ============================================================
def check_zhangxichun_contraindications(fang_name):
    """查询某方的张锡纯禁忌规则"""
    taboo = ZHANGXICHUN_RULES.get("禁忌规则", {})
    drug_rules = ZHANGXICHUN_RULES.get("药证规则", {})
    result = {"fang": fang_name, "contraindications": [], "warnings": []}
    # 模糊匹配方名
    for rule_name, rule_data in taboo.items():
        if fang_name in rule_name or rule_name in fang_name:
            result["contraindications"].append({"rule": rule_name, "data": rule_data})
    return result


def get_zhangxichun_principles():
    """获取张锡纯核心用药原则"""
    return ZHANGXICHUN_RULES.get("核心原则", ZHANGXICHUN_RULES.get("_version", "未知"))


# ============================================================
# 4. 脉象诊断（姚梅龄体系）
# ============================================================

# 已知脉象词列表（从 PULSE_DB 提取，用于复合脉短语拆解）
_PULSE_TERMS = sorted(
    [k for k in PULSE_DB.keys() if len(k) <= 4 and not k.startswith("_")],
    key=lambda x: -len(x)
)

def extract_pulse_terms(pulse_str):
    """
    从复合脉象短语中提取单个脉象词。
    如 "脉细欲绝" → ["细"]，"脉沉微" → ["沉","微"]
    "浮紧" → ["浮","紧"]
    """
    s = pulse_str.lstrip("脉")
    found = []
    i = 0
    while i < len(s):
        matched = False
        for term in _PULSE_TERMS:
            if s[i:i+len(term)] == term:
                found.append(term)
                i += len(term)
                matched = True
                break
        if not matched:
            i += 1
    return found

def query_pulse(pulse_name):
    """查询脉象的诊断意义（姚梅龄体系）"""
    result = PULSE_DB.get(pulse_name)
    if not result:
        for key in PULSE_DB:
            if pulse_name in key or key in pulse_name:
                result = PULSE_DB[key]
                pulse_name = key
                break
    return result, pulse_name


# ============================================================
# 5. 方证匹配引擎
# ============================================================
def search_fangzheng(pulses=None, symptoms=None):
    """根据脉象+症状匹配方证（含复合脉拆解）"""
    results = []
    # 拆解复合脉象为单脉词
    all_pulse_terms = set()
    for p in (pulses or []):
        for t in extract_pulse_terms(p):
            all_pulse_terms.add(t)
        all_pulse_terms.add(p)  # 也保留原始脉短语
    
    for name, fz in FANGZHENG_DB.items():
        score = 0
        if pulses:
            # 精确匹配
            matched = set(pulses) & set(fz["主脉"])
            score += len(matched) * 5
            # 拆解后单脉词匹配
            matched2 = all_pulse_terms & set(fz["主脉"])
            score += len(matched2) * 4
        if symptoms:
            for u_sym in symptoms:
                for fz_sym in fz["主症"]:
                    if u_sym in fz_sym or fz_sym in u_sym:
                        score += 2
                        break
        if score > 0:
            results.append((name, fz, score))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def search_hu_xishu_fangzheng(pulses, symptoms):
    """
    胡希恕体系独立方证检索——搜索 103 方方证对应数据库。
    匹配维度：六经症状 + 特征脉象 + 症候群关键词
    """
    fz_db = HUXISHU_RULES.get("方证对应数据库", {}).get("方剂条目", {})
    if not fz_db:
        return []
    
    all_symptoms_text = " ".join(symptoms) if symptoms else ""
    # 分解脉象
    all_pulse_terms = set()
    for p in (pulses or []):
        for t in extract_pulse_terms(p):
            all_pulse_terms.add(t)
    
    results = []
    for f_name, entry in fz_db.items():
        score = 0
        # 脉象匹配
        fp = entry.get("特征脉", "")
        if fp:
            fp_lower = fp.lower()
            for pt in all_pulse_terms:
                if pt in fp_lower:
                    score += 8
            # 完整脉短语匹配
            for p in (pulses or []):
                p_clean = p.lstrip("脉")
                if p_clean in fp_lower:
                    score += 10
        
        # 症候群匹配
        for sym in (symptoms or []):
            for fz_sym in entry.get("症候群", []):
                if sym in fz_sym or fz_sym in sym:
                    score += 3
                    break
        
        # 六经方向加分（如果已有六经定位线索）
        # 不作精确匹配，给分即可
        if score > 0:
            results.append((f_name, entry, score))
    
    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ============================================================
# 5.5 张仲景六经定纲搜索
# ============================================================
def search_zhang_zhongjing(pulses, symptoms):
    """
    张仲景层——根本层（本经）：六经提纲 + 脉证纲领 + 治则大法 + 附录方鉴别。
    返回: {
        "六经归属": [(经名, 匹配数, data), ...],
        "治则推荐": [方名, ...],
        "脉证匹配": [(规则名, 匹配内容), ...],
        "附录方匹配": [(方名, data), ...]
    }
    """
    result = {"六经归属": [], "治则推荐": [], "脉证匹配": [], "附录方匹配": []}
    
    all_symptoms_text = " ".join(symptoms) if symptoms else ""
    all_pulse_text = " ".join(pulses) if pulses else ""
    
    # --- 六经归属 ---
    jing_ti = ZHANGZHONGJING_RULES.get("六经提纲", {})
    # 扩展同义词映射
    keyword_expand = {
        "恶寒": ["恶寒", "畏寒", "怕冷", "寒战", "背恶寒"],
        "发热": ["发热", "身热", "潮热", "壮热", "翕翕发热"],
        "汗出": ["汗出", "自汗", "盗汗", "多汗", "汗自出"],
        "脉浮": ["脉浮", "浮"],
        "脉微细": ["脉微细", "脉细", "脉微", "脉沉细", "脉沉微", "细", "沉", "微"],
        "头项强痛": ["头项强痛", "头痛", "项强", "头项", "颈项强"],
        "胃家实": ["胃家实", "腹胀", "便秘", "大便难", "不大便", "燥屎"],
        "口苦": ["口苦"],
        "咽干": ["咽干", "口干", "口渴"],
        "目眩": ["目眩", "眩晕", "头晕"],
        "往来寒热": ["往来寒热", "寒热往来"],
        "胸胁苦满": ["胸胁苦满", "胸胁", "胁痛", "胁胀"],
        "腹满": ["腹满", "腹胀", "腹痛"],
        "吐": ["吐", "呕吐", "呕", "恶心"],
        "自利": ["自利", "下利", "腹泻", "便溏", "泄泻"],
        "但欲寐": ["但欲寐", "欲寐", "嗜睡", "精神萎靡", "倦怠", "乏力"],
        "消渴": ["消渴", "口渴多饮"],
        "气上撞心": ["气上撞心", "气上冲", "冲气"],
        "心中疼热": ["心中疼热", "心痛", "心下疼"],
        "四肢厥冷": ["四肢厥冷", "手足厥冷", "手足厥寒", "四肢冷", "肢冷", "厥冷", "厥寒"],
    }
    
    for jing_name in ["太阳", "阳明", "少阳", "太阴", "少阴", "厥阴"]:
        jdata = jing_ti.get(jing_name, {})
        if not jdata:
            continue
        match_count = 0
        matched_items = []
        keywords = jdata.get("关键症状", [])
        for kw in keywords:
            expanded = keyword_expand.get(kw, [kw])
            for exp_kw in expanded:
                if exp_kw in all_symptoms_text or exp_kw in all_pulse_text:
                    # 脉象关键词加权2倍
                    weight = 2 if ("脉" in kw or any(p in exp_kw for p in ["浮","沉","细","微","弦","紧","滑","涩","数","迟","弱"])) else 1
                    match_count += weight
                    matched_items.append(f"{kw}（{exp_kw}）")
                    break
        if match_count > 0:
            result["六经归属"].append((jing_name, match_count, matched_items, jdata))
    result["六经归属"].sort(key=lambda x: -x[1])
    
    # --- 治则大法 ---
    zhize = ZHANGZHONGJING_RULES.get("治则大法", {})
    # 按六经归属推断治则——仅从top经的治则字段提取推荐方
    if result["六经归属"]:
        top_jing = result["六经归属"][0]
        jing_name = top_jing[0]
        jdata = top_jing[3]
        zhize_raw = jdata.get("治则", "")
        for zf in ["麻黄汤","桂枝汤","葛根汤","大青龙汤","小青龙汤",
                    "白虎汤","白虎加人参汤","大承气汤","小承气汤","调胃承气汤",
                    "小柴胡汤","大柴胡汤","柴胡桂枝汤",
                    "四逆汤","通脉四逆汤","白通汤","理中丸","理中汤",
                    "当归四逆汤","乌梅丸","黄连阿胶汤","四逆辈",
                    "栀子豉汤","五苓散","猪苓汤","苓桂术甘汤",
                    "抵当汤","桃核承气汤","小建中汤","炙甘草汤"]:
            if zf in zhize_raw and zf not in result["治则推荐"]:
                result["治则推荐"].append(zf)
        # 同时提取治则大法名称
        zhize_names = []
        if ("汗" in zhize_raw or "发汗" in zhize_raw) and "禁汗" not in zhize_raw: zhize_names.append("汗法")
        if ("下" in zhize_raw) and "禁下" not in zhize_raw: zhize_names.append("下法")
        if "和" in zhize_raw: zhize_names.append("和法")
        if "温" in zhize_raw: zhize_names.append("温法")
        if "清" in zhize_raw: zhize_names.append("清法")
        if ("吐" in zhize_raw) and "禁吐" not in zhize_raw: zhize_names.append("吐法")
        if "消" in zhize_raw: zhize_names.append("消法")
        if "补" in zhize_raw: zhize_names.append("补法")
        result["治则推荐"] = zhize_names + result["治则推荐"]
    
    # --- 脉证纲领匹配 ---
    maizheng = ZHANGZHONGJING_RULES.get("脉证纲领", {})
    # 检查各层
    for section_key in ["三_病脉纲领", "八_六经病脉", "四_特殊脉象"]:
        section = maizheng.get(section_key, {})
        if not isinstance(section, dict):
            continue
        for rule_key, rule_data in section.items():
            if rule_key.startswith("_"):
                continue
            rule_text = str(rule_data)
            pulse_match = any(p in rule_text for p in pulses)
            sym_match = any(s in rule_text for s in (symptoms or [])[:5])
            if pulse_match or sym_match:
                snippet = rule_text[:80]
                result["脉证匹配"].append((f"{section_key}/{rule_key}", snippet))
    
    # --- 附录方脉证鉴别 ---
    for key in ZHANGZHONGJING_RULES:
        if key.startswith("附录_") and "脉证鉴别" in key:
            append_data = ZHANGZHONGJING_RULES[key]
            if not isinstance(append_data, dict):
                continue
            score = 0
            matched_detail = []
            for sub_key, sub_val in append_data.items():
                if sub_key.startswith("_"):
                    continue
                sub_text = str(sub_val)
                for p in pulses:
                    if p in sub_text:
                        score += 3
                        matched_detail.append(f"脉{p}")
                for s in (symptoms or [])[:8]:
                    if s in sub_text:
                        score += 2
                        matched_detail.append(s)
            if score >= 4:
                fang_name = key.replace("附录_", "").replace("_脉证鉴别_巍哥口述原著原文", "")
                result["附录方匹配"].append((fang_name, score, append_data, matched_detail))
    result["附录方匹配"].sort(key=lambda x: -x[1])
    
    return result


# ============================================================
# 6. 综合辨证分析
# ============================================================
def differential_diagnosis(pulses, symptoms, zhiyibang_opts=None, tongue_opts=None):
    """综合辨证分析（姚梅龄脉诊 + 方证匹配 + 知医邦量化 + 舌诊 + 七家并列）"""
    lines = []
    sheng_hits = []
    jiang_hits = []
    yangxu_hits = []
    yinxu_hits = []
    jing_hits = []
    lines.append("=" * 60)
    lines.append("【辨证施治分析报告 v2.2（八家并列·仲景为根）】")
    lines.append("  张仲景（本经）→ 姚梅龄脉诊 · 胡希恕六经 · 张锡纯升降 · 刘渡舟十论")
    lines.append("  曹颖甫方证 · 郑钦安阴阳 · 知医邦量化（脉诊/舌诊）")
    lines.append("=" * 60)

    # 0. 张仲景六经定纲（根本层）
    zzj_result = search_zhang_zhongjing(pulses, symptoms)
    lines.append("\n【零·根本层】张仲景六经定纲")
    lines.append("-" * 40)
    lines.append(f"  体系：宋本《伤寒论》397法113方·《金匮要略》杂病纲领")
    lines.append(f"  总纲：'观其脉证，知犯何逆，随证治之'（第16条）")
    
    # 六经归属
    if zzj_result["六经归属"]:
        ti = zzj_result["六经归属"][0]
        jdata = ti[3]
        lines.append(f"\n  六经归属：{ti[0]}病（匹配{ti[1]}项：{'、'.join(ti[2][:5])}）")
        lines.append(f"    原文：{jdata.get('原文','')[:80]}")
        lines.append(f"    分类：{jdata.get('分类','')} | 病位：{jdata.get('病位','')} | 病性：{jdata.get('病性','')}")
        lines.append(f"    治则：{jdata.get('治则','')[:80]}")
        lines.append(f"    出处：{jdata.get('出处','')}")
        if len(zzj_result["六经归属"]) > 1:
            ci = zzj_result["六经归属"][1]
            lines.append(f"  兼见：{ci[0]}病（{'、'.join(ci[2][:3])}）")
    else:
        lines.append("\n  六经归属：症状不足以定经，需补充恶寒/发热/汗出/二便等信息。")
    
    # 脉证纲领
    if zzj_result["脉证匹配"]:
        lines.append(f"\n  脉证纲领（{len(zzj_result['脉证匹配'])}条命中）：")
        for rule_name, snippet in zzj_result["脉证匹配"][:4]:
            short_name = rule_name.split("/")[-1] if "/" in rule_name else rule_name
            lines.append(f"    [{short_name}] {snippet[:70]}")
    
    # 治则大法
    if zzj_result["治则推荐"]:
        lines.append(f"\n  治则大法：{'、'.join(zzj_result['治则推荐'][:4])}")
    
    # 附录方鉴别
    if zzj_result["附录方匹配"]:
        lines.append(f"\n  附录方脉证鉴别（{len(zzj_result['附录方匹配'])}方命中）：")
        for fang_name, score, data, hits in zzj_result["附录方匹配"][:3]:
            ben_pulse = data.get("本方脉证", "")
            lines.append(f"    ■ {fang_name}（{score}分）→ {'、'.join(hits[:4])}")
            if ben_pulse:
                lines.append(f"      脉证：{ben_pulse[:100]}")

    # 1. 姚梅龄脉象分析
    lines.append("\n\n一、姚梅龄脉象分析")
    lines.append("-" * 40)
    for p in pulses:
        result, matched = query_pulse(p)
        if result:
            lines.append(f"\n■ {matched}脉")
            lines.append(f"  类别：{result['category']}")
            lines.append(f"  指感：{result['rate']}")
            if result.get('grades'):
                lines.append(f"  分级：{', '.join(result['grades'])}")
            lines.append(f"  诊断意义：")
            for i, diag in enumerate(result['diagnosis'][:5], 1):
                lines.append(f"    {i}. {diag}")
        else:
            lines.append(f"\n■ {p}脉：未在数据库中。")

    # 2. 知医邦量化计算
    if zhiyibang_opts:
        lines.append("\n\n二、知医邦28脉量化计算")
        lines.append("-" * 40)
        labeled = options_with_meaning(zhiyibang_opts)
        lines.append(f"  [脉诊: 知医邦] 选中：{', '.join(labeled)}")
        results_28 = zhiyibang_diagnose_28mai(zhiyibang_opts)
        if results_28:
            lines.append(f"  成立脉象（∈>0）：")
            for pname, eps in results_28[:10]:
                lines.append(f"    [脉象: 知医邦] {pname} ∈={eps}")
        else:
            lines.append("  无脉象成立（所有∈≤0）。")

    # 3. 舌诊辨证
    if tongue_opts:
        lines.append("\n\n三、知医邦舌诊辨证")
        lines.append("-" * 40)
        labeled = options_with_meaning(tongue_opts)
        lines.append(f"  [舌诊: 知医邦] 选中：{', '.join(labeled)}")
        tongue_results = tongue_diagnose(tongue_opts)
        if tongue_results:
            lines.append(f"  [证型: 知医邦] 推导：{'、'.join(tongue_results)}")
        else:
            lines.append("  未推导出明确证型。")

    # 方证匹配结果（预计算，各体系共用）
    results = search_fangzheng(pulses, symptoms)

    # 4. 胡希恕六经八纲辨证
    lines.append("\n\n四、胡希恕六经八纲辨证")
    lines.append("-" * 40)
    liujing = HUXISHU_RULES.get("六经体系", {})
    bagang = HUXISHU_RULES.get("八纲辨证框架", {})
    # 六经定位
    jing_hits.clear()
    all_symptoms = " ".join(symptoms).lower() if symptoms else ""
    for jname, jdata in liujing.items():
        if jname == "六经皆有表证（关键规则）":
            continue
        hits = 0
        if isinstance(jdata, dict):
            if "主症" in jdata:
                for s in jdata["主症"]:
                    if s and s in all_symptoms:
                        hits += 1
            if "提纲" in jdata:
                for s in jdata["提纲"].replace("，",",").replace("、",",").split(","):
                    if s.strip() and s.strip() in all_symptoms:
                        hits += 1
        if hits > 0:
            jing_hits.append((jname, hits, jdata))
    jing_hits.sort(key=lambda x: x[1], reverse=True)
    if jing_hits:
        for jname, hits, jdata in jing_hits[:3]:
            lines.append(f"\n■ {jname}（命中{hits}项）")
            if isinstance(jdata, dict):
                lines.append(f"  病位：{jdata.get('病位','?')} / 病性：{jdata.get('病性','?')}")
                if jdata.get("核心病机"):
                    lines.append(f"  病机：{jdata['核心病机'][:60]}")
                if jdata.get("代表方"):
                    lines.append(f"  [胡希恕: 六经] 代表方：{jdata['代表方']}")
        # 八纲判定
        lines.append(f"\n  [胡希恕: 八纲] 已有线索：{'阳' if jing_hits[0][0] in ['太阳病','阳明病','少阳病'] else '阴'}证 · {'表' if jing_hits[0][0] in ['太阳病','少阴病'] else '里' if jing_hits[0][0] in ['阳明病','太阴病'] else '半表半里'}位")
    else:
        lines.append("\n  症状不足，未定位六经。需补充恶寒/发热/汗出/饮食/二便等信息以定六经归属。")
    # 方证对应——检索103方完整数据库
    lines.append(f"\n  [胡希恕: 方证] 103方检索结果：")
    hu_results = search_hu_xishu_fangzheng(pulses, symptoms)
    if hu_results:
        for f_name, entry, score in hu_results[:5]:
            lines.append(f"    {f_name}（{score}分）→ {entry.get('六经','?')}·{entry.get('八纲','?')}")
            lines.append(f"      症候：{'；'.join(entry.get('症候群',[])[:3])}")
            lines.append(f"      按语：{entry.get('胡希恕按语','')[:80]}")
    else:
        # 兜底：尝试六经方向 + 代表方
        if jing_hits:
            top_jing = jing_hits[0]
            rep_fang = top_jing[2].get("代表方", "")
            if rep_fang:
                lines.append(f"    症状不足以精确定方，六经方向指向：[{top_jing[0]}] 代表方：{rep_fang}")
        else:
            lines.append("    脉症不足，请补充详细症状以精确定方。")

    # 5. 张锡纯方证升降分析
    lines.append("\n\n五、张锡纯方证升降分析")
    lines.append("-" * 40)
    sx_frame = ZHANGXICHUN_RULES.get("升降辨证框架", {})
    if sx_frame:
        lines.append(f"  体系：张锡纯衷中参西——大气升降·药证对应")
        lines.append(f"  [张锡纯: 核心] {sx_frame.get('核心升降对立轴','')[:80]}")
        # 升降判断
        sx_symptoms = all_symptoms
        sheng_indicators = ["气短","不足以息","胸闷","乏力","懒言","脉弱","脉沉迟"]
        jiang_indicators = ["气逆","喘促","呃逆","呕吐","眩晕","面赤","脉弦","脉弦长"]
        sheng_hits.clear()
        jiang_hits.clear()
        sheng_hits.extend([s for s in sheng_indicators if s in sx_symptoms])
        jiang_hits.extend([s for s in jiang_indicators if s in sx_symptoms])
        if sheng_hits:
            lines.append(f"\n  [张锡纯: 升降] 大气下陷指征：{'、'.join(sheng_hits)}")
            lines.append(f"  [张锡纯: 方药] 升陷汤类方适用。忌破气、忌误降。")
            # 展示升陷类方鉴别
            sx_classes = sx_frame.get("升陷类方鉴别", {})
            if sx_classes:
                lines.append(f"  升陷类方：{' / '.join(sx_classes.keys())}")
        if jiang_hits:
            lines.append(f"\n  [张锡纯: 升降] 气机上逆指征：{'、'.join(jiang_hits)}")
            lines.append(f"  [张锡纯: 方药] 镇逆降气类方适用。")
        if not sheng_hits and not jiang_hits:
            lines.append(f"\n  症状中未发现明显升降失常指征。")
        # 用药禁忌
        if results:
            top_fangs = [name for name, _, _ in results[:3]]
            taboo = ZHANGXICHUN_RULES.get("禁忌规则", {})
            for rule_name in taboo:
                for f in top_fangs:
                    if f in rule_name or rule_name in f:
                        lines.append(f"\n  [张锡纯: 禁忌] 「{f}」相关：{list(taboo[rule_name].keys())[:2]}")
    else:
        lines.append("\n  张锡纯规则数据未完整加载。")

    # 6. 刘渡舟十论辨证
    lines.append("\n\n六、刘渡舟十论辨证")
    lines.append("-" * 40)
    ldz_rules = LIUDUZHOU_RULES.get("核心原则", [])
    ldz_hits = []
    for rule in ldz_rules:
        rid = rule.get("id","")
        cat = rule.get("分类","")
        # 水证论匹配
        if "水" in cat and any(s in all_symptoms for s in ["小便","浮肿","眩","悸","渴","泻","咳","痰","舌"]):
            ldz_hits.append(f"  [刘渡舟: {cat}] {rid}")
        # 气机论匹配
        if "气机" in cat and any(s in all_symptoms for s in ["胁","口苦","纳","呕","痞","胀","弦"]):
            ldz_hits.append(f"  [刘渡舟: {cat}] {rid}")
        # 脾胃论匹配
        if "脾胃" in cat and any(s in all_symptoms for s in ["食","腹","便","泄","呕","痞","胀"]):
            ldz_hits.append(f"  [刘渡舟: {cat}] {rid}")
        # 六经
        if "六经" in cat:
            ldz_hits.append(f"  [刘渡舟: {cat}] 六经提纲+标本中气已加载，可交叉验证")
    if ldz_hits:
        for h in ldz_hits[:5]:
            lines.append(h)
        lines.append(f"\n  [刘渡舟: 辨证知机] 方证相对为初阶，辨证知机为神品——以色脉之诊决死生处百病。")
    else:
        lines.append("\n  症状不足以触发刘渡舟十论的具体分支。请补充小便/浮肿/痰饮/气机/脾胃/六经相关症状。")

    # 7. 曹颖甫方证对应评估
    lines.append("\n\n七、曹颖甫方证对应评估")
    lines.append("-" * 40)
    cyf_rules = CAOYINGFU_RULES.get("核心原则", [])
    lines.append(f"  体系：{CAOYINGFU_RULES.get('体系','曹颖甫经方实验派')}")
    lines.append(f"  准则：法遵仲景·方证对应——有是证用是方。92案中91案用仲景方，66案（72%）原方不加减。")
    lines.append(f"  曹氏加减原则：加减不出经方范畴。不拘病名，唯证是辨。")
    # 方证匹配结果与曹氏标准对照
    if results:
        top3 = results[:3]
        lines.append(f"\n  方证匹配Top3与曹氏标准对照：")
        for name, fz, score in top3:
            src = fz.get("来源","?")
            is_zhongjing = src in ["伤寒论","金匮要略"]
            zhongjing_tag = "√仲景方" if is_zhongjing else "⚠非仲景方(曹氏极少用)"
            lines.append(f"    {name}（{score}分）→ {src} [{zhongjing_tag}]")
    else:
        lines.append("\n  未匹配到方证，无法对照曹氏标准。")

    # 8. 方证匹配
    lines.append("\n\n八、方证匹配（跨体系）")
    lines.append("-" * 40)
    if results:
        for rank, (name, fz, score) in enumerate(results[:8], 1):
            lines.append(f"\n{rank}. 【{name}】（匹配度：{score}分）")
            lines.append(f"   主脉：{'、'.join(fz['主脉'])}")
            lines.append(f"   主症：{'、'.join(fz['主症'][:4])}{'...' if len(fz['主症'])>4 else ''}")
            lines.append(f"   [方证: {fz['来源']}]")
            for f_name, f_comp in fz['方剂']:
                lines.append(f"   → 方：{f_name}")
                lines.append(f"      组成：{f_comp}")
    else:
        lines.append("\n未匹配到方证。")

    # 9. 郑钦安阴阳辨证
    lines.append("\n\n九、郑钦安阴阳辨证")
    lines.append("-" * 40)
    if symptoms:
        yangxu_hits.clear()
        yinxu_hits.clear()
        for rule in ZHENGQINAN_RULES["核心原则"]:
            keywords = rule.get("关键症状", [])
            if not keywords:
                continue
            rule_text = rule.get("规则", rule.get("原文", ""))[:30]
            for kw in keywords:
                for sym in symptoms:
                    if kw in sym or sym in kw:
                        cat = rule.get("分类", "")
                        if cat in ["阳虚辨识", "阳虚阴盛核心病机", "真阳判别法", "阴盛逼阳外越"]:
                            yangxu_hits.append(f"[郑钦安: 阴阳辨证] {rule['id']}「{kw}」→ {rule_text}")
                        elif cat == "阴虚辨识":
                            yinxu_hits.append(f"[郑钦安: 阴阳辨证] {rule['id']}「{kw}」→ {rule_text}")
        if yangxu_hits:
            lines.append(f"\n  阳虚证据（{len(yangxu_hits)}条）：")
            for h in yangxu_hits[:6]:
                lines.append(f"    {h}")
            lines.append(f"\n  [郑钦安: 阴阳辨证] 结论：阳虚阴盛，治以扶阳抑阴。阳不化阴则湿浊内生。")
        if yinxu_hits:
            lines.append(f"\n  阴虚证据（{len(yinxu_hits)}条）：")
            for h in yinxu_hits[:6]:
                lines.append(f"    {h}")
        if not yangxu_hits and not yinxu_hits:
            lines.append("\n  症状未直接命中核心辨证条目，需四诊合参。")
    else:
        lines.append("\n  请提供症状以进行郑钦安阴阳辨证。")

    # 10. 鉴别诊断
    if len(results) >= 2:
        lines.append("\n\n十、鉴别诊断")
        lines.append("-" * 40)
        top = results[:3]
        for i in range(len(top)):
            for j in range(i+1, len(top)):
                n1, fz1, _ = top[i]
                n2, fz2, _ = top[j]
                diff_sym = set(fz1["主症"]) - set(fz2["主症"])
                diff_pulse = set(fz1["主脉"]) - set(fz2["主脉"])
                if diff_sym or diff_pulse:
                    lines.append(f"\n【{n1}】vs【{n2}】")
                    if diff_sym:
                        lines.append(f"  {n1}特有：{'、'.join(list(diff_sym)[:3])}")
                        rev = set(fz2["主症"]) - set(fz1["主症"])
                        if rev:
                            lines.append(f"  {n2}特有：{'、'.join(list(rev)[:3])}")
                    if diff_pulse:
                        lines.append(f"  {n1}脉：{'、'.join(list(diff_pulse)[:2])}")
                        rev = set(fz2["主脉"]) - set(fz1["主脉"])
                        if rev:
                            lines.append(f"  {n2}脉：{'、'.join(list(rev)[:2])}")

    # 11. 七家综合处方建议
    lines.append("\n\n十一、八家综合处方建议")
    lines.append("-" * 40)
    if results:
        top = results[0]
        lines.append(f"  首选方证：{top[0]}（{top[2]}分）")
        lines.append(f"  来源体系：[方证: {top[1]['来源']}]")
        lines.append(f"  方剂：{' / '.join(x[0] for x in top[1]['方剂'])}")
        # 跨体系审查
        lines.append(f"\n  跨体系审查：")
        if jing_hits:
            lines.append(f"    [胡希恕: 六经定位] {jing_hits[0][0]} → 治法方向：{jing_hits[0][2].get('治疗原则','随证治之')}")
        if yangxu_hits:
            lines.append(f"    [郑钦安: 阴阳] 阳虚阴盛 → 治以扶阳抑阴，诊脉当辩'独处藏奸'")
            lines.append(f"    [姚梅龄: 脉诊] 如脉沉细无力=阳不化阴，脉浮大而空=虚阳外越——需结合具体脉象判断")
        lines.append(f"    [张锡纯: 升降] {'大气下陷→升陷类方慎用破气药' if sheng_hits else '气机上逆→镇逆降气' if jiang_hits else '升降未显异常'}")
        lines.append(f"    [刘渡舟: 接轨] 经方为骨，时方为翼——可据兼证参入古今接轨思路")
        lines.append(f"    [曹颖甫: 原方率] 曹氏72%原方不加减。如用仲景方，先考原方，非必要不加减。")
        # 冲突审查
        conflicts = []
        if yangxu_hits and top[0] in ["白虎汤证","承气汤证","泻心汤证"]:
            conflicts.append("⚠ 郑钦安阳虚辨证 vs 方证匹配寒凉方——需重点复核脉象：脉沉细微弱不可用寒凉")
        if sheng_hits and "破气" in " ".join(top[1].get("方剂",[("","")])[0][1] if top[1].get("方剂") else ""):
            conflicts.append("⚠ 张锡纯大气下陷 vs 方中含破气药——冲突")
        if conflicts:
            lines.append(f"\n  ⚠ 冲突警示：")
            for c in conflicts:
                lines.append(f"    {c}")
    else:
        lines.append("  无方证匹配结果，无法生成处方建议。")

    lines.append("\n" + "=" * 60)
    lines.append("【八家辨证完成】张仲景（本经）·姚梅龄·胡希恕·张锡纯·刘渡舟·曹颖甫·郑钦安·知医邦——八体系并列输出。")
    lines.append("以上分析仅供参考。临床需四诊合参，不可偏执一家。")
    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================
# 7. 列表功能
# ============================================================
def list_all_pulses():
    cats = {}
    for name, info in PULSE_DB.items():
        cat = info["category"]
        cats.setdefault(cat, []).append(name)
    lines = ["【姚梅龄脉学·病脉分类】", ""]
    for cat in ["脉率", "脉律", "脉体", "脉位", "脉力", "脉势", "复合脉"]:
        if cat in cats:
            lines.append(f"\n{cat}异常类（{len(cats[cat])}种）：")
            for name in cats[cat]:
                info = PULSE_DB[name]
                lines.append(f"  {name}脉（{info['rate'][:25]}）")
    return "\n".join(lines)


def list_all_fangzheng():
    lines = [f"【方证数据库 v2】（共{len(FANGZHENG_DB)}条）", ""]
    sources = {}
    for name, fz in FANGZHENG_DB.items():
        src = fz["来源"]
        sources.setdefault(src, []).append((name, fz))
    for src in ["伤寒论", "金匮要略", "张锡纯"]:
        if src in sources:
            lines.append(f"\n{src}方证（{len(sources[src])}条）：")
            for name, fz in sources[src]:
                f_names = [x[0] for x in fz["方剂"]]
                lines.append(f"  {name} → {' / '.join(f_names)}")
    return "\n".join(lines)


def list_zhiyibang_pulse_formulas():
    lines = ["【知医邦28脉公式】", ""]
    for pname in PULSE_FORMULAS:
        if pname.startswith("_"):
            continue
        formula = PULSE_FORMULAS[pname]
        lines.append(f"  [脉象: 知医邦] {pname} = {formula['依赖']}")
    return "\n".join(lines)


def list_tongue_options():
    lines = ["【知医邦舌诊量表选项清单】", ""]
    lines.append("[舌诊: 知医邦] A 舌体颜色: AA(=浅淡发白) AB(=红艳) AC(=暗红) AD(=发紫) AE(=浅淡发青)")
    lines.append("[舌诊: 知医邦] A 裂纹点刺: AF(=裂纹) AG(=点刺)")
    lines.append("[舌诊: 知医邦] A 凹凸: AH(=凹陷) AI(=凸起)")
    lines.append("[舌诊: 知医邦] B 舌苔颜色: BA(=白色) BB(=黄色) BC(=灰色) BD(=黑色)")
    lines.append("[舌诊: 知医邦] B 舌苔形状: BE(=厚苔) BF(=少苔) BG(=无苔如牛肉)")
    lines.append("[舌诊: 知医邦] B 舌苔质地: BH(=湿滑黏腻) BI(=干燥粗糙) BJ(=光滑如镜)")
    lines.append("[舌诊: 知医邦] C 神态: CA-CZ（24项，可选）")
    lines.append("[舌诊: 知医邦] D 舌下: DA(=舌脉怒张) DB(=青紫) DC(=紫黯) DD(=瘀斑) DE(=浅淡)")
    return "\n".join(lines)


# ============================================================
# 8. 帮助与交互
# ============================================================
HELP_TEXT = """
========================================
  辨证施治辅助系统 v2.1（七家并列版）
  姚梅龄 + 胡希恕 + 张锡纯 + 刘渡舟
  + 曹颖甫 + 郑钦安 + 知医邦
========================================

命令：
  search <症状> / <脉象>
    例: search 头痛恶寒 发热 / 浮紧

  pulse <脉名>
    查询脉象诊断意义（姚梅龄体系）
    例: pulse 涩

  zhiyibang <选项1> <选项2> ...
    知医邦10维度量化计算28脉∈值
    例: zhiyibang AA AB EA IB

  tongue <选项1> <选项2> ...
    知医邦舌诊辨证
    例: tongue AB BA BE

  contraindication <方名>
    查询张锡纯用药禁忌
    例: contraindication 升陷汤

  list-pulses      列出全部脉象
  list-fangzheng   列出全部方证
  list-formulas    列出知医邦28脉公式
  list-tongue      列出舌诊选项
  help             帮助
  quit             退出
========================================
"""


def parse_input(user_input):
    user_input = user_input.strip()
    if not user_input:
        return None, None

    if user_input.lower().startswith("search "):
        content = user_input[7:].strip()
        if "/" in content:
            sym_part, pulse_part = content.split("/", 1)
            symptoms = [s.strip() for s in sym_part.split() if s.strip()]
            pulses = [p.strip() for p in pulse_part.split() if p.strip()]
        else:
            symptoms = [s.strip() for s in content.split() if s.strip()]
            pulses = []
        return ("search", {"symptoms": symptoms, "pulses": pulses})

    if user_input.lower().startswith("pulse "):
        return ("pulse", {"name": user_input[6:].strip()})

    if user_input.lower().startswith("zhiyibang "):
        opts = [s.strip() for s in user_input[10:].split() if s.strip()]
        return ("zhiyibang", {"options": opts})

    if user_input.lower().startswith("tongue "):
        opts = [s.strip() for s in user_input[7:].split() if s.strip()]
        return ("tongue", {"options": opts})

    if user_input.lower().startswith("contraindication "):
        return ("contraindication", {"fang": user_input[17:].strip()})

    cmd = user_input.lower()
    if cmd in ["list-pulses", "list-fangzheng", "list-formulas", "list-tongue", "help", "quit", "exit"]:
        return (cmd, None)

    # 默认当作search
    if "/" in user_input:
        sym_part, pulse_part = user_input.split("/", 1)
        symptoms = [s.strip() for s in sym_part.split() if s.strip()]
        pulses = [p.strip() for p in pulse_part.split() if p.strip()]
    else:
        symptoms = []
        pulses = []
        for word in user_input.split():
            if word in PULSE_DB:
                pulses.append(word)
            else:
                symptoms.append(word)
    return ("search", {"symptoms": symptoms, "pulses": pulses})


def interactive():
    print(HELP_TEXT)
    while True:
        try:
            user_input = input("辨证施治> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if not user_input:
            continue

        cmd, params = parse_input(user_input)
        if cmd in ("quit", "exit"):
            print("再见。")
            break
        elif cmd == "help":
            print(HELP_TEXT)
        elif cmd == "list-pulses":
            print(list_all_pulses())
        elif cmd == "list-fangzheng":
            print(list_all_fangzheng())
        elif cmd == "list-formulas":
            print(list_zhiyibang_pulse_formulas())
        elif cmd == "list-tongue":
            print(list_tongue_options())
        elif cmd == "pulse":
            result, matched = query_pulse(params["name"])
            if result:
                print(f"\n■ {matched}脉")
                print(f"  类别：{result['category']}")
                print(f"  指感：{result['rate']}")
                if result.get('grades'):
                    print(f"  分级：{', '.join(result['grades'])}")
                print(f"  诊断意义：")
                for i, diag in enumerate(result['diagnosis'], 1):
                    print(f"    {i}. {diag}")
            else:
                print(f"未找到脉象：{params['name']}")
        elif cmd == "zhiyibang":
            opts = params["options"]
            if not opts:
                print("请输入知医邦维度选项。例：zhiyibang AA EA IB CC")
                continue
            results = zhiyibang_diagnose_28mai(opts)
            labeled = options_with_meaning(opts)
            print(f"\n[脉诊: 知医邦] 选中：{', '.join(labeled)}")
            if results:
                for pname, eps in results:
                    print(f"  [脉象: 知医邦] {pname}  ∈={eps}")
            else:
                print("  无脉象成立。")
        elif cmd == "tongue":
            opts = params["options"]
            if not opts:
                print("请输入舌诊选项。例：tongue AB BA BE")
                continue
            results = tongue_diagnose(opts)
            labeled = options_with_meaning(opts)
            print(f"\n[舌诊: 知医邦] 选中：{', '.join(labeled)}")
            if results:
                print(f"  [证型: 知医邦] 推导：{'、'.join(results)}")
            else:
                print("  未推导出明确证型。")
        elif cmd == "contraindication":
            fang = params["fang"]
            result = check_zhangxichun_contraindications(fang)
            print(f"\n张锡纯用药禁忌查询：{fang}")
            if result["contraindications"]:
                for item in result["contraindications"]:
                    print(f"  规则：{item['rule']}")
            else:
                print(f"  未找到针对「{fang}」的专用禁忌规则。")
        elif cmd == "search":
            syms = params["symptoms"]
            puls = params["pulses"]
            if not syms and not puls:
                print("请输入症状或脉象。格式：search 症状 / 脉象")
                continue
            report = differential_diagnosis(puls, syms)
            print("\n" + report)
        else:
            print(f"未知命令。输入 help 查看帮助。")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = " ".join(sys.argv[1:])
        cmd, params = parse_input(arg)
        if cmd == "search":
            print(differential_diagnosis(params["pulses"], params["symptoms"]))
        elif cmd == "pulse":
            result, matched = query_pulse(params["name"])
            if result:
                print(f"{matched}脉：{'；'.join(result['diagnosis'])}")
        elif cmd == "zhiyibang":
            results = zhiyibang_diagnose_28mai(params["options"])
            for p, e in results:
                print(f"{p} ∈={e}")
        elif cmd == "tongue":
            results = tongue_diagnose(params["options"])
            if results:
                print("；".join(results))
        elif cmd == "list-pulses":
            print(list_all_pulses())
        elif cmd == "list-fangzheng":
            print(list_all_fangzheng())
        elif cmd == "list-formulas":
            print(list_zhiyibang_pulse_formulas())
        elif cmd == "list-tongue":
            print(list_tongue_options())
    else:
        interactive()
