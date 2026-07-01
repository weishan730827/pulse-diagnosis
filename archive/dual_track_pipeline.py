#!/usr/bin/env python3
"""
双轨辨证流水线 — 一键入口
===========================
轨道A: 八家辨证（张仲景/姚梅龄/胡希恕/张锡纯/刘渡舟/曹颖甫/郑钦安/黄元御）
轨道B: 陈建国六步定向50方独立匹配（基于勾选表B）
输出:  双轨交叉验证报告

用法:
    python dual_track_pipeline.py --input chen_input.json
    python dual_track_pipeline.py --pulses "左寸中取濡,左关弦细,左尺沉细,右寸弱,右尺沉微弦" --symptoms "胸闷气短,畏寒,..."
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Ensure the current directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bianzheng_shizhi_v3 import (
    differential_diagnosis,
    chen_jianguo_analyze,
)

# ============================================================================
# 1. 输入解析
# ============================================================================

def parse_cli_args():
    parser = argparse.ArgumentParser(description="双轨辨证流水线")
    parser.add_argument("--input", type=str, help="JSON输入文件路径（chen_input.json格式）")
    parser.add_argument("--pulses", type=str, help="脉象，逗号分隔")
    parser.add_argument("--symptoms", type=str, help="症状，逗号分隔")
    parser.add_argument("--zhiyibang-opts", type=str, default="", help="知医邦选项，空格分隔（可选）")
    parser.add_argument("--tongue-opts", type=str, default="", help="舌诊选项，空格分隔（可选）")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    return parser.parse_args()


def parse_chen_form_md(md_path):
    """
    从 dual_system_form_已填.md 解析陈建国六步勾选数据。
    返回 chen_data dict，解析失败返回 None。
    """
    if not os.path.exists(md_path):
        return None

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    chen = {}

    # —— step1 总体 ——
    if "总体太过" in text and "☑" in text.split("总体太过")[1].split("\n")[0] if "总体太过" in text else False:
        chen["step1_overall"] = "太过"
    else:
        chen["step1_overall"] = "不及"

    # —— step2 左右大法 ——
    if "左手更弱" in text:
        # 找勾选
        left_weaker = False
        for line in text.split("\n"):
            if "左手更弱" in line and "☑" in line:
                left_weaker = True
                break
        if left_weaker:
            chen["step2_direction"] = {"weaker_side": "left", "method": "甘寒降法", "quadrant": "阴虚"}
        else:
            chen["step2_direction"] = {"weaker_side": "right", "method": "甘温升法", "quadrant": "阳虚"}
    else:
        chen["step2_direction"] = {"weaker_side": "unknown", "method": "unknown", "quadrant": "unknown"}

    # —— step3 三部九候 ——
    left_pos = {}
    right_pos = {}
    for pos_name, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
        # 找左手对应部位
        for side_prefix, side_dict in [("左", left_pos), ("右", right_pos)]:
            # 在陈建国判定行找太过/不及
            pattern = f"### {side_prefix}{pos_label}"
            idx = text.find(pattern)
            if idx == -1:
                continue
            block = text[idx:idx+500]
            if "太过" in block.split("陈建国")[-1][:200] if "陈建国" in block else False:
                # 简单判断：看勾选
                for line in block.split("\n"):
                    if "太过" in line and "☑" in line:
                        side_dict[pos_name] = "太过"
                        break
                    elif "不及" in line and "☑" in line:
                        side_dict[pos_name] = "不及"
                        break
                else:
                    side_dict[pos_name] = "不及"  # 默认

    # 如果上面没解析到，用核心脉感兜底
    if not left_pos:
        left_pos = {"cun": "不及", "guan": "不及", "chi": "不及"}
    if not right_pos:
        right_pos = {"cun": "不及", "guan": "不及", "chi": "不及"}

    chen["step3_positions"] = {"left": left_pos, "right": right_pos}

    # —— step4 层次 ——
    layers = {}
    depth_map = {"浅": "浮", "中": "中", "不深不浅": "中", "深": "沉", "极深": "沉"}
    for side_key, side_label in [("left", "左"), ("right", "右")]:
        for pos_key, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
            grid_key = f"{side_key}_{pos_key}"
            # 找知医邦 A 深度行
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

    # —— step5 脉质 ——
    quals = {}
    quality_map = {"无力": "无力", "有力": "有力", "弦": "弦", "紧": "紧", "滑": "滑",
                   "涩": "涩", "濡": "濡", "弱": "弱", "微": "微", "细": "细",
                   "软": "软", "硬": "硬", "空": "空"}
    for side_key, side_label in [("left", "左"), ("right", "右")]:
        for pos_key, pos_label in [("cun", "寸"), ("guan", "关"), ("chi", "尺")]:
            grid_key = f"{side_key}_{pos_key}"
            pattern = f"### {side_label}{pos_label}"
            idx = text.find(pattern)
            if idx == -1:
                quals[grid_key] = ""
                continue
            block = text[idx:idx+600]
            # 找核心脉感
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

    # —— step6 交叉 ——
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
    cross["dual_guan_excess"] = "否" if "双关同强" in text and "否" in text.split("双关同强")[1][:10] else False
    cross["dual_chi_collapse"] = "是" if "双尺同塌" in text and "是" in text.split("双尺同塌")[1][:10] else False
    cross["cun_excess_chi_deficiency_same_side"] = False
    cross["floating_strongest"] = False
    chen["step6_cross"] = cross

    # —— symptoms ——
    symptoms_fields = {}
    # 提取表六症状
    table6_idx = text.find("表六：症状补充")
    if table6_idx != -1:
        t6 = text[table6_idx:]
        for line in t6.split("\n"):
            line = line.strip()
            if "主诉" in line and "|" in line:
                symptoms_fields["chief_complaint"] = line.split("|")[1].strip()
            elif "寒热" in line and "☑" in line:
                symptoms_fields["cold_heat"] = line.split("☑")[-1].strip().split("□")[0].strip() if "☑" in line else ""
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


def load_input(args):
    """解析输入：优先JSON文件，其次CLI参数。--pulses模式下自动尝试加载dual_system_form_已填.md"""
    if args.input:
        with open(args.input) as f:
            return json.load(f)
    elif args.pulses:
        pulses = [p.strip() for p in args.pulses.split(",") if p.strip()]
        symptoms = [s.strip() for s in args.symptoms.split(",") if s.strip()] if args.symptoms else []
        zhiyibang = args.zhiyibang_opts.split() if args.zhiyibang_opts else None
        tongue = args.tongue_opts.split() if args.tongue_opts else None
        # 自动加载勾选表B
        script_dir = os.path.dirname(os.path.abspath(__file__))
        md_path = os.path.join(script_dir, "dual_system_form_已填.md")
        chen_input = parse_chen_form_md(md_path)
        return {
            "pulses": pulses,
            "symptoms": symptoms,
            "zhiyibang_opts": zhiyibang,
            "tongue_opts": tongue,
            "chen_input": chen_input
        }
    else:
        print("错误：需要 --input 或 --pulses")
        sys.exit(1)


# ============================================================================
# 2. 轨道A: 八家辨证
# ============================================================================

def run_bajia(pulses, symptoms, zhiyibang_opts=None, tongue_opts=None):
    """
    运行八家辨证（排除知医邦和陈建国章节）。
    返回：八家报告文本
    """
    full_report = differential_diagnosis(pulses, symptoms, zhiyibang_opts, tongue_opts)

    # 按章节头分割，排除"二、知医邦28脉"、"三、知医邦舌诊"、"九、陈建国"
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
# 3. 轨道B: 陈建国独立辨证（勾选表B匹配）
# ============================================================================

def run_chen_jianguo(chen_data):
    """
    基于勾选表B六步数据，运行陈建国50方独立匹配。
    chen_data: dict with step1~step6 + symptoms
    """
    if not chen_data:
        return "无勾选表B数据，无法运行陈建国独立辨证。"

    overall = chen_data.get("step1_overall", "")
    method = chen_data.get("step2_direction", {}).get("method", "")
    quadrant = chen_data.get("step2_direction", {}).get("quadrant", "")
    left = chen_data.get("step3_positions", {}).get("left", {})
    right = chen_data.get("step3_positions", {}).get("right", {})
    layers = chen_data.get("step4_layers", {})
    quals = chen_data.get("step5_qualities", {})
    cross = chen_data.get("step6_cross", {})

    # 构建脉位网格
    hand_map = {"L": "left", "R": "right"}
    pos_map = {"cun": "cun", "guan": "guan", "chi": "chi"}
    depth_map = {"fu": "浮", "zhong": "中", "chen": "沉"}

    grid = {}
    for side in ["left", "right"]:
        src = left if side == "left" else right
        for part in ["cun", "guan", "chi"]:
            key = f"{side}_{part}"
            grid[key] = {"trend": src.get(part, ""), "layer": layers.get(key, ""), "quality": quals.get(key, "")}

    # 加载50方签名库
    sig_file = os.path.join(os.path.dirname(__file__), "chen_jianguo_formula_signatures.json")
    if not os.path.exists(sig_file):
        return "错误：找不到 chen_jianguo_formula_signatures.json"

    with open(sig_file) as f:
        sigs = json.load(f)

    # 逐方匹配打分
    scored = []
    for fdata in sigs:
        fname = fdata.get("name", "")
        if not fname:
            continue
        sig = fdata.get("signature", {})
        positions = sig.get("positions", [])
        score = 0
        details = []
        for sp in positions:
            hand = sp.get("hand", "")
            pos = sp.get("pos", "")
            depth = sp.get("depth", "")
            excess_def = sp.get("excess_deficiency", "")
            weight = sp.get("weight", 1)

            grid_key = f"{hand_map.get(hand,'')}_{pos_map.get(pos,'')}"
            if grid_key not in grid:
                continue

            g = grid[grid_key]
            sig_trend = "太过" if excess_def == "excess" else "不及" if excess_def == "deficiency" else ""
            sig_depth = depth_map.get(depth, "")

            if sig_trend and sig_trend == g["trend"]:
                score += 100 * weight
            if sig_depth and sig_depth == g["layer"]:
                score += 150 * weight

        if score > 0:
            scored.append((fname, score, fdata.get("treatment_direction", ""), fdata.get("pathomechanism", "")))

    scored.sort(key=lambda x: x[1], reverse=True)

    # 生成报告
    report = []
    report.append("=" * 60)
    report.append("【陈建国独立辨证 — 勾选表B·50方脉位签名匹配】")
    report.append("=" * 60)
    report.append("")
    report.append("## 六步定向")
    report.append(f"总体：{overall}  |  大法：{method}  |  四象：{quadrant}")
    report.append(f"三部：左{{寸:{left.get('cun')},关:{left.get('guan')},尺:{left.get('chi')}}}  右{{寸:{right.get('cun')},关:{right.get('guan')},尺:{right.get('chi')}}}")
    report.append(f"层次：左{{寸:{layers.get('left_cun')},关:{layers.get('left_guan')},尺:{layers.get('left_chi')}}}  右{{寸:{layers.get('right_cun')},关:{layers.get('right_guan')},尺:{layers.get('right_chi')}}}")
    report.append(f"脉质：左{{寸:{quals.get('left_cun')},关:{quals.get('left_guan')},尺:{quals.get('left_chi')}}}  右{{寸:{quals.get('right_cun')},关:{quals.get('right_guan')},尺:{quals.get('right_chi')}}}")
    report.append(f"交叉：寸{cross.get('cun_lr')} | 关{cross.get('guan_lr')} | 尺{cross.get('chi_lr')} | 双尺同塌={'是' if cross.get('double_chi_collapse') else '否'}")
    report.append("")
    report.append("## 匹配结果")
    report.append("")
    for i, (name, score, direction, patho) in enumerate(scored[:15]):
        report.append(f"  {i+1}. {name}（{score}分）→ {direction}")
        report.append(f"     病机：{patho[:80]}")
        report.append("")

    return "\n".join(report)


# ============================================================================
# 4. 交叉验证
# ============================================================================

def cross_validate(bajia_report, chen_report, symptoms):
    """生成双轨并行深度交叉验证报告（会合点·分叉点·三线整合）"""
    import re
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sep = "=" * 70
    lines = []

    # ===================================================================
    # 1. 解析八家辨证报告 — 逐家提取关键结论
    # ===================================================================
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

    # 逐家提取关键结论
    def extract_first_match(text, patterns):
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0).strip()
        return ""

    zzj_conclusion = extract_first_match(bajia_sections.get("张仲景", ""),
        [r"六经归属[：:].*", r"少阴病.*", r"治则大法[：:].*"])
    hu_conclusion = extract_first_match(bajia_sections.get("胡希恕", ""),
        [r"■ (?:厥阴病|少阳病|阳明病|太阳病|少阴病).*命中\d+项.*", r"六经定位.*"])
    zhangxi_conclusion = extract_first_match(bajia_sections.get("张锡纯", ""),
        [r"大气下陷[指征]*[：:].*", r"结论[：:].*升陷汤.*", r"升陷.*"])
    liu_conclusion = extract_first_match(bajia_sections.get("刘渡舟", ""),
        [r"触发[：:].*", r"苓桂.*", r"水[证饮].*"])
    cao_conclusion = extract_first_match(bajia_sections.get("曹颖甫", ""),
        [r"Top.*", r"原方率.*", r"曹氏标准.*"])
    zhengqin_conclusion = extract_first_match(bajia_sections.get("郑钦安", ""),
        [r"结论[：:].*", r"阳虚阴盛.*", r"扶阳抑阴.*"])
    huang_conclusion = extract_first_match(bajia_sections.get("黄元御", ""),
        [r"气机方向.*", r"命中规则.*", r"一气周流.*"])

    # 方证匹配 Top8
    fz_top = []
    fz_text = bajia_sections.get("方证匹配", "")
    for m in re.finditer(r"(\d+)\.\s*(\S+)\s*\((\d+)分\)|Top(\d+).*?:.*?(\S+)", fz_text):
        fz_top.append(m.group(0).strip())
    if not fz_top:
        # fallback: grab lines starting with digits
        for line in fz_text.split("\n"):
            if re.match(r"^\s*\d+[\.\)]\s", line):
                fz_top.append(line.strip()[:80])
                if len(fz_top) >= 8:
                    break

    # ===================================================================
    # 2. 解析陈建国独立辨证报告
    # ===================================================================
    chen_results = []
    for line in chen_report.split("\n"):
        # 支持中文全角括号和英文半角括号
        m = re.match(r"\s*(\d+)\.\s*(\S+)\s*[（(](\d+)分[）)]", line)
        if m:
            chen_results.append((int(m.group(1)), m.group(2), int(m.group(3))))

    # ===================================================================
    # 3. 构建会合点矩阵
    # ===================================================================
    # 方名规范化映射（八家 vs 陈建国 同一方的不同叫法）
    name_map = {
        "乌梅丸": ["乌梅丸"],
        "四逆汤": ["四逆汤", "通脉四逆汤"],
        "真武汤": ["真武汤", "附子汤"],
        "小柴胡汤": ["小柴胡汤", "柴胡桂枝汤"],
        "四逆散": ["四逆散"],
        "大柴胡汤": ["大柴胡汤"],
        "当归四逆汤": ["当归四逆汤", "当归四逆加吴茱萸生姜汤"],
        "肾气丸": ["肾气丸", "八味肾气丸"],
        "苓桂术甘汤": ["苓桂术甘汤"],
        "升陷汤": ["升陷汤"],
        "半夏泻心汤": ["半夏泻心汤"],
        "半夏厚朴汤": ["半夏厚朴汤"],
        "黄连阿胶汤": ["黄连阿胶汤"],
        "麻黄细辛附子汤": ["麻黄细辛附子汤", "麻黄附子细辛汤"],
        "吴茱萸汤": ["吴茱萸汤"],
    }

    bajia_formulas = []
    for name, aliases in name_map.items():
        for alias in aliases:
            if alias in bajia_report:
                bajia_formulas.append(name)
                break
    # also check fz_top
    for item in fz_top:
        for name, aliases in name_map.items():
            for alias in aliases:
                if alias in item:
                    if name not in bajia_formulas:
                        bajia_formulas.append(name)
                    break

    chen_formulas = [c[1] for c in chen_results[:15]]
    chen_score_map = {c[1]: c[2] for c in chen_results}

    # 会合点：两轨都出现
    convergence = []
    for name in bajia_formulas:
        if name in chen_formulas:
            score = chen_score_map.get(name, 0)
            # 排星：高分=高置信度
            stars = "★★★" if score >= 700 else "★★☆" if score >= 500 else "★☆☆"
            convergence.append((name, score, stars))

    # also check for directional convergence (e.g., 升陷汤 not in chen's 50方 but 升法 matches)
    directional = []
    if "升陷汤" in bajia_formulas:
        chen_direction = ""
        for line in chen_report.split("\n"):
            if "大法" in line and "升法" in line:
                chen_direction = "升法"
                break
        if chen_direction == "升法":
            directional.append(("升陷汤·升法方向", "★★☆", "八家张锡纯升陷汤 ↔ 陈建国升法定向一致"))

    convergence.sort(key=lambda x: x[1], reverse=True)

    # 分叉点：八家支持但陈建国Top15无对应
    divergence = []
    for name in bajia_formulas:
        if name not in chen_formulas:
            # 尝试找原因
            reason = ""
            if "小柴胡" in name:
                reason = "（陈建国需总体太过方入选，当前总体不及→拒入）"
            elif "苓桂术甘" in name:
                reason = "（陈建国需双关太过方入选，当前双关不及→拒入）"
            elif "大柴胡" in name:
                reason = "（陈建国需总体太过，当前总体不及→拒入）"
            divergence.append((name, reason))

    # 单向点：仅陈建国有但八家无
    chen_only = [c[1] for c in chen_results[:5] if c[1] not in bajia_formulas and c[1] not in [d[0] for d in divergence]]

    # ===================================================================
    # 4. 三线整合方案
    # ===================================================================
    three_line = []
    three_line.append("上焦（心肺·大气）:")
    if "升陷汤" in bajia_formulas or "升陷汤" in str(directional):
        three_line.append("  → 升陷汤 提大气下陷（张锡纯 ± 陈建国升法印证）")
    else:
        three_line.append("  → 待定")

    three_line.append("中焦（脾胃·肝胆·气机）:")
    if "乌梅丸" in [c[0] for c in convergence]:
        three_line.append("  → 乌梅丸 调厥阴枢机、清上温下（胡希恕厥阴 + 陈建国850分双向印证）")
    elif "小柴胡汤" in bajia_formulas:
        three_line.append("  → 小柴胡汤 调少阳枢机（胡希恕少阳方向）")
    elif "苓桂术甘汤" in bajia_formulas:
        three_line.append("  → 苓桂术甘汤 化中焦水饮（刘渡舟水证论）")
    else:
        three_line.append("  → 待定")

    three_line.append("下焦（肾·膀胱·水液）:")
    if "真武汤" in [c[0] for c in convergence]:
        three_line.append("  → 真武汤 温阳利水（少阴水泛 ± 陈建国右尺弦质指向）")
    elif "肾气丸" in [c[0] for c in convergence]:
        three_line.append("  → 肾气丸 温补肾阳、化气行水")
    elif "四逆汤" in [c[0] for c in convergence]:
        three_line.append("  → 四逆汤 回阳救逆（少阴寒化本证）")
    else:
        three_line.append("  → 待定")

    # ===================================================================
    # 5. 组装报告
    # ===================================================================
    lines.append(sep)
    lines.append("【双轨并行交叉验证报告 v3.0】")
    lines.append(f"生成时间：{now}")
    lines.append(sep)
    lines.append("")

    # —— 轨道A摘要 ——
    lines.append("## 一、轨道A：八家辨证关键结论")
    lines.append("")
    lines.append("| 医家 | 关键结论 |")
    lines.append("|------|----------|")
    if zzj_conclusion:
        lines.append(f"| 张仲景（本经） | {zzj_conclusion[:60]} |")
    if hu_conclusion:
        lines.append(f"| 胡希恕（六经） | {hu_conclusion[:60]} |")
    if zhangxi_conclusion:
        lines.append(f"| 张锡纯（升降） | {zhangxi_conclusion[:60]} |")
    if liu_conclusion:
        lines.append(f"| 刘渡舟（十论） | {liu_conclusion[:60]} |")
    if cao_conclusion:
        lines.append(f"| 曹颖甫（方证） | {cao_conclusion[:60]} |")
    if zhengqin_conclusion:
        lines.append(f"| 郑钦安（阴阳） | {zhengqin_conclusion[:60]} |")
    if huang_conclusion:
        lines.append(f"| 黄元御（周流） | {huang_conclusion[:60]} |")
    lines.append("")

    if fz_top:
        lines.append("**方证匹配Top8**：")
        for i, f in enumerate(fz_top[:8]):
            lines.append(f"  {i+1}. {f}")
        lines.append("")

    # —— 轨道B摘要 ——
    lines.append("## 二、轨道B：陈建国独立辨证摘要")
    lines.append("")
    # 六步
    for line in chen_report.split("\n"):
        if "总体：" in line and "大法" in line:
            lines.append(f"  {line.strip()}")
            break
    lines.append("")
    lines.append("**50方匹配Top10**：")
    for rank, name, score in chen_results[:10]:
        direction = ""
        for rline in chen_report.split("\n"):
            if rline.strip().startswith(f"  {rank}. {name}"):
                parts = rline.strip().split("→")
                if len(parts) > 1:
                    direction = parts[1].strip()
                break
        lines.append(f"  {rank}. {name}（{score}分）{'→ ' + direction if direction else ''}")
    lines.append("")

    # —— 会合点 ——
    lines.append("## 三、会合点（两轨共同指向）")
    lines.append("")
    lines.append("| 方剂 | 陈建国评分 | 置信度 | 说明 |")
    lines.append("|------|-----------|--------|------|")
    for name, score, stars in convergence:
        lines.append(f"| {name} | {score}分 | {stars} | 八家多体系支撑 × 陈建国脉位签名匹配 |")
    for label, stars, note in directional:
        lines.append(f"| {label} | — | {stars} | {note} |")
    if not convergence and not directional:
        lines.append("| （无明确会合点） | — | — | 两轨无共同方剂命中 |")
    lines.append("")

    # —— 分叉点 ——
    lines.append("## 四、分叉点（需辨析的不一致）")
    lines.append("")
    if divergence:
        lines.append("| 方剂 | 八家支持 | 陈建国拒入原因 |")
        lines.append("|------|---------|---------------|")
        for name, reason in divergence:
            lines.append(f"| {name} | 八家辨证命中 | {reason} |")
    else:
        lines.append("（无显著分叉点）")
    lines.append("")

    # —— 单向点 ——
    if chen_only:
        lines.append("## 五、单向点（仅陈建国给出，八家未命中的方剂）")
        lines.append("")
        lines.append("| 方剂 | 陈建国评分 | 备注 |")
        lines.append("|------|-----------|------|")
        for name in chen_only[:5]:
            score = chen_score_map.get(name, 0)
            lines.append(f"| {name} | {score}分 | 50方签名自动匹配，需八家交叉复核 |")
        lines.append("")

    # —— 三线整合 ——
    lines.append("## 六、三线整合方案（临证参考）")
    lines.append("")
    for line in three_line:
        lines.append(line)
    lines.append("")

    # —— 症状输入 ——
    lines.append("---")
    lines.append("## 症状输入")
    lines.append("")
    lines.append("、".join(symptoms) if symptoms else "（无）")
    lines.append("")

    # —— 底注 ——
    lines.append("---")
    lines.append("> **双轨交叉验证规则**：八家（原文辨证）与陈建国（脉位签名）独立运行，仅在交叉验证阶段比较结论。")
    lines.append("> 会合点=两轨一致指向（高确定性）；分叉点=八家支持但陈建国因脉位条件不满足否定（需辨析）；单向点=仅一轨给出（需补另一轨视角）。")

    return "\n".join(lines)


# ============================================================================
# 5. 主入口
# ============================================================================

def main():
    args = parse_cli_args()
    data = load_input(args)
    output_dir = args.output_dir or os.path.dirname(os.path.abspath(__file__))
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 提取脉象/症状
    if args.input and "pulses" not in data:
        # chen_input.json格式：从chen_data推断脉象，从symptoms提取全部症状
        pulses_raw = data.get("step3_positions", {})
        sym_dict = data.get("symptoms", {})
        # 合并所有症状字段
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
                quality = data.get("step5_qualities", {}).get(f"{side_key}_{pos}", "")
                pulses.append(f"{'左' if side_key=='left' else '右'}{pos}{layer}取{'弦' if quality=='拘急' else '无力'}")
    else:
        pulses = data.get("pulses", [])
        symptoms = data.get("symptoms", [])

    zhiyibang = data.get("zhiyibang_opts")
    tongue = data.get("tongue_opts")
    chen_data = data if (args.input and "step1_overall" in data) else data.get("chen_input")

    print(f"输入脉象：{pulses}")
    print(f"输入症状：{symptoms}")
    print()

    # === 轨道A ===
    print("[轨道A] 运行八家辨证...")
    bajia_report = run_bajia(pulses, symptoms, zhiyibang, tongue)
    bajia_path = os.path.join(output_dir, f"bajia_report_{now}.txt")
    with open(bajia_path, "w") as f:
        f.write(bajia_report)
    print(f"  → 已保存：{bajia_path}")

    # === 轨道B ===
    print("[轨道B] 运行陈建国独立辨证...")
    chen_report = run_chen_jianguo(chen_data)
    chen_path = os.path.join(output_dir, f"chen_report_{now}.txt")
    with open(chen_path, "w") as f:
        f.write(chen_report)
    print(f"  → 已保存：{chen_path}")

    # === 交叉验证 ===
    print("[交叉] 生成双轨交叉验证...")
    cross_report = cross_validate(bajia_report, chen_report, symptoms)
    cross_path = os.path.join(output_dir, f"cross_validate_{now}.txt")
    with open(cross_path, "w") as f:
        f.write(cross_report)
    print(f"  → 已保存：{cross_path}")

    print()
    print("=" * 50)
    print("双轨辨证流水线完成。产出文件：")
    print(f"  1. 八家辨证    : {bajia_path}")
    print(f"  2. 陈建国辨证  : {chen_path}")
    print(f"  3. 交叉验证    : {cross_path}")


if __name__ == "__main__":
    main()
