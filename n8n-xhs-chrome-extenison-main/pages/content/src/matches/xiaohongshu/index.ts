import { xhsAuthorStorage } from '@extension/storage';

console.log('[XHS] 小红书内容脚本已加载');

interface XhsNoteData {
  title: string;
  desc: string;
  like: string;
  collect: string;
}

// 等待元素出现的辅助函数
const waitForElement = (selector: string, timeout = 10000): Promise<Element> =>
  new Promise((resolve, reject) => {
    const element = document.querySelector(selector);
    if (element) {
      resolve(element);
      return;
    }

    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (element) {
        observer.disconnect();
        resolve(element);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    setTimeout(() => {
      observer.disconnect();
      reject(new Error(`等待元素 ${selector} 超时`));
    }, timeout);
  });

// 延迟函数
const delay = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

// 清理userId，只保留数字和英文字符
const cleanUserId = (userId: string): string => {
  return userId.replace(/[^a-zA-Z0-9]/g, '');
};

// 同步数据到云端
const syncToCloud = async (authorData: any) => {
  const apiUrl = process.env.CEB_N8N_API_URL;
  if (!apiUrl) {
    console.warn('[XHS] 未配置API_URL，跳过云端同步');
    return { success: false, error: '未配置API地址' };
  }

  try {
    console.log('[XHS] 开始同步数据到云端...');
    
    const response = await fetch(`${apiUrl}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(authorData),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('[XHS] 云端同步成功:', result);
    
    return { success: true, data: result };
  } catch (error) {
    console.error('[XHS] 云端同步失败:', error);
    return { 
      success: false, 
      error: error instanceof Error ? error.message : '同步失败' 
    };
  }
};

// 获取用户基本信息
const getUserBasicInfo = () => {
  const userName = document.querySelector('.user-name')?.textContent?.trim() || '';
  const userIdRaw = document.querySelector('.user-redId')?.textContent?.trim() || '';
  const userId = cleanUserId(userIdRaw);

  const userInteractions = document.querySelectorAll('.user-interactions .count');
  const subscribers = userInteractions[0]?.textContent?.trim() || '0';
  const followers = userInteractions[1]?.textContent?.trim() || '0';
  const likes = userInteractions[2]?.textContent?.trim() || '0';

  return {
    userName,
    userId,
    subscribers,
    followers,
    likes,
  };
};

// 获取所有笔记标题
const getAllTitles = (): string[] => {
  const titleElements = document.querySelectorAll('#userPostedFeeds .footer .title');
  return Array.from(titleElements).map(el => el.textContent?.trim() || '');
};

// 从笔记卡片获取链接URL
const getNoteUrlFromCard = (noteItem: Element): string => {
  // 调试：打印元素结构
  console.log('[XHS] 笔记卡片HTML:', noteItem.outerHTML.substring(0, 500));

  // 尝试多种方式获取链接
  let noteUrl = '';
  let linkInfo = '';

  // 方法1: 查找隐藏的 explore 链接
  const firstLink = noteItem.querySelector('a[href^="/explore/"]') as HTMLAnchorElement;
  if (firstLink) {
    const basePath = firstLink.getAttribute('href') || '';
    linkInfo += `找到explore链接: ${basePath}; `;
    
    // 查找带参数的链接
    const secondLink = noteItem.querySelector('a.cover') as HTMLAnchorElement;
    if (secondLink) {
      const secondHref = secondLink.getAttribute('href') || '';
      linkInfo += `找到cover链接: ${secondHref}; `;
      
      try {
        // 解析第二个链接的参数
        const url = new URL(secondHref, window.location.origin);
        const xsecToken = url.searchParams.get('xsec_token');
        const xsecSource = url.searchParams.get('xsec_source');

        // 构建完整URL
        noteUrl = `${window.location.origin}${basePath}`;
        const params = new URLSearchParams();

        if (xsecToken) params.set('xsec_token', xsecToken);
        if (xsecSource) params.set('xsec_source', xsecSource);

        if (params.toString()) {
          noteUrl += `?${params.toString()}`;
        }
        linkInfo += `构建URL成功: ${noteUrl}`;
      } catch (error) {
        linkInfo += `构建URL失败: ${error}`;
      }
    } else {
      linkInfo += '未找到cover链接';
    }
  } else {
    linkInfo += '未找到explore链接; ';
    
    // 方法2: 查找任何包含 explore 的链接
    const allLinks = noteItem.querySelectorAll('a[href*="explore"]');
    if (allLinks.length > 0) {
      linkInfo += `找到${allLinks.length}个explore相关链接: `;
      allLinks.forEach((link, index) => {
        const href = (link as HTMLAnchorElement).getAttribute('href') || '';
        linkInfo += `${index + 1}. ${href}; `;
        if (index === 0) {
          noteUrl = href.startsWith('http') ? href : `${window.location.origin}${href}`;
        }
      });
    } else {
      // 方法3: 查找所有链接
      const allAnyLinks = noteItem.querySelectorAll('a[href]');
      linkInfo += `找到${allAnyLinks.length}个链接: `;
      allAnyLinks.forEach((link, index) => {
        const href = (link as HTMLAnchorElement).getAttribute('href') || '';
        linkInfo += `${index + 1}. ${href}; `;
      });
    }
  }

  console.log('[XHS] 链接解析信息:', linkInfo);
  return noteUrl;
};

// 点击链接并在当前页面获取详细信息
const fetchNoteDetails = async (noteUrl: string, cardTitle: string, cardLike: string): Promise<XhsNoteData> => {
  if (!noteUrl) {
    return {
      title: cardTitle,
      desc: '无法获取笔记链接',
      like: cardLike,
      collect: '0',
    };
  }

  const originalUrl = window.location.href;
  
  try {
    console.log(`[XHS] 正在导航到笔记页面: ${noteUrl}`);
    
    // 直接修改当前页面URL来导航到笔记页面
    window.history.pushState({}, '', noteUrl);
    
    // 等待页面状态改变和内容加载
    await delay(3000); // 增加延迟到3秒，避免被识别为爬虫
    
    // 触发popstate事件来让SPA响应URL变化
    window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
    
    // 再等待一段时间让页面内容完全加载
    await delay(2000);
    
    // 尝试等待笔记详情页面的关键元素
    let title = cardTitle;
    let desc = '无描述内容';
    let like = cardLike;
    let collect = '0';
    
    try {
      // 等待详情页面元素加载
      await waitForElement('#detail-title, .note-content, .interaction-container', 5000);
      
      // 获取标题
      const titleElement = document.querySelector('#detail-title') || 
                          document.querySelector('.note-title') ||
                          document.querySelector('[class*="title"]');
      if (titleElement?.textContent?.trim()) {
        title = titleElement.textContent.trim();
      }
      
      // 获取描述内容
      const descSelectors = [
        '#detail-desc.desc',
        '.note-content .desc',
        '.note-desc',
        '.content .desc',
        '[class*="desc"]:not(.note-title)',
        '.note-content'
      ];
      
      for (const selector of descSelectors) {
        const descElement = document.querySelector(selector);
        if (descElement?.textContent?.trim()) {
          desc = descElement.textContent.trim();
          console.log(`[XHS] 使用选择器 ${selector} 获取到描述`);
          break;
        }
      }
      
      // 获取点赞数
      const likeSelectors = [
        '.interaction-container .like-wrapper .count',
        '.like-wrapper .count',
        '.interaction .like .count',
        '[class*="like"] .count',
        '[class*="like"][class*="count"]'
      ];
      
      for (const selector of likeSelectors) {
        const likeElement = document.querySelector(selector);
        if (likeElement?.textContent?.trim()) {
          like = likeElement.textContent.trim();
          console.log(`[XHS] 使用选择器 ${selector} 获取到点赞数: ${like}`);
          break;
        }
      }
      
      // 获取收藏数
      const collectSelectors = [
        '.interaction-container .collect-wrapper .count',
        '.collect-wrapper .count', 
        '.interaction .collect .count',
        '[class*="collect"] .count',
        '[class*="collect"][class*="count"]'
      ];
      
      for (const selector of collectSelectors) {
        const collectElement = document.querySelector(selector);
        if (collectElement?.textContent?.trim()) {
          collect = collectElement.textContent.trim();
          console.log(`[XHS] 使用选择器 ${selector} 获取到收藏数: ${collect}`);
          break;
        }
      }
      
    } catch (waitError) {
      console.warn(`[XHS] 等待详情页面元素超时: ${waitError}`);
    }

    console.log(`[XHS] 成功获取笔记详情: ${title.substring(0, 20)}...`);

    return {
      title,
      desc,
      like,
      collect,
    };
  } catch (error) {
    console.error(`[XHS] 获取笔记详情失败: ${error}`);
    
    return {
      title: cardTitle,
      desc: `无法获取详细描述 (${error instanceof Error ? error.message : '未知错误'})`,
      like: cardLike,
      collect: '0',
    };
  } finally {
    // 无论成功还是失败，都要导航回原始页面
    try {
      console.log(`[XHS] 正在导航回原始页面: ${originalUrl}`);
      window.history.pushState({}, '', originalUrl);
      window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
      
      // 等待页面恢复
      await delay(2000);
    } catch (navError) {
      console.error(`[XHS] 导航回原始页面失败: ${navError}`);
    }
  }
};

// 获取前10篇笔记的详细信息
const getTop10Notes = async (): Promise<XhsNoteData[]> => {
  const noteItems = document.querySelectorAll('#userPostedFeeds .note-item');
  const notes: XhsNoteData[] = [];
  const maxNotes = Math.min(10, noteItems.length);

  console.log(`[XHS] 开始获取前 ${maxNotes} 篇笔记详细信息`);

  for (let i = 0; i < maxNotes; i++) {
    try {
      console.log(`[XHS] 正在获取第 ${i + 1} 篇笔记...`);

      const noteItem = noteItems[i];

      // 从卡片获取基本信息
      const titleElement = noteItem.querySelector('.footer .title');
      const cardTitle = titleElement?.textContent?.trim() || '';
      
      const likeElement = noteItem.querySelector('.like-wrapper .count');
      const cardLike = likeElement?.textContent?.trim() || '0';

      // 获取笔记链接
      const noteUrl = getNoteUrlFromCard(noteItem);

      // 访问笔记页面获取详细信息
      const noteData = await fetchNoteDetails(noteUrl, cardTitle, cardLike);
      notes.push(noteData);

      console.log(`[XHS] 第 ${i + 1} 篇笔记获取完成:`, noteData.title);

      // 等待2-3秒避免被识别为爬虫，最后一个笔记不需要等待
      if (i < maxNotes - 1) {
        const randomDelay = 2000 + Math.random() * 1000; // 2-3秒随机延迟
        console.log(`[XHS] 等待 ${Math.round(randomDelay / 1000 * 10) / 10} 秒后处理下一篇笔记...`);
        await delay(randomDelay);
      }
    } catch (error) {
      console.error(`[XHS] 获取第 ${i + 1} 篇笔记失败:`, error);
      notes.push({ title: '', desc: '获取失败', like: '0', collect: '0' });
      
      // 即使出错也要等待，避免快速连续请求
      if (i < maxNotes - 1) {
        const errorDelay = 1000 + Math.random() * 1000; // 1-2秒错误延迟
        await delay(errorDelay);
      }
    }
  }

  return notes;
};

// 主要的数据获取函数
const getXhsAuthorData = async (profileUrl: string) => {
  try {
    console.log('[XHS] 开始获取小红书作者数据...');

    // 等待页面基本元素加载
    await waitForElement('.user-name', 10000);
    await delay(2000);

    // 获取基本信息
    const basicInfo = getUserBasicInfo();
    console.log('[XHS] 基本信息获取完成:', basicInfo);

    // 获取所有标题
    const allTitles = getAllTitles();
    console.log('[XHS] 标题获取完成，共', allTitles.length, '篇');

    // 获取前10篇笔记详情
    const top10Notes = await getTop10Notes();
    console.log('[XHS] 前10篇笔记详情获取完成');

    // 组装完整数据
    const authorData = {
      ...basicInfo,
      allTitles,
      top10Notes,
      profileUrl,
    };

    // 保存到存储
    await xhsAuthorStorage.addAuthor(authorData);
    console.log('[XHS] 数据保存完成');

    // 同步到云端
    const syncResult = await syncToCloud(authorData);
    
    // 通知保存成功，同时包含同步结果
    chrome.runtime.sendMessage({
      action: 'XHS_DATA_SAVED',
      data: authorData,
      syncResult: syncResult,
    });
  } catch (error) {
    console.error('[XHS] 获取作者数据失败:', error);
    chrome.runtime.sendMessage({
      action: 'XHS_DATA_ERROR',
      error: error instanceof Error ? error.message : '未知错误',
    });
  }
};

// 监听来自popup的消息
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  console.log('[XHS] 收到消息:', message);

  if (message.action === 'GET_XHS_AUTHOR_DATA') {
    console.log('[XHS] 开始处理获取数据请求');

    // 异步处理数据获取
    getXhsAuthorData(message.url)
      .then(() => {
        sendResponse({ success: true });
      })
      .catch(error => {
        console.error('[XHS] 处理失败:', error);
        sendResponse({ success: false, error: error.message });
      });

    // 返回 true 表示会异步发送响应
    return true;
  }

  sendResponse({ success: false, error: '未知操作' });
  return false;
});
