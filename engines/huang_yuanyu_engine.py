#!/usr/bin/env python3
"""
黄元御一气周流辨证匹配引擎 v2
方法：中气为轴→四维为轮→升降方向→方证锁定。
     先判中气（脾升胃降）→再定升降偏颇→最后方药映射。
     不是数左数右，而是看中轴带动四维的连锁关系。
"""

import json
import os
from typing import Dict, List

_OUTPUT_DIR = "/home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output"
CHECKBOX_PATH = os.path.join(_OUTPUT_DIR, "黄元御一气周流辨证勾选表_v1.json")


class HuangYuanYuEngine:
    """黄元御引擎：一气周流，中气→四维→方药"""

    # 六种核心模式（中轴状态 × 四维偏颇 = 方药）
    PATTERNS = {
        "脾虚为主": {
            "desc": "中气不足，脾不升清",
            "chain": "脾虚 → 左路升发无力 → 肝郁/清阳不升 → 湿困",
            "primary": ["苓桂术甘汤（健脾利湿，恢复轴心）"],
            "secondary": {
                "肝": "四逆散（肝郁气滞）",
                "清阳不升": "补中益气汤（升阳举陷）",
                "水湿": "五苓散（利水渗湿）",
                "下寒": "真武汤（温阳利水）",
            },
        },
        "胃逆为主": {
            "desc": "胃气不降，浊阴上逆",
            "chain": "胃逆 → 右路肃降不足 → 肺气不降/心火不下 → 上热",
            "primary": ["旋覆代赭汤（降逆和胃，恢复轴心）"],
            "secondary": {
                "肺": "泻白散（清肺降气）",
                "心": "黄连阿胶汤（交通心肾）",
                "胃火": "白虎汤（清胃降火）",
                "食积": "保和丸（消食导滞）",
            },
        },
        "脾虚胃逆（左右同病）": {
            "desc": "中气溃败，升降俱废",
            "chain": "脾不升 + 胃不降 → 清浊相干 → 上热下寒 → 痰湿内停",
            "primary": ["半夏泻心汤（辛开苦降，恢复斡旋）"],
            "secondary": {
                "上热下寒": "乌梅丸（寒热并用）",
                "痰湿": "二陈汤（化痰和中）",
                "升降不通": "半夏厚朴汤（行气降逆）",
            },
        },
        "食积停滞": {
            "desc": "饮食积滞，中轴受阻",
            "chain": "食积 → 中气不运 → 升降受阻 → 腐浊内生",
            "primary": ["保和丸（消食导滞）"],
            "secondary": {
                "胃逆": "枳实导滞丸（消食降逆）",
                "湿热": "葛根黄芩黄连汤（清利湿热）",
            },
        },
        "清阳不升": {
            "desc": "中气下陷，清阳不升（脾虚的延伸）",
            "chain": "脾虚下陷 → 清气不升 → 头晕/疲倦/泄泻",
            "primary": ["补中益气汤（升阳举陷）"],
            "secondary": {
                "下利": "升阳益胃汤（升阳止泻）",
                "湿困": "苓桂术甘汤（健脾利水）",
            },
        },
        "浊阴不降": {
            "desc": "中气不畅，浊阴不降（胃逆的延伸）",
            "chain": "胃逆不降 → 浊阴上犯 → 腹满/便秘/嗳气",
            "primary": ["调胃承气汤（通降阳明）"],
            "secondary": {
                "肺逆": "苏子降气汤（降气平喘）",
                "水肿": "五皮饮（利水消肿）",
            },
        },
    }

    def __init__(self, checkbox_path: str = CHECKBOX_PATH):
        with open(checkbox_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._id_map: Dict[str, Dict] = {}
        self._build_maps()

    def _build_maps(self):
        for step_key in ["step1_中气轴心", "step2_四维升降", "step3_方药映射"]:
            for section in self.data.get(step_key, {}).get("sections", []):
                for item in section.get("items", []):
                    self._id_map[item["id"]] = {
                        "text": item.get("text", ""),
                        "section_id": section.get("id", ""),
                    }

    def diagnose(self, checked_ids: List[str]) -> Dict:
        """一气周流模式判定"""
        zhongqi: List[str] = []
        left_lu: List[str] = []
        right_lu: List[str] = []
        transition: List[str] = []
        fangzheng: List[str] = []

        for sid in checked_ids:
            item = self._id_map.get(sid)
            if not item:
                continue
            text = item["text"]
            sec = item["section_id"]

            if "A1" in sec:
                zhongqi.append(text)
            elif "B1" in sec:
                left_lu.append(text)
            elif "B2" in sec:
                right_lu.append(text)
            elif "B3" in sec:
                transition.append(text)
            elif "C1" in sec:
                fangzheng.append(text)

        ext_text = " ".join(zhongqi + left_lu + right_lu + transition)

        # --- 中气模式判定（先判中轴） ---
        pattern = self._determine_pattern(zhongqi, transition, ext_text)
        pattern_info = self.PATTERNS.get(pattern, {})

        # --- 四维偏颇 → 细化方证 ---
        formulas = list(pattern_info.get("primary", []))
        secondary_map = pattern_info.get("secondary", {})

        # 遍历四维症状，匹配到 finer grained recommendation
        def _add_if(keyword: str, sub_key: str):
            if keyword in ext_text and sub_key in secondary_map:
                if secondary_map[sub_key] not in formulas:
                    formulas.append(secondary_map[sub_key])

        _add_if("肝", "肝")
        _add_if("清阳不升", "清阳不升")
        if ("头晕" in ext_text and "疲倦" in ext_text):
            _add_if("头晕", "清阳不升")
        if "咳" in ext_text or ("肺" in ext_text and "逆" in ext_text):
            _add_if("肺", "肺")
        if "心" in ext_text or "烦" in ext_text or "失眠" in ext_text:
            _add_if("心", "心")
        _add_if("上热下寒", "上热下寒")
        if "水" in ext_text or "湿" in ext_text or "浮肿" in ext_text:
            _add_if("水", "水湿")
        _add_if("下寒", "下寒")
        _add_if("胃火", "胃火")
        _add_if("食积", "食积")

        return {
            "pattern": pattern,
            "pattern_desc": pattern_info.get("desc", ""),
            "chain": pattern_info.get("chain", ""),
            "zhongqi_items": zhongqi,
            "left_items": left_lu,
            "right_items": right_lu,
            "transition_items": transition,
            "fangzheng_items": fangzheng,
            "formulas": formulas
        }

    def _determine_pattern(self, zhongqi: List[str], transition: List[str], ext_text: str) -> str:
        """根据中轴状态 + 过渡症状判定一气周流模式"""
        has_pixu = any("脾虚" in z for z in zhongqi)
        has_weini = any("胃逆" in z for z in zhongqi)
        has_shiji = any("食积" in z for z in zhongqi)
        has_qingyang = any("清阳不升" in t for t in transition)
        has_zhuoyin = any("浊阴不降" in t for t in transition)
        has_shangrexiehan = any("上热下寒" in t for t in transition)

        # 逐级判定
        if has_pixu and has_weini:
            return "脾虚胃逆（左右同病）"
        if has_shiji:
            return "食积停滞"
        if has_qingyang:
            return "清阳不升"
        if has_zhuoyin:
            return "浊阴不降"
        if has_pixu:
            return "脾虚为主"
        if has_weini:
            return "胃逆为主"
        if has_shangrexiehan:
            return "脾虚胃逆（左右同病）"

        # 无中气信号：靠过渡症状推断
        if "清阳不升" in ext_text:
            return "清阳不升"
        if "浊阴不降" in ext_text:
            return "浊阴不降"

        return "中气待判（请优先勾选中气项）"

    def format_result(self, result: Dict) -> str:
        lines = []
        lines.append("=== 黄元御一气周流辨证结果 ===")
        lines.append(f"一气周流模式: {result['pattern']}")
        lines.append(f"  病机描述: {result['pattern_desc']}")
        lines.append(f"  病机链: {result['chain']}")
        lines.append("")

        if result["zhongqi_items"]:
            lines.append(f"【中气轴心】({len(result['zhongqi_items'])} 项)")
            for t in result["zhongqi_items"]:
                lines.append(f"  ○ {t}")
        if result["left_items"]:
            lines.append(f"\n【左路升发】({len(result['left_items'])} 项)")
            for t in result["left_items"]:
                lines.append(f"  ↗ {t}")
        if result["right_items"]:
            lines.append(f"\n【右路肃降】({len(result['right_items'])} 项)")
            for t in result["right_items"]:
                lines.append(f"  ↘ {t}")
        if result["transition_items"]:
            lines.append(f"\n【过渡症状】({len(result['transition_items'])} 项)")
            for t in result["transition_items"]:
                lines.append(f"  ⇄ {t}")
        if result["formulas"]:
            lines.append(f"\n【推荐方剂】（主方→细化）")
            for i, f in enumerate(result["formulas"]):
                prefix = "★" if i == 0 else "  └"
                lines.append(f"  {prefix} {f}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = HuangYuanYuEngine()
    print(f"已加载 {len(engine._id_map)} 项")

    # 测试1: 脾虚为主 + 肝郁
    print("=" * 60)
    print("测试1: 脾虚→肝郁")
    test1 = ["hyy_zq_pi_xu", "hyy_zl_le_gan_yu",
             "hyy_gd_tan_shi", "hyy_fz_xiang", "hyy_fz_gan_yu"]
    r1 = engine.diagnose(test1)
    print(engine.format_result(r1))

    print()
    print("=" * 60)
    print("测试2: 脾虚胃逆 + 上热下寒")
    test2 = ["hyy_zq_pixu_ni", "hyy_zl_le_gan_yu", "hyy_yl_fe_qi_ni",
             "hyy_gd_bu_tong", "hyy_fz_gan_yu", "hyy_fz_wei_ni"]
    r2 = engine.diagnose(test2)
    print(engine.format_result(r2))
