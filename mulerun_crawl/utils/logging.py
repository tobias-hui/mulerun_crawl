"""日志工具函数"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from ..config import LOG_CONFIG, BASE_DIR


def setup_logging():
    """配置日志"""
    # 创建日志目录
    log_file = LOG_CONFIG['file']
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(LOG_CONFIG['format'])
    
    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG['max_bytes'],
        backupCount=LOG_CONFIG['backup_count'],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(LOG_CONFIG['level'])
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(LOG_CONFIG['level'])
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_CONFIG['level'])
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

