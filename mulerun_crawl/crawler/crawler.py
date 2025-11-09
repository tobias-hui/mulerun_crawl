"""爬虫模块 - 使用 Playwright 爬取 MuleRun agents"""
import logging
import time
import re
from typing import List, Dict
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser

from ..config import CRAWLER_CONFIG

logger = logging.getLogger(__name__)


class MuleRunCrawler:
    """MuleRun 网站爬虫"""
    
    def __init__(self):
        self.config = CRAWLER_CONFIG
        self.browser: Browser = None
        self.page: Page = None
    
    def _init_browser(self):
        """初始化浏览器"""
        playwright = sync_playwright().start()
        
        # VPS 环境下的启动参数
        launch_options = {
            'headless': self.config['headless'],
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',  # 避免共享内存问题
                '--disable-gpu',
            ]
        }
        
        self.browser = playwright.chromium.launch(**launch_options)
        logger.info("浏览器启动成功")
        context = self.browser.new_context(
            user_agent=self.config['user_agent'],
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = context.new_page()
        logger.info("浏览器初始化完成")
    
    def _scroll_to_bottom(self) -> bool:
        """
        滚动到页面底部，等待新内容加载
        
        Returns:
            bool: 是否有新内容加载
        """
        # 记录滚动前的 agent 数量
        before_count = len(self.page.query_selector_all('a[href^="/@"]'))
        
        # 滚动到底部
        self.page.evaluate("""
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            })
        """)
        
        # 等待内容加载
        time.sleep(self.config['scroll_delay'])
        
        # 等待可能的加载动画
        try:
            self.page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        # 记录滚动后的 agent 数量
        after_count = len(self.page.query_selector_all('a[href^="/@"]'))
        
        return after_count > before_count
    
    def _extract_agent_info(self, element) -> Dict:
        """
        从 agent 卡片元素中提取信息
        
        Args:
            element: Playwright ElementHandle
            
        Returns:
            Dict: agent 信息字典
        """
        try:
            # 链接
            link = element.get_attribute('href') or ''
            
            # 名称
            name_elem = element.query_selector('h3')
            name = name_elem.inner_text() if name_elem else ''
            
            # 描述
            desc_elem = element.query_selector('.line-clamp-2')
            description = desc_elem.inner_text() if desc_elem else ''
            
            # 头像 URL
            avatar_elem = element.query_selector('img[data-slot="avatar-image"]')
            avatar_url = avatar_elem.get_attribute('src') if avatar_elem else ''
            
            # 价格（格式：50/ run (approx.)）
            price_elem = element.query_selector('span.font-jetbrains-mono')
            price_text = price_elem.inner_text() if price_elem else ''
            # 提取价格数字和单位
            price_match = re.search(r'(\d+)\s*/.*?run', price_text)
            price = price_match.group(0) if price_match else price_text
            
            # 作者（格式：by laughing_code）
            # 尝试多种选择器来查找作者信息
            author_elem = (
                element.query_selector('div.font-inter.max-w-\\[50\\%\\]') or
                element.query_selector('div:has-text("by ")') or
                element.query_selector('div.text-zinc-400:has-text("by ")')
            )
            author_text = author_elem.inner_text() if author_elem else ''
            author = author_text.replace('by ', '').strip() if author_text.startswith('by ') else author_text
            
            return {
                'link': link,
                'name': name,
                'description': description,
                'avatar_url': avatar_url,
                'price': price,
                'author': author,
            }
        except Exception as e:
            logger.error(f"提取 agent 信息失败: {e}")
            return None
    
    def crawl(self) -> List[Dict]:
        """
        爬取所有 agents
        
        Returns:
            List[Dict]: agent 信息列表，按排名排序
        """
        try:
            self._init_browser()
            
            # 访问首页
            logger.info(f"访问 {self.config['base_url']}")
            self.page.goto(self.config['base_url'], wait_until='networkidle')
            time.sleep(2)  # 等待页面完全加载
            
            # 确保是 Most used 模式（默认模式）
            # 检查当前排序模式，如果不是 Most used 则点击切换
            try:
                # 查找排序按钮，可能需要根据实际页面结构调整选择器
                sort_button = self.page.query_selector('button:has-text("Most used"), a:has-text("Most used")')
                if sort_button:
                    current_text = sort_button.inner_text()
                    if 'Most used' not in current_text:
                        sort_button.click()
                        time.sleep(1)
            except Exception as e:
                logger.warning(f"无法确认排序模式: {e}，假设已经是 Most used")
            
            # 无限滚动加载所有内容
            logger.info("开始滚动加载内容...")
            scroll_count = 0
            no_new_content_count = 0
            
            while scroll_count < self.config['max_scroll_attempts']:
                has_new_content = self._scroll_to_bottom()
                
                if has_new_content:
                    no_new_content_count = 0
                    logger.info(f"已滚动 {scroll_count + 1} 次，发现新内容")
                else:
                    no_new_content_count += 1
                    logger.info(f"已滚动 {scroll_count + 1} 次，未发现新内容 ({no_new_content_count}/{self.config['no_new_content_threshold']})")
                    
                    if no_new_content_count >= self.config['no_new_content_threshold']:
                        logger.info("连续多次未发现新内容，停止滚动")
                        break
                
                scroll_count += 1
            
            # 提取所有 agent 卡片
            logger.info("开始提取 agent 信息...")
            agent_elements = self.page.query_selector_all('a[href^="/@"]')
            logger.info(f"找到 {len(agent_elements)} 个 agent 卡片")
            
            agents = []
            for idx, element in enumerate(agent_elements, start=1):
                agent_info = self._extract_agent_info(element)
                if agent_info:
                    agent_info['rank'] = idx  # 排名从1开始
                    agents.append(agent_info)
            
            logger.info(f"成功提取 {len(agents)} 个 agents")
            return agents
            
        except Exception as e:
            logger.error(f"爬取过程出错: {e}", exc_info=True)
            raise
        finally:
            self._close_browser()
    
    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            logger.info("浏览器已关闭")


def crawl_agents() -> List[Dict]:
    """
    爬取 agents 的便捷函数
    
    Returns:
        List[Dict]: agent 信息列表
    """
    crawler = MuleRunCrawler()
    return crawler.crawl()

