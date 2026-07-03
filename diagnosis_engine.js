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
      'zhangxichun': 'pulse_match_zxc_compact_v3.json',
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

// ========== 寸部力度评估（张锡纯升陷汤关键前驱）==========
// 根据寸部脉形+力度返回虚弱等级 0-4（级别越高越虚弱）
// level 3(微)/4(摸不到)=大气下陷标准脉象；level 2(弱)=需结合症状确认
function getCunForceLevels(d) {
  var result = { left: 0, right: 0 };
  var FORCE_MAP = {
    '有力': 0, '稍有力': 0,
    '中（不有力不无力）': 1, '中': 1, '细': 1,
    '无力': 2, '弱': 2, '濡': 2,
    '微': 3, '按之即无': 3, '芤': 3, '散': 3,
    '摸不到': 4, '极微': 4
  };
  function evalCun(cun) {
    if (!cun) return 0;
    var level = 0;
    // 力度优先
    if (cun.force && FORCE_MAP.hasOwnProperty(cun.force)) {
      level = Math.max(level, FORCE_MAP[cun.force]);
    }
    // 脉形补充评定
    if (cun.shape) {
      var shapes = typeof cun.shape === 'string' ? cun.shape.split(',').map(function(s){return s.trim();}) : cun.shape;
      for (var i = 0; i < shapes.length; i++) {
        if (FORCE_MAP.hasOwnProperty(shapes[i])) {
          level = Math.max(level, FORCE_MAP[shapes[i]]);
        }
      }
    }
    return level;
  }
  result.left  = evalCun(d.leftCun);
  result.right = evalCun(d.rightCun);
  return result;
}

// ========== 张锡纯 气机升降辨证（v8：三步漏斗 + 原著脉案匹配）==========
// 数据文件：pulse_match_zxc_compact_v2.json（172方，从原著提取）
// 辨证流程：Step1方向 → Step2方剂 → Step3脉诊确认
function diagnoseZhangXichun(formData, symptoms, complaint) {
  // ===== 构建 text 描述 =====
  var textParts = [];
  var zL = formData.zx_zongL || '';
  var zLF = formData.zx_zongLF || '';
  var zR = formData.zx_zongR || '';
  var zRF = formData.zx_zongRF || '';
  if (zL) { var lp='左手总按：'+zL; if(zLF) lp+=zLF; textParts.push(lp); }
  if (zR) { var rp='右手总按：'+zR; if(zRF) rp+=zRF; textParts.push(rp); }
  var posLabels = ['左寸','左关','左尺','右寸','右关','右尺'];
  var posKeys = ['zx_cunLMx','zx_guanLMx','zx_chiLMx','zx_cunRMx','zx_guanRMx','zx_chiRMx'];
  var posForceKeys = ['zx_cunLF','zx_guanLF','zx_chiLF','zx_cunRF','zx_guanRF','zx_chiRF'];
  for (var pi=0; pi<6; pi++) {
    var ps = formData[posKeys[pi]] || [];
    var pf = formData[posForceKeys[pi]] || '';
    if (ps.length) { var pt=posLabels[pi]+':'+ps.join(','); if(pf) pt+='('+pf+')'; textParts.push(pt); }
  }
  if (symptoms && symptoms.length) textParts.push('症状：'+symptoms.join('，'));
  if (complaint) textParts.push('主诉：'+complaint);
  var text = textParts.join('。');

  var d = {
    zongLeft:  { shape: zL, force: zLF },
    zongRight: { shape: zR, force: zRF },
    leftCun:   { shape: (formData.zx_cunLMx||[]).join(','), force: formData.zx_cunLF || '' },
    leftGuan:  { shape: (formData.zx_guanLMx||[]).join(','), force: formData.zx_guanLF || '' },
    leftChi:   { shape: (formData.zx_chiLMx||[]).join(','), force: formData.zx_chiLF || '' },
    rightCun:  { shape: (formData.zx_cunRMx||[]).join(','), force: formData.zx_cunRF || '' },
    rightGuan: { shape: (formData.zx_guanRMx||[]).join(','), force: formData.zx_guanRF || '' },
    rightChi:  { shape: (formData.zx_chiRMx||[]).join(','), force: formData.zx_chiRF || '' },
    symptoms: symptoms || [],
    complaint: complaint || ''
  };

  var allText = text;
  var sinkingKw=['气短','乏力','下坠感','呼气困难','努力呼吸','气息将停',
                 '短气','大气下陷','怔忡','大汗淋漓','气短不足以息',
                 '神昏','肢体痿废','二便不禁','肛门突出','声颤'];
  var flowKw=['气上冲','呃逆','呕吐','头目眩晕','吸气难','肩息',
              '胃气上逆','哕气','胁下胀疼','冲气','心下有气上冲',
              '腹中有气自下上冲','饮食不下','胸中烦热','昏仆'];
  var nSink=0, nFlow=0;
  for (var i=0;i<sinkingKw.length;i++) if (allText.indexOf(sinkingKw[i])>=0) nSink++;
  for (var i=0;i<flowKw.length;i++) if (allText.indexOf(flowKw[i])>=0) nFlow++;

  var exhaleDiff=allText.indexOf('呼气难')>=0||allText.indexOf('呼气困难')>=0;
  var inhaleDiff=allText.indexOf('吸气难')>=0||allText.indexOf('肩息')>=0;
  var qiDir='neutral';
  var steps=[], result='', herbs=[], warn='', matchedCases=[];

  if (nSink>0 && nFlow===0) { qiDir='sinking'; steps.push('第一步·辨气机：检出'+nSink+'项下陷症状，无上逆 → 判定大气下陷 → 升陷类方池'); }
  else if (nFlow>0 && nSink===0) { qiDir='counterflow'; steps.push('第一步·辨气机：检出'+nFlow+'项上逆症状，无下陷 → 判定气机上逆 → 镇逆类方池'); }
  else if (nSink>0 && nFlow>0) { qiDir='mixed'; steps.push('第一步·辨气机：下陷'+nSink+'项+上逆'+nFlow+'项 → 升降失调 → 全方池评估'); }
  else { steps.push('第一步·辨气机：无明显气机升降偏倾 → 基于脉诊深入辨证'); }
  if (exhaleDiff && !inhaleDiff) steps.push('  ⚠ 呼气困难 → 支持大气下陷');
  else if (inhaleDiff) steps.push('  ⚠ 吸气困难/肩息 → 支持气逆之喘');

  // 第二步：脉诊虚实
  var gemaiKw=['革','大而不洪','如按鼓革'];
  var hasGemai=false;
  for (var i=0;i<gemaiKw.length;i++) if (allText.indexOf(gemaiKw[i])>=0) hasGemai=true;
  if (hasGemai) {
    steps.push('第二步·脉诊：⚠ 革脉特征 → 阴阳离绝之险 → 禁峻下，急收敛固脱');
    warn='革脉——阴阳离绝之险！虽见便结腹满，禁忌峻下！';
  } else {
    var hasHong=allText.indexOf('洪')>=0, hasHua=allText.indexOf('滑')>=0;
    var hasXianYing=allText.indexOf('弦硬')>=0||(allText.indexOf('硬')>=0&&allText.indexOf('弦')<0);
    var hasWeak=allText.indexOf('无力')>=0||allText.indexOf('按之即无')>=0||allText.indexOf('微弱')>=0||allText.indexOf('极微弱')>=0;
    if (hasHong&&hasHua) steps.push('第二步·脉诊：洪滑兼具 → 真有力，实热实证');
    else if (hasXianYing&&!hasHong&&!hasHua) steps.push('第二步·脉诊：弦硬但无洪滑 → 假有力（阴虚阳浮）→ 滋阴潜阳，忌峻攻');
    else if (hasWeak) steps.push('第二步·脉诊：三部总按无力 → 虚证，补益为主');
    else steps.push('第二步·脉诊：脉力未见明确偏颇，继续辨浮沉数迟');
    if (allText.indexOf('浮')>=0) steps.push('  └ 浮脉 → 表证或阴虚阳浮');
    if (allText.indexOf('沉')>=0) steps.push('  └ 沉脉 → 里证或大气下陷');
    if (allText.indexOf('数')>=0 && hasWeak) steps.push('  └ 数而无力 → 虚！忌寒凉。原著：见数脉便用凉药，杀人无数');
    else if (allText.indexOf('数')>=0) steps.push('  └ 数而有力 → 真热');
    if (allText.indexOf('迟')>=0) steps.push('  └ 迟而无力 → 大气下陷；迟而有力 → 寒积');
    var cunLevels = getCunForceLevels(d);
    if (cunLevels.right >= 3) steps.push('  └ 右寸力度量尺：level '+cunLevels.right+'（≥微弱）→ 大气下陷标准脉象');
    else if (cunLevels.right >= 2 && cunLevels.left >= 2) steps.push('  └ 两寸皆弱 → 关前尤甚，支持升陷');
    else if (cunLevels.left >= 3) steps.push('  └ 左寸力度：level '+cunLevels.left+'（≥微弱），但右寸非弱 → 需结合症状确认');
  }

  // 第三步：左右脏腑
  var leftStr=zL+' '+(zLF||''), rightStr=zR+' '+(zRF||''), combined=leftStr+' '+rightStr;
  var xuanMatched='';
  if (combined.indexOf('弦硬')>=0 && rightStr.indexOf('弦硬')>=0 && (rightStr.indexOf('长')>=0||zR==='大')) { xuanMatched='左右弦硬有力长 → 冲气上冲 → 镇逆+滋阴'; if (qiDir!=='counterflow') qiDir='mixed'; }
  else if (leftStr.indexOf('弦硬')>=0 && rightStr.indexOf('洪')>=0) xuanMatched='左弦硬+右洪实 → 肝火+阳明热 → 白虎加人参汤';
  else if (leftStr.indexOf('弦硬')>=0 && (rightStr.indexOf('沉')>=0||rightStr.indexOf('濡')>=0)) xuanMatched='左弦硬+右濡沉 → 湿痰留饮，中焦气化不足';
  else if (leftStr.indexOf('弦细')>=0 && leftStr.indexOf('无力')>=0) xuanMatched='左弦细无力 → 肝血虚、大气下陷 → 升陷方向';
  else if (leftStr.indexOf('弦硬')>=0 && leftStr.indexOf('无力')<0) xuanMatched='左弦硬（假有力，肝木横恣）→ 镇降';
  else if (combined.indexOf('弦无力')>=0) xuanMatched='弦无力（真无力，气化已衰）→ 补升';
  else if (leftStr.indexOf('微细')>=0 && leftStr.indexOf('按之即无')>=0) xuanMatched='左微细模糊按之即无 → 肝胆虚热/肝虚胁痛 → 滋阴柔肝';
  else if (leftStr.indexOf('弦硬')<0 && rightStr.indexOf('弦硬')>=0) { xuanMatched='右弦硬有力长（>左脉）→ 冲气上冲、胃气不降 → 参赭镇气汤/镇逆汤'; if (qiDir==='neutral') qiDir='counterflow'; }
  else if (leftStr.indexOf('弦')>=0 && rightStr.indexOf('弦')>=0 && combined.indexOf('无力')>=0) xuanMatched='左右弦细无力 → 气血两亏、阴阳两虚 → 双补气血';

  if (xuanMatched) steps.push('第三步·左右脏腑：'+xuanMatched);
  else {
    var leftExcess=false, rightExcess=false;
    var excShapes=['洪','大','硬','革','实','滑','紧','弦'];
    for (var e=0;e<excShapes.length;e++) { if (zL.indexOf(excShapes[e])>=0) leftExcess=true; if (zR.indexOf(excShapes[e])>=0) rightExcess=true; }
    if (zLF==='有力'||zLF==='弹指') leftExcess=true;
    if (zRF==='有力'||zRF==='弹指') rightExcess=true;
    if (rightExcess&&!leftExcess) steps.push('第三步·左右脏腑：右脉实+左脉虚 → 冲气上冲、胃气不降 → 镇逆降胃');
    else if (leftExcess&&!rightExcess) steps.push('第三步·左右脏腑：左脉实+右脉虚 → 肝阳上亢、阴虚火旺 → 平肝滋阴');
    else if (!leftExcess && !rightExcess) steps.push('第三步·左右脏腑：左右皆虚 → 以寸部为重点辨大气下陷');
    else steps.push('第三步·左右脏腑：左右皆实 → 辨真热假热');
  }

  // 第四步：尺部
  var chiNoRoot = (d.leftChi.force==='按之即无'&&d.rightChi.force==='按之即无')||((d.leftChi.shape==='微'||d.leftChi.shape==='弱')&&(d.rightChi.shape==='微'||d.rightChi.shape==='弱')&&(d.leftChi.force==='按之即无'||d.rightChi.force==='按之即无'));
  var chiWeak = d.leftChi.shape==='弱'||d.leftChi.shape==='微'||d.leftChi.force==='按之即无'||d.rightChi.shape==='弱'||d.rightChi.shape==='微'||d.rightChi.force==='按之即无';
  if (chiNoRoot||(allText.indexOf('尺脉无根')>=0)) { steps.push('第四步·尺部虚里：⚠ 尺脉无根 → 肝肾虚极，急防虚脱！'); if (!warn) warn='尺脉无根——肝肾虚极！急防虚脱。'; }
  else if (chiWeak) steps.push('第四步·尺部虚里：尺脉虚弱 → 阳升而阴不能应，滋阴为要');
  else if (d.leftChi.shape||d.rightChi.shape) steps.push('第四步·尺部虚里：尺脉有根 → 预后可治');
  else steps.push('第四步·尺部虚里：尺部未提供 → 建议补充以决预后');

  // 第五步：数据驱动方证匹配（pulse_match_zxc_compact_v3.json，293条方证特征，源自772原始医案）
  var formulas=[], direction=formData.zx_direction||'';
  var data = DataCache['zhangxichun'];

  if (data && !data._error && !data._no_data && Array.isArray(data)) {
    // 构建用户脉象搜索池：总按 + 力度 + 六部
    var pulsePool = (zL + ' ' + (zLF||'') + ' ' + zR + ' ' + (zRF||''));
    for (var pi2=0; pi2<6; pi2++) {
      var ps2 = formData[posKeys[pi2]] || [];
      var pf2 = formData[posForceKeys[pi2]] || '';
      if (ps2.length) pulsePool += ' ' + ps2.join(',');
      if (pf2) pulsePool += ' ' + pf2;
    }

    // 逐条匹配打分
    for (var ei=0; ei<data.length; ei++) {
      var entry = data[ei], feats = entry.feats;
      if (!feats) continue;
      var score = 0, reasons = [];

      // 总体脉象
      if (feats.总体) {
        for (var fj=0; fj<feats.总体.length; fj++) {
          if (pulsePool.indexOf(feats.总体[fj]) >= 0) { score += 3; reasons.push('脉:'+feats.总体[fj]); }
        }
      }
      // 左脉
      if (feats.左) {
        for (var fj=0; fj<feats.左.length; fj++) {
          if (zL.indexOf(feats.左[fj]) >= 0) { score += 4; reasons.push('左:'+feats.左[fj]); }
        }
      }
      // 右脉
      if (feats.右) {
        for (var fj=0; fj<feats.右.length; fj++) {
          if (zR.indexOf(feats.右[fj]) >= 0) { score += 4; reasons.push('右:'+feats.右[fj]); }
        }
      }
      // 力度
      if (feats.力度 && feats.力度 !== '') {
        if (zLF===feats.力度 || zRF===feats.力度 || (zLF+' '+zRF).indexOf(feats.力度)>=0) {
          score += 3; reasons.push('力度:'+feats.力度);
        }
      }
      // 速率（含数字如 "数" "迟" "5" "6"）
      if (feats.速率 && feats.速率 !== '') {
        if (pulsePool.indexOf('数')>=0 && feats.速率==='数') { score += 3; reasons.push('速率:数'); }
        else if (pulsePool.indexOf('迟')>=0 && feats.速率==='迟') { score += 3; reasons.push('速率:迟'); }
        else if (pulsePool.indexOf(feats.速率)>=0) { score += 2; reasons.push('速率:'+feats.速率); }
      }
      // 医案数量加权（>5案加1分, >15案加2分）
      if (entry.case_count >= 15) score += 2;
      else if (entry.case_count >= 5) score += 1;

      if (score > 0) {
        formulas.push({
          name: entry.formula,
          score: score,
          reasons: reasons,
          case_count: entry.case_count || 0
        });
      }
    }
    formulas.sort(function(a,b){ return b.score - a.score; });

    if (formulas.length > 0) {
      var topN = Math.min(5, formulas.length);
      steps.push('第五步·数据驱动方证匹配：共匹配'+formulas.length+'条方剂（源自772医案），Top '+topN+'：'
        + formulas.slice(0,topN).map(function(f){ return f.name+'('+f.score+'分/'+f.case_count+'案)'; }).join(' > '));
    }
  }

  // 回退层：数据不可用或匹配为空时，启用硬编码基础方剂（评分降低以区分）
  if (formulas.length === 0) {
    if (direction==='sink'||qiDir==='sinking'||qiDir==='mixed') {
      if (allText.indexOf('身冷')>=0||allText.indexOf('恶寒')>=0||allText.indexOf('心肺阳虚')>=0) formulas.push({name:'回阳升陷汤',score:5,reasons:['关键词:心肺阳虚']});
      if (allText.indexOf('胸中满痛')>=0||allText.indexOf('胁胀')>=0) formulas.push({name:'理郁升陷汤',score:5,reasons:['关键词:气分郁结']});
      if (allText.indexOf('小便不禁')>=0||allText.indexOf('脾气虚')>=0) formulas.push({name:'醒脾升陷汤',score:5,reasons:['关键词:脾气虚极']});
      if (formulas.length===0) formulas.push({name:'升陷汤',score:3,reasons:['大气下陷基础方']});
    }
    if (direction==='up'||qiDir==='counterflow'||qiDir==='mixed') {
      if (xuanMatched&&xuanMatched.indexOf('弦硬')>=0||rightStr.indexOf('弦硬')>=0) formulas.push({name:'参赭镇气汤',score:5,reasons:['关键词:弦硬冲逆']});
      if (allText.indexOf('呕吐')>=0||allText.indexOf('胃气上逆')>=0||allText.indexOf('呃逆')>=0) formulas.push({name:'镇逆汤',score:4,reasons:['关键词:冲胃并逆']});
      if (allText.indexOf('吐血')>=0||allText.indexOf('衄血')>=0||allText.indexOf('咳血')>=0) {
        if (allText.indexOf('洪')>=0&&allText.indexOf('滑')>=0) formulas.push({name:'寒降汤',score:4,reasons:['关键词:吐衄阳明实热']});
        else formulas.push({name:'温降汤',score:3,reasons:['关键词:吐衄虚寒']});
      }
      if (formulas.filter(function(f){return f.score>=5;}).length===0) formulas.push({name:'参赭镇气汤',score:2,reasons:['冲逆基础方(回退)']});
    }
    formulas.sort(function(a,b){return b.score-a.score;});
    if (formulas.length>0) {
      steps.push('第五步·方证锁定(回退模式)：'+formulas.slice(0,3).map(function(f){return f.name+'('+f.score+'分)';}).join(' > '));
    }
  }

  if (formulas.length > 0) {
    var top = formulas[0];
    result = '推荐方剂：'+top.name;
    if (top.case_count) result += '（源自'+top.case_count+'则医案）';
    if (top.reasons && top.reasons.length) result += ' 脉象依据：'+top.reasons.join('，');
    herbs = [];
  }
  return {steps:steps, result:result, herbs:herbs, matchedCases:matchedCases, warn:warn||''};
}


function extractZXCFeatures(formData) {
  var feats = {
    left: [], right: [],           // 整合左右脉（向后兼容）
    cunL: [], guanL: [], chiL: [], // 左三部
    cunR: [], guanR: [], chiR: [], // 右三部
    force: '', speed: ''
  };
  var zL  = formData.zx_zongL  || '';
  var zLF = formData.zx_zongLF || '';
  var zR  = formData.zx_zongR  || '';
  var zRF = formData.zx_zongRF || '';

  // 分别收集左右chip勾选
  var leftMx = [], rightMx = [];
  ['cunL','guanL','chiL'].forEach(function(k){
    var v = formData['zx_'+k+'Mx'];
    if (v && v.length) leftMx = leftMx.concat(v);
  });
  ['cunR','guanR','chiR'].forEach(function(k){
    var v = formData['zx_'+k+'Mx'];
    if (v && v.length) rightMx = rightMx.concat(v);
  });
  // 每部位的独立脉形
  feats.cunL  = formData.zx_cunLMx  || [];
  feats.guanL = formData.zx_guanLMx || [];
  feats.chiL  = formData.zx_chiLMx  || [];
  feats.cunR  = formData.zx_cunRMx  || [];
  feats.guanR = formData.zx_guanRMx || [];
  feats.chiR  = formData.zx_chiRMx  || [];

  var terms = ['弦硬','弦细','弦数','弦长','弦浮','弦滑','弦大','弦','细','弱','浮','沉','洪','滑','涩','大','硬','微','数','迟','紧','缓','散','濡','芤','结','代'];

  // === 左脉特征 ===
  // 优先使用总按chip组（用户明确勾选的脉形，源自772案数据）
  var zongLMx = formData.zx_zongLMx || [];
  if (zongLMx.length) {
    feats.left = zongLMx.slice();
  } else if (zL) {
    for (var i = 0; i < terms.length; i++) {
      if (zL.indexOf(terms[i]) >= 0) feats.left.push(terms[i]);
    }
  }
  if (feats.left.length === 0 && leftMx.length) {
    for (var j = 0; j < terms.length; j++) {
      if (leftMx.indexOf(terms[j]) >= 0) feats.left.push(terms[j]);
    }
  }

  // === 右脉特征 ===
  var zongRMx = formData.zx_zongRMx || [];
  if (zongRMx.length) {
    feats.right = zongRMx.slice();
  } else if (zR) {
    for (var k = 0; k < terms.length; k++) {
      if (zR.indexOf(terms[k]) >= 0) feats.right.push(terms[k]);
    }
  }
  if (feats.right.length === 0 && rightMx.length) {
    for (var l = 0; l < terms.length; l++) {
      if (rightMx.indexOf(terms[l]) >= 0) feats.right.push(terms[l]);
    }
  }

  // === 力度（统一映射为"有力"/"无力"，与v3数据对齐） ===
  if (zLF) {
    if (zLF.indexOf('无力') >= 0 || zLF === '弦无力' || zLF === '按之即无') feats.force = '无力';
    else if (zLF.indexOf('有力') >= 0 || zLF === '弦硬') feats.force = '有力';
  }
  if (zRF && !feats.force) {
    if (zRF.indexOf('无力') >= 0 || zRF === '弦无力' || zRF === '按之即无') feats.force = '无力';
    else if (zRF.indexOf('有力') >= 0 || zRF === '弦硬') feats.force = '有力';
  }
  if (!feats.force) {
    var fc = { '有力':0, '无力':0, '弦硬':0 };
    ['zx_cunLF','zx_guanLF','zx_chiLF','zx_cunRF','zx_guanRF','zx_chiRF'].forEach(function(k){
      var v = formData[k] || '';
      if (v === '有力' || v === '弦硬') fc['有力']++;
      if (v === '无力') fc['无力']++;
    });
    if (fc['有力'] > fc['无力']) feats.force = '有力';
    else if (fc['无力'] > 0) feats.force = '无力';
  }

  // === 速率 ===
  var allMxForRate = leftMx.concat(rightMx);
  if (zL && zL.indexOf('数') >= 0) feats.speed = '数';
  else if (zL && zL.indexOf('迟') >= 0) feats.speed = '迟';
  else if (zR && zR.indexOf('数') >= 0) feats.speed = '数';
  else if (zR && zR.indexOf('迟') >= 0) feats.speed = '迟';
  else if (allMxForRate.indexOf('数') >= 0) feats.speed = '数';
  else if (allMxForRate.indexOf('迟') >= 0) feats.speed = '迟';

  return feats;
}
function matchZXCCase(caseData, userFeats) {
  var score = 0;
  var cf = caseData.feats || {};

  // ---- 左三部位置匹配（权重×4）----
  ['cunL','guanL','chiL'].forEach(function(pos){
    var user = userFeats[pos] || [];
    var target = cf['左'] || [];
    for (var i = 0; i < user.length; i++) {
      if (target.indexOf(user[i]) >= 0) score += 4;
      else if (cf['总体'] && cf['总体'].indexOf(user[i]) >= 0) score += 1;
    }
  });

  // ---- 右三部位置匹配（权重×4）----
  ['cunR','guanR','chiR'].forEach(function(pos){
    var user = userFeats[pos] || [];
    var target = cf['右'] || [];
    for (var i = 0; i < user.length; i++) {
      if (target.indexOf(user[i]) >= 0) score += 4;
      else if (cf['总体'] && cf['总体'].indexOf(user[i]) >= 0) score += 1;
    }
  });

  // ---- 整合左右回退匹配（权重×2）----
  for (var j = 0; j < userFeats.left.length; j++) {
    if (cf['左'] && cf['左'].indexOf(userFeats.left[j]) >= 0) score += 2;
    if (cf['总体'] && cf['总体'].indexOf(userFeats.left[j]) >= 0) score += 1;
  }
  for (var k = 0; k < userFeats.right.length; k++) {
    if (cf['右'] && cf['右'].indexOf(userFeats.right[k]) >= 0) score += 2;
    if (cf['总体'] && cf['总体'].indexOf(userFeats.right[k]) >= 0) score += 1;
  }

  // ---- 力度匹配（权重×5）----
  // userFeats.force: "有力"/"无力"; cf['力度']: "有力"/"弦硬有力"/"无力"/"虚"/"实"
  if (userFeats.force && cf['力度']) {
    var uf = userFeats.force;
    var df = cf['力度'];
    if (df.indexOf(uf) >= 0) score += 5;
    else if ((uf === '有力' && (df === '实' || df.indexOf('弦硬') >= 0 || df.indexOf('有力') >= 0)) ||
             (uf === '无力' && (df === '虚' || df === '按之即无' || df.indexOf('无力') >= 0))) score += 4;
  }

  // ---- 速率匹配（权重×3）----
  if (userFeats.speed && cf['速率']) {
    var ur = userFeats.speed;
    var dr = String(cf['速率']);
    // 数字速率（5,6,7,...）→ 数; 3→迟
    var drNorm = dr;
    if (/^\d+$/.test(dr)) { var n = parseInt(dr); drNorm = n >= 5 ? '数' : '迟'; }
    if (drNorm === ur || dr === ur) score += 3;
  }

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
var HXS_PULSE_WEIGHTS = [
  { formula: '桂枝汤', liujing: '太阳', bagang: '表阳·虚·中风', triggers: ["发热", "汗出", "恶风", "头项强痛", "鼻鸣干呕"], patterns: [{"p": ["浮", "缓"], "w": 8}, {"p": ["浮", "弱"], "w": 8}] },
  { formula: '桂枝加葛根汤', liujing: '太阳', bagang: '表阳·虚·中风兼项背强', triggers: ["汗出", "恶风", "项背强几几"], patterns: [{"p": ["浮", "缓"], "w": 8}] },
  { formula: '桂枝加厚朴杏子汤', liujing: '太阳', bagang: '表阳·虚·中风兼喘', triggers: ["汗出", "恶风", "喘"], patterns: [{"p": ["浮", "缓"], "w": 8}] },
  { formula: '桂枝加附子汤', liujing: '太阳→少阴', bagang: '表阴·虚·过汗亡阳', triggers: ["汗漏不止", "恶风", "小便难", "四肢微急难以屈伸"], patterns: [{"p": ["浮", "弱", "微"], "w": 10}] },
  { formula: '桂枝去芍药汤', liujing: '太阳', bagang: '表阳·虚·胸阳不振', triggers: ["恶风发热", "胸满", "脉促"], patterns: [{"p": ["沉", "浮", "促"], "w": 10}] },
  { formula: '桂枝去芍药加附子汤', liujing: '太阳→少阴', bagang: '表阴·虚·胸阳衰微', triggers: ["恶风寒", "胸满", "脉微"], patterns: [{"p": ["微"], "w": 5}] },
  { formula: '桂枝加芍药生姜各一两人参三两新加汤', liujing: '太阳', bagang: '表阳·虚·气血不足', triggers: ["发汗后身疼痛", "脉沉迟"], patterns: [{"p": ["沉", "迟"], "w": 8}] },
  { formula: '麻黄汤', liujing: '太阳', bagang: '表阳·实·伤寒', triggers: ["发热恶寒", "无汗", "身疼腰痛", "骨节疼痛", "喘"], patterns: [{"p": ["浮", "紧"], "w": 8}] },
  { formula: '葛根汤', liujing: '太阳', bagang: '表阳·实·伤寒兼项背强', triggers: ["发热恶寒", "无汗", "项背强几几"], patterns: [{"p": ["浮", "紧"], "w": 8}] },
  { formula: '葛根加半夏汤', liujing: '太阳阳明合病', bagang: '表阳·实·兼呕', triggers: ["发热恶寒", "无汗", "项背强", "不下利但呕"], patterns: [{"p": ["浮", "紧"], "w": 8}] },
  { formula: '葛根黄芩黄连汤', liujing: '太阳阳明合病', bagang: '表阳未解·里热', triggers: ["汗出而喘", "下利", "喘而汗出"], patterns: [{"p": ["沉", "浮", "促"], "w": 10}] },
  { formula: '大青龙汤', liujing: '太阳阳明合病', bagang: '表阳·实·外寒里热', triggers: ["恶寒发热", "无汗", "烦躁", "身疼痛", "不汗出而烦躁"], patterns: [{"p": ["浮", "紧"], "w": 8}] },
  { formula: '小青龙汤', liujing: '太阳太阴合病', bagang: '表阳·实·外寒内饮', triggers: ["恶寒发热", "无汗", "咳喘", "干呕", "不渴", "或利/噎/小便不利/少腹满"], patterns: [{"p": ["浮", "弦", "紧"], "w": 10}] },
  { formula: '麻黄杏仁甘草石膏汤', liujing: '太阳阳明合病', bagang: '表邪未尽·里热壅肺', triggers: ["汗出", "喘", "无大热"], patterns: [{"p": ["浮", "数"], "w": 8}] },
  { formula: '桂枝麻黄各半汤', liujing: '太阳', bagang: '表阳·微邪·小邪在表', triggers: ["发热恶寒如疟状", "热多寒少", "面有热色", "身痒"], patterns: [{"p": ["浮", "微"], "w": 8}] },
  { formula: '桂枝二麻黄一汤', liujing: '太阳', bagang: '表阳·虚多实少', triggers: ["发热恶寒形似疟", "一日再发"], patterns: [{"p": ["浮", "缓", "微"], "w": 10}] },
  { formula: '桂枝二越婢一汤', liujing: '太阳阳明', bagang: '表阳·微邪兼微热', triggers: ["发热恶寒", "热多寒少", "微烦"], patterns: [{"p": ["弱", "微"], "w": 8}] },
  { formula: '桂枝去桂加茯苓白术汤', liujing: '太阳太阴', bagang: '表未全解·水饮内停', triggers: ["头项强痛", "翕翕发热", "无汗", "心下满微痛", "小便不利"], patterns: [] },
  { formula: '五苓散', liujing: '太阳太阴合病', bagang: '表未解·水蓄膀胱', triggers: ["脉浮", "小便不利", "微热消渴", "烦渴", "水入即吐"], patterns: [{"p": ["浮", "数"], "w": 8}] },
  { formula: '茯苓桂枝白术甘草汤', liujing: '太阴（兼太阳）', bagang: '里阴·虚·水饮上冲', triggers: ["心下逆满", "气上冲胸", "起则头眩", "身为振振摇"], patterns: [{"p": ["沉", "紧"], "w": 8}] },
  { formula: '茯苓甘草汤', liujing: '太阳太阴', bagang: '表未解·胃中水停', triggers: ["厥而心下悸"], patterns: [] },
  { formula: '桂枝甘草汤', liujing: '太阳', bagang: '表阳·虚·心阳虚', triggers: ["叉手自冒心", "心下悸", "欲得按"], patterns: [] },
  { formula: '桂枝甘草龙骨牡蛎汤', liujing: '太阳', bagang: '表阳·虚·心阳虚烦躁', triggers: ["烦躁", "心悸"], patterns: [] },
  { formula: '桂枝去芍药加蜀漆牡蛎龙骨救逆汤', liujing: '太阳', bagang: '表阳·虚·亡阳惊狂', triggers: ["惊狂", "卧起不安"], patterns: [] },
  { formula: '桂枝加桂汤', liujing: '太阳', bagang: '表阳·虚·奔豚', triggers: ["气从少腹上冲心"], patterns: [] },
  { formula: '桂枝加芍药汤', liujing: '太阴', bagang: '里阴·虚·腹满时痛', triggers: ["腹满时痛"], patterns: [] },
  { formula: '桂枝加大黄汤', liujing: '太阴阳明合病', bagang: '里阴兼里实', triggers: ["腹满大实痛"], patterns: [] },
  { formula: '麻黄附子细辛汤', liujing: '少阴', bagang: '表阴·虚寒', triggers: ["但恶寒", "不发热", "反发热", "无汗", "脉沉"], patterns: [{"p": ["细", "沉"], "w": 8}] },
  { formula: '麻黄附子甘草汤', liujing: '少阴', bagang: '表阴·虚寒（轻证）', triggers: ["恶寒", "无汗", "得之二三日"], patterns: [{"p": ["沉"], "w": 5}] },
  { formula: '附子汤', liujing: '少阴', bagang: '表阴·虚寒·身痛', triggers: ["背恶寒", "身体痛", "手足寒", "骨节痛"], patterns: [{"p": ["沉"], "w": 5}] },
  { formula: '真武汤', liujing: '少阴太阴合病', bagang: '里阴·虚·水气泛滥', triggers: ["心下悸", "头眩", "身瞤动", "振振欲擗地", "腹痛", "小便不利", "四肢沉重疼痛", "下利"], patterns: [{"p": ["沉", "弦"], "w": 8}] },
  { formula: '四逆汤', liujing: '少阴太阴', bagang: '里阴·虚寒·亡阳', triggers: ["四肢厥逆", "下利清谷", "恶寒踡卧", "但欲寐", "大汗出", "热不去"], patterns: [{"p": ["细", "微"], "w": 8}, {"p": ["沉", "微"], "w": 8}] },
  { formula: '四逆加人参汤', liujing: '少阴', bagang: '里阴·虚寒·亡阳兼亡津液', triggers: ["恶寒", "脉微", "下利", "利止亡血"], patterns: [{"p": ["微"], "w": 5}] },
  { formula: '通脉四逆汤', liujing: '少阴', bagang: '里阴·虚寒·阴盛格阳', triggers: ["下利清谷", "里寒外热", "手足厥逆", "身反不恶寒", "面色赤"], patterns: [{"p": ["微"], "w": 5}] },
  { formula: '白通汤', liujing: '少阴', bagang: '里阴·虚寒·阴盛戴阳', triggers: ["下利", "恶寒", "脉微", "面赤"], patterns: [{"p": ["微"], "w": 5}] },
  { formula: '白通加猪胆汁汤', liujing: '少阴', bagang: '里阴·虚寒·阴盛格阳兼阴竭', triggers: ["下利不止", "厥逆无脉", "干呕烦"], patterns: [] },
  { formula: '干姜附子汤', liujing: '少阴', bagang: '里阴·虚寒·昼躁夜静', triggers: ["昼日烦躁不得眠", "夜而安静", "不呕不渴无表证"], patterns: [{"p": ["沉", "微"], "w": 8}] },
  { formula: '茯苓四逆汤', liujing: '少阴', bagang: '里阴·虚寒·阴阳两虚烦躁', triggers: ["烦躁", "恶寒", "下利", "厥逆"], patterns: [{"p": ["细", "微"], "w": 8}] },
  { formula: '芍药甘草附子汤', liujing: '少阴', bagang: '里阴·虚·阴阳两虚', triggers: ["发汗后恶寒", "脚挛急"], patterns: [] },
  { formula: '甘草干姜汤', liujing: '太阴少阴', bagang: '里阴·虚寒·肺痿', triggers: ["吐涎沫", "不咳", "遗尿", "小便数", "眩"], patterns: [] },
  { formula: '芍药甘草汤', liujing: '太阳（变证）', bagang: '阴血不足', triggers: ["脚挛急", "或腹挛痛"], patterns: [] },
  { formula: '桂枝加附子汤(重出)', liujing: '太阳少阴', bagang: '表阳转表阴·过汗亡阳', triggers: ["发汗遂漏不止", "恶风", "小便难", "四肢微急"], patterns: [{"p": ["浮", "弱"], "w": 8}] },
  { formula: '白虎汤', liujing: '阳明', bagang: '里阳·实·热', triggers: ["大热", "大汗出", "口大渴", "心烦"], patterns: [{"p": ["洪", "大"], "w": 8}, {"p": ["浮", "滑"], "w": 8}] },
  { formula: '白虎加人参汤', liujing: '阳明', bagang: '里阳·实·热盛伤津', triggers: ["大热", "大渴", "口舌干燥", "欲饮水数升", "心烦", "背微恶寒"], patterns: [{"p": ["洪", "大", "芤"], "w": 10}] },
  { formula: '调胃承气汤', liujing: '阳明', bagang: '里阳·实·燥热', triggers: ["蒸蒸发热", "腹胀满", "心烦", "大便不通"], patterns: [{"p": ["实"], "w": 5}] },
  { formula: '小承气汤', liujing: '阳明', bagang: '里阳·实·痞满实', triggers: ["腹大满", "大便硬", "谵语", "潮热"], patterns: [{"p": ["滑"], "w": 5}] },
  { formula: '大承气汤', liujing: '阳明', bagang: '里阳·实·痞满燥实', triggers: ["潮热", "谵语", "手足濈然汗出", "腹满硬痛拒按", "大便硬结不通"], patterns: [{"p": ["沉", "实"], "w": 8}, {"p": ["沉", "迟", "有力"], "w": 10}] },
  { formula: '麻子仁丸', liujing: '阳明', bagang: '里阳·实·脾约', triggers: ["大便硬", "小便数", "不更衣十日无所苦"], patterns: [{"p": ["浮", "涩"], "w": 8}] },
  { formula: '蜜煎导方', liujing: '阳明', bagang: '里阳·津亏便秘（外用）', triggers: ["大便硬", "欲解不能"], patterns: [] },
  { formula: '栀子豉汤', liujing: '阳明（余热）', bagang: '里热·虚烦', triggers: ["虚烦不得眠", "心中懊憹", "反复颠倒"], patterns: [] },
  { formula: '栀子甘草豉汤', liujing: '阳明（余热）', bagang: '里热·虚烦·兼气虚', triggers: ["虚烦不得眠", "心中懊憹", "少气"], patterns: [] },
  { formula: '栀子生姜豉汤', liujing: '阳明（余热）', bagang: '里热·虚烦·兼呕', triggers: ["虚烦不得眠", "心中懊憹", "呕"], patterns: [] },
  { formula: '栀子厚朴汤', liujing: '阳明太阴', bagang: '里热兼气滞', triggers: ["心烦", "腹满", "卧起不安"], patterns: [] },
  { formula: '栀子干姜汤', liujing: '阳明太阴', bagang: '上热下寒', triggers: ["身热", "微烦", "下利"], patterns: [] },
  { formula: '茵陈蒿汤', liujing: '阳明', bagang: '里阳·实·湿热黄疸', triggers: ["身黄如橘子色", "小便不利", "腹微满", "头汗出身无汗"], patterns: [] },
  { formula: '猪苓汤', liujing: '阳明少阴', bagang: '里热·水热互结·伤阴', triggers: ["发热", "渴欲饮水", "小便不利", "心烦不得眠"], patterns: [{"p": ["浮"], "w": 5}] },
  { formula: '桃核承气汤', liujing: '太阳阳明合病', bagang: '表未解·血热结于下焦', triggers: ["少腹急结", "其人如狂"], patterns: [] },
  { formula: '抵当汤', liujing: '太阳阳明', bagang: '里实·蓄血重证', triggers: ["少腹硬满", "其人发狂", "善忘", "大便黑"], patterns: [{"p": ["沉", "结"], "w": 8}, {"p": ["沉", "微"], "w": 8}] },
  { formula: '抵当丸', liujing: '太阳阳明', bagang: '里实·蓄血轻证', triggers: ["少腹满", "小便自利"], patterns: [] },
  { formula: '十枣汤', liujing: '太阳', bagang: '表解里实·悬饮', triggers: ["心下痞硬满", "引胁下痛", "干呕短气", "头痛"], patterns: [{"p": ["沉", "弦"], "w": 8}] },
  { formula: '小柴胡汤', liujing: '少阳', bagang: '半表半里·阳', triggers: ["往来寒热", "胸胁苦满", "默默不欲饮食", "心烦喜呕", "口苦咽干目眩"], patterns: [{"p": ["细", "弦"], "w": 8}, {"p": ["弦", "数"], "w": 8}] },
  { formula: '大柴胡汤', liujing: '少阳阳明合病', bagang: '半表半里阳证兼里实', triggers: ["呕不止", "心下急", "郁郁微烦", "热结在里", "心中痞硬", "下利"], patterns: [{"p": ["弦", "数", "有力"], "w": 10}] },
  { formula: '柴胡加芒硝汤', liujing: '少阳阳明', bagang: '半表半里阳证兼燥结', triggers: ["胸胁满而呕", "日晡潮热", "微利"], patterns: [] },
  { formula: '柴胡桂枝汤', liujing: '少阳太阳合病', bagang: '少阳兼表', triggers: ["发热微恶寒", "支节烦疼", "微呕", "心下支结"], patterns: [] },
  { formula: '柴胡桂枝干姜汤', liujing: '少阳太阴合病', bagang: '半表半里阳证兼中寒水饮', triggers: ["胸胁满微结", "小便不利", "渴而不呕", "头汗出", "往来寒热", "心烦"], patterns: [] },
  { formula: '柴胡加龙骨牡蛎汤', liujing: '少阳', bagang: '半表半里·邪气弥漫·烦惊', triggers: ["胸满", "烦惊", "小便不利", "谵语", "一身尽重不可转侧"], patterns: [] },
  { formula: '黄芩汤', liujing: '少阳阳明合病', bagang: '半表半里热·下利', triggers: ["下利", "腹痛", "身热口苦"], patterns: [] },
  { formula: '黄芩加半夏生姜汤', liujing: '少阳', bagang: '半表半里热·下利兼呕', triggers: ["下利", "腹痛", "呕"], patterns: [] },
  { formula: '黄连汤', liujing: '少阳太阴', bagang: '上热下寒', triggers: ["胸中有热", "胃中有邪气", "腹中痛", "欲呕吐"], patterns: [] },
  { formula: '理中汤（理中丸）', liujing: '太阴', bagang: '里阴·虚寒', triggers: ["腹满而吐", "食不下", "自利益甚", "时腹自痛", "不渴"], patterns: [] },
  { formula: '桂枝人参汤', liujing: '太阴兼太阳', bagang: '里阴·虚寒·表里同病', triggers: ["心下痞硬", "下利不止", "表里不解", "恶寒发热"], patterns: [] },
  { formula: '厚朴生姜半夏甘草人参汤', liujing: '太阴', bagang: '里阴·虚·气滞', triggers: ["腹胀满", "食后胀甚"], patterns: [] },
  { formula: '赤石脂禹余粮汤', liujing: '太阴', bagang: '里阴·虚·滑脱下利', triggers: ["下利不止", "滑脱不禁"], patterns: [] },
  { formula: '旋覆代赭汤', liujing: '太阴', bagang: '里阴·虚·胃虚痰阻', triggers: ["心下痞硬", "噫气不除"], patterns: [] },
  { formula: '小建中汤', liujing: '太阴', bagang: '里阴·虚·中焦虚寒', triggers: ["腹中急痛", "心中悸而烦", "手足烦热", "咽干口燥"], patterns: [{"p": ["涩"], "w": 5}, {"p": ["弦"], "w": 5}] },
  { formula: '桂枝去芍药加麻黄细辛附子汤', liujing: '太阴少阴太阳合病', bagang: '里阴·阳虚水停·表不解', triggers: ["心下坚", "大如盘", "边如旋杯"], patterns: [] },
  { formula: '乌梅丸', liujing: '厥阴', bagang: '半表半里·阴·寒热错杂', triggers: ["消渴", "气上撞心", "心中疼热", "饥而不欲食", "食则吐蛔", "久利"], patterns: [] },
  { formula: '当归四逆汤', liujing: '厥阴', bagang: '半表半里·阴·血虚寒凝', triggers: ["手足厥寒", "四肢冷", "或腹中痛", "或肩背腰腿寒痛"], patterns: [{"p": ["细"], "w": 5}, {"p": ["细", "沉"], "w": 8}] },
  { formula: '当归四逆加吴茱萸生姜汤', liujing: '厥阴', bagang: '半表半里·阴·血虚寒凝兼内有久寒', triggers: ["手足厥寒", "脉细欲绝", "久寒", "呕", "吐涎沫", "巅顶痛"], patterns: [{"p": ["细"], "w": 5}] },
  { formula: '麻黄升麻汤', liujing: '厥阴', bagang: '半表半里·阴·上热下寒·正虚邪陷', triggers: ["手足厥逆", "咽喉不利", "唾脓血", "泄利不止", "寸脉沉迟"], patterns: [{"p": ["沉", "迟"], "w": 8}] },
  { formula: '干姜黄芩黄连人参汤', liujing: '厥阴', bagang: '半表半里·阴·上热下寒（寒格）', triggers: ["食入口即吐", "下利"], patterns: [] },
  { formula: '白头翁汤', liujing: '厥阴', bagang: '里热·热利下重', triggers: ["下利", "便脓血", "里急后重", "腹痛", "渴欲饮水"], patterns: [] },
  { formula: '半夏泻心汤', liujing: '太阴阳明合病', bagang: '寒热错杂·痞证', triggers: ["心下痞", "呕", "腹中雷鸣", "下利"], patterns: [] },
  { formula: '生姜泻心汤', liujing: '太阴阳明合病', bagang: '寒热错杂·痞证·水饮食滞', triggers: ["心下痞硬", "干噫食臭", "腹中雷鸣", "下利"], patterns: [] },
  { formula: '甘草泻心汤', liujing: '太阴阳明合病', bagang: '寒热错杂·痞证·胃虚', triggers: ["心下痞硬而满", "下利日数十行", "谷不化", "腹中雷鸣", "干呕心烦不得安"], patterns: [] },
  { formula: '大黄黄连泻心汤', liujing: '阳明', bagang: '里热·痞证（热痞）', triggers: ["心下痞", "按之濡", "其脉关上浮"], patterns: [{"p": ["浮"], "w": 5}] },
  { formula: '附子泻心汤', liujing: '阳明少阴', bagang: '上热下寒·热痞兼阳虚', triggers: ["心下痞", "恶寒", "汗出"], patterns: [] },
  { formula: '大陷胸汤', liujing: '太阳阳明合病', bagang: '里阳·实·水热互结', triggers: ["心下痛", "按之石硬", "从心下至少腹硬满而痛不可近", "不大便", "日晡潮热"], patterns: [{"p": ["沉", "紧"], "w": 8}] },
  { formula: '大陷胸丸', liujing: '太阳阳明合病', bagang: '里阳·实·水热在上', triggers: ["结胸", "项强如柔痉状"], patterns: [] },
  { formula: '小陷胸汤', liujing: '太阳阳明', bagang: '里阳·实·痰热互结', triggers: ["正在心下", "按之则痛"], patterns: [{"p": ["浮", "滑"], "w": 8}] },
  { formula: '文蛤散', liujing: '太阳', bagang: '表热·渴', triggers: ["渴欲饮水不止"], patterns: [] },
  { formula: '瓜蒂散', liujing: '太阳', bagang: '实·痰食在上', triggers: ["胸中痞硬", "气上冲咽喉不得息"], patterns: [] },
  { formula: '吴茱萸汤', liujing: '阳明少阴厥阴', bagang: '里阴·虚寒·肝胃虚寒', triggers: ["食谷欲呕", "吐利", "手足逆冷", "烦躁欲死", "干呕吐涎沫头痛"], patterns: [] },
  { formula: '炙甘草汤', liujing: '太阳少阴', bagang: '阴血虚·心阴阳两虚', triggers: ["心动悸", "脉结代"], patterns: [{"p": ["结", "代"], "w": 8}] },
  { formula: '竹叶石膏汤', liujing: '阳明', bagang: '里热·气津两伤', triggers: ["虚羸少气", "气逆欲吐", "发热", "烦渴"], patterns: [] },
  { formula: '牡蛎泽泻散', liujing: '太阳', bagang: '水气·腰以下肿', triggers: ["腰以下有水气", "肿"], patterns: [] },
  { formula: '烧裈散', liujing: '阴阳易', bagang: '', triggers: ["身重少气", "少腹里急", "阴中拘挛", "热上冲胸", "头重不欲举"], patterns: [] },
  { formula: '黄连阿胶汤', liujing: '少阴', bagang: '阴虚火旺（少阴热化）', triggers: ["心中烦", "不得卧"], patterns: [] },
  { formula: '猪肤汤', liujing: '少阴', bagang: '阴虚咽痛', triggers: ["下利", "咽痛", "胸满", "心烦"], patterns: [] },
  { formula: '苦酒汤', liujing: '少阴', bagang: '痰热咽伤', triggers: ["咽中伤生疮", "不能语言", "声不出"], patterns: [] },
  { formula: '半夏散及汤', liujing: '少阴', bagang: '寒痰咽痛', triggers: ["咽中痛"], patterns: [] },
  { formula: '四逆散', liujing: '少阴（辨为少阳）', bagang: '气郁阳郁', triggers: ["四逆（手足冷）", "或咳", "或悸", "或小便不利", "或腹中痛", "或泄利下重"], patterns: [] },
  { formula: '桃花汤', liujing: '少阴', bagang: '里阴·虚寒·滑脱', triggers: ["下利不止", "便脓血", "腹痛", "小便不利"], patterns: [] }
];

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
