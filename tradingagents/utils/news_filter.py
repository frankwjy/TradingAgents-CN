"""
新闻相关性过滤器
用于过滤与特定股票/公司不相关的新闻，提高新闻分析质量
"""

import pandas as pd
import re
from typing import List, Dict, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NewsRelevanceFilter:
    """基于规则的新闻相关性过滤器"""
    
    def __init__(self, stock_code: str, company_name: str):
        """
        初始化过滤器
        
        Args:
            stock_code: 股票代码，如 "600036"
            company_name: 公司名称，如 "招商银行"
        """
        self.stock_code = stock_code.upper()
        self.company_name = company_name
        
        # 排除关键词 - 这些词出现时降低相关性
        self.exclude_keywords = [
            'etf', '指数基金', '基金', '指数', 'index', 'fund',
            '权重股', '成分股', '板块', '概念股', '主题基金',
            '跟踪指数', '被动投资', '指数投资', '基金持仓'
        ]
        
        # 包含关键词 - 这些词出现时提高相关性
        self.include_keywords = [
            '业绩', '财报', '公告', '重组', '并购', '分红', '派息',
            '高管', '董事', '股东', '增持', '减持', '回购',
            '年报', '季报', '半年报', '业绩预告', '业绩快报',
            '股东大会', '董事会', '监事会', '重大合同',
            '投资', '收购', '出售', '转让', '合作', '协议'
        ]
        
        # 强相关关键词 - 这些词出现时大幅提高相关性
        self.strong_keywords = [
            '停牌', '复牌', '涨停', '跌停', '限售解禁',
            '股权激励', '员工持股', '定增', '配股', '送股',
            '资产重组', '借壳上市', '退市', '摘帽', 'ST'
        ]
    
    def calculate_relevance_score(self, title: str, content: str) -> float:
        """
        计算新闻相关性评分
        
        Args:
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            float: 相关性评分 (0-100)
        """
        score = 0
        title_lower = title.lower()
        content_lower = content.lower()
        
        # 1. 直接提及公司名称
        if self.company_name in title:
            score += 50  # 标题中出现公司名称，高分
            logger.debug(f"[过滤器] 标题包含公司名称 '{self.company_name}': +50分")
        elif self.company_name in content:
            score += 25  # 内容中出现公司名称，中等分
            logger.debug(f"[过滤器] 内容包含公司名称 '{self.company_name}': +25分")
            
        # 2. 直接提及股票代码
        if self.stock_code in title:
            score += 40  # 标题中出现股票代码，高分
            logger.debug(f"[过滤器] 标题包含股票代码 '{self.stock_code}': +40分")
        elif self.stock_code in content:
            score += 20  # 内容中出现股票代码，中等分
            logger.debug(f"[过滤器] 内容包含股票代码 '{self.stock_code}': +20分")
            
        # 3. 强相关关键词检查
        strong_matches = []
        for keyword in self.strong_keywords:
            if keyword in title_lower:
                score += 30
                strong_matches.append(keyword)
            elif keyword in content_lower:
                score += 15
                strong_matches.append(keyword)
        
        if strong_matches:
            logger.debug(f"[过滤器] 强相关关键词匹配: {strong_matches}")
            
        # 4. 包含关键词检查
        include_matches = []
        for keyword in self.include_keywords:
            if keyword in title_lower:
                score += 15
                include_matches.append(keyword)
            elif keyword in content_lower:
                score += 8
                include_matches.append(keyword)
        
        if include_matches:
            logger.debug(f"[过滤器] 相关关键词匹配: {include_matches[:3]}...")  # 只显示前3个
            
        # 5. 排除关键词检查（减分）
        exclude_matches = []
        for keyword in self.exclude_keywords:
            if keyword in title_lower:
                score -= 40  # 标题中出现排除词，大幅减分
                exclude_matches.append(keyword)
            elif keyword in content_lower:
                score -= 20  # 内容中出现排除词，中等减分
                exclude_matches.append(keyword)
        
        if exclude_matches:
            logger.debug(f"[过滤器] 排除关键词匹配: {exclude_matches[:3]}...")
            
        # 6. 特殊规则：如果标题完全不包含公司信息但包含排除词，严重减分
        if (self.company_name not in title and self.stock_code not in title and 
            any(keyword in title_lower for keyword in self.exclude_keywords)):
            score -= 30
            logger.debug(f"[过滤器] 标题无公司信息但含排除词: -30分")
        
        # 确保评分在0-100范围内
        final_score = max(0, min(100, score))
        
        logger.debug(f"[过滤器] 最终评分: {final_score}分 - 标题: {title[:30]}...")
        
        return final_score
    
    def filter_news(self, news_df: pd.DataFrame, min_score: float = 30) -> pd.DataFrame:
        """
        过滤新闻DataFrame
        
        Args:
            news_df: 原始新闻DataFrame
            min_score: 最低相关性评分阈值
            
        Returns:
            pd.DataFrame: 过滤后的新闻DataFrame，按相关性评分排序
        """
        if news_df.empty:
            logger.warning("[过滤器] 输入新闻DataFrame为空")
            return news_df
        
        logger.info(f"[过滤器] 开始过滤新闻，原始数量: {len(news_df)}条，最低评分阈值: {min_score}")
        
        filtered_news = []
        
        for idx, row in news_df.iterrows():
            title = row.get('新闻标题', row.get('标题', ''))
            content = row.get('新闻内容', row.get('内容', ''))
            
            # 计算相关性评分
            score = self.calculate_relevance_score(title, content)
            
            if score >= min_score:
                row_dict = row.to_dict()
                row_dict['relevance_score'] = score
                filtered_news.append(row_dict)
                
                logger.debug(f"[过滤器] 保留新闻 (评分: {score:.1f}): {title[:50]}...")
            else:
                logger.debug(f"[过滤器] 过滤新闻 (评分: {score:.1f}): {title[:50]}...")
        
        # 创建过滤后的DataFrame
        if filtered_news:
            filtered_df = pd.DataFrame(filtered_news)
            # 按相关性评分排序
            filtered_df = filtered_df.sort_values('relevance_score', ascending=False)
            logger.info(f"[过滤器] 过滤完成，保留 {len(filtered_df)}条 新闻")
        else:
            filtered_df = pd.DataFrame()
            logger.warning(f"[过滤器] 所有新闻都被过滤，无符合条件的新闻")
            
        return filtered_df
    
    def get_filter_statistics(self, original_df: pd.DataFrame, filtered_df: pd.DataFrame) -> Dict:
        """
        获取过滤统计信息
        
        Args:
            original_df: 原始新闻DataFrame
            filtered_df: 过滤后新闻DataFrame
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'filter_rate': (len(original_df) - len(filtered_df)) / len(original_df) * 100 if len(original_df) > 0 else 0,
            'avg_score': filtered_df['relevance_score'].mean() if not filtered_df.empty else 0,
            'max_score': filtered_df['relevance_score'].max() if not filtered_df.empty else 0,
            'min_score': filtered_df['relevance_score'].min() if not filtered_df.empty else 0
        }
        
        return stats


# 股票代码到公司名称的映射
STOCK_COMPANY_MAPPING = {
    # A股主要银行
    '600036': '招商银行',
    '000001': '平安银行', 
    '600000': '浦发银行',
    '601166': '兴业银行',
    '002142': '宁波银行',
    '601328': '交通银行',
    '601398': '工商银行',
    '601939': '建设银行',
    '601288': '农业银行',
    '601818': '光大银行',
    '600015': '华夏银行',
    '600016': '民生银行',
    
    # A股主要白酒股
    '000858': '五粮液',
    '600519': '贵州茅台',
    '000568': '泸州老窖',
    '002304': '洋河股份',
    '000596': '古井贡酒',
    '603369': '今世缘',
    '000799': '酒鬼酒',
    
    # A股主要科技股
    '000002': '万科A',
    '000858': '五粮液',
    '002415': '海康威视',
    '000725': '京东方A',
    '002230': '科大讯飞',
    '300059': '东方财富',
    
    # 更多股票可以继续添加...
}


# 港股主要公司映射
HK_STOCK_COMPANY_MAPPING = {
    # 科技/互联网
    '00700': '腾讯控股', '0700': '腾讯控股',
    '09988': '阿里巴巴', '9988': '阿里巴巴',
    '09618': '京东集团', '9618': '京东集团',
    '03690': '美团', '3690': '美团',
    '09999': '网易', '9999': '网易',
    '01024': '快手', '1024': '快手',
    '09626': '哔哩哔哩', '9626': '哔哩哔哩',
    '02015': '理想汽车', '2015': '理想汽车',
    '09868': '小鹏汽车', '9868': '小鹏汽车',
    '09866': '蔚来', '9866': '蔚来',
    '06060': '众安在线', '6060': '众安在线',
    '00285': '比亚迪电子', '285': '比亚迪电子',

    # 电信运营商
    '00941': '中国移动', '941': '中国移动',
    '00762': '中国联通', '762': '中国联通',
    '00728': '中国电信', '728': '中国电信',

    # 银行
    '00939': '建设银行', '939': '建设银行',
    '01398': '工商银行', '1398': '工商银行',
    '03988': '中国银行', '3988': '中国银行',
    '00005': '汇丰控股', '5': '汇丰控股',
    '03968': '招商银行', '3968': '招商银行',
    '01288': '农业银行', '1288': '农业银行',
    '06818': '光大银行', '6818': '光大银行',
    '01658': '邮储银行', '1658': '邮储银行',
    '06881': '中信银行', '6881': '中信银行',
    '03618': '重庆农村商业银行', '3618': '重庆农村商业银行',

    # 保险
    '01299': '友邦保险', '1299': '友邦保险',
    '02318': '中国平安', '2318': '中国平安',
    '02628': '中国人寿', '2628': '中国人寿',
    '01336': '新华保险', '1336': '新华保险',
    '02601': '中国太保', '2601': '中国太保',
    '02328': '中国财险', '2328': '中国财险',

    # 石油化工
    '00857': '中国石油', '857': '中国石油',
    '00386': '中国石化', '386': '中国石化',
    '00883': '中海油', '883': '中海油',

    # 地产
    '01109': '华润置地', '1109': '华润置地',
    '02007': '碧桂园', '2007': '碧桂园',
    '03333': '恒大集团', '3333': '恒大集团',
    '00688': '中国海外发展', '688': '中国海外发展',
    '01997': '九龙仓置业', '1997': '九龙仓置业',
    '00017': '新世界发展', '17': '新世界发展',
    '00012': '恒基地产', '12': '恒基地产',
    '00016': '新鸿基地产', '16': '新鸿基地产',

    # 汽车
    '01211': '比亚迪', '1211': '比亚迪',
    '02238': '广汽集团', '2238': '广汽集团',
    '00175': '吉利汽车', '175': '吉利汽车',
    '02333': '长城汽车', '2333': '长城汽车',
    '01958': '北京汽车', '1958': '北京汽车',

    # 消费
    '01876': '百威亚太', '1876': '百威亚太',
    '00291': '华润啤酒', '291': '华润啤酒',
    '00288': '万洲国际', '288': '万洲国际',
    '01044': '恒安国际', '1044': '恒安国际',
    '02319': '蒙牛乳业', '2319': '蒙牛乳业',
    '00867': '康师傅', '867': '康师傅',
    '00220': '统一企业中国', '220': '统一企业中国',

    # 医药
    '01093': '石药集团', '1093': '石药集团',
    '02269': '药明生物', '2269': '药明生物',
    '01177': '中国生物制药', '1177': '中国生物制药',
    '06969': '思摩尔国际', '6969': '思摩尔国际',
    '02196': '复星医药', '2196': '复星医药',

    # 航空
    '00753': '中国国航', '753': '中国国航',
    '00670': '中国东航', '670': '中国东航',
    '00285': '比亚迪电子', '285': '比亚迪电子',

    # 钢铁/矿业
    '00347': '鞍钢股份', '347': '鞍钢股份',
    '02600': '中国铝业', '2600': '中国铝业',
    '03323': '中国建材', '3323': '中国建材',

    # 电力/公用事业
    '00902': '华能国际', '902': '华能国际',
    '00991': '大唐发电', '991': '大唐发电',
    '00836': '华润电力', '836': '华润电力',
    '01816': '中广核电力', '1816': '中广核电力',

    # 金融/券商
    '06030': '中信证券', '6030': '中信证券',
    '03908': '中金公司', '3908': '中金公司',
    '06886': '华泰证券', '6886': '华泰证券',
    '02611': '国泰君安', '2611': '国泰君安',

    # 其他
    '00002': '中电控股', '2': '中电控股',
    '00003': '香港中华煤气', '3': '香港中华煤气',
    '00006': '电能实业', '6': '电能实业',
    '00011': '恒生银行', '11': '恒生银行',
    '00027': '银河娱乐', '27': '银河娱乐',
    '00066': '港铁公司', '66': '港铁公司',
    '00267': '中信股份', '267': '中信股份',
    '00388': '香港交易所', '388': '香港交易所',
    '00669': '创科实业', '669': '创科实业',
    '00823': '领展房产基金', '823': '领展房产基金',
    '00857': '中国石油', '857': '中国石油',
    '01038': '长江基建集团', '1038': '长江基建集团',
    '01093': '石药集团', '1093': '石药集团',
    '01398': '工商银行', '1398': '工商银行',
    '02020': '安踏体育', '2020': '安踏体育',
    '02313': '申洲国际', '2313': '申洲国际',
    '02382': '舜宇光学科技', '2382': '舜宇光学科技',
    '06098': '碧桂园服务', '6098': '碧桂园服务',
    '09633': '农夫山泉', '9633': '农夫山泉',
    '09961': '携程集团', '9961': '携程集团',
}

def get_company_name(ticker: str) -> str:
    """
    获取股票代码对应的公司名称

    Args:
        ticker: 股票代码

    Returns:
        str: 公司名称
    """
    # 清理股票代码（移除后缀）
    clean_ticker = ticker.split('.')[0]

    # 港股判断：4-5位数字 或 带.HK后缀
    is_hk = ticker.upper().endswith('.HK') or (clean_ticker.isdigit() and 4 <= len(clean_ticker) <= 5)

    if is_hk:
        # 尝试港股映射（先尝试原始代码，再尝试补齐到5位）
        company_name = HK_STOCK_COMPANY_MAPPING.get(clean_ticker)
        if not company_name and len(clean_ticker) < 5:
            company_name = HK_STOCK_COMPANY_MAPPING.get(clean_ticker.zfill(5))
        if company_name:
            logger.debug(f"[公司映射] {ticker} -> {company_name}")
            return company_name
        default_name = f"港股{clean_ticker}"
        logger.warning(f"[公司映射] 未找到 {ticker} 的港股公司名称映射，使用默认: {default_name}")
        return default_name

    # A股映射
    company_name = STOCK_COMPANY_MAPPING.get(clean_ticker)

    if company_name:
        logger.debug(f"[公司映射] {ticker} -> {company_name}")
        return company_name
    else:
        # 如果没有映射，返回默认名称
        default_name = f"股票{clean_ticker}"
        logger.warning(f"[公司映射] 未找到 {ticker} 的公司名称映射，使用默认: {default_name}")
        return default_name


def create_news_filter(ticker: str) -> NewsRelevanceFilter:
    """
    创建新闻过滤器的便捷函数
    
    Args:
        ticker: 股票代码
        
    Returns:
        NewsRelevanceFilter: 配置好的过滤器实例
    """
    company_name = get_company_name(ticker)
    return NewsRelevanceFilter(ticker, company_name)


# 使用示例
if __name__ == "__main__":
    # 测试过滤器
    import pandas as pd
    
    # 模拟新闻数据
    test_news = pd.DataFrame([
        {
            '新闻标题': '招商银行发布2024年第三季度业绩报告',
            '新闻内容': '招商银行今日发布第三季度财报，净利润同比增长8%...'
        },
        {
            '新闻标题': '上证180ETF指数基金（530280）自带杠铃策略',
            '新闻内容': '数据显示，上证180指数前十大权重股分别为贵州茅台、招商银行600036...'
        },
        {
            '新闻标题': '银行ETF指数(512730多只成分股上涨',
            '新闻内容': '银行板块今日表现强势，招商银行、工商银行等多只成分股上涨...'
        }
    ])
    
    # 创建过滤器
    filter = create_news_filter('600036')
    
    # 过滤新闻
    filtered_news = filter.filter_news(test_news, min_score=30)
    
    print(f"原始新闻: {len(test_news)}条")
    print(f"过滤后新闻: {len(filtered_news)}条")
    
    if not filtered_news.empty:
        print("\n过滤后的新闻:")
        for _, row in filtered_news.iterrows():
            print(f"- {row['新闻标题']} (评分: {row['relevance_score']:.1f})")