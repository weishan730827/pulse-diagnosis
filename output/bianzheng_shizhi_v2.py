#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辨证施治辅助系统 v2.1（七家并列版）
整合：姚梅龄脉学 + 胡希恕六经八纲 + 张锡纯方证升降 + 刘渡舟十论辨证 + 曹颖甫方证对应 + 郑钦安阴阳辨证 + 知医邦量化（脉诊/舌诊）
七家并列输出 → 方证匹配 → 跨体系冲突审查 → 综合处方建议
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
    """计算某脉象的置信度∈值"""
    formula = PULSE_FORMULAS.get(pulse_name)
    if not formula:
        return 0.0
    core, secondary, normal = parse_formula_weight(pulse_name)
    positive = 0.0
    negative = 0.0
    selected_set = set(selected_options)
    for c in core:
        if c in selected_set:
            positive += 2  # f=2
        else:
            negative += 1
    for s in secondary:
        if s in selected_set:
            positive += 0.5  # f=1/2
        else:
            negative += 1
    for n in normal:
        if n in selected_set:
            positive += 1  # f=1
        else:
            negative += 1
    denom = positive + negative + 1.5
    if denom == 0:
        return 0.0
    epsilon = (positive * 1.0 - negative) / denom  # e=1
    return round(epsilon, 2)


def zhiyibang_diagnose_28mai(selected_options):
    """输入选中的维度选项列表，输出28脉∈值排序"""
    results = {}
    for pname in PULSE_FORMULAS:
        if pname.startswith("_"):
            continue
        eps = calc_pulse_confidence(selected_options, pname)
        if eps > 0:
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
    """根据脉象+症状匹配方证"""
    results = []
    for name, fz in FANGZHENG_DB.items():
        score = 0
        if pulses:
            matched = set(pulses) & set(fz["主脉"])
            if matched:
                score += len(matched) * 5
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
    lines.append("【辨证施治分析报告 v2.1（七家并列）】")
    lines.append("  姚梅龄脉诊 · 胡希恕六经 · 张锡纯升降 · 刘渡舟十论")
    lines.append("  曹颖甫方证 · 郑钦安阴阳 · 知医邦量化（脉诊/舌诊）")
    lines.append("=" * 60)

    # 1. 姚梅龄脉象分析
    lines.append("\n一、姚梅龄脉象分析")
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
    fzd = HUXISHU_RULES.get("方证对应核心", {})
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
    # 方证对应核心速查
    if symptoms:
        lines.append(f"\n  [胡希恕: 方证] 速查：")
        for fz_name, fz_data in fzd.items():
            if "必备" in fz_data:
                reqs = fz_data["必备"]
                matched = sum(1 for s in symptoms if any(kw in s for kw in reqs.split("+")))
                total = len([x for x in reqs.replace("+"," ").split() if x])
                if total > 0 and matched / total >= 0.5:
                    lines.append(f"    {fz_name}（{matched}/{total}）：{fz_data.get('方','?')}")

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
    lines.append("\n\n十一、七家综合处方建议")
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
    lines.append("【七家辨证完成】姚梅龄·胡希恕·张锡纯·刘渡舟·曹颖甫·郑钦安·知医邦——七体系并列输出。")
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
