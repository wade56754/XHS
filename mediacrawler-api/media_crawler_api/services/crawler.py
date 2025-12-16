"""
爬虫服务

提供小红书内容采集的核心功能:
- 搜索笔记
- 获取笔记详情
- 获取评论

此服务封装了底层爬虫实现，提供统一的接口。
"""

from typing import Optional, Dict, Any, List
import asyncio
import aiohttp
from datetime import datetime

from .cookie import Cookie
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CrawlerError(Exception):
    """爬虫错误基类"""
    pass


class TimeoutError(CrawlerError):
    """超时错误"""
    pass


class ParseError(CrawlerError):
    """解析错误"""
    pass


class PlatformError(CrawlerError):
    """平台错误"""
    pass


class CrawlerService:
    """
    爬虫服务

    封装小红书内容采集功能
    """

    # 默认超时配置 (秒)
    DEFAULT_TIMEOUT = {
        "search": 30,
        "detail": 15,
        "comments": 15,
    }

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化爬虫服务

        Args:
            base_url: MediaCrawler API 基础 URL
        """
        import os
        self.base_url = base_url or os.environ.get(
            "MEDIACRAWLER_BASE_URL",
            "http://localhost:8080"
        )

    async def search(
        self,
        platform: str,
        keyword: str,
        cookie: Cookie,
        page: int = 1,
        page_size: int = 20,
        sort_type: str = "general",
        note_type: str = "0",
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        搜索笔记

        Args:
            platform: 平台
            keyword: 搜索关键词
            cookie: Cookie 对象
            page: 页码
            page_size: 每页数量
            sort_type: 排序方式
            note_type: 笔记类型
            timeout: 超时时间 (秒)

        Returns:
            搜索结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT["search"]

        logger.info(f"搜索笔记: keyword={keyword}, page={page}")

        try:
            cookie_value = cookie.get_decrypted_value()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/xhs/search",
                    json={
                        "keyword": keyword,
                        "page": page,
                        "page_size": page_size,
                        "sort_type": sort_type,
                        "note_type": note_type
                    },
                    headers={
                        "Cookie": cookie_value,
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status != 200:
                        raise PlatformError(f"搜索失败: HTTP {resp.status}")

                    data = await resp.json()

                    # 处理响应
                    return self._parse_search_result(data)

        except asyncio.TimeoutError:
            raise TimeoutError(f"搜索超时: {timeout}秒")
        except aiohttp.ClientError as e:
            raise PlatformError(f"网络错误: {e}")
        except Exception as e:
            if isinstance(e, CrawlerError):
                raise
            raise CrawlerError(f"搜索失败: {e}")

    async def get_note_detail(
        self,
        platform: str,
        note_id: str,
        cookie: Cookie,
        get_comments: bool = True,
        comments_limit: int = 50,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取笔记详情

        Args:
            platform: 平台
            note_id: 笔记 ID
            cookie: Cookie 对象
            get_comments: 是否获取评论
            comments_limit: 评论数量限制
            timeout: 超时时间 (秒)

        Returns:
            笔记详情
        """
        timeout = timeout or self.DEFAULT_TIMEOUT["detail"]

        logger.info(f"获取笔记详情: note_id={note_id}")

        try:
            cookie_value = cookie.get_decrypted_value()

            async with aiohttp.ClientSession() as session:
                # 获取笔记详情
                async with session.get(
                    f"{self.base_url}/api/xhs/note/{note_id}",
                    headers={
                        "Cookie": cookie_value
                    },
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 404:
                        raise ParseError(f"笔记不存在: {note_id}")
                    if resp.status != 200:
                        raise PlatformError(f"获取笔记失败: HTTP {resp.status}")

                    data = await resp.json()
                    result = self._parse_note_detail(data)

                # 获取评论
                if get_comments and comments_limit > 0:
                    try:
                        comments = await self._get_comments(
                            session,
                            note_id,
                            cookie_value,
                            limit=comments_limit
                        )
                        result["comments"] = comments
                        result["comment_count"] = len(comments)
                    except Exception as e:
                        logger.warning(f"获取评论失败: {e}")
                        result["comments"] = []

                return result

        except asyncio.TimeoutError:
            raise TimeoutError(f"获取笔记超时: {timeout}秒")
        except aiohttp.ClientError as e:
            raise PlatformError(f"网络错误: {e}")
        except Exception as e:
            if isinstance(e, CrawlerError):
                raise
            raise CrawlerError(f"获取笔记失败: {e}")

    async def _get_comments(
        self,
        session: aiohttp.ClientSession,
        note_id: str,
        cookie_value: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取笔记评论"""
        timeout = self.DEFAULT_TIMEOUT["comments"]

        async with session.get(
            f"{self.base_url}/api/xhs/note/{note_id}/comments",
            params={"limit": limit},
            headers={"Cookie": cookie_value},
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status != 200:
                return []

            data = await resp.json()
            return self._parse_comments(data)

    def _parse_search_result(self, data: Dict) -> Dict[str, Any]:
        """解析搜索结果"""
        # 适配不同的响应格式
        if "data" in data:
            data = data["data"]

        items = data.get("items", data.get("notes", []))

        return {
            "items": [
                {
                    "note_id": item.get("id") or item.get("note_id"),
                    "title": item.get("title", ""),
                    "desc": item.get("desc", ""),
                    "type": item.get("type", ""),
                    "user": {
                        "user_id": item.get("user", {}).get("user_id") or item.get("user_id"),
                        "nickname": item.get("user", {}).get("nickname") or item.get("nickname"),
                    },
                    "liked_count": item.get("liked_count", 0),
                    "collected_count": item.get("collected_count", 0),
                    "cover": item.get("cover", {}).get("url") if isinstance(item.get("cover"), dict) else item.get("cover"),
                }
                for item in items
            ],
            "total": data.get("total", len(items)),
            "has_more": data.get("has_more", False)
        }

    def _parse_note_detail(self, data: Dict) -> Dict[str, Any]:
        """解析笔记详情"""
        if "data" in data:
            data = data["data"]

        note = data.get("note_card", data)

        # 处理图片列表
        image_list = []
        for img in note.get("image_list", note.get("images", [])):
            if isinstance(img, dict):
                image_list.append({
                    "url": img.get("url") or img.get("url_default"),
                    "width": img.get("width"),
                    "height": img.get("height")
                })
            else:
                image_list.append({"url": img})

        # 处理视频
        video_url = None
        video = note.get("video", {})
        if video:
            video_url = video.get("url") or video.get("media", {}).get("stream", {}).get("h264", [{}])[0].get("master_url")

        # 处理标签
        tag_list = []
        for tag in note.get("tag_list", note.get("tags", [])):
            if isinstance(tag, dict):
                tag_list.append({
                    "id": tag.get("id"),
                    "name": tag.get("name"),
                    "type": tag.get("type")
                })
            else:
                tag_list.append({"name": tag})

        return {
            "note_id": note.get("id") or note.get("note_id"),
            "title": note.get("title", ""),
            "desc": note.get("desc", note.get("content", "")),
            "type": note.get("type", ""),
            "image_list": image_list,
            "video_url": video_url,
            "tag_list": tag_list,
            "time": note.get("time", note.get("create_time")),
            "user": {
                "user_id": note.get("user", {}).get("user_id") or note.get("user_id"),
                "nickname": note.get("user", {}).get("nickname") or note.get("nickname"),
                "avatar": note.get("user", {}).get("avatar"),
                "fans_count": note.get("user", {}).get("fans_count"),
            },
            "interact_info": {
                "liked_count": note.get("liked_count") or note.get("interact_info", {}).get("liked_count", 0),
                "collected_count": note.get("collected_count") or note.get("interact_info", {}).get("collected_count", 0),
                "comment_count": note.get("comment_count") or note.get("interact_info", {}).get("comment_count", 0),
                "share_count": note.get("share_count") or note.get("interact_info", {}).get("share_count", 0),
            },
            "comments": [],
            "crawled_at": datetime.utcnow().isoformat()
        }

    def _parse_comments(self, data: Dict) -> List[Dict[str, Any]]:
        """解析评论"""
        if "data" in data:
            data = data["data"]

        comments = data.get("comments", [])

        return [
            {
                "comment_id": c.get("id") or c.get("comment_id"),
                "content": c.get("content", ""),
                "user": {
                    "user_id": c.get("user", {}).get("user_id") or c.get("user_id"),
                    "nickname": c.get("user", {}).get("nickname") or c.get("nickname"),
                },
                "liked_count": c.get("liked_count", 0),
                "create_time": c.get("create_time"),
                "sub_comments": c.get("sub_comments", [])
            }
            for c in comments
        ]

    async def validate_cookie(self, cookie: Cookie) -> bool:
        """
        验证 Cookie 是否有效

        Args:
            cookie: Cookie 对象

        Returns:
            是否有效
        """
        try:
            cookie_value = cookie.get_decrypted_value()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/xhs/user/info",
                    headers={"Cookie": cookie_value},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200

        except Exception as e:
            logger.warning(f"Cookie 验证失败: {e}")
            return False


# ============ 依赖注入 ============

_crawler_service: Optional[CrawlerService] = None


def get_crawler_service() -> CrawlerService:
    """获取爬虫服务实例 (单例)"""
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service


def reset_crawler_service() -> None:
    """重置爬虫服务 (用于测试)"""
    global _crawler_service
    _crawler_service = None
