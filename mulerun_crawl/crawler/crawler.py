"""爬虫模块 - 使用 Playwright 爬取 MuleRun agents"""
import logging
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Page, Browser

from ..config import CRAWLER_CONFIG

logger = logging.getLogger(__name__)


class MuleRunCrawler:
    """MuleRun 网站爬虫"""
    
    def __init__(self):
        self.config = CRAWLER_CONFIG
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.base_url = 'https://mulerun.com'
    
    def _init_browser(self):
        """初始化浏览器"""
        # 确保之前的实例已清理
        self._close_browser()
        
        # 启动 playwright（使用上下文管理器确保正确清理）
        self.playwright = sync_playwright().start()
        
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
        
        self.browser = self.playwright.chromium.launch(**launch_options)
        logger.info("浏览器启动成功")
        context = self.browser.new_context(
            user_agent=self.config['user_agent'],
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = context.new_page()
        logger.info("浏览器初始化完成")
    
    def _scroll_page(self, times: int = 3):
        """
        滚动页面以触发懒加载
        
        Args:
            times: 滚动次数
        """
        logger.info(f"开始滚动页面 {times} 次以触发懒加载...")
        for i in range(times):
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
            
            logger.info(f"已完成第 {i + 1}/{times} 次滚动")
    
    def _get_active_category(self) -> Optional[str]:
        """
        获取当前高亮的分类按钮文本
        
        Returns:
            str: 分类名称，如果没有则返回 None
        """
        try:
            # 查找具有 bg-[#EFEFF0] 或 font-semibold 的按钮
            active_button = (
                self.page.query_selector('button.bg-\\[\\#EFEFF0\\] span') or
                self.page.query_selector('button.font-semibold span') or
                self.page.query_selector('a.bg-\\[\\#EFEFF0\\] span') or
                self.page.query_selector('a.font-semibold span')
            )
            
            if active_button:
                return active_button.inner_text().strip()
            
            return None
        except Exception as e:
            logger.warning(f"获取活跃分类失败: {e}")
            return None
    
    def _extract_top_picks(self) -> List[Dict]:
        """
        提取 Top Picks 列表
        Top Picks 每次只显示 6 个，需要点击右侧按钮加载更多
        
        Returns:
            List[Dict]: Top Picks 列表
        """
        logger.info("开始提取 Top Picks 列表...")
        top_picks = []
        active_category = self._get_active_category()
        seen_urls = set()  # 用于去重
        
        try:
            # 查找包含 "Top Picks" 文案的区域
            top_picks_section = self.page.query_selector('text="Top Picks"')
            if not top_picks_section:
                logger.warning("未找到 Top Picks 区域")
                return top_picks
            
            # 找到 Top Picks 容器（包含按钮的父元素）
            # 根据 HTML 结构，容器应该是包含 data-slot="explore-recommend-item" 的父级
            container = self.page.query_selector('div:has-text("Top Picks")')
            if not container:
                # 尝试查找包含 explore-recommend-item 的容器
                first_item = self.page.query_selector('a[data-slot="explore-recommend-item"]')
                if first_item:
                    container = first_item.evaluate("""
                        (el) => {
                            let parent = el.closest('.font-inter-sans');
                            return parent || el.parentElement;
                        }
                    """)
            
            max_clicks = 50  # 最大点击次数，防止无限循环
            click_count = 0
            
            while click_count < max_clicks:
                # 等待页面稳定
                time.sleep(0.5)
                
                # 提取当前可见的所有列表项（每次重新查询，避免使用过期的元素）
                items = self.page.query_selector_all('a[data-slot="explore-recommend-item"]')
                logger.info(f"当前可见 {len(items)} 个 Top Picks 项目")
                
                if len(items) == 0:
                    logger.warning("未找到任何 Top Picks 项目，可能页面结构已变化")
                    # 等待一下再重试
                    time.sleep(2)
                    items = self.page.query_selector_all('a[data-slot="explore-recommend-item"]')
                    if len(items) == 0:
                        logger.info("重试后仍未找到项目，停止加载")
                        break
                
                # 提取当前批次的 agent 信息
                batch_count = 0
                for item in items:
                    try:
                        # agent_url: a@href（转为绝对 URL）
                        href = item.get_attribute('href') or ''
                        agent_url = urljoin(self.base_url, href) if href else ''
                        
                        # 跳过已处理的 URL
                        if not agent_url or agent_url in seen_urls:
                            continue
                        
                        seen_urls.add(agent_url)
                        
                        # rank: span.font-anton 的文本
                        rank_elem = item.query_selector('span.font-anton')
                        rank = rank_elem.inner_text().strip() if rank_elem else str(len(top_picks) + 1)
                        
                        # title: 卡片内 div[title] 或 .text-sm 的文本；优先取 @title
                        title = item.get_attribute('title') or ''
                        if not title:
                            title_elem = item.query_selector('div[title]')
                            if title_elem:
                                title = title_elem.get_attribute('title') or title_elem.inner_text().strip()
                            else:
                                text_sm_elem = item.query_selector('.text-sm')
                                if text_sm_elem:
                                    title = text_sm_elem.inner_text().strip()
                        
                        # author: .font-inter.mt-auto.text-xs 文本（形如 by xxx，去掉前缀 by）
                        author_elem = item.query_selector('.font-inter.mt-auto.text-xs')
                        author_text = author_elem.inner_text().strip() if author_elem else ''
                        author = re.sub(r'^by\s+', '', author_text, flags=re.IGNORECASE).strip()
                        
                        # cover_image: 卡片首图 img@src
                        img_elem = item.query_selector('img')
                        cover_image = img_elem.get_attribute('src') if img_elem else ''
                        
                        top_picks.append({
                            'rank': rank,
                            'title': title,
                            'author': author,
                            'cover_image': cover_image,
                            'agent_url': agent_url,
                            'section': 'Top Picks',
                            'active_category': active_category,
                        })
                        batch_count += 1
                    
                    except Exception as e:
                        logger.error(f"提取 Top Picks 项目失败: {e}")
                        continue
                
                if batch_count == 0:
                    # 如果没有新项目，检查是否是因为所有项目都已处理
                    if len(items) <= len(seen_urls):
                        logger.info("所有可见项目都已处理，尝试加载更多...")
                    else:
                        logger.info("当前批次没有新项目，停止加载")
                        break
                
                logger.info(f"已提取 {len(top_picks)} 个 Top Picks 项目（本批次新增 {batch_count} 个）")
                
                # 查找右侧按钮（用于加载下一组）
                # 每次重新查找按钮，因为页面可能已更新
                # 按钮特征：在 Top Picks 容器内，位置在右侧，包含 SVG
                next_button = None
                try:
                    # 方法1: 通过 JavaScript 查找按钮（更可靠）
                    button_found = self.page.evaluate("""
                        () => {
                            // 查找包含 Top Picks 的容器
                            const containers = Array.from(document.querySelectorAll('div'));
                            let topPicksContainer = null;
                            
                            for (const container of containers) {
                                if (container.textContent && container.textContent.includes('Top Picks')) {
                                    const items = container.querySelectorAll('a[data-slot="explore-recommend-item"]');
                                    if (items.length > 0) {
                                        topPicksContainer = container;
                                        break;
                                    }
                                }
                            }
                            
                            if (!topPicksContainer) return null;
                            
                            // 查找右侧按钮
                            const buttons = topPicksContainer.querySelectorAll('button');
                            const viewportWidth = window.innerWidth;
                            
                            for (const btn of buttons) {
                                const svg = btn.querySelector('svg');
                                if (!svg) continue;
                                
                                const rect = btn.getBoundingClientRect();
                                const style = window.getComputedStyle(btn);
                                
                                // 检查是否在右侧，且不是 disabled
                                if (rect.right > viewportWidth - 100 && 
                                    !btn.hasAttribute('disabled')) {
                                    return {
                                        found: true,
                                        x: rect.x,
                                        y: rect.y,
                                        right: rect.right
                                    };
                                }
                            }
                            return null;
                        }
                    """)
                    
                    if button_found:
                        # 如果找到按钮信息，通过位置查找按钮
                        buttons = self.page.query_selector_all('button')
                        for btn in buttons:
                            try:
                                svg = btn.query_selector('svg')
                                if not svg:
                                    continue
                                
                                rect = btn.bounding_box()
                                if rect and abs(rect['x'] - button_found['x']) < 10:
                                    is_disabled = btn.get_attribute('disabled') is not None
                                    if not is_disabled:
                                        next_button = btn
                                        break
                            except:
                                continue
                    
                    # 方法2: 如果方法1失败，使用原来的查找逻辑
                    if not next_button:
                        containers = self.page.query_selector_all('div')
                        for container in containers:
                            try:
                                text = container.inner_text()
                                if 'Top Picks' in text:
                                    container_items = container.query_selector_all('a[data-slot="explore-recommend-item"]')
                                    if container_items:
                                        buttons = container.query_selector_all('button')
                                        for btn in buttons:
                                            try:
                                                svg = btn.query_selector('svg')
                                                if not svg:
                                                    continue
                                                
                                                rect = btn.bounding_box()
                                                if rect:
                                                    viewport_width = self.page.viewport_size['width'] if self.page.viewport_size else 1920
                                                    if rect['x'] + rect['width'] > viewport_width - 100:
                                                        is_disabled = btn.get_attribute('disabled') is not None
                                                        if not is_disabled:
                                                            next_button = btn
                                                            break
                                            except:
                                                continue
                                        
                                        if next_button:
                                            break
                            except:
                                continue
                            
                            if next_button:
                                break
                                
                except Exception as e:
                    logger.debug(f"查找按钮失败: {e}")
                
                if not next_button:
                    logger.info("未找到下一组按钮，停止加载")
                    break
                
                # 检查按钮是否可点击（不是 disabled）
                is_disabled = next_button.get_attribute('disabled') is not None
                if is_disabled:
                    logger.info("下一组按钮已禁用，停止加载")
                    break
                
                # 检查按钮是否可见（opacity > 0）
                try:
                    opacity = next_button.evaluate('el => window.getComputedStyle(el).opacity')
                    if float(opacity) == 0:
                        logger.info("下一组按钮不可见，停止加载")
                        break
                except:
                    pass
                
                # 点击按钮加载下一组
                logger.info(f"点击按钮加载下一组 Top Picks (第 {click_count + 1} 次)...")
                try:
                    # 记录点击前的项目数量
                    items_before = len(self.page.query_selector_all('a[data-slot="explore-recommend-item"]'))
                    
                    # 滚动到 Top Picks 区域，确保按钮可见
                    try:
                        top_picks_elem = self.page.query_selector('text="Top Picks"')
                        if top_picks_elem:
                            top_picks_elem.scroll_into_view_if_needed()
                            time.sleep(0.5)
                    except:
                        pass
                    
                    # 确保按钮可见（hover 触发显示）
                    next_button.scroll_into_view_if_needed()
                    time.sleep(0.3)
                    next_button.hover()
                    time.sleep(0.3)
                    
                    # 点击按钮
                    next_button.click()
                    
                    # 等待新内容加载 - 使用更长的等待时间
                    time.sleep(1.5)
                    
                    # 等待新项目出现（等待元素数量增加或新内容加载）
                    try:
                        # 等待至少有一个新的项目出现，或者等待网络空闲
                        self.page.wait_for_function(
                            f"""
                            () => {{
                                const items = document.querySelectorAll('a[data-slot="explore-recommend-item"]');
                                return items.length > {items_before};
                            }}
                            """,
                            timeout=10000
                        )
                    except:
                        # 如果等待函数超时，尝试等待网络空闲
                        try:
                            self.page.wait_for_load_state('networkidle', timeout=5000)
                        except:
                            pass
                    
                    # 额外等待确保内容完全渲染
                    time.sleep(1)
                    
                    click_count += 1
                    
                    # 重新查询当前可见的项目数量
                    items_after = len(self.page.query_selector_all('a[data-slot="explore-recommend-item"]'))
                    logger.info(f"点击后，项目数量从 {items_before} 变为 {items_after}")
                    
                except Exception as e:
                    logger.warning(f"点击下一组按钮失败: {e}")
                    break
            
            logger.info(f"成功提取 {len(top_picks)} 个 Top Picks 项目（共点击 {click_count} 次）")
            return top_picks
            
        except Exception as e:
            logger.error(f"提取 Top Picks 失败: {e}", exc_info=True)
            return top_picks
    
    def _extract_trending_ai_pics(self) -> List[Dict]:
        """
        提取 Trending AI Pics 轮播卡片
        
        Returns:
            List[Dict]: Trending AI Pics 列表
        """
        logger.info("开始提取 Trending AI Pics 轮播卡片...")
        trending_items = []
        active_category = self._get_active_category()
        
        try:
            # 查找包含 "Trending AI Pics" 文案的区域
            trending_section = self.page.query_selector('text="Trending AI Pics"')
            if not trending_section:
                logger.warning("未找到 Trending AI Pics 区域")
                return trending_items
            
            # 提取所有轮播卡片
            items = self.page.query_selector_all('[data-slot="carousel-item"] a.group, [data-slot="carousel-item"] a.card')
            logger.info(f"找到 {len(items)} 个 Trending AI Pics 项目")
            
            for item in items:
                try:
                    # title: .font-inter.text-sm 文本
                    title_elem = item.query_selector('.font-inter.text-sm')
                    title = title_elem.inner_text().strip() if title_elem else ''
                    
                    # author: .font-inter.text-xs 文本（去掉 by）
                    author_elem = item.query_selector('.font-inter.text-xs')
                    author_text = author_elem.inner_text().strip() if author_elem else ''
                    author = re.sub(r'^by\s+', '', author_text, flags=re.IGNORECASE).strip()
                    
                    # cover_image: 卡片首图 img@src
                    img_elem = item.query_selector('img')
                    cover_image = img_elem.get_attribute('src') if img_elem else ''
                    
                    # agent_url: a@href（绝对 URL）
                    href = item.get_attribute('href') or ''
                    agent_url = urljoin(self.base_url, href) if href else ''
                    
                    # approx_run_cost: 卡片底部"NN / run (approx.)"里的数字
                    approx_run_cost = None
                    cost_text = item.inner_text()
                    cost_match = re.search(r'(\d+)\s*/.*?run.*?approx', cost_text, re.IGNORECASE)
                    if cost_match:
                        approx_run_cost = int(cost_match.group(1))
                    
                    if agent_url:
                        trending_items.append({
                            'title': title,
                            'author': author,
                            'cover_image': cover_image,
                            'agent_url': agent_url,
                            'approx_run_cost': approx_run_cost,
                            'section': 'Trending AI Pics',
                            'active_category': active_category,
                        })
                
                except Exception as e:
                    logger.error(f"提取 Trending AI Pics 项目失败: {e}")
                    continue
            
            logger.info(f"成功提取 {len(trending_items)} 个 Trending AI Pics 项目")
            return trending_items
            
        except Exception as e:
            logger.error(f"提取 Trending AI Pics 失败: {e}", exc_info=True)
            return trending_items
    
    def _extract_detail_page_info(self, agent_url: str) -> Dict:
        """
        从详情页提取额外信息
        
        Args:
            agent_url: agent 详情页 URL
            
        Returns:
            Dict: 详情页信息
        """
        detail_info = {
            'agent_name': None,
            'owner_handle': None,
            'description': None,
            'tags': [],
            'stats': {},
            'version': None,
            'last_updated': None,
            'inputs_schema': [],
            'external_links': [],
        }
        
        detail_page = None
        try:
            logger.debug(f"访问详情页: {agent_url}")
            
            # 在新标签页中打开详情页（避免影响主页面）
            detail_page = self.browser.new_page()
            detail_page.goto(
                agent_url,
                wait_until='domcontentloaded',
                timeout=self.config.get('detail_page_timeout', 30000)
            )
            
            # 等待 JavaScript 渲染
            time.sleep(self.config.get('detail_page_wait', 2))
            
            # 尝试等待网络空闲
            try:
                detail_page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            
            # agent_name: 页面主标题（首个 h1 或 [data-agent-name]）
            agent_name_elem = (
                detail_page.query_selector('h1') or
                detail_page.query_selector('[data-agent-name]')
            )
            if agent_name_elem:
                detail_info['agent_name'] = agent_name_elem.inner_text().strip()
            
            # owner_handle: 作者/发布者标识
            # 优先取显式 by xxx 或作者链接文本
            owner_elem = (
                detail_page.query_selector('text=/by\\s+\\w+/i') or
                detail_page.query_selector('a[href*="/@"]')
            )
            if owner_elem:
                owner_text = owner_elem.inner_text().strip()
                owner_match = re.search(r'by\s+([^\s]+)', owner_text, re.IGNORECASE)
                if owner_match:
                    detail_info['owner_handle'] = owner_match.group(1)
                else:
                    detail_info['owner_handle'] = owner_text
            
            # description: 首屏描述段落（首个长段落或 meta og:description）
            desc_elem = detail_page.query_selector('meta[property="og:description"]')
            if desc_elem:
                detail_info['description'] = desc_elem.get_attribute('content') or ''
            else:
                # 查找首屏长段落
                paragraphs = detail_page.query_selector_all('p')
                for p in paragraphs:
                    text = p.inner_text().strip()
                    if len(text) > 50:  # 长段落
                        detail_info['description'] = text
                        break
            
            # tags: 详情页展示的标签 chips
            tag_elements = detail_page.query_selector_all('span.badge, span.chip, [class*="tag"], [class*="label"]')
            for tag_elem in tag_elements:
                tag_text = tag_elem.inner_text().strip()
                if tag_text and tag_text not in detail_info['tags']:
                    detail_info['tags'].append(tag_text)
            
            # stats: 运行数、点赞/收藏数等（数字+标签对）
            # 查找包含数字和标签的统计信息
            stat_elements = detail_page.query_selector_all('[class*="stat"], [class*="count"]')
            for stat_elem in stat_elements:
                text = stat_elem.inner_text().strip()
                # 尝试提取数字和标签
                stat_match = re.search(r'(\d+[\d,]*)\s*([^\d]+)', text)
                if stat_match:
                    value = stat_match.group(1).replace(',', '')
                    label = stat_match.group(2).strip()
                    detail_info['stats'][label] = value
            
            # version: 页面可见版本号或卡片图 URL 参数中的 v1.0.x
            version_elem = detail_page.query_selector('text=/v?\\d+\\.\\d+(\\.\\d+)?/i')
            if version_elem:
                version_text = version_elem.inner_text()
                version_match = re.search(r'v?(\d+\.\d+(?:\.\d+)?)', version_text, re.IGNORECASE)
                if version_match:
                    detail_info['version'] = version_match.group(1)
            
            # 如果页面中没有找到版本号，尝试从图片 URL 中提取
            if not detail_info['version']:
                img_elem = detail_page.query_selector('img[src*="v"]')
                if img_elem:
                    img_src = img_elem.get_attribute('src') or ''
                    version_match = re.search(r'[vV](\d+\.\d+(?:\.\d+)?)', img_src)
                    if version_match:
                        detail_info['version'] = version_match.group(1)
            
            # last_updated: 页面展示的更新时间
            update_elem = detail_page.query_selector('text=/updated|last.*?update/i')
            if update_elem:
                update_text = update_elem.inner_text()
                detail_info['last_updated'] = update_text.strip()
            
            # inputs_schema: 若页面提供参数/表单项，列出字段名与类型
            input_elements = detail_page.query_selector_all('input, select, textarea')
            for input_elem in input_elements:
                input_name = input_elem.get_attribute('name') or input_elem.get_attribute('id') or ''
                input_type = input_elem.get_attribute('type') or input_elem.evaluate('el => el.tagName.toLowerCase()')
                
                # 查找对应的 label
                label_elem = detail_page.query_selector(f'label[for="{input_name}"]')
                label = label_elem.inner_text().strip() if label_elem else input_name
                
                if label:
                    detail_info['inputs_schema'].append({
                        'name': input_name,
                        'label': label,
                        'type': input_type,
                    })
            
            # external_links: 详情页中的外链（如 GitHub/文档/演示）
            link_elements = detail_page.query_selector_all('a[href^="http"]')
            for link_elem in link_elements:
                href = link_elem.get_attribute('href') or ''
                link_text = link_elem.inner_text().strip()
                
                # 过滤掉 mulerun.com 的链接
                if 'mulerun.com' not in href:
                    detail_info['external_links'].append({
                        'url': href,
                        'text': link_text,
                    })
            
        except Exception as e:
            logger.error(f"提取详情页信息失败 ({agent_url}): {e}", exc_info=True)
        finally:
            # 确保关闭详情页
            if detail_page:
                try:
                    detail_page.close()
                except:
                    pass
        
        return detail_info
    
    def crawl(self) -> List[Dict]:
        """
        爬取所有 agents
        
        Returns:
            List[Dict]: agent 信息列表
        """
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 5)
        
        # 重试访问页面
        for attempt in range(max_retries):
            try:
                self._init_browser()
                
                # 访问 agent-store 页面
                logger.info(f"访问 {self.config['base_url']} (尝试 {attempt + 1}/{max_retries})")
                
                # 设置超时时间
                timeout = self.config.get('page_load_timeout', 60000)
                wait_strategy = self.config.get('page_wait_strategy', 'load')
                
                self.page.goto(
                    self.config['base_url'],
                    wait_until=wait_strategy,
                    timeout=timeout
                )
                
                # 等待 JavaScript 渲染（SPA 应用需要）
                wait_after_load = self.config.get('page_wait_after_load', 5)
                logger.info(f"页面加载完成，等待 {wait_after_load} 秒让 JavaScript 渲染...")
                time.sleep(wait_after_load)
                
                break  # 成功则跳出重试循环
                
            except Exception as e:
                logger.warning(f"访问页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                # 确保完全清理浏览器和 playwright 实例
                self._close_browser()
                
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    raise  # 最后一次尝试失败则抛出异常
        
        # 页面访问成功后，继续执行爬取逻辑
        try:
            # 滚动页面以触发懒加载
            scroll_count = self.config.get('scroll_count', 3)
            self._scroll_page(times=scroll_count)
            
            # 提取 Top Picks
            top_picks = self._extract_top_picks()
            
            # 提取 Trending AI Pics
            trending_items = self._extract_trending_ai_pics()
            
            # 合并所有项目
            all_agents = top_picks + trending_items
            logger.info(f"列表页共提取 {len(all_agents)} 个 agents")
            
            # 访问详情页获取额外信息
            logger.info("开始访问详情页获取额外信息...")
            for idx, agent in enumerate(all_agents, start=1):
                agent_url = agent.get('agent_url')
                if agent_url:
                    logger.info(f"处理详情页 {idx}/{len(all_agents)}: {agent_url}")
                    detail_info = self._extract_detail_page_info(agent_url)
                    # 合并详情页信息
                    agent.update(detail_info)
                    # 添加延迟避免请求过快
                    time.sleep(0.5)
            
            # 映射字段名到数据库期望的格式
            mapped_agents = []
            for idx, agent in enumerate(all_agents, start=1):
                try:
                    # 处理 rank（优先使用原始 rank，否则使用索引）
                    rank_value = idx  # 默认使用索引
                    rank_str = agent.get('rank')
                    if rank_str:
                        try:
                            # 尝试从 rank 字符串中提取数字
                            rank_match = re.search(r'(\d+)', str(rank_str))
                            if rank_match:
                                rank_value = int(rank_match.group(1))
                        except:
                            pass
                    
                    # 字段映射
                    mapped_agent = {
                        'link': agent.get('agent_url', ''),
                        'name': agent.get('agent_name') or agent.get('title', ''),
                        'description': agent.get('description'),
                        'avatar_url': agent.get('cover_image'),
                        'price': None,
                        'author': agent.get('author') or agent.get('owner_handle'),
                        'rank': rank_value,
                    }
                    
                    # 处理 price 字段（approx_run_cost）
                    approx_cost = agent.get('approx_run_cost')
                    if approx_cost is not None:
                        mapped_agent['price'] = f"{approx_cost} / run (approx.)"
                    
                    # 保留原始字段和详情页字段（用于扩展）
                    mapped_agent['section'] = agent.get('section')
                    mapped_agent['active_category'] = agent.get('active_category')
                    mapped_agent['tags'] = agent.get('tags', [])
                    mapped_agent['stats'] = agent.get('stats', {})
                    mapped_agent['version'] = agent.get('version')
                    mapped_agent['last_updated'] = agent.get('last_updated')
                    mapped_agent['inputs_schema'] = agent.get('inputs_schema', [])
                    mapped_agent['external_links'] = agent.get('external_links', [])
                    
                    # 确保必需字段存在
                    if mapped_agent['link'] and mapped_agent['name']:
                        mapped_agents.append(mapped_agent)
                    else:
                        logger.warning(f"跳过无效 agent: {agent}")
                
                except Exception as e:
                    logger.error(f"映射 agent 字段失败: {e}")
                    continue
            
            logger.info(f"成功爬取 {len(mapped_agents)} 个 agents")
            return mapped_agents
            
        except Exception as e:
            logger.error(f"爬取过程出错: {e}", exc_info=True)
            raise
        finally:
            self._close_browser()
    
    def _close_browser(self):
        """关闭浏览器和 playwright 实例"""
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.warning(f"关闭浏览器时出错: {e}")
            self.browser = None
            self.page = None
        
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.warning(f"停止 playwright 时出错: {e}")
            self.playwright = None


def crawl_agents() -> List[Dict]:
    """
    爬取 agents 的便捷函数
    
    Returns:
        List[Dict]: agent 信息列表
    """
    crawler = MuleRunCrawler()
    return crawler.crawl()
