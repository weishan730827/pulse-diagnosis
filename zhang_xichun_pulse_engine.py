#!/usr/bin/env python3
"""
张锡纯脉诊辨证匹配引擎（恢复版）
核心：勾选表输入 → 172案脉象签名库 → 命中医案+方剂
"""

import json, os, sys, re

DIR = os.path.dirname(os.path.abspath(__file__))

# ============== 术语映射：勾选表ID → 脉象术语 ==============

TERM_MAP = {}  # 由表单自动构建

def build_term_map(form_path):
    """从勾选表JSON构建术语映射"""
    with open(form_path, 'r', encoding='utf-8') as f:
        form = json.load(f)
    
    term_map = {}
    pos_map = {}  # id → (side, position)
    
    # 左侧ID映射
    left_prefixes = {
        'zxc_lc_': ('left', '寸'), 'zxc_lg_': ('left', '关'), 'zxc_lch_': ('left', '尺'),
        'zxc_rc_': ('right', '寸'), 'zxc_rg_': ('right', '关'), 'zxc_rch_': ('right', '尺'),
    }
    
    for step_key in form:
        if not step_key.startswith('step'):
            continue
        for section in form[step_key].get('sections', []):
            for item in section.get('items', []):
                tid = item['id']
                text = item['text']
                # 提取核心术语
                term = text.split('（')[0] if '（' in text else text
                term_map[tid] = term
                
                # 判断侧别和部位
                for prefix, (side, pos) in left_prefixes.items():
                    if tid.startswith(prefix):
                        pos_map[tid] = (side, pos)
                        break
    
    return term_map, pos_map


def parse_checked_ids(checked_ids, term_map, pos_map):
    """解析勾选的ID列表为结构化脉象"""
    result = {
        'overall': [],
        'left': {'寸': [], '关': [], '尺': []},
        'right': {'寸': [], '关': [], '尺': []}
    }
    
    for cid in checked_ids:
        term = term_map.get(cid)
        if not term:
            continue
        
        side_pos = pos_map.get(cid)
        if side_pos:
            side, pos = side_pos
            result[side][pos].append(term)
        else:
            # 总按或症状，放入overall
            result['overall'].append(term)
    
    return result


# ============== 脉象提取（从医案原文） ==============

def extract_pulse_terms(text):
    terms = set()
    patterns = [
        (r'脉\s*弦', '弦'), (r'脉\s*细', '细'), (r'脉\s*滑', '滑'),
        (r'脉\s*涩', '涩'), (r'脉\s*紧', '紧'), (r'脉\s*洪', '洪'),
        (r'脉\s*大', '大'), (r'脉\s*濡', '濡'), (r'脉\s*硬', '硬'),
        (r'脉\s*散', '散'), (r'脉\s*微', '微'), (r'脉\s*弱', '弱'),
        (r'脉\s*虚', '虚'), (r'脉\s*实', '实'), (r'脉\s*长', '长'),
        (r'脉\s*短', '短'), (r'脉\s*芤', '芤'), (r'脉\s*革', '革'),
        (r'脉\s*牢', '牢'), (r'脉\s*浮', '浮'), (r'脉\s*沉', '沉'),
        (r'脉\s*伏', '伏'), (r'脉\s*数', '数'), (r'脉\s*迟', '迟'),
        (r'脉\s*缓', '缓'), (r'脉\s*疾', '疾'),
    ]
    for pat, term in patterns:
        if re.search(pat, text):
            terms.add(term)
    if '有力' in text: terms.add('有力')
    if '无力' in text: terms.add('无力')
    if re.search(r'(结\s*脉|脉\s*结)', text): terms.add('结')
    if re.search(r'(代\s*脉|脉\s*代)', text): terms.add('代')
    return sorted(terms)


def extract_side(text, side):
    markers = {'left': r'(?:左[脉部手]|左手|左[寸关尺])',
               'right': r'(?:右[脉部手]|右手|右[寸关尺])'}
    sentences = re.split(r'[。；]', text)
    results = []
    for s in sentences:
        s = s.strip()
        if '脉' not in s or not re.search(markers[side], s):
            continue
        terms = extract_pulse_terms(s)
        if not terms:
            continue
        site = None
        for pos in ['寸', '关', '尺']:
            if pos in s:
                site = pos; break
        results.append({'text': s[:120], 'terms': terms, 'site': site})
    return results


def extract_overall(text):
    sentences = re.split(r'[。；]', text)
    results = []
    for s in sentences:
        s = s.strip()
        if '脉' not in s or re.search(r'[左右][脉部手]', s):
            continue
        terms = extract_pulse_terms(s)
        if len(terms) >= 2:
            results.append({'text': s[:120], 'terms': terms})
    return results


# ============== 匹配引擎 ==============

class ZhangXiChunPulseEngine:
    def __init__(self, form_path, cases_path):
        self.term_map, self.pos_map = build_term_map(form_path)
        
        with open(cases_path, 'r', encoding='utf-8') as f:
            cases = json.load(f)
        
        self.signatures = []
        for c in cases:
            pr = c.get('pulse_raw', '') + ' ' + c.get('zhi_zhi', '')
            sig = {
                'id': c['id'], 'formula': c['formula'],
                'indication': c.get('zhi_zhi', ''),
                'ingredients': c.get('ingredients', []),
                'left': extract_side(pr, 'left'),
                'right': extract_side(pr, 'right'),
                'overall': extract_overall(pr),
            }
            self.signatures.append(sig)
    
    def diagnose(self, checked_ids):
        """主入口：勾选ID列表 → 匹配结果"""
        pulse_input = parse_checked_ids(checked_ids, self.term_map, self.pos_map)
        return self._match(pulse_input)
    
    def _match(self, pulse_input):
        results = []
        inp_terms = set()
        for pos in ['寸', '关', '尺']:
            inp_terms.update(pulse_input['left'][pos])
            inp_terms.update(pulse_input['right'][pos])
        inp_terms.update(pulse_input['overall'])
        
        if not inp_terms:
            return []
        
        for sig in self.signatures:
            score = 0
            evidence = []
            
            # 左侧
            for ld in sig['left']:
                ct = set(ld['terms'])
                ov = inp_terms & ct
                if ov:
                    score += len(ov) * 3
                    evidence.append({'side': 'left', 'site': ld.get('site'),
                                    'matched': sorted(ov), 'text': ld['text'][:80]})
            # 右侧
            for rd in sig['right']:
                ct = set(rd['terms'])
                ov = inp_terms & ct
                if ov:
                    score += len(ov) * 3
                    evidence.append({'side': 'right', 'site': rd.get('site'),
                                    'matched': sorted(ov), 'text': rd['text'][:80]})
            # 整体
            for od in sig['overall']:
                ct = set(od['terms'])
                ov = inp_terms & ct
                if ov:
                    score += len(ov) * 1
                    evidence.append({'side': 'overall', 'site': None,
                                    'matched': sorted(ov), 'text': od['text'][:80]})
            
            if score > 0:
                results.append({
                    'id': sig['id'], 'formula': sig['formula'],
                    'indication': sig['indication'],
                    'ingredients': sig['ingredients'],
                    'score': score, 'evidence': evidence
                })
        
        results.sort(key=lambda x: -x['score'])
        return results


# ============== 命令行 ==============

if __name__ == '__main__':
    form_path = os.path.join(DIR, '张锡纯脉诊辨证勾选表_恢复版.json')
    cases_path = os.path.join(os.path.dirname(DIR), 'temp', 'zxc_cases.json')
    
    engine = ZhangXiChunPulseEngine(form_path, cases_path)
    
    # 测试：模拟左弦细 + 右弱 + 数虚
    test_ids = [
        'zxc_lg_xian', 'zxc_lg_xi',  # 左关弦细
        'zxc_rg_ruo',                 # 右关弱
        'zxc_shu', 'zxc_xu',          # 数、虚
    ]
    
    results = engine.diagnose(test_ids)
    
    print(f"匹配结果 TOP 10:")
    for i, r in enumerate(results[:10]):
        print(f"\n{'='*60}")
        print(f"#{i+1} 【{r['id']}】{r['formula']}  匹配度:{r['score']}")
        print(f"主治: {r['indication'][:100]}")
        for ev in r['evidence'][:3]:
            pos_tag = f"[{ev['site']}]" if ev.get('site') else ""
            side_tag = {'left': '左', 'right': '右', 'overall': '总'}[ev['side']]
            print(f"  {side_tag}{pos_tag}: {', '.join(ev['matched'])} →「{ev['text']}」")
    
    # 保存结果示例
    out = os.path.join(DIR, 'zxc_match_demo.json')
    with open(out, 'w') as f:
        json.dump({'input_ids': test_ids, 'results': results[:10]}, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out}")
