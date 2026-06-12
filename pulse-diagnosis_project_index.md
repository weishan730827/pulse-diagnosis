---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 57820eb7fd6ef0dda45da07410462809_ec2c62be665511f1a99c5254007bceed
    ReservedCode1: 0i4Uc/HWsZ+topwQPfuXTlIqVcCKBf9wy15W5VsmMPhLYQRJAdD8faaINGRPrIFWLEIFukNkSa/aYhqm9mDEgGVe2PduoK7koZr2XtxHDD2lji9iEna8i1YsZNSnhUAQAQT1lG52nk5XGKRhIPxdy4F2ysPbV8QnBDbpTeBxAAsPqWDqwIyEKpgDIAg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 57820eb7fd6ef0dda45da07410462809_ec2c62be665511f1a99c5254007bceed
    ReservedCode2: 0i4Uc/HWsZ+topwQPfuXTlIqVcCKBf9wy15W5VsmMPhLYQRJAdD8faaINGRPrIFWLEIFukNkSa/aYhqm9mDEgGVe2PduoK7koZr2XtxHDD2lji9iEna8i1YsZNSnhUAQAQT1lG52nk5XGKRhIPxdy4F2ysPbV8QnBDbpTeBxAAsPqWDqwIyEKpgDIAg=
---

# pulse-diagnosis 项目索引

## 仓库

- **GitHub**: https://github.com/weishan730827/pulse-diagnosis
- **本地**: /home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/output/
- **备份**: /home/marvis/Marvis/User/oAN1i2ePwijhdLlZVjI-pSbfHGlo/workspace/conv_19eb8a37d20_f48cc2b702ad/temp/v2_project_backup.tar.gz

## 核心文件（15个）

| 文件 | 说明 |
|------|------|
| `bianzheng_shizhi_v2.py` | 核心脚本，22K，交互/命令行双模式 |
| `pulse_db.json` | 40种病脉（姚梅龄体系） |
| `fangzheng_db_v2.json` | 48条方证（伤寒论26+金匮要略12+张锡纯10） |
| `zhiyibang_quant.json` | 知医邦脉诊10维度+30脉∈公式 |
| `zhiyibang_tongue.json` | 知医邦舌诊量表+辨证算法 |
| `zhang_xichun_rules.json` | 张锡纯用药禁忌规则 |
| `hu_xishu_rules.json` | 胡希恕经方辨证规则 |
| `yao_meiling_rules.json` | 姚梅龄脉诊规则 |
| `zheng_qinan_rules.json` | 郑钦安阴阳辨证规则（12条，含伤寒六经+脉诊纲要，三书核验） |
| `liu_duzhou_rules.json` | 刘渡舟十论体系（11条，方证相对+辨证知机+气机+水/火/湿/痰饮/脾胃+古今接轨+六经纲要+苓桂剂群，全文核验） |
| `使用手册_v2.md` | 完整使用手册（11章） |
| `胡希恕_辨证施治概论_全文.md` | 胡希恕唯一正式论文全文 |
| `脉案记录.md` | 临床脉案讨论记录 |
| `升陷温中利湿汤.md` | 巍哥定制方（16味） |
| `README.md` | GitHub项目首页 |

## 编码体系

所有编码三元标注：`[维度: 来源] 编码 = 含义`

严禁跨体系混用编码，严禁编造或推测编码，数据只从已核验JSON原文输出。

## 用户约定

- 称呼：巍哥
- 人设：理智高效
- 体系：胡希恕六经八纲、张锡纯升降辨证+禁忌规则、姚梅龄脉诊独处藏奸、郑钦安阴阳辨证、刘渡舟十论体系（方证相对·辨证知机·气机·水·火·湿·痰饮·脾胃·古今接轨·六经纲要·苓桂剂群），多体系并行
- 方药审查：逐药审查来源依据、药性冲突及方剂啮合关系
- 经典原文：逐条核验原始文献，不确定须标注"未核实"

## 外部引用

张锡纯《医学衷中参西录》全文（1.9M）、胡希恕伤寒论讲稿（1.3M）、胡希恕金匮要略讲稿（951K）位于另一个workspace，当前项目通过本地路径引用，不在本仓库内。
*（内容由AI生成，仅供参考）*
