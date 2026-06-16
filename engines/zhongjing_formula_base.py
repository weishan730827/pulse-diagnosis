"""仲景方剂基座——八家引擎共享的底层方库。
收录《伤寒杂病论》核心方剂，按类编排。

数据结构：每条记录包含 方名、类别、核心条文、主治关键词
支持别名查找：苓桂术甘汤→茯苓桂枝白术甘草汤 等
"""

from typing import Dict, List, Optional


# 临床常用别名 → 基座正式名
ALIASES: Dict[str, str] = {
    "苓桂术甘汤": "茯苓桂枝白术甘草汤",
    "麻杏甘石汤": "麻黄杏仁甘草石膏汤",
    "瓜蒌薤白白酒汤": "栝蒌薤白白酒汤",
    "瓜蒌薤白半夏汤": "栝蒌薤白半夏汤",
    "麻黄连翘赤小豆汤": "麻黄连轺赤小豆汤",
    "金匮肾气丸": "肾气丸",
    "八味肾气丸": "肾气丸",
    "肾气丸": "肾气丸",
    "桂枝加桂汤": "桂枝加桂汤",
    "麻杏石甘汤": "麻黄杏仁甘草石膏汤",
    "桂甘龙牡汤": "桂枝加龙骨牡蛎汤",
}


class ZhongJingFormulaBase:
    """仲景方剂统一基座。八家引擎各自通过诊断OS映射到本库中的方剂。"""

    def __init__(self):
        self._formulas: Dict[str, dict] = {}
        self._build()

    def _build(self):
        categories = self._define_all()
        for cat_name, formulas in categories.items():
            for f in formulas:
                name = f["name"]
                f["category"] = cat_name
                self._formulas[name] = f

    def get(self, name: str) -> Optional[dict]:
        """支持别名查找"""
        if name in self._formulas:
            return self._formulas[name]
        if name in ALIASES:
            return self._formulas.get(ALIASES[name])
        return None

    def get_by_category(self, category: str) -> List[dict]:
        return [f for f in self._formulas.values() if f["category"] == category]

    def all_names(self) -> List[str]:
        return sorted(self._formulas.keys())

    def search(self, keyword: str) -> List[dict]:
        """搜索主治关键词（同时搜索方名和indications）"""
        results = []
        for f in self._formulas.values():
            if keyword in f.get("name", "") or keyword in f.get("indications", ""):
                results.append(f)
        return results

    def total_count(self) -> int:
        return len(self._formulas)

    def _define_all(self) -> Dict[str, List[dict]]:
        return {
            "桂枝汤类": [
                {"name": "桂枝汤", "indications": "太阳中风头痛发热汗出恶风脉浮缓", "tiaowen": "12"},
                {"name": "桂枝加葛根汤", "indications": "太阳中风项背强几几", "tiaowen": "14"},
                {"name": "桂枝加厚朴杏子汤", "indications": "太阳中风兼喘", "tiaowen": "18/43"},
                {"name": "桂枝加附子汤", "indications": "太阳病发汗太过遂漏不止恶风小便难四肢微急", "tiaowen": "20"},
                {"name": "桂枝去芍药汤", "indications": "太阳病下后脉促胸满", "tiaowen": "21"},
                {"name": "桂枝去芍药加附子汤", "indications": "脉促胸满兼恶寒", "tiaowen": "22"},
                {"name": "桂枝麻黄各半汤", "indications": "太阳病如疟状热多寒少面有热色", "tiaowen": "23"},
                {"name": "桂枝二麻黄一汤", "indications": "服桂枝汤后形似疟", "tiaowen": "25"},
                {"name": "桂枝二越婢一汤", "indications": "太阳病发热恶寒热多寒少", "tiaowen": "27"},
                {"name": "桂枝去桂加茯苓白术汤", "indications": "服桂枝汤后头项强痛翕翕发热无汗", "tiaowen": "28"},
                {"name": "桂枝加芍药生姜各一两人参三两新加汤", "indications": "发汗后身疼痛脉沉迟", "tiaowen": "62"},
                {"name": "桂枝甘草汤", "indications": "发汗过多叉手自冒心心下悸", "tiaowen": "64"},
                {"name": "桂枝甘草龙骨牡蛎汤", "indications": "火逆下之烦躁", "tiaowen": "118"},
                {"name": "桂枝去芍药加蜀漆牡蛎龙骨救逆汤", "indications": "伤寒脉浮火劫亡阳惊狂卧起不安", "tiaowen": "112"},
                {"name": "桂枝加桂汤", "indications": "烧针令汗针处被寒核起而赤奔豚", "tiaowen": "117"},
                {"name": "桂枝加芍药汤", "indications": "太阳病误下腹满时痛", "tiaowen": "279"},
                {"name": "桂枝加大黄汤", "indications": "腹满大实痛", "tiaowen": "279"},
                {"name": "小建中汤", "indications": "腹中急痛心中悸而烦", "tiaowen": "100/102"},
                {"name": "黄芪建中汤", "indications": "虚劳里急诸不足", "tiaowen": "金匮·血痹虚劳"},
                {"name": "当归四逆汤", "indications": "手足厥寒脉细欲绝", "tiaowen": "351"},
                {"name": "当归四逆加吴茱萸生姜汤", "indications": "手足厥寒内有久寒", "tiaowen": "352"},
            ],
            "麻黄汤类": [
                {"name": "麻黄汤", "indications": "太阳伤寒头痛发热身疼腰痛骨节疼痛恶风无汗而喘", "tiaowen": "35"},
                {"name": "大青龙汤", "indications": "太阳中风脉浮紧发热恶寒身疼痛不汗出而烦躁", "tiaowen": "38"},
                {"name": "小青龙汤", "indications": "伤寒表不解心下有水气干呕发热而咳", "tiaowen": "40"},
                {"name": "麻黄杏仁甘草石膏汤", "indications": "汗出而喘无大热", "tiaowen": "63"},
                {"name": "麻黄附子细辛汤", "indications": "少阴病始得之反发热脉沉", "tiaowen": "301"},
                {"name": "麻黄附子甘草汤", "indications": "少阴病得之二三日无里证", "tiaowen": "302"},
            ],
            "葛根汤类": [
                {"name": "葛根汤", "indications": "太阳病项背强几几无汗恶风", "tiaowen": "31"},
                {"name": "葛根加半夏汤", "indications": "太阳阳明合病不下利但呕", "tiaowen": "33"},
                {"name": "葛根黄芩黄连汤", "indications": "太阳病桂枝证医反下之利遂不止脉促表未解喘而汗出", "tiaowen": "34"},
            ],
            "白虎汤类": [
                {"name": "白虎汤", "indications": "阳明病大热大汗大渴脉洪大", "tiaowen": "176/219"},
                {"name": "白虎加人参汤", "indications": "大汗出大烦渴不解脉洪大", "tiaowen": "26"},
                {"name": "竹叶石膏汤", "indications": "伤寒解后虚羸少气气逆欲吐", "tiaowen": "397"},
            ],
            "承气汤类": [
                {"name": "调胃承气汤", "indications": "阳明病不吐不下心烦蒸蒸发热", "tiaowen": "207/248"},
                {"name": "小承气汤", "indications": "阳明病谵语发潮热大便硬", "tiaowen": "208/213"},
                {"name": "大承气汤", "indications": "阳明病潮热谵语大便硬腹满痛", "tiaowen": "208/212/215"},
                {"name": "桃核承气汤", "indications": "太阳病不解热结膀胱其人如狂", "tiaowen": "106"},
                {"name": "抵当汤", "indications": "太阳病六七日表证仍在脉微而沉反不结胸其人发狂", "tiaowen": "124"},
                {"name": "抵当丸", "indications": "伤寒有热少腹满应小便不利今反利", "tiaowen": "126"},
            ],
            "栀子豉汤类": [
                {"name": "栀子豉汤", "indications": "发汗吐下后虚烦不得眠心中懊憹", "tiaowen": "76"},
                {"name": "栀子甘草豉汤", "indications": "虚烦少气", "tiaowen": "76"},
            ],
            "柴胡汤类": [
                {"name": "小柴胡汤", "indications": "往来寒热胸胁苦满默默不欲饮食心烦喜呕", "tiaowen": "96"},
                {"name": "大柴胡汤", "indications": "呕不止心下急郁郁微烦", "tiaowen": "103/165"},
                {"name": "柴胡加芒硝汤", "indications": "胸胁满而呕日晡潮热", "tiaowen": "104"},
                {"name": "柴胡桂枝汤", "indications": "发热微恶寒支节烦疼微呕心下支结", "tiaowen": "146"},
                {"name": "柴胡桂枝干姜汤", "indications": "胸胁满微结小便不利渴而不呕", "tiaowen": "147"},
                {"name": "柴胡加龙骨牡蛎汤", "indications": "胸满烦惊小便不利谵语", "tiaowen": "107"},
                {"name": "四逆散", "indications": "少阴病四逆或咳或悸或小便不利或腹中痛", "tiaowen": "318"},
            ],
            "泻心汤类": [
                {"name": "半夏泻心汤", "indications": "呕而发热心下痞满而不痛", "tiaowen": "149"},
                {"name": "生姜泻心汤", "indications": "胃中不和心下痞硬干噫食臭胁下有水气", "tiaowen": "157"},
                {"name": "甘草泻心汤", "indications": "其人下利日数十行谷不化腹中雷鸣心下痞硬", "tiaowen": "158"},
                {"name": "大黄黄连泻心汤", "indications": "心下痞按之濡其脉关上浮", "tiaowen": "154"},
                {"name": "附子泻心汤", "indications": "心下痞而复恶寒汗出", "tiaowen": "155"},
                {"name": "黄连汤", "indications": "胸中有热胃中有邪气腹中痛欲呕吐", "tiaowen": "173"},
                {"name": "旋覆代赭汤", "indications": "心下痞硬噫气不除", "tiaowen": "161"},
            ],
            "陷胸汤类": [
                {"name": "大陷胸汤", "indications": "心下痛按之石硬", "tiaowen": "134/135"},
                {"name": "大陷胸丸", "indications": "结胸者项亦强如柔痉状", "tiaowen": "131"},
                {"name": "小陷胸汤", "indications": "小结胸病正在心下按之则痛脉浮滑", "tiaowen": "138"},
                {"name": "三物白散", "indications": "寒实结胸无热证", "tiaowen": "141"},
                {"name": "瓜蒂散", "indications": "胸中痞硬气上冲喉咽", "tiaowen": "166"},
                {"name": "十枣汤", "indications": "太阳中风下利呕逆表解乃可攻之", "tiaowen": "152"},
            ],
            "苓桂类": [
                {"name": "茯苓桂枝白术甘草汤", "indications": "心下逆满气上冲胸起则头眩", "tiaowen": "67"},
                {"name": "茯苓桂枝甘草大枣汤", "indications": "发汗后脐下悸欲作奔豚", "tiaowen": "65"},
                {"name": "茯苓甘草汤", "indications": "伤寒汗出而渴", "tiaowen": "73"},
                {"name": "五苓散", "indications": "脉浮小便不利微热消渴", "tiaowen": "71"},
                {"name": "猪苓汤", "indications": "脉浮发热渴欲饮水小便不利", "tiaowen": "223"},
            ],
            "理中汤类": [
                {"name": "理中汤", "indications": "霍乱头痛发热身疼痛寒多不用水", "tiaowen": "386"},
                {"name": "桂枝人参汤", "indications": "太阳病外证未除而数下之遂协热而利", "tiaowen": "163"},
                {"name": "甘草干姜汤", "indications": "脉浮自汗出小便数心烦微恶寒脚挛急", "tiaowen": "29"},
            ],
            "真武汤类": [
                {"name": "真武汤", "indications": "心下悸头眩身瞤动振振欲擗地", "tiaowen": "82"},
                {"name": "附子汤", "indications": "少阴病口中和背恶寒", "tiaowen": "304/305"},
            ],
            "四逆汤类": [
                {"name": "四逆汤", "indications": "少阴病脉沉微细但欲寐下利清谷手足厥冷", "tiaowen": "323/324"},
                {"name": "四逆加人参汤", "indications": "恶寒脉微而复利利止亡血", "tiaowen": "385"},
                {"name": "通脉四逆汤", "indications": "下利清谷里寒外热手足厥逆脉微欲绝", "tiaowen": "317"},
                {"name": "通脉四逆加猪胆汁汤", "indications": "吐已下断汗出而厥四肢拘急不解脉微欲绝", "tiaowen": "390"},
                {"name": "白通汤", "indications": "少阴病下利脉微", "tiaowen": "314"},
                {"name": "白通加猪胆汁汤", "indications": "下利脉微厥逆无脉干呕烦", "tiaowen": "315"},
            ],
            "黄连阿胶类": [
                {"name": "黄连阿胶汤", "indications": "少阴病心中烦不得卧", "tiaowen": "303"},
                {"name": "干姜黄芩黄连人参汤", "indications": "寒格食入即吐", "tiaowen": "359"},
                {"name": "黄芩汤", "indications": "太阳与少阳合病自下利", "tiaowen": "172"},
                {"name": "黄芩加半夏生姜汤", "indications": "太阳与少阳合病呕", "tiaowen": "172"},
            ],
            "炙甘草汤类": [
                {"name": "炙甘草汤", "indications": "伤寒脉结代心动悸", "tiaowen": "177"},
                {"name": "芍药甘草附子汤", "indications": "发汗病不解反恶寒", "tiaowen": "68"},
            ],
            "杂病类": [
                {"name": "甘草汤", "indications": "少阴病咽痛", "tiaowen": "311"},
                {"name": "桔梗汤", "indications": "少阴病咽痛不差", "tiaowen": "311"},
                {"name": "半夏散及汤", "indications": "少阴病咽中痛", "tiaowen": "313"},
                {"name": "苦酒汤", "indications": "少阴病咽中伤生疮不能语言声不出", "tiaowen": "312"},
                {"name": "猪肤汤", "indications": "少阴病下利咽痛胸满心烦", "tiaowen": "310"},
                {"name": "芍药甘草汤", "indications": "脚挛急", "tiaowen": "29"},
                {"name": "茵陈蒿汤", "indications": "发热汗出小便不利渴引水浆身黄如橘子色", "tiaowen": "236/260"},
                {"name": "麻黄连轺赤小豆汤", "indications": "瘀热在里身必黄", "tiaowen": "262"},
                {"name": "栀子柏皮汤", "indications": "身黄发热", "tiaowen": "261"},
                {"name": "吴茱萸汤", "indications": "吐利手足逆冷烦躁欲死", "tiaowen": "309"},
                {"name": "桃花汤", "indications": "少阴病下利便脓血", "tiaowen": "306/307"},
                {"name": "赤石脂禹余粮汤", "indications": "下利不止心下痞硬", "tiaowen": "159"},
                {"name": "牡蛎泽泻散", "indications": "大病差后腰以下有水气", "tiaowen": "395"},
            ],
            "金匮要略方": [
                {"name": "瓜蒌桂枝汤", "indications": "身体强几几然脉反沉迟此为痉", "tiaowen": "金匮·痉湿暍"},
                {"name": "麻黄加术汤", "indications": "湿家身烦疼", "tiaowen": "金匮·痉湿暍"},
                {"name": "麻杏薏甘汤", "indications": "一身尽疼发热日晡所剧", "tiaowen": "金匮·痉湿暍"},
                {"name": "防己黄芪汤", "indications": "风湿脉浮身重汗出恶风", "tiaowen": "金匮·痉湿暍"},
                {"name": "桂枝附子汤", "indications": "风湿相搏身体疼烦不能自转侧", "tiaowen": "174"},
                {"name": "白术附子汤", "indications": "风湿相搏大便硬小便自利", "tiaowen": "174"},
                {"name": "甘草附子汤", "indications": "风湿相搏骨节疼烦掣痛不得屈伸", "tiaowen": "175"},
                {"name": "白虎加桂枝汤", "indications": "温疟身无寒但热骨节疼烦时呕", "tiaowen": "金匮·疟病"},
                {"name": "蜀漆散", "indications": "疟多寒", "tiaowen": "金匮·疟病"},
                {"name": "风引汤", "indications": "除热瘫痫", "tiaowen": "金匮·中风历节"},
                {"name": "桂枝芍药知母汤", "indications": "诸肢节疼痛身体尪羸脚肿如脱", "tiaowen": "金匮·中风历节"},
                {"name": "乌头汤", "indications": "病历节不可屈伸疼痛", "tiaowen": "金匮·中风历节"},
                {"name": "黄芪桂枝五物汤", "indications": "血痹外证身体不仁如风痹状", "tiaowen": "金匮·血痹虚劳"},
                {"name": "桂枝加龙骨牡蛎汤", "indications": "男子失精女子梦交", "tiaowen": "金匮·血痹虚劳"},
                {"name": "薯蓣丸", "indications": "虚劳诸不足风气百疾", "tiaowen": "金匮·血痹虚劳"},
                {"name": "酸枣仁汤", "indications": "虚劳虚烦不得眠", "tiaowen": "金匮·血痹虚劳"},
                {"name": "大黄庶虫丸", "indications": "五劳虚极内有干血", "tiaowen": "金匮·血痹虚劳"},
                {"name": "射干麻黄汤", "indications": "咳而上气喉中水鸡声", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "厚朴麻黄汤", "indications": "咳而脉浮", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "麦门冬汤", "indications": "火逆上气咽喉不利", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "葶苈大枣泻肺汤", "indications": "肺痈喘不得卧", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "越婢加半夏汤", "indications": "肺胀其人喘目如脱状脉浮大", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "小青龙加石膏汤", "indications": "肺胀咳而上气烦躁而喘脉浮", "tiaowen": "金匮·肺痿肺痈"},
                {"name": "奔豚汤", "indications": "奔豚气上冲胸腹痛往来寒热", "tiaowen": "金匮·奔豚气"},
                {"name": "栝蒌薤白白酒汤", "indications": "胸痹喘息咳唾胸背痛短气", "tiaowen": "金匮·胸痹心痛"},
                {"name": "栝蒌薤白半夏汤", "indications": "胸痹不得卧心痛彻背", "tiaowen": "金匮·胸痹心痛"},
                {"name": "枳实薤白桂枝汤", "indications": "胸痹心中痞胸满胁下逆抢心", "tiaowen": "金匮·胸痹心痛"},
                {"name": "人参汤", "indications": "胸痹心中痞", "tiaowen": "金匮·胸痹心痛"},
                {"name": "茯苓杏仁甘草汤", "indications": "胸痹胸中气塞短气", "tiaowen": "金匮·胸痹心痛"},
                {"name": "橘枳姜汤", "indications": "胸痹胸中气塞短气偏于气滞", "tiaowen": "金匮·胸痹心痛"},
                {"name": "薏苡附子散", "indications": "胸痹缓急", "tiaowen": "金匮·胸痹心痛"},
                {"name": "桂枝生姜枳实汤", "indications": "心中痞诸逆心悬痛", "tiaowen": "金匮·胸痹心痛"},
                {"name": "乌头赤石脂丸", "indications": "心痛彻背背痛彻心", "tiaowen": "金匮·胸痹心痛"},
                {"name": "厚朴七物汤", "indications": "腹满发热脉浮而数饮食如故", "tiaowen": "金匮·腹满寒疝"},
                {"name": "附子粳米汤", "indications": "腹中寒气雷鸣切痛胸胁逆满呕吐", "tiaowen": "金匮·腹满寒疝"},
                {"name": "大建中汤", "indications": "心胸中大寒痛呕不能饮食腹中寒", "tiaowen": "金匮·腹满寒疝"},
                {"name": "大黄附子汤", "indications": "胁下偏痛发热脉弦紧", "tiaowen": "金匮·腹满寒疝"},
                {"name": "赤丸", "indications": "寒气厥逆", "tiaowen": "金匮·腹满寒疝"},
                {"name": "当归生姜羊肉汤", "indications": "寒疝腹中痛及胁痛里急", "tiaowen": "金匮·腹满寒疝"},
                {"name": "乌头桂枝汤", "indications": "寒疝腹中痛逆冷手足不仁身疼痛", "tiaowen": "金匮·腹满寒疝"},
                {"name": "甘姜苓术汤", "indications": "肾着腰以下冷痛如坐水中", "tiaowen": "金匮·五脏风寒"},
                {"name": "麻子仁丸", "indications": "趺阳脉浮涩小便数大便硬", "tiaowen": "247"},
                {"name": "小半夏汤", "indications": "呕家心下有支饮", "tiaowen": "金匮·痰饮咳嗽"},
                {"name": "小半夏加茯苓汤", "indications": "心下有支饮眩悸", "tiaowen": "金匮·痰饮咳嗽"},
                {"name": "木防己汤", "indications": "膈间支饮喘满心下痞坚面色黧黑脉沉紧", "tiaowen": "金匮·痰饮咳嗽"},
                {"name": "泽泻汤", "indications": "心下有支饮其人苦冒眩", "tiaowen": "金匮·痰饮咳嗽"},
                {"name": "防己茯苓汤", "indications": "皮水四肢肿水气在皮肤中", "tiaowen": "金匮·水气病"},
                {"name": "越婢汤", "indications": "风水恶风一身悉肿脉浮不渴续自汗出", "tiaowen": "金匮·水气病"},
                {"name": "越婢加术汤", "indications": "里水一身面目黄肿脉沉小便不利", "tiaowen": "金匮·水气病"},
                {"name": "甘草麻黄汤", "indications": "里水", "tiaowen": "金匮·水气病"},
                {"name": "桂甘姜枣麻辛附子汤", "indications": "气分心下坚大如盘边如旋杯", "tiaowen": "金匮·水气病"},
                {"name": "枳术汤", "indications": "心下坚大如盘边如旋盘", "tiaowen": "金匮·水气病"},
                {"name": "大黄硝石汤", "indications": "黄疸腹满小便不利而赤", "tiaowen": "金匮·黄疸"},
                {"name": "黄土汤", "indications": "下血先便后血远血", "tiaowen": "金匮·惊悸吐衄"},
                {"name": "泻心汤", "indications": "心气不足吐血衄血", "tiaowen": "金匮·惊悸吐衄"},
                {"name": "白头翁汤", "indications": "热利下重", "tiaowen": "371"},
                {"name": "橘皮竹茹汤", "indications": "哕逆", "tiaowen": "金匮·呕吐哕"},
            ],
            "金匮要略补遗方": [
                {"name": "乌梅丸", "indications": "厥阴病消渴气上撞心心中疼热饥而不欲食蛔厥", "tiaowen": "338/金匮·趺蹶"},
                {"name": "半夏厚朴汤", "indications": "妇人咽中如有炙脔（梅核气）", "tiaowen": "金匮·妇人杂病"},
                {"name": "肾气丸", "indications": "虚劳腰痛少腹拘急小便不利脚气上入少腹不仁消渴", "tiaowen": "金匮·血痹虚劳/痰饮/消渴/妇人杂病"},
                {"name": "桂枝茯苓丸", "indications": "妇人宿有癥病经断未及三月漏下不止", "tiaowen": "金匮·妇人妊娠"},
                {"name": "大黄牡丹汤", "indications": "肠痈少腹肿痞按之即痛如淋小便自调", "tiaowen": "金匮·疮痈肠痈"},
                {"name": "薏苡附子败酱散", "indications": "肠痈之为病其身甲错腹皮急按之濡如肿状", "tiaowen": "金匮·疮痈肠痈"},
                {"name": "当归芍药散", "indications": "妇人怀妊腹中㽲痛", "tiaowen": "金匮·妇人妊娠/妇人杂病"},
                {"name": "温经汤", "indications": "妇人少腹寒久不受胎崩中去血月水来过多", "tiaowen": "金匮·妇人杂病"},
                {"name": "麻黄升麻汤", "indications": "伤寒六七日大下后寸脉沉而迟手足厥逆下部脉不至咽喉不利唾脓血", "tiaowen": "357"},
            ],
        }
