"""
统一响应模型 - 与 v6.1.0 架构文档对齐

本模块定义了 API 的统一响应格式，包括:
- 错误码枚举 (ErrorCode)
- 错误详情 (ErrorDetail)
- 响应元数据 (ResponseMeta)
- 统一响应信封 (APIResponse)
- 批量响应 (BatchResponse)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """
    错误码枚举 - 与 v6.1.0 §B.2 对齐

    分为两类:
    1. 可重试错误 (retryable=true): 建议 n8n 进行重试
    2. 不可重试错误 (retryable=false): 需要人工介入或跳过
    """

    # ============ LLM 相关错误 (从 v6.1.0 继承) ============
    LLM_OUTPUT_PARSE_FAIL = "LLM_OUTPUT_PARSE_FAIL"      # LLM输出解析失败
    LLM_OUTPUT_SCHEMA_FAIL = "LLM_OUTPUT_SCHEMA_FAIL"    # LLM输出schema校验失败
    LLM_TIMEOUT = "LLM_TIMEOUT"                          # LLM请求超时
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"                    # LLM速率限制
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"              # LLM服务错误
    GENERATION_FAILED = "GENERATION_FAILED"              # 生成失败
    LLM_REQUEST_ERROR = "LLM_REQUEST_ERROR"              # LLM请求错误 (不可重试)
    INVALID_INPUT = "INVALID_INPUT"                      # 无效输入 (不可重试)
    CONTENT_VIOLATION = "CONTENT_VIOLATION"              # 内容违规 (不可重试)

    # ============ 爬虫特有错误 ============
    COOKIE_EXHAUSTED = "COOKIE_EXHAUSTED"    # Cookie耗尽，无可用账号
    COOKIE_INVALID = "COOKIE_INVALID"        # Cookie失效，需要重新登录
    COOKIE_COOLING = "COOKIE_COOLING"        # Cookie冷却中，需要等待
    ACCOUNT_BANNED = "ACCOUNT_BANNED"        # 账号被封禁
    PLATFORM_ERROR = "PLATFORM_ERROR"        # 平台返回错误
    PARSE_ERROR = "PARSE_ERROR"              # 内容解析错误
    NETWORK_ERROR = "NETWORK_ERROR"          # 网络错误
    TIMEOUT_ERROR = "TIMEOUT_ERROR"          # 请求超时
    PARTIAL_FAIL = "PARTIAL_FAIL"            # 批量操作部分失败
    NOT_FOUND = "NOT_FOUND"                  # 资源不存在
    RATE_LIMITED = "RATE_LIMITED"            # 请求频率限制


# 错误码配置: 定义每个错误码的重试策略和HTTP状态码
ERROR_CONFIG: Dict[str, Dict] = {
    # Cookie 相关
    ErrorCode.COOKIE_EXHAUSTED: {
        "retryable": False,
        "http_status": 503,
        "description": "无可用Cookie，需要人工添加新账号"
    },
    ErrorCode.COOKIE_INVALID: {
        "retryable": True,
        "http_status": 401,
        "description": "Cookie失效，将自动切换到其他Cookie"
    },
    ErrorCode.COOKIE_COOLING: {
        "retryable": True,
        "http_status": 429,
        "description": "Cookie冷却中，等待后重试"
    },
    ErrorCode.ACCOUNT_BANNED: {
        "retryable": False,
        "http_status": 403,
        "description": "账号被平台封禁，需移除此Cookie"
    },

    # 平台/网络相关
    ErrorCode.PLATFORM_ERROR: {
        "retryable": True,
        "http_status": 502,
        "description": "平台返回错误，建议重试2次"
    },
    ErrorCode.PARSE_ERROR: {
        "retryable": True,
        "http_status": 500,
        "description": "内容解析失败，建议重试2次"
    },
    ErrorCode.NETWORK_ERROR: {
        "retryable": True,
        "http_status": 503,
        "description": "网络错误，建议指数退避重试3次"
    },
    ErrorCode.TIMEOUT_ERROR: {
        "retryable": True,
        "http_status": 504,
        "description": "请求超时，建议重试2次"
    },

    # 批量操作
    ErrorCode.PARTIAL_FAIL: {
        "retryable": True,  # 部分失败时，可重试失败项
        "http_status": 207,
        "description": "部分项目失败，成功项已返回"
    },

    # 输入相关
    ErrorCode.INVALID_INPUT: {
        "retryable": False,
        "http_status": 400,
        "description": "输入参数无效，需要修正后重试"
    },
    ErrorCode.NOT_FOUND: {
        "retryable": False,
        "http_status": 404,
        "description": "请求的资源不存在"
    },
    ErrorCode.RATE_LIMITED: {
        "retryable": True,
        "http_status": 429,
        "description": "请求频率过高，需要降低频率"
    },

    # LLM 相关
    ErrorCode.LLM_OUTPUT_PARSE_FAIL: {
        "retryable": True,
        "http_status": 500,
        "description": "LLM输出解析失败"
    },
    ErrorCode.LLM_OUTPUT_SCHEMA_FAIL: {
        "retryable": True,
        "http_status": 500,
        "description": "LLM输出schema校验失败"
    },
    ErrorCode.LLM_TIMEOUT: {
        "retryable": True,
        "http_status": 504,
        "description": "LLM请求超时"
    },
    ErrorCode.LLM_RATE_LIMIT: {
        "retryable": True,
        "http_status": 429,
        "description": "LLM速率限制"
    },
    ErrorCode.LLM_SERVICE_ERROR: {
        "retryable": True,
        "http_status": 503,
        "description": "LLM服务错误"
    },
    ErrorCode.GENERATION_FAILED: {
        "retryable": True,
        "http_status": 500,
        "description": "生成失败"
    },
    ErrorCode.LLM_REQUEST_ERROR: {
        "retryable": False,
        "http_status": 400,
        "description": "LLM请求错误"
    },
    ErrorCode.CONTENT_VIOLATION: {
        "retryable": False,
        "http_status": 403,
        "description": "内容违规"
    },
}


class ErrorDetail(BaseModel):
    """
    错误详情模型

    用于描述错误的详细信息，包括错误码、消息、是否可重试等
    """
    code: ErrorCode = Field(..., description="错误码")
    message: str = Field(..., description="错误描述信息")
    retryable: bool = Field(..., description="是否可重试")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="额外错误详情，如失败的ID列表、原始错误信息等"
    )

    @classmethod
    def from_code(cls, code: ErrorCode, message: str, details: Optional[Dict] = None):
        """从错误码创建错误详情"""
        config = ERROR_CONFIG.get(code, {"retryable": False})
        return cls(
            code=code,
            message=message,
            retryable=config["retryable"],
            details=details
        )


class ResponseMeta(BaseModel):
    """
    响应元数据 - 用于可观测性

    每个响应都包含元数据，用于追踪请求、分析性能等
    """
    request_id: str = Field(..., description="请求追踪ID，全链路唯一")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="响应时间戳 (UTC)"
    )
    latency_ms: int = Field(..., description="处理耗时(毫秒)")
    cookie_used: Optional[str] = Field(
        None,
        description="使用的Cookie名称 (脱敏后)"
    )
    retry_count: int = Field(
        default=0,
        description="内部重试次数"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIResponse(BaseModel):
    """
    统一响应信封 - 所有API响应的标准格式

    设计原则:
    - success: 明确标识请求是否成功
    - data: 成功时返回的数据
    - error: 失败时返回的错误详情
    - meta: 可观测性元数据
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="成功时的响应数据"
    )
    error: Optional[ErrorDetail] = Field(
        None,
        description="失败时的错误详情"
    )
    meta: ResponseMeta = Field(..., description="响应元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "items": [],
                    "total": 0
                },
                "error": None,
                "meta": {
                    "request_id": "req-abc123",
                    "timestamp": "2025-12-16T10:00:00Z",
                    "latency_ms": 1234,
                    "cookie_used": "account_01",
                    "retry_count": 0
                }
            }
        }


class BatchItemResult(BaseModel):
    """
    批量操作单项结果

    用于批量操作时，记录每个项目的处理结果
    """
    id: str = Field(..., description="项目ID (如 note_id)")
    success: bool = Field(..., description="该项是否成功")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="成功时的数据"
    )
    error: Optional[ErrorDetail] = Field(
        None,
        description="失败时的错误详情"
    )


class BatchResponse(BaseModel):
    """
    批量操作响应 - 支持部分失败

    设计原则:
    - 即使部分失败，也返回成功的结果
    - items 包含每个项目的详细结果
    - summary 提供统计信息
    - error 在有失败时包含整体错误信息
    """
    success: bool = Field(
        ...,
        description="全部成功时为true，有任何失败时为false"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="请求相关的元信息"
    )
    items: List[BatchItemResult] = Field(
        default_factory=list,
        description="每个项目的处理结果"
    )
    summary: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "succeeded": 0, "failed": 0},
        description="处理结果统计"
    )
    error: Optional[ErrorDetail] = Field(
        None,
        description="有失败时的整体错误信息"
    )
    meta: ResponseMeta = Field(..., description="响应元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "data": {"platform": "xhs", "keyword": "粉底液"},
                "items": [
                    {
                        "id": "note_001",
                        "success": True,
                        "data": {"title": "好用的粉底液", "liked_count": 3200},
                        "error": None
                    },
                    {
                        "id": "note_002",
                        "success": False,
                        "data": None,
                        "error": {
                            "code": "TIMEOUT_ERROR",
                            "message": "获取笔记详情超时",
                            "retryable": True,
                            "details": {"timeout_seconds": 30}
                        }
                    }
                ],
                "summary": {"total": 2, "succeeded": 1, "failed": 1},
                "error": {
                    "code": "PARTIAL_FAIL",
                    "message": "部分笔记获取失败: 1/2",
                    "retryable": True,
                    "details": {"failed_ids": ["note_002"]}
                },
                "meta": {
                    "request_id": "req-batch-001",
                    "timestamp": "2025-12-16T10:00:00Z",
                    "latency_ms": 5000,
                    "cookie_used": "account_01",
                    "retry_count": 0
                }
            }
        }


# ============ 辅助函数 ============

def create_success_response(
    data: Dict[str, Any],
    request_id: str,
    latency_ms: int,
    cookie_used: Optional[str] = None
) -> APIResponse:
    """创建成功响应"""
    return APIResponse(
        success=True,
        data=data,
        error=None,
        meta=ResponseMeta(
            request_id=request_id,
            latency_ms=latency_ms,
            cookie_used=cookie_used
        )
    )


def create_error_response(
    error_code: ErrorCode,
    message: str,
    request_id: str,
    latency_ms: int,
    details: Optional[Dict] = None,
    cookie_used: Optional[str] = None
) -> APIResponse:
    """创建错误响应"""
    return APIResponse(
        success=False,
        data=None,
        error=ErrorDetail.from_code(error_code, message, details),
        meta=ResponseMeta(
            request_id=request_id,
            latency_ms=latency_ms,
            cookie_used=cookie_used
        )
    )


def create_batch_response(
    items: List[BatchItemResult],
    request_id: str,
    latency_ms: int,
    data: Optional[Dict] = None,
    cookie_used: Optional[str] = None
) -> BatchResponse:
    """创建批量响应"""
    succeeded = sum(1 for item in items if item.success)
    failed = len(items) - succeeded

    error = None
    if failed > 0:
        failed_ids = [item.id for item in items if not item.success]
        error = ErrorDetail.from_code(
            ErrorCode.PARTIAL_FAIL,
            f"部分操作失败: {failed}/{len(items)}",
            {"failed_ids": failed_ids}
        )

    return BatchResponse(
        success=(failed == 0),
        data=data or {},
        items=items,
        summary={
            "total": len(items),
            "succeeded": succeeded,
            "failed": failed
        },
        error=error,
        meta=ResponseMeta(
            request_id=request_id,
            latency_ms=latency_ms,
            cookie_used=cookie_used
        )
    )
