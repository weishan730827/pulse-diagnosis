#!/usr/bin/env python3
"""
双轨辨证流水线 v4.0 — 签名库升级为277方
============================================
v4 核心升级：
  1. 签名库：chen_jianguo_formula_signatures.json(50方) → formula_pulse_bilateral_v4.json(277方)
  2. 匹配维度：trend+layer → trend+site+level+quality 四维加权
  3. 解读集成：50方_脉证解读与鉴别_完整采集.md → 匹配结果附解读/鉴别原文
  4. 外部方剂：external_pulse_signatures.md → 附录与鉴别段提及方剂可查

用法：
    python dual_track_pipeline_v4.py --pulses "左寸浮紧,左关浮,左尺沉紧,右寸濡,右尺沉弱" --symptoms "恶寒发热,头痛,..."
    python dual_track_pipeline_v4.py --input chen_input.json
"""

import sys
import os
import json
import re
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bianzheng_shizhi_v3 import (
    differential_diagnosis,
)

# ============================================================================
# 0. 全局路径
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V4_SIG_PATH = os.path.join(SCRIPT_DIR, "formula_pulse_bilateral_v4.json")
INTERP_PATH = os.path.join(SCRIPT_DIR, "50方_脉证解读与鉴别_完整采集.md")
EXTERNAL_PATH = os.path.join(SCRIPT_DIR, "external_pulse_signatures.md")

# ============================================================================
# 1. 输入解析（复用v3的parse_chen_form_md和load_input）
# ============================================================================

def parse_cli_args():
    parser = argparse.ArgumentParser(description="双轨辨证流水线 v4.0（277方）")
    parser.add_argument("--input", type=str, help="JSON输入文件路径（chen_input.json格式）")
    parser.add_argument("--pulses", type=str, help="脉象，逗号分隔")
    parser.add_argument("--symptoms", type=str, help="症状，逗号分隔")
    parser.add_argument("--zhiyibang-opts", type=str, default="", help="知医邦选项，空格分隔（可选）")
    parser.add_argument("--tongue-opts", type=str, default="", help="舌诊选项，空格分隔（可选）")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    return parser.parse_args()


def parse_chen_form_md(md_path):
    if not os.path.exists(md_path):
        return None
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    chen = {}

    # step1 总体
    if "总体太过" in text:
        idx = text.find("总体太过")
        block = text[idx:idx+200]
        chen["step1_overall"] = "太过" if "☑" in block.split("\n")[0] else "不及"
    else:
        chen["step1_overall"] = "不及"

    # step2 左右大法
    left_weaker = False
    for line in text.split("\n"):
        if "左手更弱" in line and "☑" in line:
            left_weaker = True
            break
    if left_weaker:
        chen["step2_direction"] = {"weaker_side": "left", "method": "甘寒降法", "quadrant": "阴虚"}
    else:
        chen["step2_direction"] = {"weaker_side": "right", "method": "甘温升法", "quadrant": "阳虚"}

    # step3 三部
    left_pos, right_pos = {}, {}
    for pos_name, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
        for side_label, side_dict in [("左", left_pos), ("右", right_pos)]:
            pattern = f"### {side_label}{pos_label}"
            idx = text.find(pattern)
            if idx == -1:
                side_dict[pos_name] = "不及"
                continue
            block = text[idx:idx+500]
            for line in block.split("\n"):
                if "太过" in line and "☑" in line:
                    side_dict[pos_name] = "太过"
                    break
            else:
                side_dict[pos_name] = "不及"
    chen["step3_positions"] = {"left": left_pos, "right": right_pos}

    # step4 层次
    layers = {}
    depth_map = {"浅": "浮", "中": "中", "不深不浅": "中", "深": "沉", "极深": "沉"}
    for side_key, side_label in [("left", "左"), ("right", "右")]:
        for pos_key, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
            grid_key = f"{side_key}_{pos_key}"
            pattern = f"### {side_label}{pos_label}"
            idx = text.find(pattern)
            if idx == -1:
                layers[grid_key] = "中"
                continue
            block = text[idx:idx+600]
            for line in block.split("\n"):
                if "☑" in line:
                    for abbr, depth in depth_map.items():
                        if abbr in line:
                            layers[grid_key] = depth
                            break
                    if grid_key not in layers:
                        layers[grid_key] = "中"
                    break
            else:
                layers[grid_key] = "中"
    chen["step4_layers"] = layers

    # step5 脉质
    quals = {}
    for side_key, side_label in [("left", "左"), ("right", "右")]:
        for pos_key, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
            grid_key = f"{side_key}_{pos_key}"
            pattern = f"### {side_label}{pos_label}"
            idx = text.find(pattern)
            if idx == -1:
                quals[grid_key] = ""
                continue
            block = text[idx:idx+600]
            core_idx = block.find("核心脉感")
            if core_idx != -1:
                core_block = block[core_idx:core_idx+200]
                found = []
                for q in ["无力", "有力", "弦", "拘急", "管细", "细", "濡", "弱", "微", "软", "硬", "滑", "涩", "紧"]:
                    if f"☑ {q}" in core_block or f"☑{q}" in core_block:
                        found.append(q)
                quals[grid_key] = "".join(found) if found else ""
            if not quals.get(grid_key):
                quals[grid_key] = ""
    chen["step5_qualities"] = quals

    # step6 交叉
    cross = {}
    for key, label in [("left_vs_right_cun", "左寸 vs 右寸"), ("left_vs_right_guan", "左关 vs 右关"),
                        ("left_vs_right_chi", "左尺 vs 右尺")]:
        for line in text.split("\n"):
            if label in line:
                val = line.split("|")[-1].strip() if "|" in line else ""
                cross[key] = val
                break
        else:
            cross[key] = ""
    cross["dual_guan_excess"] = "否"
    cross["dual_chi_collapse"] = "否"
    chen["step6_cross"] = cross

    # symptoms
    symptoms_fields = {}
    table6_idx = text.find("表六：症状补充")
    if table6_idx != -1:
        t6 = text[table6_idx:]
        for line in t6.split("\n"):
            line = line.strip()
            if "主诉" in line and "|" in line:
                symptoms_fields["chief_complaint"] = line.split("|")[1].strip()
            elif "寒热" in line and "☑" in line:
                symptoms_fields["cold_heat"] = line.split("☑")[-1].strip().split("□")[0].strip()
            elif "二便" in line:
                parts = line.split("|")
                if len(parts) > 1:
                    symptoms_fields["stool"] = parts[1].strip()
            elif "舌象" in line:
                symptoms_fields["tongue"] = line.split("**")[1] if "**" in line else line
            elif "疼痛" in line and "|" in line:
                symptoms_fields["pain"] = line.split("|")[1].strip()
            elif "其他" in line and "|" in line:
                symptoms_fields["other"] = line.split("|")[1].strip()
    chen["symptoms"] = symptoms_fields

    return chen


def parse_pulse_string_to_grid(pulse_strs):
    """
    将CLI脉冲字符串解析为脉位网格，用于Track B匹配。
    例如: "左寸浮紧" → {"left_cun": {"trend":"太过","layer":"浮","quality":"紧"}}
    """
    grid = {}
    excess_keywords = ["浮紧", "紧", "弦", "滑", "有力", "洪", "大", "数", "实", "促", "急"]
    deficiency_keywords = ["沉弱", "濡", "弱", "微", "细", "无力", "虚", "迟", "缓", "软", "空"]
    level_map = {"浮": "浮", "中": "中", "沉": "沉"}
    quality_list = ["紧", "弦", "滑", "涩", "濡", "弱", "微", "细", "软", "硬", "空", "有力", "无力", "数", "缓", "促", "急"]

    for ps in pulse_strs:
        ps = ps.strip()
        # 解析：左/右 + 寸/关/尺 + 浮/中/沉? + 脉质
        m = re.match(r'(左|右)(寸|关|尺)(浮|中|沉)?(.+)', ps)
        if not m:
            continue
        side = "left" if m.group(1) == "左" else "right"
        pos_map = {"寸": "cun", "关": "guan", "尺": "chi"}
        pos = pos_map.get(m.group(2), "cun")
        raw_layer = m.group(3) or "中"
        raw_quality = m.group(4)

        layer = level_map.get(raw_layer, "中")
        quality = raw_quality

        # 判断太过/不及
        trend = "不及"  # default
        for kw in excess_keywords:
            if kw in raw_quality:
                trend = "太过"
                break
        if trend == "不及":
            for kw in deficiency_keywords:
                if kw in raw_quality:
                    trend = "不及"
                    break

        key = f"{side}_{pos}"
        grid[key] = {"trend": trend, "layer": layer, "quality": quality}
    return grid


def load_input(args):
    if args.input:
        with open(args.input) as f:
            data = json.load(f)
        # 如果JSON中有pulses字符串列表且没有step3_positions，尝试解析
        if "pulses" in data and "step3_positions" not in data:
            data["pulse_grid"] = parse_pulse_string_to_grid(data["pulses"])
        return data
    elif args.pulses:
        pulses = [p.strip() for p in args.pulses.split(",") if p.strip()]
        symptoms = [s.strip() for s in args.symptoms.split(",") if s.strip()] if args.symptoms else []
        zhiyibang = args.zhiyibang_opts.split() if args.zhiyibang_opts else None
        tongue = args.tongue_opts.split() if args.tongue_opts else None
        md_path = os.path.join(SCRIPT_DIR, "dual_system_form_已填.md")
        chen_input = parse_chen_form_md(md_path)
        # 从CLI脉冲字符串解析脉位网格
        pulse_grid = parse_pulse_string_to_grid(pulses)
        return {
            "pulses": pulses,
            "symptoms": symptoms,
            "zhiyibang_opts": zhiyibang,
            "tongue_opts": tongue,
            "chen_input": chen_input,
            "pulse_grid": pulse_grid
        }
    else:
        print("错误：需要 --input 或 --pulses")
        sys.exit(1)


# ============================================================================
# 2. 轨道A: 八家辨证（复用v3）
# ============================================================================

def run_bajia(pulses, symptoms, zhiyibang_opts=None, tongue_opts=None):
    full_report = differential_diagnosis(pulses, symptoms, zhiyibang_opts, tongue_opts)
    lines = full_report.split("\n")
    bajia_lines = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped in ("二、知医邦28脉量化计算", "三、知医邦舌诊辨证", "九、陈建国仲景阴阳脉法"):
            skip = True
            continue
        if skip and any(stripped.startswith(p) for p in ["三、","四、","五、","六、","七、","八、","九、","十、"]):
            skip = False
            bajia_lines.append(line)
            continue
        if not skip:
            bajia_lines.append(line)
    return "\n".join(bajia_lines)


# ============================================================================
# 3. 轨道B: 陈建国277方签名匹配（v4核心升级）
# ============================================================================

def load_v4_signatures():
    """加载 v4 签名库，返回 formulas dict + meta"""
    if not os.path.exists(V4_SIG_PATH):
        raise FileNotFoundError(f"v4签名库不存在: {V4_SIG_PATH}")
    with open(V4_SIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["meta"], data["formulas"]


def load_interpretation_data():
    """
    从 50方_脉证解读与鉴别_完整采集.md 按方名索引提取解读/鉴别段落。
    返回 dict: {方名: {"interpretation": "解读原文...", "discrimination": "鉴别原文..."}}
    """
    if not os.path.exists(INTERP_PATH):
        return {}

    with open(INTERP_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    index = {}
    # 按 ## 数字. 方名 分割
    sections = re.split(r'\n(?=## \d+\. )', text)

    for sec in sections:
        # 提取方名：## 数字. 方名
        h_match = re.match(r'## \d+\.\s*(.+?)(?:\n|$)', sec)
        if not h_match:
            continue
        name = h_match.group(1).strip()

        # 提取解读段
        interp = ""
        discr = ""
        lines = sec.split("\n")
        in_interp = False
        in_discr = False
        interp_buf = []
        discr_buf = []

        for line in lines:
            if "脉证解读" in line:
                in_interp = True
                in_discr = False
                continue
            if "脉证鉴别" in line:
                in_discr = True
                in_interp = False
                continue
            if in_interp:
                interp_buf.append(line)
            elif in_discr:
                discr_buf.append(line)

        interp = "\n".join(interp_buf).strip()
        discr = "\n".join(discr_buf).strip()
        if interp or discr:
            # 存储完整名称
            index[name] = {"interpretation": interp, "discrimination": discr}
            # 也按纯方名索引（处理"阴虚——肾气丸"等复合名）
            if "——" in name:
                pure_name = name.split("——")[-1].strip()
                if pure_name and pure_name not in index:
                    index[pure_name] = {"interpretation": interp, "discrimination": discr}
            elif "—" in name:
                pure_name = name.split("—")[-1].strip()
                if pure_name and pure_name not in index:
                    index[pure_name] = {"interpretation": interp, "discrimination": discr}

    return index


def match_v4_signature(grid, formula_entry, formula_name):
    """
    v4 四维加权匹配：trend + site + level + quality

    grid: {left_cun: {trend, layer, quality}, ...}
    formula_entry: v4单个方签名 {left: {overall, site, level, quality, detail}, right: {...}}

    返回 (score, details_list)
    """
    score = 0
    details = []

    for side in ["left", "right"]:
        f_side = formula_entry.get(side, {})
        if not f_side:
            continue
        f_overall = f_side.get("overall", "")
        f_site_raw = f_side.get("site", "")
        f_level_raw = f_side.get("level", "")
        f_quality_raw = f_side.get("quality", "")

        # 跳过待补充条目
        if f_overall in ("待补充", "", "正常") or not f_site_raw:
            continue

        # 解析 site：支持 "寸＞关＞尺"、"关尺"、"寸关之间"等形式
        sites = set()
        pos_cn_to_en = {"寸": "cun", "关": "guan", "尺": "chi"}
        if f_site_raw:
            for token in re.split(r'[＞>\s、，/]', f_site_raw):
                token = token.strip()
                if token in pos_cn_to_en:
                    sites.add(pos_cn_to_en[token])

        if not sites:
            continue

        # 对每个site，检查匹配
        for pos in sites:
            grid_key = f"{side}_{pos}"
            if grid_key not in grid:
                continue

            g = grid[grid_key]
            f_trend = f_overall

            # ① trend匹配（太过/不及）: weight 200
            if f_trend == g.get("trend", ""):
                score += 200
                details.append(f"  ✓ {side}{pos}趋势匹配: {f_trend}")

            # ② level匹配（浮/中/沉）: weight 150
            if f_level_raw and g.get("layer"):
                if f_level_raw in g["layer"] or g["layer"] in f_level_raw:
                    score += 150
                    details.append(f"  ✓ {side}{pos}层次匹配: {f_level_raw}≈{g['layer']}")
                # 部分匹配：如 "浮" in "浮+沉" 等
                elif f_level_raw in ("浮", "中", "沉") and f_level_raw == g["layer"]:
                    score += 150
                    details.append(f"  ✓ {side}{pos}层次匹配: {f_level_raw}={g['layer']}")

            # ③ quality匹配（弦/紧/细/濡等）: weight 100
            if f_quality_raw and g.get("quality", ""):
                # 从方剂质量中提取1字符和2字符token（兼容"浮紧"→{"浮","紧","浮紧"}）
                f_qual_1 = set(re.findall(r'[\u4e00-\u9fff]', f_quality_raw))
                f_qual_2 = set(re.findall(r'[\u4e00-\u9fff]{2}', f_quality_raw))
                f_qual_tokens = f_qual_1 | f_qual_2
                g_qual = g["quality"]
                g_qual_tokens = set(re.findall(r'[\u4e00-\u9fff]{1,2}', g_qual))
                matched_quals = f_qual_tokens & g_qual_tokens
                if matched_quals:
                    score += 100 * len(matched_quals)
                    details.append(f"  ✓ {side}{pos}脉质匹配: {','.join(matched_quals)}")

    # ④ 双侧同时有信息的方剂加分（更完整）
    if (formula_entry.get("left", {}).get("overall") not in ("待补充", "", None) and
        formula_entry.get("right", {}).get("overall") not in ("待补充", "", None)):
        score += 50
        details.append("  ✓ 双侧脉证完整签名（+50）")

    # ⑤ 鉴别要点特殊加分：如果grid中有quality匹配到鉴别要点关键词
    left_detail = formula_entry.get("left", {}).get("鉴别要点", "")
    if left_detail:
        for side in ["left", "right"]:
            for pos in ["cun", "guan", "chi"]:
                g_qual = grid.get(f"{side}_{pos}", {}).get("quality", "")
                if g_qual and any(kw in left_detail for kw in re.findall(r'[\u4e00-\u9fff]{1,2}', g_qual)):
                    score += 30
                    break

    return score, details


def run_chen_jianguo_v4(chen_data, override_grid=None):
    """v4版陈建国辨证：277方四维匹配 + 解读/鉴别集成"""
    if not chen_data:
        return "无勾选表B数据，无法运行陈建国独立辨证。"

    meta, formulas = load_v4_signatures()
    interp_index = load_interpretation_data()

    overall = chen_data.get("step1_overall", "")
    method = chen_data.get("step2_direction", {}).get("method", "")
    quadrant = chen_data.get("step2_direction", {}).get("quadrant", "")
    left = chen_data.get("step3_positions", {}).get("left", {})
    right = chen_data.get("step3_positions", {}).get("right", {})
    layers = chen_data.get("step4_layers", {})
    quals = chen_data.get("step5_qualities", {})

    # 构建脉位网格
    grid = {}
    for side in ["left", "right"]:
        src = left if side == "left" else right
        for part in ["cun", "guan", "chi"]:
            key = f"{side}_{part}"
            grid[key] = {
                "trend": src.get(part, ""),
                "layer": layers.get(key, ""),
                "quality": quals.get(key, "")
            }

    # 如果提供了CLI脉冲网格，用其覆盖对应位置（priority: CLI > form）
    if override_grid:
        for k, v in override_grid.items():
            if k in grid:
                grid[k] = v

    # 逐方匹配
    scored = []
    for fname, fentry in formulas.items():
        score, details = match_v4_signature(grid, fentry, fname)
        if score > 0:
            # 提取治法与病机
            treatment = fentry.get("治法", fentry.get("附录分类", ""))
            patho = fentry.get("病机", "")
            chapter = fentry.get("chapter", "")

            # 双侧脉证摘要
            l_summary = fentry.get("left", {}).get("detail", fentry.get("left", {}).get("overall", ""))
            r_summary = fentry.get("right", {}).get("detail", fentry.get("right", {}).get("overall", ""))

            # 解读/鉴别引用
            interp_ref = interp_index.get(fname, {})

            scored.append({
                "name": fname,
                "score": score,
                "treatment": treatment,
                "pathomechanism": patho,
                "chapter": chapter,
                "left_summary": l_summary[:120] if l_summary else "",
                "right_summary": r_summary[:120] if r_summary else "",
                "details": details,
                "interpretation": interp_ref.get("interpretation", ""),
                "discrimination": interp_ref.get("discrimination", ""),
                "completeness": fentry.get("信息完整度", "高"),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # 生成报告
    report = []
    report.append("=" * 70)
    report.append(f"【陈建国独立辨证 v4.0 — 277方双侧脉证签名匹配】")
    report.append(f"签名库版本：{meta.get('version','4.0')} | 总方数：{meta.get('total_formulas',277)}")
    report.append("=" * 70)
    report.append("")
    report.append("## 六步定向")
    report.append(f"总体：{overall}  |  大法：{method}  |  四象：{quadrant}")
    report.append(f"三部：左{{寸:{left.get('cun')},关:{left.get('guan')},尺:{left.get('chi')}}}  右{{寸:{right.get('cun')},关:{right.get('guan')},尺:{right.get('chi')}}}")
    report.append(f"层次：左{{寸:{layers.get('left_cun')},关:{layers.get('left_guan')},尺:{layers.get('left_chi')}}}  右{{寸:{layers.get('right_cun')},关:{layers.get('right_guan')},尺:{layers.get('right_chi')}}}")
    report.append(f"脉质：左{{寸:{quals.get('left_cun')},关:{quals.get('left_guan')},尺:{quals.get('left_chi')}}}  右{{寸:{quals.get('right_cun')},关:{quals.get('right_guan')},尺:{quals.get('right_chi')}}}")
    report.append("")

    # Top25 匹配结果（简要表）
    report.append("## 匹配结果 Top25")
    report.append("")
    report.append("| 排名 | 方剂 | 评分 | 治法 | 病机 | 完整度 |")
    report.append("|------|------|------|------|------|--------|")
    for i, s in enumerate(scored[:25]):
        report.append(f"| {i+1} | **{s['name']}** | {s['score']} | {s['treatment']} | {s['pathomechanism'][:30]} | {s['completeness']} |")
    report.append("")

    # Top10 详细（含脉证解读、鉴别摘录）
    report.append("## Top10 详细分析（含脉证解读与鉴别）")
    report.append("")

    for i, s in enumerate(scored[:10]):
        report.append(f"### {i+1}. {s['name']}（{s['score']}分）")
        report.append("")
        report.append(f"**治法**：{s['treatment']}")
        report.append(f"**病机**：{s['pathomechanism']}")
        report.append(f"**章节**：{s['chapter']}")
        report.append(f"**左脉**：{s['left_summary']}")
        report.append(f"**右脉**：{s['right_summary']}")
        report.append("")

        # 匹配细节
        report.append("**匹配维度**：")
        for d in s["details"][:8]:
            report.append(d)
        report.append("")

        # 脉证解读引用（如果存在）
        if s["interpretation"]:
            interp_text = s["interpretation"]
            # 截取关键前300字
            if len(interp_text) > 300:
                interp_text = interp_text[:300] + "……（见完整采集）"
            report.append(f"**脉证解读**：")
            report.append(f"```")
            report.append(interp_text)
            report.append(f"```")
            report.append("")

        # 脉证鉴别引用
        if s["discrimination"]:
            discr_text = s["discrimination"]
            if len(discr_text) > 300:
                discr_text = discr_text[:300] + "……（见完整采集）"
            report.append(f"**脉证鉴别**：")
            report.append(f"```")
            report.append(discr_text)
            report.append(f"```")
            report.append("")

        report.append("---")
        report.append("")

    # 统计
    total_hit = len(scored)
    high_conf = sum(1 for s in scored if s["score"] >= 600)
    mid_conf = sum(1 for s in scored if 300 <= s["score"] < 600)
    report.append(f"**匹配统计**：共命中 {total_hit}/{meta.get('total_formulas',277)} 方 | "
                  f"高置信度（≥600分）：{high_conf}方 | 中置信度（300-599分）：{mid_conf}方")
    report.append("")

    return "\n".join(report), scored


# ============================================================================
# 4. 外部方剂脉证参考
# ============================================================================

def load_external_signatures():
    """加载 external_pulse_signatures.md"""
    if not os.path.exists(EXTERNAL_PATH):
        return ""
    with open(EXTERNAL_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================================
# 5. 交叉验证（v4增强版）
# ============================================================================

def cross_validate_v4(bajia_report, chen_report, chen_scored, symptoms, pulses_str=""):
    """v4增强交叉验证 —— 含解读/鉴别深度对比"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sep = "=" * 70
    lines = []

    # 解析八家报告
    bajia_sections = {}
    current_section = None
    section_lines = []
    section_marks = {
        "【零·根本层】": "张仲景",
        "一、姚梅龄": "姚梅龄",
        "四、胡希恕": "胡希恕",
        "五、张锡纯": "张锡纯",
        "六、刘渡舟": "刘渡舟",
        "七、曹颖甫": "曹颖甫",
        "八、郑钦安": "郑钦安",
        "九、黄元御": "黄元御",
        "十、方证匹配": "方证匹配",
    }

    for line in bajia_report.split("\n"):
        matched = False
        for mark, name in section_marks.items():
            if mark in line:
                if current_section and section_lines:
                    bajia_sections[current_section] = "\n".join(section_lines)
                current_section = name
                section_lines = [line.strip()]
                matched = True
                break
        if not matched and current_section:
            section_lines.append(line.strip())
    if current_section and section_lines:
        bajia_sections[current_section] = "\n".join(section_lines)

    def extract_first_match(text, patterns):
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0).strip()
        return ""

    def extract_key_line(text, keywords):
        """从多行文本中提取包含关键词的首个有意义行"""
        for line in text.split("\n"):
            line = line.strip()
            # 跳过标题行和空行
            if not line or line.startswith("=") or line.startswith("---") or line.startswith("#"):
                continue
            if len(line) < 8:
                continue
            if any(l in line for l in ["体系：", "诊断", "分析", "辨证"]):
                continue
            for kw in keywords:
                if kw in line:
                    return line[:120]
        return ""

    zzj_conclusion = extract_key_line(bajia_sections.get("张仲景", ""),
        ["六经归属", "治则大法", "太阳病", "少阴病", "阳明病", "厥阴病"])
    hu_conclusion = extract_key_line(bajia_sections.get("胡希恕", ""),
        ["方证检索", "桂枝", "麻黄", "柴胡", "六经定位", "命中"])
    zhangxi_conclusion = extract_key_line(bajia_sections.get("张锡纯", ""),
        ["升陷汤", "镇肝", "大气", "升降"])
    liu_conclusion = extract_key_line(bajia_sections.get("刘渡舟", ""),
        ["方证相对", "辨证知机", "苓桂", "水证", "接轨", "气化"])
    cao_conclusion = extract_key_line(bajia_sections.get("曹颖甫", ""),
        ["方证匹配", "原方率", "仲景方"])
    zhengqin_conclusion = extract_key_line(bajia_sections.get("郑钦安", ""),
        ["阳虚", "阴虚", "扶阳", "阴阳"])
    huang_conclusion = extract_key_line(bajia_sections.get("黄元御", ""),
        ["中气", "周流", "土枢", "湿"])

    fz_top = []
    fz_text = bajia_sections.get("方证匹配", "")
    for m in re.finditer(r"(\d+)\.\s*(\S+)\s*\((\d+)分\)|Top(\d+).*?:.*?(\S+)", fz_text):
        fz_top.append(m.group(0).strip())
    if not fz_top:
        for line in fz_text.split("\n"):
            if re.match(r"^\s*\d+[\.\)]\s", line):
                fz_top.append(line.strip()[:80])
                if len(fz_top) >= 8:
                    break

    # 解析陈建国Top25
    chen_top_names = [s["name"] for s in chen_scored[:25]]
    chen_score_map = {s["name"]: s["score"] for s in chen_scored}

    # 会合点
    name_map = {
        "乌梅丸": ["乌梅丸"], "四逆汤": ["四逆汤", "通脉四逆汤"],
        "真武汤": ["真武汤", "附子汤"], "小柴胡汤": ["小柴胡汤", "柴胡桂枝汤"],
        "四逆散": ["四逆散"], "大柴胡汤": ["大柴胡汤"],
        "当归四逆汤": ["当归四逆汤", "当归四逆加吴茱萸生姜汤"],
        "肾气丸": ["肾气丸", "八味肾气丸"], "苓桂术甘汤": ["苓桂术甘汤"],
        "升陷汤": ["升陷汤"], "半夏泻心汤": ["半夏泻心汤"],
        "半夏厚朴汤": ["半夏厚朴汤"], "黄连阿胶汤": ["黄连阿胶汤"],
        "麻黄细辛附子汤": ["麻黄细辛附子汤", "麻黄附子细辛汤"],
        "吴茱萸汤": ["吴茱萸汤"],
    }

    bajia_formulas = []
    for name, aliases in name_map.items():
        for alias in aliases:
            if alias in bajia_report:
                bajia_formulas.append(name)
                break
    for item in fz_top:
        for name, aliases in name_map.items():
            for alias in aliases:
                if alias in item and name not in bajia_formulas:
                    bajia_formulas.append(name)
                    break

    convergence = []
    for name in bajia_formulas:
        if name in chen_top_names:
            score = chen_score_map.get(name, 0)
            stars = "★★★" if score >= 600 else "★★☆" if score >= 300 else "★☆☆"
            # 补充解读/鉴别来源
            source = "八家多体系 + v4脉位签名"
            convergence.append((name, score, stars, source))

    directional = []
    if "升陷汤" in bajia_formulas:
        for s in chen_scored[:10]:
            if "升法" in s.get("treatment", ""):
                directional.append(("升陷汤·升法方向", "★★☆", f"八家张锡纯升陷汤 ↔ 陈建国{s['name']}升法定向一致"))
                break

    convergence.sort(key=lambda x: x[1], reverse=True)

    # 分叉点
    divergence = []
    for name in bajia_formulas:
        if name not in chen_top_names:
            reason = ""
            if "小柴胡" in name:
                reason = "（陈建国277方仍含小柴胡，但v4双侧脉证条件不满足）"
            elif "大柴胡" in name:
                reason = "（陈建国需总体太过方入选，当前总体不及→拒入）"
            divergence.append((name, reason))

    # 单向点：仅陈建国有
    chen_only = [(s["name"], s["score"], s.get("interpretation", "")[:80])
                 for s in chen_scored[:5] if s["name"] not in bajia_formulas]

    # 提取姚梅龄结论
    yaomei_text = bajia_sections.get("姚梅龄", "")
    yao_pulses = re.findall(r"■\s*(\S+脉)", yaomei_text)
    yao_conclusion = "、".join(yao_pulses[:6]) if yao_pulses else ""

    # ========== 提取各体系方剂 ==========
    def extract_formulas(text, top_n=5):
        """从文本中提取方剂名及分值"""
        found = []
        for m in re.finditer(r'([\u4e00-\u9fff]+汤|[\u4e00-\u9fff]+丸|[\u4e00-\u9fff]+散|[\u4e00-\u9fff]+丹)\s*[（(](\d+)\s*分[）)]', text):
            found.append((m.group(1), int(m.group(2))))
        for m in re.finditer(r'→\s*(?:方[：:]?\s*)?([\u4e00-\u9fff]+汤|[\u4e00-\u9fff]+丸|[\u4e00-\u9fff]+散)', text):
            name = m.group(1)
            if not any(f[0] == name for f in found):
                found.append((name, 0))
        return found[:top_n]

    def extract_basis(text, max_len=200):
        """提取辨证根据"""
        basis_lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("---"):
                continue
            if any(kw in line for kw in ["六经归属", "治则", "原文", "症候", "按语", "诊断意义",
                                           "核心", "准则", "方证匹配", "Top", "匹配度"]):
                basis_lines.append(line[:120])
            if len("".join(basis_lines)) > max_len:
                break
        return "; ".join(basis_lines[:3]) if basis_lines else ""

    zzj_full = bajia_sections.get("张仲景", "")
    yao_full = bajia_sections.get("姚梅龄", "")
    hu_full = bajia_sections.get("胡希恕", "")
    zhangxi_full = bajia_sections.get("张锡纯", "")
    liu_full = bajia_sections.get("刘渡舟", "")
    cao_full = bajia_sections.get("曹颖甫", "")
    zhengqin_full = bajia_sections.get("郑钦安", "")
    huang_full = bajia_sections.get("黄元御", "")
    fz_full = bajia_sections.get("方证匹配", "")

    # 方证匹配段提取方剂
    fz_formulas = []
    for line in fz_full.split("\n"):
        m = re.search(r'→\s*方[：:]\s*([\u4e00-\u9fff]+(?:汤|丸|散|丹))', line)
        if m:
            name = m.group(1)
            if name not in [f[0] for f in fz_formulas]:
                fz_formulas.append((name, 0))
        m2 = re.search(r'(\d+)\.\s*【(.+?)】', line)
        if m2:
            fz_formulas.append((f"【{m2.group(2)}】", 0))

    # ========== 组装报告 ==========
    lines.append(sep)
    lines.append(f"【双轨辨证独立报告 v4.0 — 277方签名库】")
    lines.append(f"生成时间：{now}")
    lines.append(sep)
    lines.append("")

    # 脉象输入
    lines.append("## 零·脉象输入")
    lines.append("")
    lines.append(f"```\n{pulses_str}\n```")
    if symptoms:
        lines.append(f"症状：{'、'.join(symptoms)}")
    lines.append("")

    # 各体系独立输出
    systems = [
        ("张仲景（本经·六经定纲）", zzj_full,
         [r"六经归属[：:].*", r"治则大法[：:].*", r"太阳.*病", r"原文[：:].*"],
         ["汗法", "麻黄汤", "桂枝汤", "下法", "和法"]),
        ("姚梅龄（脉象分析）", yao_full,
         [r"■\s*\S+脉", r"脉象.*结论", r"诊断意义"],
         []),
        ("胡希恕（六经八纲·方证）", hu_full,
         [r"方证.*检索", r"六经定位", r"桂枝.*汤.*\d+分"],
         []),
        ("张锡纯（升降辨证）⭐", zhangxi_full,
         [r"升陷汤.*升", r"镇肝.*降", r"大气下陷", r"升降"],
         ["升陷汤", "镇肝熄风汤", "参赭镇气汤"]),
        ("刘渡舟（十论·气化）", liu_full,
         [r"方证相对", r"辨证知机", r"苓桂", r"接轨"],
         []),
        ("曹颖甫（方证对应）", cao_full,
         [r"原方率", r"方证匹配", r"仲景方"],
         []),
        ("郑钦安（阴阳辨证）", zhengqin_full,
         [r"阳虚", r"阴虚", r"扶阳抑阴"],
         ["四逆汤", "白通汤", "理中汤"]),
        ("黄元御（一气周流）", huang_full,
         [r"中气", r"周流", r"土枢", r"湿"],
         ["黄芽汤", "天魂汤", "地魄汤"]),
    ]

    section_num = 1
    for label, full_text, conclusion_patterns, default_formulas in systems:
        lines.append(f"## {section_num}、{label}")
        lines.append("")

        # 结论
        conclusion = ""
        for pat in conclusion_patterns:
            m = re.search(pat, full_text)
            if m:
                conclusion = m.group(0).strip()[:150]
                break
        if not conclusion:
            for line in full_text.split("\n"):
                line = line.strip()
                if line and len(line) > 15 and not line.startswith("=") and not line.startswith("---") \
                   and not line.startswith("#") and "体系" not in line[:4] and "辨证" not in line[:4]:
                    conclusion = line[:150]
                    break

        lines.append(f"**辨证结论**：{conclusion if conclusion else '（症状不足，未触发）'}")
        lines.append("")

        # 推荐方剂
        formulas = extract_formulas(full_text)
        if not formulas and default_formulas:
            formulas = [(f, 0) for f in default_formulas[:3]]

        if formulas:
            lines.append("**推荐方剂**：")
            lines.append("")
            lines.append("| 方剂 | 评分/依据 |")
            lines.append("|------|-----------|")
            for fname, score in formulas[:5]:
                if score > 0:
                    lines.append(f"| {fname} | {score}分 |")
                else:
                    lines.append(f"| {fname} | 体系指向 |")
            lines.append("")

        # 辨证根据
        basis = extract_basis(full_text)
        if basis:
            lines.append(f"**辨证根据**：{basis}")
            lines.append("")

        section_num += 1

    # 方证匹配（跨体系）
    if fz_formulas:
        lines.append(f"## {section_num}、方证匹配（跨体系综合）")
        lines.append("")
        lines.append("**推荐方剂**：")
        lines.append("")
        for fname, _ in fz_formulas[:8]:
            lines.append(f"- {fname}")
        lines.append("")

        # 提取匹配根据
        fz_basis = extract_basis(fz_full, 300)
        if fz_basis:
            lines.append(f"**辨证根据**：{fz_basis}")
            lines.append("")
        section_num += 1

    # 陈建国 v4
    lines.append(f"## {section_num}、陈建国 v4（277方脉位签名）")
    lines.append("")

    # 六步定向
    for line in chen_report.split("\n"):
        line_stripped = line.strip()
        if any(kw in line_stripped for kw in ["总体：", "大法：", "四象：", "三部：", "层次：", "脉质："]):
            lines.append(f"> {line_stripped}")
    lines.append("")

    lines.append("**推荐方剂（Top10）**：")
    lines.append("")
    lines.append("| 排名 | 方剂 | 评分 | 治法 | 病机 |")
    lines.append("|------|------|------|------|------|")
    for i, s in enumerate(chen_scored[:10]):
        pm = s.get("pathomechanism", "")[:25]
        lines.append(f"| {i+1} | **{s['name']}** | {s['score']} | {s['treatment'][:16]} | {pm} |")
    lines.append("")

    # 选取Top2展示根据
    for s in chen_scored[:2]:
        interp = s.get("interpretation", "")
        if interp and len(interp) > 20:
            lines.append(f"**{s['name']} 辨证根据**：{interp[:200]}...")
            lines.append("")

    section_num += 1

    # 等待分析
    lines.append("---")
    lines.append(f"## {section_num}、待分析")
    lines.append("")
    lines.append("以上为各体系独立输出。请结合临床四诊合参，逐条讨论。")
    lines.append("")

    # 底注
    lines.append("---")
    lines.append("> **v4.0 签名库**：277方（50方主节 + 鉴别段提取 + 附录），四维匹配（趋势+层次+部位+脉质）。")
    lines.append("> **输出原则**：各体系独立辨证，不自动合并——合并分析由医者完成。")

    return "\n".join(lines)


# ============================================================================
# 6. 主入口
# ============================================================================

def main():
    args = parse_cli_args()
    data = load_input(args)
    output_dir = args.output_dir or SCRIPT_DIR
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 提取脉象/症状
    if args.input and "pulses" not in data:
        pulses_raw = data.get("step3_positions", {})
        sym_dict = data.get("symptoms", {})
        sym_parts = []
        for k in ["chief_complaint", "cold_heat", "sweat", "thirst", "stool", "urine",
                   "chest_abdomen", "head", "pain", "other", "tongue"]:
            v = sym_dict.get(k, "")
            if isinstance(v, str) and v.strip():
                sym_parts.append(v.strip())
            elif isinstance(v, bool) and v:
                sym_parts.append(k)
        symptoms = sym_parts if sym_parts else [sym_dict.get("chief_complaint", "")]
        pulses = []
        for side_key, side_data in [("left", pulses_raw.get("left", {})), ("right", pulses_raw.get("right", {}))]:
            for pos, trend in side_data.items():
                layer = data.get("step4_layers", {}).get(f"{side_key}_{pos}", "")
                pulses.append(f"{'左' if side_key=='left' else '右'}{pos}{layer}取{'弦' if trend=='太过' else '无力'}")
    else:
        pulses = data.get("pulses", [])
        symptoms = data.get("symptoms", [])

    zhiyibang = data.get("zhiyibang_opts")
    tongue = data.get("tongue_opts")
    chen_data = data if (args.input and "step1_overall" in data) else data.get("chen_input")

    print(f"v4.0 双轨辨证流水线启动")
    print(f"  签名库：formula_pulse_bilateral_v4.json (277方)")
    print(f"  输入脉象：{pulses}")
    print(f"  输入症状：{symptoms}")
    print()

    # === 轨道A ===
    print("[轨道A] 运行八家辨证...")
    bajia_report = run_bajia(pulses, symptoms, zhiyibang, tongue)
    bajia_path = os.path.join(output_dir, f"bajia_report_v4_{now}.txt")
    with open(bajia_path, "w") as f:
        f.write(bajia_report)
    print(f"  → {bajia_path}")

    # === 轨道B v4 ===
    print("[轨道B] 运行陈建国 v4.0 独立辨证（277方）...")
    pulse_grid = data.get("pulse_grid")
    chen_report, chen_scored = run_chen_jianguo_v4(chen_data, override_grid=pulse_grid)
    chen_path = os.path.join(output_dir, f"chen_report_v4_{now}.txt")
    with open(chen_path, "w") as f:
        f.write(chen_report)
    print(f"  → {chen_path}")

    # === 交叉验证 v4 ===
    print("[交叉] 生成双轨独立辨证报告 v4.0...")
    pulses_str = ", ".join(pulses) if pulses else ""
    cross_report = cross_validate_v4(bajia_report, chen_report, chen_scored, symptoms, pulses_str)
    cross_path = os.path.join(output_dir, f"bajia_chen_independent_v4_{now}.txt")
    with open(cross_path, "w") as f:
        f.write(cross_report)
    print(f"  → {cross_path}")

    print()
    print("=" * 50)
    print("v4.0 双轨辨证流水线完成。")
    print(f"  1. 八家辨证    : {bajia_path}")
    print(f"  2. 陈建国v4  : {chen_path}")
    print(f"  3. 交叉验证v4  : {cross_path}")


if __name__ == "__main__":
    main()
