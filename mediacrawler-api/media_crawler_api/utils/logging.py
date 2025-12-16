"""
日志脱敏模块

本模块提供日志的自动脱敏功能，确保敏感信息不会出现在日志中。

脱敏范围:
1. Cookie 相关字段 (web_session, a1, gid, webId 等)
2. 认证信息 (Authorization, Bearer, token)
3. API 密钥 (api_key, secret, password)

使用方式:
    from media_crawler_api.utils.logging import get_logger

    logger = get_logger(__name__)
    logger.info("处理请求", extra={"request_id": "xxx"})
"""

import re
import logging
import json
import sys
from typing import Any, Dict, Tuple, List, Optional
from functools import wraps
from contextvars import ContextVar


# ============ 上下文变量 ============

# 当前请求 ID (用于日志追踪)
current_request_id: ContextVar[str] = ContextVar('request_id', default='-')


# ============ 脱敏规则 ============

# 敏感字段正则表达式和替换规则
SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Cookie 值 (小红书相关)
    (re.compile(r'(web_session|a1|webId|gid|xsecappid|abRequestId)=[^;\s&"\']+',
                re.IGNORECASE),
     r'\1=***REDACTED***'),

    # Cookie JSON 字段
    (re.compile(r'"cookie_value"\s*:\s*"[^"]*"', re.IGNORECASE),
     '"cookie_value": "***REDACTED***"'),
    (re.compile(r'"cookie_encrypted"\s*:\s*"[^"]*"', re.IGNORECASE),
     '"cookie_encrypted": "***REDACTED***"'),
    (re.compile(r'"cookie_string"\s*:\s*"[^"]*"', re.IGNORECASE),
     '"cookie_string": "***REDACTED***"'),

    # Authorization 头
    (re.compile(r'(Authorization|Bearer)\s*[:=]\s*[^\s,}\]]+', re.IGNORECASE),
     r'\1: ***REDACTED***'),

    # API 密钥和密码
    (re.compile(r'(api_key|apikey|api-key|secret|password|passwd|pwd)\s*[:=]\s*[^\s,}\]"\']+',
                re.IGNORECASE),
     r'\1=***REDACTED***'),

    # Token
    (re.compile(r'(token|access_token|refresh_token)\s*[:=]\s*[^\s,}\]"\']+',
                re.IGNORECASE),
     r'\1=***REDACTED***'),

    # 加密密钥
    (re.compile(r'(MASTER_KEY|ENCRYPTION_KEY|PRIVATE_KEY)\s*[:=]\s*[^\s,}\]"\']+',
                re.IGNORECASE),
     r'\1=***REDACTED***'),
]

# 需要脱敏的字典键名 (小写)
SENSITIVE_KEYS = {
    'cookie_value', 'cookie_encrypted', 'cookie_string', 'cookie',
    'password', 'passwd', 'pwd', 'secret',
    'api_key', 'apikey', 'api-key',
    'token', 'access_token', 'refresh_token',
    'authorization', 'bearer',
    'master_key', 'encryption_key', 'private_key',
}


def sanitize_log(message: str) -> str:
    """
    脱敏日志消息字符串

    Args:
        message: 原始日志消息

    Returns:
        脱敏后的消息

    Example:
        >>> sanitize_log("Cookie: web_session=abc123; a1=xyz789")
        "Cookie: web_session=***REDACTED***; a1=***REDACTED***"
    """
    if not message:
        return message

    result = str(message)
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def sanitize_dict(data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
    """
    脱敏字典内容 (递归处理)

    Args:
        data: 原始字典
        max_depth: 最大递归深度

    Returns:
        脱敏后的字典

    Example:
        >>> sanitize_dict({"cookie_value": "secret123", "name": "test"})
        {"cookie_value": "***REDACTED***", "name": "test"}
    """
    if max_depth <= 0:
        return data

    def _sanitize(obj: Any, depth: int) -> Any:
        if depth <= 0:
            return obj

        if isinstance(obj, dict):
            return {
                k: '***REDACTED***' if k.lower() in SENSITIVE_KEYS else _sanitize(v, depth - 1)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_sanitize(item, depth - 1) for item in obj]
        elif isinstance(obj, str):
            return sanitize_log(obj)
        return obj

    return _sanitize(data, max_depth)


class SanitizedFormatter(logging.Formatter):
    """
    脱敏日志格式化器

    自动对日志消息和参数进行脱敏处理
    """

    def format(self, record: logging.LogRecord) -> str:
        # 添加 request_id
        if not hasattr(record, 'request_id') or not record.request_id:
            record.request_id = current_request_id.get()

        # 脱敏消息
        if record.msg:
            record.msg = sanitize_log(str(record.msg))

        # 脱敏参数
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize_log(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(sanitize_dict(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        return super().format(record)


class RequestIdFilter(logging.Filter):
    """
    请求 ID 过滤器

    自动添加 request_id 到日志记录
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id') or not record.request_id:
            record.request_id = current_request_id.get()
        return True


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取脱敏日志器

    Args:
        name: 日志器名称，通常使用 __name__
        level: 日志级别

    Returns:
        配置好的日志器

    Example:
        logger = get_logger(__name__)
        logger.info("处理用户请求", extra={"request_id": "req-123"})
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # 创建控制台处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # 设置脱敏格式化器
    formatter = SanitizedFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # 添加请求 ID 过滤器
    handler.addFilter(RequestIdFilter())

    logger.addHandler(handler)

    return logger


def set_request_id(request_id: str) -> None:
    """
    设置当前请求 ID

    Args:
        request_id: 请求追踪 ID
    """
    current_request_id.set(request_id)


def get_current_request_id() -> str:
    """获取当前请求 ID"""
    return current_request_id.get()


# ============ 装饰器 ============

def log_sanitized(logger: logging.Logger):
    """
    装饰器: 自动脱敏函数参数并记录日志

    Args:
        logger: 日志器实例

    Example:
        @log_sanitized(logger)
        async def process_cookie(cookie_value: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            sanitized_kwargs = sanitize_dict(kwargs)
            logger.info(f"调用 {func.__name__}, 参数: {sanitized_kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"{func.__name__} 成功")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} 失败: {sanitize_log(str(e))}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            sanitized_kwargs = sanitize_dict(kwargs)
            logger.info(f"调用 {func.__name__}, 参数: {sanitized_kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"{func.__name__} 成功")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} 失败: {sanitize_log(str(e))}")
                raise

        # 判断是否是异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============ JSON 日志格式化器 (用于生产环境) ============

class JSONFormatter(logging.Formatter):
    """
    JSON 格式日志 (适用于日志收集系统)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_log(str(record.getMessage())),
            "request_id": getattr(record, 'request_id', current_request_id.get()),
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = sanitize_log(self.formatException(record.exc_info))

        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_data.update(sanitize_dict(record.extra_fields))

        return json.dumps(log_data, ensure_ascii=False)


def get_json_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取 JSON 格式的脱敏日志器 (用于生产环境)
    """
    logger = logging.getLogger(f"{name}.json")

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIdFilter())

    logger.addHandler(handler)

    return logger
