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

// ========== 张锡纯 气机升降辨证 ==========
function diagnoseZhangXichun(formData) {
  var data = DataCache['zhangxichun'];
  if (!data || data._no_data || data._error) {
    return simpleZXCDiagnose(formData);
  }
  
  // 从表单提取脉象特征
  var userFeatures = extractZXCFeatures(formData);
  
  // 匹配案例
  var matches = [];
  for (var i = 0; i < data.length; i++) {
    var c = data[i];
    var score = matchZXCCase(c, userFeatures);
    if (score > 0) matches.push({ case: c, score: score });
  }
  
  matches.sort(function(a, b) { return b.score - a.score; });
  
  var result = { steps: [], result: '', herbs: [], matchedCases: [] };
  
  result.steps.push('左手总按：' + (formData.zongL || '未填') + (formData.zongLF ? '/' + formData.zongLF : ''));
  result.steps.push('右手总按：' + (formData.zongR || '未填') + (formData.zongRF ? '/' + formData.zongRF : ''));
  
  if (matches.length === 0) {
    result.steps.push('未匹配到相似脉案，启用简化逻辑');
    return simpleZXCDiagnose(formData);
  }
  
  // 取Top3
  var top3 = matches.slice(0, 3);
  result.matchedCases = top3;
  
  var top = top3[0];
  result.steps.push('最佳匹配（得分' + top.score.toFixed(1) + '）：#' + top.case.id + ' ' + top.case.title);
  result.steps.push('原文脉象：' + top.case.pulse_raw);
  result.result = top.case.diag || ('参见医案#' + top.case.id);
  if (top.case.herbs) {
    result.herbs = top.case.herbs.split(/[、，\s]+/).filter(function(x) { return x.length > 0; });
  }
  
  if (top3.length > 1) {
    for (var j = 1; j < top3.length; j++) {
      result.steps.push('次匹配（得分' + top3[j].score.toFixed(1) + '）：#' + top3[j].case.id + ' ' + top3[j].case.title);
    }
  }
  
  return result;
}

function extractZXCFeatures(formData) {
  var feats = { left: [], right: [], force: '', speed: '' };
  
  // 左手
  if (formData.zongL) {
    var terms = ['弦硬','弦细','弦数','弦浮','弦滑','弦大','弦','细','弱','浮','沉','洪','滑','涩','大','硬','微','数','迟','紧','缓','散','濡','芤'];
    for (var i = 0; i < terms.length; i++) {
      if (formData.zongL.indexOf(terms[i]) >= 0) feats.left.push(terms[i]);
    }
  }
  if (formData.zongLF) {
    if (formData.zongLF.indexOf('无力') >= 0 || formData.zongLF === '弦无力') feats.force = '虚';
    else if (formData.zongLF.indexOf('有力') >= 0 || formData.zongLF === '弦硬') feats.force = '实';
  }
  
  // 右手
  if (formData.zongR) {
    var terms2 = ['弦硬','弦细','弦数','弦浮','弦滑','弦大','弦','细','弱','浮','沉','洪','滑','涩','大','硬','微','数','迟','紧','缓','散','濡','芤'];
    for (var j = 0; j < terms2.length; j++) {
      if (formData.zongR.indexOf(terms2[j]) >= 0) feats.right.push(terms2[j]);
    }
  }
  
  return feats;
}

function matchZXCCase(caseData, userFeats) {
  var score = 0;
  var cf = caseData.feats;
  
  // 左脉匹配
  for (var i = 0; i < userFeats.left.length; i++) {
    if (cf['左'].indexOf(userFeats.left[i]) >= 0) score += 3;
  }
  // 右脉匹配
  for (var j = 0; j < userFeats.right.length; j++) {
    if (cf['右'].indexOf(userFeats.right[j]) >= 0) score += 3;
  }
  // 总体脉匹配（回退）
  for (var k = 0; k < userFeats.left.length; k++) {
    if (cf['总体'].indexOf(userFeats.left[k]) >= 0) score += 1;
  }
  for (var l = 0; l < userFeats.right.length; l++) {
    if (cf['总体'].indexOf(userFeats.right[l]) >= 0) score += 1;
  }
  
  // 力度匹配
  if (userFeats.force && cf['力度'] === userFeats.force) score += 5;
  
  // 速度匹配
  if (userFeats.speed && cf['速率'] === userFeats.speed) score += 2;
  
  return score;
}

// 张锡纯简化逻辑（JSON不可用时的回退）
function simpleZXCDiagnose(formData) {
  var zl = formData.zongL, zr = formData.zongR;
  var zlf = formData.zongLF, zrf = formData.zongRF;
  var steps = [], result = '', herbs = [];
  
  if (!zl && !zr) {
    steps.push('【总按未填】总按为张氏辨证第一层入口');
    result = '请填写左右手总按脉象';
    return { steps: steps, result: result, herbs: herbs };
  }
  
  var le = ['洪','大','硬','革','滑','紧','弦'].indexOf(zl) >= 0 || (zlf && (zlf.indexOf('有力') >= 0 || zlf === '弦硬'));
  var re = ['洪','大','硬','革','滑','紧','弦'].indexOf(zr) >= 0 || (zrf && (zrf.indexOf('有力') >= 0 || zrf === '弦硬'));
  
  steps.push('左手总按：' + zl + (zlf ? '/' + zlf : '') + '（' + (le ? '实' : '虚') + '）');
  steps.push('右手总按：' + zr + (zrf ? '/' + zrf : '') + '（' + (re ? '实' : '虚') + '）');
  
  if (le && re) {
    steps.push('左右皆实 → 白虎/承气方向');
    result = '实热内盛，清下并行。参考：白虎汤、承气汤辈';
    herbs = ['石膏', '知母', '大黄', '芒硝'];
  } else if (!le && !re) {
    steps.push('左右皆虚 → 大气下陷，升陷汤主之');
    result = '大气下陷证。升陷汤：生黄芪六钱、知母三钱、柴胡一钱五分、桔梗一钱五分、升麻一钱';
    herbs = ['生黄芪', '知母', '柴胡', '桔梗', '升麻'];
    if (zl === '弦' && zlf === '弦无力') {
      steps.push('⚠ 左弦无力非实证，乃大气虚极之假象！');
    }
  } else if (!le && re) {
    steps.push('左虚右实 → 胃气不降，冲气上逆');
    result = '胃气不降证。赭石为主药，合龙骨牡蛎镇冲降逆';
    herbs = ['生赭石', '生龙骨', '生牡蛎', '生山药'];
  } else {
    steps.push('左实右虚 → 升清降浊，肝郁脾弱');
    result = '升陷汤合降胃法。黄芪升陷，赭石降胃';
    herbs = ['生黄芪', '生赭石', '柴胡', '升麻'];
  }
  
  return { steps: steps, result: result, herbs: herbs };
}

// ========== 陈建国 三部九候脉诊 ==========
function diagnoseChenJianguo(formData) {
  var data = DataCache['chenjianguo'];
  if (!data || data._error) {
    return simpleCJGDiagnose(formData);
  }
  
  var steps = [], result = '', herbs = [];
  
  var step1 = formData.cj_step1 || '';
  var step2m = formData.cj_step2m || '';
  var step2q = formData.cj_step2q || '';
  
  // 收集六部完整数据
  var positions = ['左寸','左关','左尺','右寸','右关','右尺'];
  var filled = 0;
  for (var i = 0; i < positions.length; i++) {
    var p = positions[i];
    if (formData['cj_t_' + p] || formData['cj_d_' + p] || formData['cj_q_' + p]) filled++;
  }
  
  steps.push('总体：' + (step1 || '未填') + ' | 方向：' + (step2m || '?') + ' ' + (step2q || '?') + ' | 脉位：' + filled + '/6');
  
  if (step1 && step2m && filled >= 4) {
    // 匹配50方脉位签名
    var matches = [];
    for (var j = 0; j < data.length; j++) {
      var f = data[j];
      var score = 0;
      
      // 阴阳盛衰匹配
      if (step2q && f['阴阳']) {
        if (step2q.indexOf('阴') >= 0 && f['阴阳'].indexOf('阴') >= 0) score += 5;
        if (step2q.indexOf('阳') >= 0 && f['阴阳'].indexOf('阳') >= 0) score += 5;
      }
      
      // 左脉匹配
      if (step1 === '太过' && f['left_overall'] === '太过') score += 4;
      if (step1 === '不及' && f['left_overall'] === '不及') score += 4;
      if (step1 === '正常' && f['left_overall'] === '正常') score += 4;
      
      // 治法匹配
      if (step2m === '升法' && f['治法'] && f['治法'].indexOf('升') >= 0) score += 2;
      if (step2m === '降法' && f['治法'] && f['治法'].indexOf('降') >= 0) score += 2;
      
      if (score > 0) matches.push({ formula: f, score: score });
    }
    
    matches.sort(function(a, b) { return b.score - a.score; });
    
    if (matches.length > 0) {
      var topMatch = matches.slice(0, 5);
      steps.push('六步定向完成 → 脉位签名匹配');
      steps.push('=== 匹配方剂 ===');
      for (var k = 0; k < topMatch.length; k++) {
        var m = topMatch[k];
        var f = m.formula;
        steps.push((k+1) + '. ' + f.name + ' [' + (f['阴阳'] || '') + '·' + (f['治法'] || '') + '] 左=' + f.left_quality + ' 右=' + f.right_quality);
      }
      result = '最佳匹配：' + topMatch[0].formula.name + '。详见以上脉位签名。';
      if (topMatch[0].formula.herbs) {
        herbs = topMatch[0].formula.herbs;
      }
    }
  } else {
    steps.push('信息不足，需完成总体+方向+至少4个脉位');
    result = '陈建国纯脉诊体系要求六步信息完整才能启动50方匹配';
  }
  
  return { steps: steps, result: result, herbs: herbs };
}

function simpleCJGDiagnose(formData) {
  var steps = [], result = '';
  steps.push('【数据未加载】陈氏六步定向法需要完整脉位数据');
  steps.push('请参见 chen_jianguo_pulse_system.md 了解完整方法论');
  result = '离线模式下无法执行陈建国50方脉位签名匹配';
  return { steps: steps, result: result, herbs: [] };
}

// ========== 胡希恕 八纲六经辨证 + 脉诊辅助 ==========
function diagnoseHuXishu(formData, symptoms, complaint) {
  var data = DataCache['huxishu'];
  var pulseL = formData.hxs_pulse_l || '', pulseR = formData.hxs_pulse_r || '';
  var pulseForce = formData.hxs_pulse_force || '';
  
  var steps = [], result = '', herbs = [];
  var allText = symptoms.join(',') + ' ' + complaint;
  
  // 脉象辅助判断八纲
  var pulseClues = [];
  if (pulseL || pulseR) {
    steps.push('脉象辅助：左=' + (pulseL || '?') + ' 右=' + (pulseR || '?') + (pulseForce ? ' 力=' + pulseForce : ''));
    
    // 脉象→八纲线索
    var allPulse = (pulseL + pulseR).toLowerCase();
    if (allPulse.indexOf('浮') >= 0) pulseClues.push('表');
    if (allPulse.indexOf('沉') >= 0) pulseClues.push('里');
    if (allPulse.indexOf('数') >= 0 || allPulse.indexOf('洪') >= 0 || allPulse.indexOf('滑') >= 0) pulseClues.push('热');
    if (allPulse.indexOf('迟') >= 0 || allPulse.indexOf('缓') >= 0 || allPulse.indexOf('弱') >= 0) pulseClues.push('寒');
    if (pulseForce.indexOf('无力') >= 0 || allPulse.indexOf('弱') >= 0 || allPulse.indexOf('微') >= 0) pulseClues.push('虚');
    if (pulseForce.indexOf('有力') >= 0 || allPulse.indexOf('弦硬') >= 0) pulseClues.push('实');
    
    if (pulseClues.length > 0) steps.push('脉象提示：' + pulseClues.join('、'));
  }
  
  if (!data || data._error) {
    return simpleHXSDiagnose(symptoms, complaint, pulseClues);
  }
  
  // 六经提纲症候群匹配
  var matches = [];
  for (var i = 0; i < data.length; i++) {
    var f = data[i];
    var syndrome = f['症候群'] || [];
    var score = 0;
    for (var j = 0; j < syndrome.length; j++) {
      var kw = syndrome[j];
      if (allText.indexOf(kw) >= 0) score += 3;
      // 部分匹配
      for (var c = 0; c < kw.length - 1; c++) {
        if (allText.indexOf(kw.substring(c, c+2)) >= 0) score += 1;
      }
    }
    // 脉象匹配特征脉
    if (f['特征脉'] && (pulseL.indexOf(f['特征脉']) >= 0 || pulseR.indexOf(f['特征脉']) >= 0)) {
      score += 5;
    }
    // 八纲匹配
    if (f['八纲']) {
      for (var k = 0; k < pulseClues.length; k++) {
        if (f['八纲'].indexOf(pulseClues[k]) >= 0) score += 2;
      }
    }
    if (score > 0) matches.push({ formula: f, score: score });
  }
  
  matches.sort(function(a, b) { return b.score - a.score; });
  
  steps.push('【症状+脉象双驱动辨证】');
  
  if (matches.length === 0) {
    steps.push('六经提纲症候群未命中');
    result = '当前症状未能触发任何六经提纲。请补充更多六经特征症状';
  } else {
    steps.push('=== 六经提纲匹配（' + matches.length + '条）===');
    var top5 = matches.slice(0, 5);
    for (var k = 0; k < top5.length; k++) {
      var m = top5[k];
      steps.push((k+1) + '. ' + m.formula.name + ' [' + m.formula['六经'] + '·' + m.formula['八纲'] + '] 得分=' + m.score);
      if (m.formula['特征脉']) steps.push('   特征脉：' + m.formula['特征脉']);
      if (m.formula['按语']) steps.push('   按：' + m.formula['按语']);
    }
    result = matches[0].formula.name + ' 方向。' + matches[0].formula['六经'] + '·' + matches[0].formula['八纲'];
  }
  
  return { steps: steps, result: result, herbs: [], matchedSyndromes: matches.slice(0, 5) };
}

function simpleHXSDiagnose(symptoms, complaint, pulseClues) {
  var all = symptoms.join(',') + ' ' + complaint;
  var steps = [], result = '';
  steps.push('【症状驱动为主】脉象辅助八纲判断' + (pulseClues && pulseClues.length > 0 ? ' 脉→' + pulseClues.join('、') : ''));
  
  if (all.indexOf('往来寒热') >= 0 || all.indexOf('口苦') >= 0 || all.indexOf('胸胁') >= 0) {
    steps.push('少阳提纲命中 → 小柴胡汤方向');
    result = '小柴胡汤加减';
  } else if ((all.indexOf('腹满') >= 0 || all.indexOf('吐') >= 0 || all.indexOf('下利') >= 0)) {
    steps.push('太阴提纲倾向 → 理中汤方向');
    result = '理中汤/四逆汤辈';
  } else if (all.indexOf('恶寒') >= 0 || all.indexOf('脉浮') >= 0) {
    steps.push('太阳提纲倾向 → 桂麻方向');
    result = '建议补充汗出情况以定桂麻';
  } else {
    steps.push('六经提纲未命中');
    result = '需更完整症状描述以启动103方症候群精确匹配';
  }
  return { steps: steps, result: result, herbs: [] };
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
