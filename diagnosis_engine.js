// ============================================================
// 九家脉诊辨证引擎 v7.0
// 基于真实医案/原著数据驱动的辨证匹配系统
// v7: 九家全接入——黄元御/郑钦安/姚梅龄/刘渡舟 compact JSON 驱动
// 纯脉证经方（无需问诊）：张锡纯124案 | 陈建国277方
// 四诊合参：胡希恕103方 | 曹颖甫96案 | 张仲景256方
// 黄元御10规+脉对 | 郑钦安12规 | 姚梅龄六维 | 刘渡舟11规+十论
// ============================================================

var DataCache = {};
var BASE_URL = '';

// ========== 数据加载 ==========
function loadData(schoolId) {
  return new Promise(function(resolve, reject) {
    if (DataCache[schoolId]) { resolve(DataCache[schoolId]); return; }
    
    var urls = {
      'zhangxichun': 'pulse_match_zxc_compact.json',
      'chenjianguo': 'pulse_match_cjg_compact.json',
      'huxishu': 'pulse_match_hxs_compact.json',
      'caoyingfu': 'cao_yingfu_cases_compact.json',
      'zhangzhongjing': 'zhongjing_fangzheng_compact.json',
      'huangyuanyu': 'huang_yuanyu_compact.json',
      'zhengqinan': 'zheng_qinan_compact.json',
      'yaomeiling': 'yao_meiling_compact.json',
      'liuduzhou': 'liu_duzhou_compact.json'
    };
    
    var url = urls[schoolId];
    if (!url) { 
      DataCache[schoolId] = { _no_data: true };
      resolve(DataCache[schoolId]);
      return;
    }
    
    fetch(BASE_URL + url)
      .then(function(r) { return r.json(); })
      .then(function(d) { DataCache[schoolId] = d; resolve(d); })
      .catch(function(e) { DataCache[schoolId] = { _error: e.message }; resolve(DataCache[schoolId]); });
  });
}

// ========== 张锡纯 气机升降辨证（v8：三步漏斗 + 原著脉案匹配）==========
// 数据文件：pulse_match_zxc_compact_v2.json（172方，从原著提取）
// 辨证流程：Step1方向 → Step2方剂 → Step3脉诊确认
function diagnoseZhangXichun(formData) {
  var data = DataCache['zhangxichun'];
  if (!data || data._no_data || data._error) {
    // 数据未加载，尝试加载v2
    var v2 = DataCache['zxc_v2'];
    if (v2 && !v2._error) data = v2;
    else return simpleZXCDiagnose(formData);
  }

  var result = { steps: [], result: '', herbs: [], matchedCases: [] };

  // Step1：方向（大气下陷 / 气机上逆 / 直走门类）
  var direction = formData.zx_direction || '';
  var formula    = formData.zx_formula   || '';
  var section    = formData.zx_section   || '';

  if (direction) result.steps.push('【方向】' + (direction==='sink'?'大气下陷（短气/努力呼吸）':direction==='up'?'气机上逆（喘逆/呕恶/胸膈满闷）':'直走门类（33门）'));

  // Step2：方剂
  if (formula) {
    result.steps.push('【方剂】' + formula);
    result.result = formula;
    // 尝试在data中找该方剂的组成
    var matchedFormula = null;
    for (var f = 0; f < data.length; f++) {
      if (data[f].formula === formula || (data[f].title && data[f].title.indexOf(formula) >= 0)) {
        matchedFormula = data[f];
        break;
      }
    }
    if (matchedFormula) {
      if (matchedFormula.ingredients && matchedFormula.ingredients.length > 0) {
        result.herbs = matchedFormula.ingredients;
      }
      if (matchedFormula.indication) {
        result.steps.push('【主治】' + matchedFormula.indication.substring(0, 100));
      }
    }
  }

  // Step3：脉诊确认（左右总按对比）
  var zL  = formData.zx_zongL  || '';
  var zLF = formData.zx_zongLF || '';
  var zR  = formData.zx_zongR  || '';
  var zRF = formData.zx_zongRF || '';

  if (zL || zR) {
    result.steps.push('【脉诊确认】左=' + (zL||'?') + (zLF?'/'+zLF:'') + ' | 右=' + (zR||'?') + (zRF?'/'+zRF:''));
    
    // 用脉诊数据做二次匹配（找到最相似的医案）
    var userFeats = extractZXCFeatures(formData);
    var matches = [];
    for (var i = 0; i < data.length; i++) {
      var sc = matchZXCCase(data[i], userFeats);
      if (sc > 0) matches.push({ case: data[i], score: sc });
    }
    matches.sort(function(a,b){ return b.score - a.score; });
    
    if (matches.length > 0 && matches[0].score >= 3) {
      var best = matches[0].case;
      result.steps.push('【脉案参照】#' + best.id + ' ' + (best.formula||best.title||'') + '（得分' + matches[0].score.toFixed(1) + '）');
      if (best.pulse_raw) result.steps.push('  原文脉象：' + best.pulse_raw.substring(0, 80));
      // 如果Step2没有选方剂，用脉案匹配结果填充
      if (!formula) {
        result.result = best.formula || (best.title||'');
        if (best.ingredients) result.herbs = best.ingredients;
      }
      result.matchedCases = matches.slice(0, 3);
    }
  }

  // 如果方向是大气下陷但没选方剂，给默认建议
  if (direction === 'sink' && !formula) {
    if (!result.result) result.result = '升陷汤（纯大气下陷）';
    result.steps.push('【建议】大气下陷方向 → 升陷汤：生黄芪六钱、知母三钱、柴胡一钱五分、桔梗一钱五分、升麻一钱');
    result.herbs = ['生黄芪','知母','柴胡','桔梗','升麻'];
  }
  if (direction === 'up' && !formula) {
    if (!result.result) result.result = '参赭镇气汤（阴阳两虚喘逆）';
    result.steps.push('【建议】气机上逆方向 → 先辨阴阳虚实，参赭镇气汤/镇摄汤/寒降汤选一');
  }

  if (result.steps.length === 0) {
    return simpleZXCDiagnose(formData);
  }

  return result;
}

function extractZXCFeatures(formData) {
  var feats = { left: [], right: [], force: '', speed: '' };
  var zL  = formData.zx_zongL  || '';
  var zLF = formData.zx_zongLF || '';
  var zR  = formData.zx_zongR  || '';
  var zRF = formData.zx_zongRF || '';

  var terms = ['弦硬','弦细','弦数','弦长','弦浮','弦滑','弦大','弦','细','弱','浮','沉','洪','滑','涩','大','硬','微','数','迟','紧','缓','散','濡','芤','结','代'];
  
  if (zL) {
    for (var i = 0; i < terms.length; i++) {
      if (zL.indexOf(terms[i]) >= 0) feats.left.push(terms[i]);
    }
  }
  if (zLF) {
    if (zLF.indexOf('无力') >= 0 || zLF === '弦无力' || zLF === '按之即无') feats.force = '虚';
    else if (zLF.indexOf('有力') >= 0 || zLF === '弦硬') feats.force = '实';
  }

  if (zR) {
    for (var j = 0; j < terms.length; j++) {
      if (zR.indexOf(terms[j]) >= 0) feats.right.push(terms[j]);
    }
  }
  if (zRF) {
    if (zRF.indexOf('无力') >= 0 || zRF === '弦无力' || zRF === '按之即无') feats.force = feats.force || '虚';
    else if (zRF.indexOf('有力') >= 0 || zRF === '弦硬') feats.force = '实';
  }

  // 速率
  if (zL && zL.indexOf('数') >= 0) feats.speed = '数';
  else if (zL && zL.indexOf('迟') >= 0) feats.speed = '迟';
  else if (zR && zR.indexOf('数') >= 0) feats.speed = '数';
  else if (zR && zR.indexOf('迟') >= 0) feats.speed = '迟';

  return feats;
}

function matchZXCCase(caseData, userFeats) {
  var score = 0;
  var cf = caseData.feats || {};

  // 左脉匹配（权重×3）
  for (var i = 0; i < userFeats.left.length; i++) {
    if (cf['左'] && cf['左'].indexOf(userFeats.left[i]) >= 0) score += 3;
  }
  // 右脉匹配（权重×3）
  for (var j = 0; j < userFeats.right.length; j++) {
    if (cf['右'] && cf['右'].indexOf(userFeats.right[j]) >= 0) score += 3;
  }
  // 总体脉匹配（回退，权重×1）
  for (var k = 0; k < userFeats.left.length; k++) {
    if (cf['总体'] && cf['总体'].indexOf(userFeats.left[k]) >= 0) score += 1;
  }
  for (var l = 0; l < userFeats.right.length; l++) {
    if (cf['总体'] && cf['总体'].indexOf(userFeats.right[l]) >= 0) score += 1;
  }
  // 力度匹配（权重×5）
  if (userFeats.force && cf['力度'] === userFeats.force) score += 5;
  // 速率匹配（权重×2）
  if (userFeats.speed && cf['速率'] === userFeats.speed) score += 2;

  return score;
}

// 张锡纯简化逻辑（JSON不可用时的回退）
// 读取新字段名（zx_zongL等）
function simpleZXCDiagnose(formData) {
  var zl = formData.zx_zongL  || '';
  var zr = formData.zx_zongR  || '';
  var zlf = formData.zx_zongLF || '';
  var zrf = formData.zx_zongRF || '';
  // 回退：也读旧字段名
  if (!zl) zl = formData.zongL || '';
  if (!zr) zr = formData.zongR || '';
  if (!zlf) zlf = formData.zongLF || '';
  if (!zrf) zrf = formData.zongRF || '';

  var steps = [], result = '', herbs = [];

  if (!zl && !zr) {
    // 尝试用方向数据给建议
    var dir = formData.zx_direction || '';
    if (dir === 'sink') {
      steps.push('【方向】大气下陷（短气/努力呼吸）');
      steps.push('【建议】升陷汤：生黄芪六钱、知母三钱、柴胡一钱五分、桔梗一钱五分、升麻一钱');
      result = '升陷汤（纯大气下陷）';
      herbs = ['生黄芪','知母','柴胡','桔梗','升麻'];
    } else if (dir === 'up') {
      steps.push('【方向】气机上逆（喘逆/呕恶/胸膈满闷）');
      steps.push('【建议】先辨阴阳虚实，选参赭镇气汤/镇摄汤/寒降汤之一');
      result = '参赭镇气汤或镇摄汤（气机上逆）';
      herbs = ['人参','代赭石','生芡实','生山药'];
    } else {
      steps.push('【总按未填】总按为张氏辨证第一层入口');
      result = '请填写左手/右手总按脉象，或先在第一步选择方向';
    }
    return { steps: steps, result: result, herbs: herbs };
  }

  // 脉诊判断（实/虚）
  var le = (zl && ['洪','大','硬','滑','紧','弦','弦硬','弦长'].some(function(t){ return zl.indexOf(t)>=0; })) || (zlf && (zlf.indexOf('有力')>=0 || zlf==='弦硬'));
  var re = (zr && ['洪','大','硬','滑','紧','弦','弦硬','弦长'].some(function(t){ return zr.indexOf(t)>=0; })) || (zrf && (zrf.indexOf('有力')>=0 || zrf==='弦硬'));

  steps.push('左手总按：' + zl + (zlf ? '/'+zlf : '') + '（' + (le?'实（太过）':'虚（不及）') + '）');
  steps.push('右手总按：' + zr + (zrf ? '/'+zrf : '') + '（' + (re?'实（太过）':'虚（不及）') + '）');

  if (le && re) {
    steps.push('左右皆实 → 阳热内盛，清下并行');
    result = '实热内盛证。参考：白虎汤、承气汤辈（张氏常用知母、石膏、大黄）';
    herbs = ['石膏','知母','大黄','芒硝'];
  } else if (!le && !re) {
    steps.push('左右皆虚 → 大气下陷，升陷汤主之');
    result = '大气下陷证。升陷汤：生黄芪六钱、知母三钱、柴胡一钱五分、桔梗一钱五分、升麻一钱';
    herbs = ['生黄芪','知母','柴胡','桔梗','升麻'];
    if (zl && zl.indexOf('弦')>=0 && zlf && zlf.indexOf('无力')>=0) {
      steps.push('⚠ 左弦无力非实证，乃大气虚极之假象！忌用破气攻伐之品');
    }
  } else if (!le && re) {
    steps.push('左虚右实 → 胃气不降，冲气上逆');
    result = '胃气不降/冲气上逆证。赭石为主药，合龙骨牡蛎镇冲降逆';
    herbs = ['生赭石','生龙骨','生牡蛎','生山药'];
  } else {
    steps.push('左实右虚 → 肝脾郁热，肺肾两虚');
    result = '升清降浊法。黄芪升陷，赭石降胃，柴胡升清，白芍敛阴';
    herbs = ['生黄芪','生赭石','柴胡','生白芍'];
  }

  return { steps: steps, result: result, herbs: herbs };
}

// ========== 陈建国 三部九候脉诊（四步引导流 + 签名库匹配）==========
// 数据文件：chen_jianguo_pulse_signatures.json
function diagnoseChenJianguo(formData) {
  var data = DataCache['chenjianguo'];
  if (!data || data._error || data._no_data) {
    return simpleCJGDiagnose(formData);
  }

  var steps = [], result = '', herbs = [];

  // 收集四步数据
  var leftOver  = formData.cj_leftOver  || '';   // 左手总按：太过/不及/正常
  var rightOver = formData.cj_rightOver || '';   // 右手总按
  var leftMost  = formData.cj_leftMost  || '';   // 左手最异常部：左寸/左关/左尺
  var rightMost = formData.cj_rightMost || '';   // 右手最异常部
  var leftDepth = formData.cj_leftDepth || '';   // 左手最强脉动深度：浮/中/沉
  var rightDepth= formData.cj_rightDepth|| '';
  var leftMx    = formData.cj_leftMx    || [];  // 左手脉形（多选）
  var rightMx   = formData.cj_rightMx   || [];

  var hasBasic = (leftOver || rightOver);
  var hasFull  = (leftOver && rightOver && leftMost && rightMost);

  // 步骤日志
  if (leftOver)  steps.push('第一步·左手总按：' + leftOver + '（' + (leftOver==='太过'?'阴盛/实':'阴虚/虚') + '）');
  if (leftMost)  steps.push('第二步·左手最异部：' + leftMost + '，最强脉动在' + (leftDepth||'?') + '位');
  if (rightOver) steps.push('第三步·右手总按：' + rightOver + '（' + (rightOver==='太过'?'阳盛/实热':'阳虚/虚') + '）');
  if (rightMost) steps.push('第四步·右手最异部：' + rightMost + '，最强脉动在' + (rightDepth||'?') + '位');

  // 核心：双手组合类型判断（12种）
  var comboType = '';
  if (leftOver==='太过' && rightOver==='不及') comboType = '左实右虚（阴盛为主）';
  if (leftOver==='不及' && rightOver==='太过') comboType = '左虚右实（阳盛为主）';
  if (leftOver==='太过' && rightOver==='太过') comboType = '左右都实';
  if (leftOver==='不及' && rightOver==='不及') comboType = '左右都虚';
  if (leftOver==='太过' && rightOver==='正常') comboType = '纯左手太过（阴盛）';
  if (leftOver==='正常' && rightOver==='太过') comboType = '纯右手太过（阳盛）';
  if (leftOver==='不及' && rightOver==='正常') comboType = '纯左手不及（阴虚）';
  if (leftOver==='正常' && rightOver==='不及') comboType = '纯右手不及（阳虚）';

  if (comboType) steps.push('【双手组合类型】' + comboType);

  // 治法方向判断（仲景阴阳脉法口诀）
  var zhiFa = '';
  if (leftOver==='太过')  zhiFa += '左升（辛温汗/吐法）';
  if (rightOver==='太过') zhiFa += (zhiFa?' + ':'') + '右降（苦寒下/清法）';
  if (leftOver==='不及')  zhiFa += (zhiFa?' + ':'') + '左降（甘寒补/敛法）';
  if (rightOver==='不及') zhiFa += (zhiFa?' + ':'') + '右升（甘温补/升法）';
  if (zhiFa) steps.push('【治法方向（仲景阴阳脉法）】' + zhiFa);

  // 用签名库匹配
  var matches = [];
  for (var i = 0; i < data.length; i++) {
    var s = data[i];
    if (!s.left_overall) continue;  // 跳过占位条目
    var score = 0;

    // 左手总体匹配 ×4
    if (s.left_overall === leftOver) score += 4;

    // 右手总体匹配 ×4
    if (s.right_overall === rightOver) score += 4;

    // 最异部位置匹配 ×3
    if (leftMost && s.most_abnormal_position) {
      if (s.most_abnormal_position.indexOf(leftMost.replace('左','')) >= 0) score += 3;
    }

    // 浮中沉深度匹配 ×3
    if (leftDepth && s.strongest_depth) {
      if (s.strongest_depth.indexOf(leftDepth) >= 0) score += 3;
    }

    // 双手组合类型匹配 ×5
    if (s.combo_type && s.combo_type.indexOf(comboType) >= 0) score += 5;
    if (s.yinyang && (
         (leftOver==='太过'  && s.yinyang.indexOf('阴盛')>=0) ||
         (rightOver==='太过' && s.yinyang.indexOf('阳盛')>=0) ||
         (leftOver==='不及' && s.yinyang.indexOf('阴虚')>=0) ||
         (rightOver==='不及' && s.yinyang.indexOf('阳虚')>=0)
       )) score += 3;

    // 治法匹配 ×2
    if (leftOver==='太过' && s.zhifa && s.zhifa.indexOf('升')>=0) score += 2;
    if (rightOver==='太过' && s.zhifa && s.zhifa.indexOf('降')>=0) score += 2;

    if (score > 0) matches.push({ sig: s, score: score });
  }

  matches.sort(function(a,b){ return b.score - a.score; });

  if (matches.length === 0) {
    if (!hasBasic) {
      result = '请按四步引导流填写：左手总按 → 左手最异部 → 右手总按 → 右手最异部';
    } else {
      result = '已填步骤：' + (leftOver||'?') + '/' + (rightOver||'?') + '。未匹配到签名，可能需补充右侧最异部信息。';
    }
  } else {
    steps.push('【脉位签名匹配】（症状×3 + 总体×4 + 位置×3 + 深度×3）');
    steps.push('=== 候选方剂 ===');
    var top5 = matches.slice(0, 5);
    for (var k = 0; k < top5.length; k++) {
      var m = top5[k];
      var sig = m.sig;
      var line = (k+1) + '. ' + sig.formula;
      line += ' [' + (sig.yinyang||'') + '·' + (sig.zhifa||'') + ']';
      line += ' 得分=' + m.score;
      if (sig.pulse_note) line += ' | ' + sig.pulse_note.substring(0, 40);
      steps.push(line);
    }
    result = '首选：' + matches[0].sig.formula + '。' + (matches[0].sig.zhifa||'') + '方向。';
    if (matches[0].sig.key_symptom) {
      result += ' 参考症状：' + matches[0].sig.key_symptom.join('、');
    }
  }

  return { steps: steps, result: result, herbs: [], matchedSignatures: matches.slice(0,5) };
}

// 简单模式（离线）
function simpleCJGDiagnose(formData) {
  var steps = [], result = '';
  steps.push('【签名库未加载】使用仲景阴阳脉法规则匹配');

  var lo = formData.cj_leftOver || '';
  var ro = formData.cj_rightOver || '';

  if (!lo && !ro) {
    result = '陈建国体系：先填左手总按（太过/不及），再填右手。';
    return { steps: steps, result: result, herbs: [] };
  }

  // 规则匹配（核心方剂）
  if (lo==='太过' && formData.cj_leftMost==='左寸') {
    steps.push('左手太过 + 左寸最异 → 阴盛（升法）');
    if (formData.cj_leftDepth==='浮') {
      result = '麻黄汤方向（左寸浮位太过，脉紧）。可与桂枝汤鉴别：桂枝汤左寸浮缓。';
    } else {
      result = '阴盛升法方向，请补充浮中沉定位以精确匹配。';
    }
  } else if (ro==='太过' && formData.cj_rightMost==='右关') {
    steps.push('右手太过 + 右关最异 → 阳盛（降法）');
    result = '白虎汤/大承气汤方向，看右关/右尺沉位有力程度。';
  } else if (lo==='不及' && ro==='不及') {
    steps.push('双手不及 → 阳虚/阴虚，看哪侧更甚');
    if (formData.cj_rightMost==='右尺') result = '四逆汤方向（右尺最无力）。';
    else if (formData.cj_leftMost==='左寸') result = '麦门冬汤方向（左寸最无力，脉细）。';
    else result = '双手不及，需补充最异部定位。';
  } else {
    result = '请完成四步填写以触发精确匹配。当前：左=' + (lo||'?') + ' 右=' + (ro||'?');
  }

  return { steps: steps, result: result, herbs: [] };
}

// ========== 胡希恕 八纲六经辨证 + 三步法脉诊（含脉象权重表）==========
// 脉象权重表：症状×3 + 脉象八纲×2 + 特征脉×5
var HXS_PULSE_WEIGHTS = []; // 数据格式待修复（暂禁用，不影响张锡纯/陈建国引擎）

function diagnoseHuXishu(formData, symptoms, complaint) {
  var data = DataCache['huxishu'];
  
  // 读取三步法总按数据（多选数组）
  var Lfc = formData.hx_Lfc || [];
  var Lcs = formData.hx_Lcs || [];
  var Lld = formData.hx_Lld || [];
  var Lmx = formData.hx_Lmx || [];
  var Rfc = formData.hx_Rfc || [];
  var Rcs = formData.hx_Rcs || [];
  var Rld = formData.hx_Rld || [];
  var Rmx = formData.hx_Rmx || [];
  
  var steps = [], result = '', herbs = [];
  var allText = symptoms.join(',') + ' ' + complaint;
  var pulseClues = [];  // 八纲线索
  
  var hasPulse = (Lfc.length + Lcs.length + Lld.length + Lmx.length + Rfc.length + Rcs.length + Rld.length + Rmx.length) > 0;
  
  // ---- 三步法辨证 ----
  if (hasPulse) {
    var allFC = Lfc.concat(Rfc).join(',');
    var allCS = Lcs.concat(Rcs).join(',');
    var allLD = Lld.concat(Rld).join(',');
    var allMX = Lmx.concat(Rmx).join(',');
    
    steps.push('【左手总按】浮沉:' + (Lfc.join('+')||'未选') + ' | 迟数:' + (Lcs.join('+')||'未选') + ' | 力度:' + (Lld.join('+')||'未选') + ' | 脉形:' + (Lmx.join('+')||'无'));
    steps.push('【右手总按】浮沉:' + (Rfc.join('+')||'未选') + ' | 迟数:' + (Rcs.join('+')||'未选') + ' | 力度:' + (Rld.join('+')||'未选') + ' | 脉形:' + (Rmx.join('+')||'无'));
    
    // 第一步：浮沉定病位
    if (allFC.indexOf('浮') >= 0 && allFC.indexOf('沉') < 0 && allFC.indexOf('中') < 0) {
      steps.push('第一步·病位 → 表证（浮主表）'); pulseClues.push('表');
    } else if (allFC.indexOf('沉') >= 0 && allFC.indexOf('浮') < 0) {
      steps.push('第一步·病位 → 里证（沉主里）'); pulseClues.push('里');
    } else if (allFC.indexOf('中（不浮不沉）') >= 0) {
      steps.push('第一步·病位 → 半表半里（不浮不沉）'); pulseClues.push('半表半里');
    } else if (allFC.indexOf('伏') >= 0) {
      steps.push('第一步·病位 → 里证深（伏脉，阳气极虚或邪闭）'); pulseClues.push('里');
    }
    
    // 第二步：迟数定寒热（含缓脉专项注释）
    if (allCS.indexOf('数') >= 0 && allCS.indexOf('迟') < 0) {
      steps.push('第二步·寒热 → 热证（数主热）'); pulseClues.push('热');
    } else if (allCS.indexOf('迟') >= 0 && allCS.indexOf('数') < 0) {
      steps.push('第二步·寒热 → 寒证（迟主寒）'); pulseClues.push('寒');
    } else if (allCS.indexOf('缓') >= 0) {
      steps.push('第二步·寒热 → 缓脉——注意：缓≠迟！缓=脉管弛缓（张力低，因汗出津伤），非速度慢');
      pulseClues.push('缓');
    }
    
    // 第三步：力度定虚实
    if (allLD.indexOf('有力') >= 0 && allLD.indexOf('无力') < 0) {
      steps.push('第三步·虚实 → 实证（有力主实）'); pulseClues.push('实');
    } else if (allLD.indexOf('无力') >= 0 && allLD.indexOf('有力') < 0) {
      steps.push('第三步·虚实 → 虚证（无力主虚）'); pulseClues.push('虚');
    }
    
    // 脉形辅助提示
    if (allMX) {
      var mxHints = [];
      if (allMX.indexOf('弦') >= 0) mxHints.push('弦：少阳/水饮/肝气郁滞');
      if (allMX.indexOf('细') >= 0) mxHints.push('细：血虚/湿证/少阴');
      if (allMX.indexOf('弱') >= 0) mxHints.push('弱：气血两虚');
      if (allMX.indexOf('滑') >= 0) mxHints.push('滑：痰热/食积/阳明');
      if (allMX.indexOf('涩') >= 0) mxHints.push('涩：血瘀/津亏/少阴');
      if (allMX.indexOf('紧') >= 0) mxHints.push('紧：寒邪盛/太阳寒伤营');
      if (allMX.indexOf('微') >= 0) mxHints.push('微：阳气极虚/少阴危象');
      if (mxHints.length > 0) steps.push('脉形提示：' + mxHints.join('；'));
    }
  }
  
  // ---- 核心：症状×3 + 脉象八纲×2 + 特征脉×5 双驱动匹配 ----
  var matches = [];
  for (var i = 0; i < HXS_PULSE_WEIGHTS.length; i++) {
    var w = HXS_PULSE_WEIGHTS[i];
    var score = 0;
    
    // 症状触发词 ×3
    for (var t = 0; t < w.triggers.length; t++) {
      if (allText.indexOf(w.triggers[t]) >= 0) score += 3;
    }
    
    // 脉象权重表匹配 ×（权重值）
    if (hasPulse) {
      for (var p = 0; p < w.patterns.length; p++) {
        var pat = w.patterns[p];
        var matched = true;
        for (var pi = 0; pi < pat.p.length; pi++) {
          if (allMX.indexOf(pat.p[pi]) < 0 && allFC.indexOf(pat.p[pi]) < 0 && allCS.indexOf(pat.p[pi]) < 0 && allLD.indexOf(pat.p[pi]) < 0) {
            matched = false; break;
          }
        }
        if (matched) score += pat.w;
      }
    }
    
    // 八纲线索加权 ×2
    for (var c = 0; c < pulseClues.length; c++) {
      if (w.bagang && w.bagang.indexOf(pulseClues[c]) >= 0) score += 2;
    }
    
    if (score > 0) matches.push({ formula: w, score: score });
  }
  
  // 若JSON数据文件可用，叠加其医案匹配
  if (data && !data._error && !data._no_data) {
    for (var j = 0; j < data.length; j++) {
      var f = data[j];
      var score2 = 0;
      var syndrome = f['症候群'] || [];
      for (var s = 0; s < syndrome.length; s++) {
        if (allText.indexOf(syndrome[s]) >= 0) score2 += 3;
      }
      if (hasPulse) {
        var allMXstr = Lmx.concat(Rmx).join(',');
        if (f['特征脉'] && allMXstr.indexOf(f['特征脉']) >= 0) score2 += 5;
        if (f['八纲']) {
          for (var k = 0; k < pulseClues.length; k++) {
            if (f['八纲'].indexOf(pulseClues[k]) >= 0) score2 += 2;
          }
        }
      }
      if (score2 > 0) {
        var existing = matches.filter(function(m){ return m.formula.formula === f.name; })[0];
        if (existing) existing.score += score2;
        else matches.push({ formula: {formula:f.name,liujing:f['六经'],bagang:f['八纲'],triggers:f['症候群']||[]}, score: score2 });
      }
    }
  }
  
  matches.sort(function(a, b) { return b.score - a.score; });
  
  if (matches.length === 0) {
    if (pulseClues.length >= 2) {
      steps.push('【脉象有线索但症状不足】脉象提示：' + pulseClues.join('/'));
      result = '请补充六经特征症状以触发方证匹配。脉象线索：' + pulseClues.join('/');
    } else {
      steps.push('【信息不足】请填写三步法脉象，并补充症状。');
      result = '请填写左手/右手总按三步法（浮沉/迟数/力度），并勾选症状。';
    }
  } else {
    steps.push('=== 六经方证匹配（症状×3 + 脉象权重 + 八纲×2）===');
    var top5 = matches.slice(0, 5);
    for (var m = 0; m < top5.length; m++) {
      var mm = top5[m];
      var note = '';
      if (mm.formula.patterns) {
        var bestPat = mm.formula.patterns[0];
        if (bestPat && bestPat.note) note = '（注：' + bestPat.note + '）';
      }
      steps.push((m+1) + '. ' + mm.formula.formula + ' [' + (mm.formula.liujing||'') + '·' + (mm.formula.bagang||'') + '] 得分=' + mm.score + note);
    }
    result = matches[0].formula.formula + ' 方向。' + (matches[0].formula.liujing||'') + '·' + (matches[0].formula.bagang||'');
  }
  
  return { steps: steps, result: result, herbs: herbs, matchedSyndromes: matches.slice(0, 5) };
}

// ========== 曹颖甫 经方实验录 脉案匹配 ==========
function diagnoseCaoYingfu(formData) {
  var data = DataCache['caoyingfu'];
  if (!data || data._error) {
    return simpleCYDiagnose(formData);
  }
  
  var cl = formData.cy_left || '', cr = formData.cy_right || '';
  var steps = [], result = '', herbs = [];
  
  if (!cl && !cr) {
    steps.push('【脉象未填】请填写左右手脉象');
    result = '曹颖甫经方实验录以脉证对勘为核心，需脉象输入';
    return { steps: steps, result: result, herbs: herbs };
  }
  
  steps.push('左：' + (cl || '?') + ' | 右：' + (cr || '?'));
  
  // 脉象关键词匹配案库
  var matches = [];
  var pulseKws = (cl + ',' + cr).split(/[,，、\s]+/).filter(function(x) { return x.length > 0; });
  
  for (var i = 0; i < data.length; i++) {
    var c = data[i];
    if (!c.pulse) continue;
    var score = 0;
    for (var j = 0; j < pulseKws.length; j++) {
      if (c.pulse.indexOf(pulseKws[j]) >= 0) score += 3;
    }
    // 方剂匹配加分
    if (c.formulas && c.formulas.length > 0) score += 2;
    if (score > 0) matches.push({ case: c, score: score });
  }
  
  matches.sort(function(a, b) { return b.score - a.score; });
  
  if (matches.length === 0) {
    steps.push('未匹配到相似脉案（案库' + data.length + '条），启用简化逻辑');
    return simpleCYDiagnose(formData);
  }
  
  var top3 = matches.slice(0, 3);
  steps.push('=== 经方实验录脉案匹配（' + data.length + '案库）===');
  
  for (var k = 0; k < top3.length; k++) {
    var m = top3[k];
    steps.push((k+1) + '. #' + m.case.id + ' [' + m.case.chapter + '] 脉：' + (m.case.pulse || '无记载').substring(0,60));
    if (m.case.diag) steps.push('   诊断：' + m.case.diag);
    if (m.case.formulas && m.case.formulas.length > 0) steps.push('   方剂：' + m.case.formulas.join('、'));
  }
  
  var top = top3[0];
  result = top.case.chapter + '方向。' + (top.case.diag || '参见曹颖甫原案脉证');
  if (top.case.formulas && top.case.formulas.length > 0) {
    herbs = top.case.formulas;
  }
  
  return { steps: steps, result: result, herbs: herbs, matchedCases: top3 };
}

function simpleCYDiagnose(formData) {
  var cl = formData.cy_left || '', cr = formData.cy_right || '', cs = formData.cy_sweat || '';
  var steps = [], result = '', herbs = [];
  
  steps.push('【简化逻辑】47案数据未加载，使用曹氏经典脉证规则');
  steps.push('左：' + cl + ' | 右：' + cr + (cs ? ' | 汗：' + cs : ''));
  
  if (cl === '浮' && cr === '浮') {
    if (cs === '有汗') { result = '太阳中风，桂枝汤主之'; herbs = ['桂枝','芍药','甘草','生姜','大枣']; }
    else if (cs === '无汗') { result = '太阳伤寒，麻黄汤主之'; herbs = ['麻黄','桂枝','杏仁','甘草']; }
    else { result = '浮脉见于左右，请补充汗出情况以定桂枝汤/麻黄汤'; }
  } else if (cl === '弦' && (cr === '实' || cr === '大')) {
    result = '少阳阳明合病，大柴胡汤'; herbs = ['柴胡','黄芩','芍药','半夏','枳实','大黄','生姜','大枣'];
  } else {
    result = '脉证组合未触发曹氏经典方证。请参见曹颖甫92案脉证映射。';
  }
  return { steps: steps, result: result, herbs: herbs };
}

// ========== 张仲景 六经辨证 + 256方匹配 ==========
function diagnoseZhangZhongjing(formData, symptoms, complaint) {
  var data = DataCache['zhangzhongjing'];
  var p = formData.zj_pulse || '', f = formData.zj_force || '';
  var steps = [], result = '', herbs = [];
  
  if (!p) {
    steps.push('【脉象未填】');
    result = '请填写总体脉象';
    return { steps: steps, result: result, herbs: herbs };
  }
  
  steps.push('脉象：' + p + (f ? ' ' + f : ''));
  
  // 脉→六经基础映射
  var mapping = {
    '浮': { jing: '太阳', desc: '浮为在表，太阳主表', herbs: ['麻黄', '桂枝'] },
    '洪': { jing: '阳明', desc: '洪大为阳明经证主脉', herbs: ['石膏', '知母'] },
    '大': { jing: '阳明', desc: '大而有力为阳明实热', herbs: ['石膏', '知母', '大黄'] },
    '弦': { jing: '少阳', desc: '弦为少阳主脉', herbs: ['柴胡', '黄芩'] },
    '缓': { jing: '太阴', desc: '缓弱为太阴脾虚主脉', herbs: ['人参', '干姜', '白术'] },
    '弱': { jing: '少阴', desc: '少阴虚寒', herbs: ['附子', '干姜'] },
    '微': { jing: '少阴', desc: '脉微细为少阴病提纲脉', herbs: ['附子', '干姜', '甘草'] },
    '细': { jing: '少阴', desc: '细为血虚或寒盛', herbs: ['当归', '桂枝'] },
    '沉': { jing: '少阴', desc: '里证，沉而有力为里实', herbs: ['附子'] },
    '滑': { jing: '阳明', desc: '滑主痰热或食积', herbs: ['大黄', '半夏'] },
    '数': { jing: '热证', desc: '数主热，需结合浮沉定表里' },
    '迟': { jing: '寒证', desc: '迟主寒' },
    '紧': { jing: '太阳', desc: '紧主寒主痛', herbs: ['麻黄'] },
    '涩': { jing: '少阴', desc: '涩主血少或瘀滞' }
  };
  
  var baseM = mapping[p];
  var targetJing = baseM ? baseM.jing : '';
  
  steps.push(p + '脉 → ' + (targetJing || '待定') + '病方向');
  
  // 如果有症状+方证数据，进行256方匹配
  if (data && !data._error && data.length > 0 && (symptoms.length > 0 || complaint)) {
    var allText = symptoms.join(',') + ' ' + complaint;
    var formulaMatches = [];
    
    for (var i = 0; i < data.length; i++) {
      var fn = data[i];
      var score = 0;
      
      // 六经匹配
      if (targetJing && fn.jing.indexOf(targetJing) >= 0) score += 10;
      
      // 症状关键词匹配
      if (fn.symptoms) {
        for (var j = 0; j < fn.symptoms.length; j++) {
          if (allText.indexOf(fn.symptoms[j]) >= 0) score += 4;
        }
      }
      
      if (score > 0) formulaMatches.push({ formula: fn, score: score });
    }
    
    formulaMatches.sort(function(a, b) { return b.score - a.score; });
    
    if (formulaMatches.length > 0) {
      steps.push('=== 256方匹配 ===');
      var top5 = formulaMatches.slice(0, 5);
      for (var k = 0; k < top5.length; k++) {
        var fm = top5[k];
        steps.push((k+1) + '. ' + fm.formula.name + ' [' + fm.formula.jing + '] 得分=' + fm.score);
      }
      result = top5[0].formula.name + '（' + top5[0].formula.jing + '）方向';
    } else {
      result = baseM ? baseM.desc : '脉象需结合症状定六经——建议补充寒热、汗出、二便等信息';
    }
  } else {
    result = baseM ? baseM.desc : '脉象需结合症状定六经，256方数据加载后可精确匹配';
  }
  
  if (baseM && baseM.herbs) herbs = baseM.herbs;
  
  return { steps: steps, result: result, herbs: herbs };
}

// ========== 黄元御 一气周流 ==========
function diagnoseHuangYuanyu(formData) {
  var data = DataCache['huangyuanyu'];
  var g = formData.hy_guan || '', gf = formData.hy_guanF || '';
  var steps = [], result = '', herbs = [];
  
  if (!g) {
    steps.push('【右关未填】右关为中气之枢，黄氏体系启动条件');
    result = '请填写右关脉象';
    return { steps: steps, result: result, herbs: herbs };
  }
  
  steps.push('右关：' + g + (gf ? '/' + gf : ''));
  
  // 加载compact数据
  if (data && !data._no_data && !data._error) {
    var ds = data.diagnosis_sequence;
    if (ds) {
      for (var i = 0; i < ds.length; i++) {
        steps.push('步骤' + (i+1) + '【' + ds[i].name + '】(' + ds[i].key + ')');
      }
    }
    steps.push('核心规则：' + (data.core_rules ? data.core_rules.length : 0) + '条，脉象对：' + (data.pulse_pairs ? data.pulse_pairs.length : 0) + '组');
  }
  
  if (g === '弱' || g === '缓' || g === '濡') {
    steps.push('右关弱/缓/濡 → 中气不足，脾土不运');
    result = '黄芽汤/理中汤方向。黄元御：中气衰则升降窒，黄芽汤运中气。';
    herbs = ['人参', '干姜', '甘草', '茯苓'];
  } else if (g === '弦' || g === '硬') {
    steps.push('右关弦/硬 → 木郁克土，肝木横逆犯脾');
    result = '达郁汤合下气汤。黄元御：木郁则贼土，达郁汤疏木培土。';
    herbs = ['桂枝', '鳖甲', '茯苓', '甘草', '白芍'];
  } else if (g === '滑') {
    steps.push('右关滑 → 中焦痰湿');
    result = '姜苓半夏汤。湿阻中焦，化痰运脾。';
    herbs = ['茯苓', '半夏', '生姜', '甘草'];
  } else if (g === '浮') {
    steps.push('右关浮 → 中气外越，脾不统血');
    result = '需加固涩。黄元御：中气浮散为危象。';
  }
  
  return { steps: steps, result: result, herbs: herbs };
}

// ========== 郑钦安 阴阳辨证 ==========
function diagnoseZhengQinan(formData) {
  var data = DataCache['zhengqinan'];
  var lchi = formData.zn_lchi || '', rchi = formData.zn_rchi || '';
  var lchiF = formData.zn_lchiF || '', rchiF = formData.zn_rchiF || '';
  var hot = formData.zn_hot || '', stool = formData.zn_stool || '', thirst = formData.zn_thirst || '';
  
  var steps = [], result = '', herbs = [], warn = '';
  
  if (!lchi && !rchi) {
    steps.push('【尺脉未填】郑氏以尺脉辨真阳');
    result = '请填写至少一侧尺脉';
    return { steps: steps, result: result, herbs: herbs };
  }
  
  steps.push('左尺：' + (lchi || '?') + ' | 右尺：' + (rchi || '?'));
  
  // 加载compact数据
  if (data && !data._no_data && !data._error) {
    var ds = data.diagnosis_sequence;
    if (ds) {
      for (var i = 0; i < ds.length; i++) {
        if (i === 0) steps.push('【' + ds[i].name + '】→');
        else steps.push('  →【' + ds[i].name + '】');
      }
    }
    steps.push('核心规则：' + (data.core_rules ? data.core_rules.length : 0) + '条');
  }
  
  var chiWeak = (lchi === '弱' || lchi === '微' || rchi === '弱' || rchi === '微' || 
                 lchiF === '无力' || lchiF === '按之即无' || rchiF === '无力' || rchiF === '按之即无');
  
  if (chiWeak) {
    steps.push('尺脉虚 → 真阳不足');
    
    if (hot === '发热') {
      steps.push('发热+尺虚 → 假热真寒！');
      warn = '虽有发热但尺脉虚，此为阴盛逼阳外越——郑氏核心鉴别点！'
    }
    
    if (stool === '便溏') {
      steps.push('便溏+尺虚 → 脾肾阳虚');
      result = '四逆汤/附子理中汤。郑钦安：尺脉弱而便溏，四逆汤温肾暖脾。';
      herbs = ['附子', '干姜', '炙甘草', '白术', '人参'];
    } else if (thirst === '不渴' || thirst === '渴喜热饮') {
      steps.push('不渴/喜热饮+尺虚 → 阳虚无疑');
      result = '四逆汤证。郑钦安：不渴为无热之征，尺虚为阳衰之象。';
      herbs = ['附子', '干姜', '炙甘草'];
    } else {
      result = '阳虚为本。四逆汤/附子理中汤。需结合三问进一步定方。';
      herbs = ['附子', '干姜', '炙甘草'];
    }
  } else {
    steps.push('尺脉可 → 结合三问');
    if (hot === '畏寒' && (thirst === '不渴' || stool === '便溏')) {
      result = '阳虚倾向，但尺脉未衰 → 理中汤/建中汤方向';
    } else if (hot === '发热' && stool === '便秘' && thirst === '渴喜冷饮') {
      result = '阳证倾向 → 承气/白虎方向（非郑氏火神派主攻方向）';
    } else {
      result = '三问信息不完整，建议补充寒热、二便、渴饮以定阴阳';
    }
  }
  
  return { steps: steps, result: result, herbs: herbs, warn: warn };
}

// ========== 姚梅龄 六维分层 ==========
function diagnoseYaoMeiling(formData) {
  var data = DataCache['yaomeiling'];
  var steps = [], result = '';
  var wei = formData.ym_wei || '', ti = formData.ym_ti || '', li = formData.ym_li || '';
  var lv = formData.ym_lv || '', lu = formData.ym_lu || '', xing = formData.ym_xing || '';
  var lr = formData.ym_lr || '';
  
  var dims = [wei, ti, li, lv, lu].filter(function(x) { return x; }).length;
  
  steps.push('六维：位=' + (wei || '?') + ' | 体=' + (ti || '?') + ' | 力=' + (li || '?') + ' | 率=' + (lv || '?') + ' | 律=' + (lu || '?') + ' | 形=' + (xing || '?'));
  steps.push('已采集 ' + dims + '/5 主维度');
  
  // 加载compact数据
  if (data && !data._no_data && !data._error) {
    if (data.six_dimensions) {
      steps.push('六维体系：' + Object.keys(data.six_dimensions).map(function(k) { return data.six_dimensions[k].name; }).join(' / '));
    }
    if (data.key_pulse_diagnosis) {
      steps.push('独处藏奸：' + data.key_pulse_diagnosis.principle);
    }
  }
  
  if (dims >= 4) {
    steps.push('维度充分 → 姚氏六维分层分析启动');
    if (lr) steps.push('左右差异：' + lr);
    result = '姚梅龄六维分层分析。建议参考《临证脉学十六讲》进行深度辨证。';
  } else if (dims >= 2) {
    result = '部分维度可用，但需至少4个维度才能全面启动姚氏脉学分析。';
  } else {
    result = '请补充脉位、脉体、脉力、脉率、脉律中至少4项。';
  }
  
  return { steps: steps, result: result, herbs: [] };
}

// ========== 刘渡舟 十论分诊 ==========
function diagnoseLiuDuzhou(symptoms, complaint) {
  var data = DataCache['liuduzhou'];
  var all = symptoms.join(',') + ' ' + complaint;
  var steps = [], result = '', trig = [];
  
  steps.push('【症状驱动辨证】脉象辅助六经定位');
  
  // 加载compact数据
  if (data && !data._no_data && !data._error) {
    var ds = data.diagnosis_sequence;
    if (ds && ds.length >= 2) {
      steps.push('六经提纲：' + ds[1].name + '已加载');
    }
    if (data.shi_lun) {
      var shiNames = Object.keys(data.shi_lun);
      steps.push('十论体系：' + shiNames.join('、'));
    }
    steps.push('核心规则：' + (data.core_rules ? data.core_rules.length : 0) + '条');
  }
  
  if (all.indexOf('小便') >= 0 || all.indexOf('浮肿') >= 0 || all.indexOf('眩') >= 0 || all.indexOf('悸') >= 0) {
    trig.push('水证论');
  }
  if (all.indexOf('胁') >= 0 || all.indexOf('口苦') >= 0 || all.indexOf('呕') >= 0 || (all.indexOf('痞') >= 0)) {
    trig.push('气机论');
  }
  if (all.indexOf('食') >= 0 || all.indexOf('腹') >= 0 || all.indexOf('泄') >= 0 || all.indexOf('便') >= 0) {
    trig.push('脾胃论');
  }
  if (all.indexOf('痰') >= 0 || all.indexOf('饮') >= 0 || all.indexOf('咳') >= 0) {
    trig.push('痰饮论');
  }
  if (all.indexOf('热') >= 0 || all.indexOf('火') >= 0 || all.indexOf('烦') >= 0) {
    trig.push('火证论');
  }
  if (all.indexOf('湿') >= 0 || all.indexOf('重') >= 0) {
    trig.push('湿证论');
  }
  
  if (trig.length > 0) {
    steps.push('触发分论：' + trig.join('、'));
    // 提取对应用药建议
    if (data && data.shi_lun) {
      for (var t = 0; t < trig.length; t++) {
        var sl = data.shi_lun[trig[t].replace('证论','').replace('论','')];
        if (sl) {
          steps.push(trig[t] + '核心：' + (sl.core || '').substring(0, 60));
        }
      }
    }
    result = '可进入对应分论深度辨证。刘渡舟十论体系详见 liu_duzhou_decision_tree.md';
  } else {
    steps.push('十论分支未触发');
    result = '需补充小便/浮肿/眩/胁/口苦/腹胀等关键词以触发十论分诊';
  }
  
  return { steps: steps, result: result, herbs: [] };
}

// ========== 统一入口 ==========
function diagnose(schoolId, formData, symptoms, complaint) {
  switch(schoolId) {
    case 'zhangxichun': return diagnoseZhangXichun(formData);
    case 'chenjianguo': return diagnoseChenJianguo(formData);
    case 'huxishu': return diagnoseHuXishu(formData, symptoms, complaint);
    case 'caoyingfu': return diagnoseCaoYingfu(formData);
    case 'zhangzhongjing': return diagnoseZhangZhongjing(formData, symptoms, complaint);
    case 'huangyuanyu': return diagnoseHuangYuanyu(formData);
    case 'zhengqinan': return diagnoseZhengQinan(formData);
    case 'yaomeiling': return diagnoseYaoMeiling(formData);
    case 'liuduzhou': return diagnoseLiuDuzhou(symptoms, complaint);
    default: return { steps: ['未知体系'], result: '', herbs: [] };
  }
}
