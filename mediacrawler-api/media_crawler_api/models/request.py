"""
请求模型定义

本模块定义了 API 的请求参数模型
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class Platform(str, Enum):
    """支持的平台"""
    XHS = "xhs"           # 小红书
    DOUYIN = "dy"         # 抖音
    WEIBO = "wb"          # 微博


class SortType(str, Enum):
    """搜索排序类型"""
    GENERAL = "general"           # 综合排序
    TIME_DESC = "time_descending" # 最新优先
    POPULARITY = "popularity_descending"  # 热度优先


class NoteType(str, Enum):
    """笔记类型"""
    ALL = "0"      # 全部
    VIDEO = "1"    # 视频
    IMAGE = "2"    # 图文


class NoteDetailRequest(BaseModel):
    """
    获取笔记详情请求

    支持单个或批量获取笔记详情
    """
    platform: Platform = Field(
        default=Platform.XHS,
        description="目标平台"
    )
    note_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=20,
        description="笔记ID列表，最多20个"
    )
    cookie_name: Optional[str] = Field(
        None,
        description="指定使用的Cookie名称，不指定则自动选择"
    )
    get_comments: bool = Field(
        default=True,
        description="是否获取评论"
    )
    comments_limit: int = Field(
        default=50,
        ge=0,
        le=200,
        description="评论获取数量上限"
    )

    @validator('note_ids')
    def validate_note_ids(cls, v):
        """验证笔记ID列表"""
        if len(v) == 0:
            raise ValueError('note_ids 不能为空')
        # 去重
        return list(dict.fromkeys(v))

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "xhs",
                "note_ids": ["6707e0ec000000001e0318cc", "6707e0ec000000001e0318cd"],
                "cookie_name": None,
                "get_comments": True,
                "comments_limit": 50
            }
        }


class SearchRequest(BaseModel):
    """
    搜索笔记请求
    """
    platform: Platform = Field(
        default=Platform.XHS,
        description="目标平台"
    )
    keyword: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="搜索关键词"
    )
    cookie_name: Optional[str] = Field(
        None,
        description="指定使用的Cookie名称"
    )
    page: int = Field(
        default=1,
        ge=1,
        le=100,
        description="页码"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=50,
        description="每页数量"
    )
    sort_type: SortType = Field(
        default=SortType.GENERAL,
        description="排序方式"
    )
    note_type: NoteType = Field(
        default=NoteType.ALL,
        description="笔记类型过滤"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "xhs",
                "keyword": "粉底液推荐",
                "page": 1,
                "page_size": 20,
                "sort_type": "general",
                "note_type": "0"
            }
        }


class CookieStatus(str, Enum):
    """Cookie状态"""
    ACTIVE = "active"       # 活跃可用
    COOLING = "cooling"     # 冷却中
    INVALID = "invalid"     # 已失效
    BANNED = "banned"       # 已封禁


class CookieCreateRequest(BaseModel):
    """
    创建Cookie请求

    Cookie值会在API层加密后存储
    """
    cookie_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Cookie标识名，用于区分不同账号"
    )
    platform: Platform = Field(
        default=Platform.XHS,
        description="所属平台"
    )
    cookie_value: str = Field(
        ...,
        min_length=10,
        description="Cookie字符串 (将被加密存储)"
    )
    priority: int = Field(
        default=1,
        ge=0,
        le=100,
        description="优先级，越大越优先使用"
    )
    daily_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="每日使用次数限制"
    )
    description: Optional[str] = Field(
        None,
        max_length=200,
        description="备注说明"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "cookie_name": "account_01",
                "platform": "xhs",
                "cookie_value": "web_session=xxxxx; a1=xxxxx; ...",
                "priority": 1,
                "daily_limit": 100,
                "description": "主账号"
            }
        }


class CookieUpdateRequest(BaseModel):
    """
    更新Cookie请求
    """
    cookie_value: Optional[str] = Field(
        None,
        min_length=10,
        description="新的Cookie值"
    )
    status: Optional[CookieStatus] = Field(
        None,
        description="状态"
    )
    priority: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="优先级"
    )
    daily_limit: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="每日限制"
    )
    description: Optional[str] = Field(
        None,
        max_length=200,
        description="备注"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "active",
                "priority": 2,
                "daily_limit": 200
            }
        }


class CrawlTaskRequest(BaseModel):
    """
    采集任务请求 (用于手动触发)
    """
    keyword: str = Field(
        ...,
        description="搜索关键词"
    )
    platform: Platform = Field(
        default=Platform.XHS,
        description="目标平台"
    )
    max_notes: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="最大采集数量"
    )
    get_comments: bool = Field(
        default=True,
        description="是否获取评论"
    )
    save_to_feishu: bool = Field(
        default=True,
        description="是否保存到飞书"
    )


class ValidateCookieRequest(BaseModel):
    """
    验证Cookie请求
    """
    cookie_name: str = Field(
        ...,
        description="Cookie名称"
    )
    platform: Platform = Field(
        default=Platform.XHS,
        description="平台"
    )
