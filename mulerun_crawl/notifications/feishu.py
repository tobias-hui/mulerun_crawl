"""飞书机器人通知模块"""
import logging
import requests
import os
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 从环境变量读取飞书 Webhook URL
FEISHU_WEBHOOK_URL = os.getenv(
    'FEISHU_WEBHOOK_URL',
    'https://open.feishu.cn/open-apis/bot/v2/hook/94adca4b-556b-4a5b-9b63-ce3cac5bd8bc'
)


class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: 飞书 Webhook URL，如果不提供则从环境变量读取
        """
        self.webhook_url = webhook_url or FEISHU_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)
    
    def send_text(self, text: str) -> bool:
        """
        发送文本消息
        
        Args:
            text: 消息内容
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("飞书通知未启用")
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        return self._send(payload)
    
    def send_crawl_summary(self, stats: Dict, crawl_time: datetime) -> bool:
        """
        发送爬取总结消息
        
        Args:
            stats: 统计信息字典
            crawl_time: 爬取时间
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        text = f"""✅ MuleRun 爬取完成

📊 统计信息：
• 活跃 agents: {stats.get('active_agents', 0)}
• 下架 agents: {stats.get('inactive_agents', 0)}
• 总爬取次数: {stats.get('total_crawls', 0)}
• 爬取时间: {crawl_time.strftime('%Y-%m-%d %H:%M:%S')}

⏰ 下次执行: 24小时后"""
        
        return self.send_text(text)
    
    def send_agent_removed_notification(self, removed_agents: List[Dict]) -> bool:
        """
        发送 agent 下架通知
        
        Args:
            removed_agents: 下架的 agent 列表，每个元素包含 link, name 等信息
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled or not removed_agents:
            return False
        
        if len(removed_agents) == 1:
            agent = removed_agents[0]
            text = f"""⚠️ Agent 下架通知

📛 名称: {agent.get('name', 'Unknown')}
🔗 链接: https://mulerun.com{agent.get('link', '')}
👤 作者: {agent.get('author', 'Unknown')}

该 agent 已从 MuleRun 下架"""
        else:
            agent_list = "\n".join([
                f"• {agent.get('name', 'Unknown')} ({agent.get('author', 'Unknown')})"
                for agent in removed_agents[:10]  # 最多显示10个
            ])
            if len(removed_agents) > 10:
                agent_list += f"\n... 还有 {len(removed_agents) - 10} 个"
            
            text = f"""⚠️ 批量 Agent 下架通知

共发现 {len(removed_agents)} 个 agents 下架：

{agent_list}

请查看详情: https://mulerun.com"""
        
        return self.send_text(text)
    
    def _send(self, payload: Dict) -> bool:
        """
        发送消息到飞书
        
        Args:
            payload: 消息负载
            
        Returns:
            bool: 是否发送成功
        """
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                logger.info("飞书通知发送成功")
                return True
            else:
                logger.warning(f"飞书通知发送失败: {result.get('msg', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"发送飞书通知时出错: {e}", exc_info=True)
            return False


def send_feishu_notification(text: str) -> bool:
    """
    发送飞书通知的便捷函数
    
    Args:
        text: 消息内容
        
    Returns:
        bool: 是否发送成功
    """
    notifier = FeishuNotifier()
    return notifier.send_text(text)

