"""
爬虫 API 路由

提供小红书内容采集相关的 API 端点:
- /api/search: 搜索笔记
- /api/note/detail: 获取笔记详情 (支持批量)
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
import time
import uuid

from ..models.response import (
    APIResponse, BatchResponse, ErrorDetail, ErrorCode,
    ResponseMeta, BatchItemResult, ERROR_CONFIG,
    create_success_response, create_error_response, create_batch_response
)
from ..models.request import NoteDetailRequest, SearchRequest
from ..services.crawler import CrawlerService, get_crawler_service
from ..services.cookie import CookieManager, get_cookie_manager
from ..utils.logging import get_logger, set_request_id

router = APIRouter(prefix="/api", tags=["crawler"])
logger = get_logger(__name__)


def get_request_id(request: Request) -> str:
    """
    获取或生成请求 ID

    优先使用请求头中的 X-Request-ID，否则自动生成
    """
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = f"req-{uuid.uuid4().hex[:12]}"
    set_request_id(request_id)
    return request_id


@router.post("/search", response_model=APIResponse, summary="搜索笔记")
async def search_notes(
    request: Request,
    body: SearchRequest,
    crawler: CrawlerService = Depends(get_crawler_service),
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> APIResponse:
    """
    搜索小红书笔记

    根据关键词搜索笔记列表，返回基础信息 (不含完整内容)。

    **参数说明:**
    - keyword: 搜索关键词
    - page: 页码 (1-100)
    - page_size: 每页数量 (1-50)
    - sort_type: 排序方式 (general/time_descending/popularity_descending)
    - note_type: 笔记类型 (0=全部, 1=视频, 2=图文)

    **响应说明:**
    - success=true: data 包含搜索结果列表
    - success=false: error 包含错误详情
    """
    request_id = get_request_id(request)
    start_time = time.time()

    logger.info(f"开始搜索: keyword={body.keyword}, page={body.page}")

    try:
        # 获取 Cookie
        cookie = await cookie_mgr.acquire(
            platform=body.platform.value,
            cookie_name=body.cookie_name
        )

        if not cookie:
            latency_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                error_code=ErrorCode.COOKIE_EXHAUSTED,
                message="无可用 Cookie，请添加新账号",
                request_id=request_id,
                latency_ms=latency_ms
            )

        # 执行搜索
        result = await crawler.search(
            platform=body.platform.value,
            keyword=body.keyword,
            cookie=cookie,
            page=body.page,
            page_size=body.page_size,
            sort_type=body.sort_type.value,
            note_type=body.note_type.value
        )

        # 更新 Cookie 使用统计
        await cookie_mgr.mark_used(cookie.name, success_count=1)

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"搜索完成: 找到 {len(result.get('items', []))} 条结果")

        return create_success_response(
            data={
                "keyword": body.keyword,
                "platform": body.platform.value,
                "page": body.page,
                "page_size": body.page_size,
                "items": result.get("items", []),
                "total": result.get("total", 0),
                "has_more": result.get("has_more", False)
            },
            request_id=request_id,
            latency_ms=latency_ms,
            cookie_used=cookie.name
        )

    except TimeoutError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"搜索超时: {e}")
        return create_error_response(
            error_code=ErrorCode.TIMEOUT_ERROR,
            message=f"搜索超时: {str(e)}",
            request_id=request_id,
            latency_ms=latency_ms
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"搜索失败: {e}", exc_info=True)
        return create_error_response(
            error_code=ErrorCode.PLATFORM_ERROR,
            message=f"搜索失败: {str(e)}",
            request_id=request_id,
            latency_ms=latency_ms
        )


@router.post("/note/detail", response_model=BatchResponse, summary="获取笔记详情")
async def get_note_detail(
    request: Request,
    body: NoteDetailRequest,
    crawler: CrawlerService = Depends(get_crawler_service),
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> BatchResponse:
    """
    获取笔记详情 (支持批量)

    批量获取笔记的完整内容，包括标题、正文、图片、视频、互动数据等。

    **特性:**
    - 支持批量请求 (最多20条)
    - 支持部分失败: 即使部分笔记获取失败，成功的结果也会返回
    - 返回结构化的成功/失败信息

    **响应说明:**
    - success=true: 全部成功
    - success=false: 有部分或全部失败，items 包含每条的详细结果
    """
    request_id = get_request_id(request)
    start_time = time.time()

    logger.info(f"开始获取笔记详情: note_ids={body.note_ids}")

    items = []
    succeeded = 0
    failed = 0
    used_cookie = None

    try:
        # 获取 Cookie
        cookie = await cookie_mgr.acquire(
            platform=body.platform.value,
            cookie_name=body.cookie_name
        )

        if not cookie:
            latency_ms = int((time.time() - start_time) * 1000)
            return BatchResponse(
                success=False,
                data={"platform": body.platform.value},
                items=[],
                summary={"total": len(body.note_ids), "succeeded": 0, "failed": len(body.note_ids)},
                error=ErrorDetail.from_code(
                    ErrorCode.COOKIE_EXHAUSTED,
                    "无可用 Cookie，请添加新账号"
                ),
                meta=ResponseMeta(
                    request_id=request_id,
                    latency_ms=latency_ms,
                    cookie_used=None
                )
            )

        used_cookie = cookie.name

        # 逐个获取笔记详情
        for note_id in body.note_ids:
            try:
                detail = await crawler.get_note_detail(
                    platform=body.platform.value,
                    note_id=note_id,
                    cookie=cookie,
                    get_comments=body.get_comments,
                    comments_limit=body.comments_limit,
                    timeout=15  # 单条超时 15 秒
                )

                items.append(BatchItemResult(
                    id=note_id,
                    success=True,
                    data=detail,
                    error=None
                ))
                succeeded += 1

            except TimeoutError as e:
                logger.warning(f"笔记超时: {note_id}")
                items.append(BatchItemResult(
                    id=note_id,
                    success=False,
                    data=None,
                    error=ErrorDetail.from_code(
                        ErrorCode.TIMEOUT_ERROR,
                        f"获取笔记超时: {str(e)}",
                        {"timeout_seconds": 15}
                    )
                ))
                failed += 1

            except ValueError as e:
                # 解析错误
                logger.warning(f"笔记解析失败: {note_id}")
                items.append(BatchItemResult(
                    id=note_id,
                    success=False,
                    data=None,
                    error=ErrorDetail.from_code(
                        ErrorCode.PARSE_ERROR,
                        f"笔记内容解析失败: {str(e)}"
                    )
                ))
                failed += 1

            except Exception as e:
                logger.error(f"获取笔记失败: {note_id}, {e}")
                items.append(BatchItemResult(
                    id=note_id,
                    success=False,
                    data=None,
                    error=ErrorDetail.from_code(
                        ErrorCode.PLATFORM_ERROR,
                        f"获取笔记失败: {str(e)}"
                    )
                ))
                failed += 1

        # 更新 Cookie 使用统计
        await cookie_mgr.mark_used(
            cookie.name,
            success_count=succeeded,
            error_count=failed
        )

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"笔记详情获取完成: 成功={succeeded}, 失败={failed}")

        # 构建响应
        return create_batch_response(
            items=items,
            request_id=request_id,
            latency_ms=latency_ms,
            data={"platform": body.platform.value},
            cookie_used=used_cookie
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"批量获取笔记失败: {e}", exc_info=True)

        return BatchResponse(
            success=False,
            data={"platform": body.platform.value},
            items=items,
            summary={"total": len(body.note_ids), "succeeded": succeeded, "failed": failed or len(body.note_ids)},
            error=ErrorDetail.from_code(
                ErrorCode.PLATFORM_ERROR,
                f"批量获取笔记失败: {str(e)}"
            ),
            meta=ResponseMeta(
                request_id=request_id,
                latency_ms=latency_ms,
                cookie_used=used_cookie
            )
        )


@router.get("/note/{note_id}", response_model=APIResponse, summary="获取单条笔记详情")
async def get_single_note_detail(
    request: Request,
    note_id: str,
    platform: str = "xhs",
    get_comments: bool = True,
    comments_limit: int = 50,
    crawler: CrawlerService = Depends(get_crawler_service),
    cookie_mgr: CookieManager = Depends(get_cookie_manager)
) -> APIResponse:
    """
    获取单条笔记详情 (GET 方法)

    便捷端点，适用于获取单条笔记。

    **参数:**
    - note_id: 笔记 ID (路径参数)
    - platform: 平台 (默认 xhs)
    - get_comments: 是否获取评论
    - comments_limit: 评论数量限制
    """
    request_id = get_request_id(request)
    start_time = time.time()

    logger.info(f"获取单条笔记: {note_id}")

    try:
        cookie = await cookie_mgr.acquire(platform=platform)

        if not cookie:
            latency_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                error_code=ErrorCode.COOKIE_EXHAUSTED,
                message="无可用 Cookie",
                request_id=request_id,
                latency_ms=latency_ms
            )

        detail = await crawler.get_note_detail(
            platform=platform,
            note_id=note_id,
            cookie=cookie,
            get_comments=get_comments,
            comments_limit=comments_limit
        )

        await cookie_mgr.mark_used(cookie.name, success_count=1)

        latency_ms = int((time.time() - start_time) * 1000)

        return create_success_response(
            data=detail,
            request_id=request_id,
            latency_ms=latency_ms,
            cookie_used=cookie.name
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"获取笔记失败: {note_id}, {e}")
        return create_error_response(
            error_code=ErrorCode.PLATFORM_ERROR,
            message=f"获取笔记失败: {str(e)}",
            request_id=request_id,
            latency_ms=latency_ms
        )
