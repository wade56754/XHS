import 'webextension-polyfill';
import { exampleThemeStorage } from '@extension/storage';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

// 处理来自content script的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Background] 收到消息:', message);
  
  if (message.action === 'XHS_DATA_SAVED') {
    // 数据保存成功，显示成功通知
    chrome.notifications.create('xhs-data-success', {
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icon-34.png'),
      title: '数据获取成功',
      message: `已成功获取 ${message.data.userName} 的数据，包含 ${message.data.top10Notes.length} 篇笔记详情`,
    });
    
    sendResponse({ success: true });
  } else if (message.action === 'XHS_DATA_ERROR') {
    // 数据获取失败，显示错误通知
    chrome.notifications.create('xhs-data-error', {
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icon-34.png'),
      title: '数据获取失败',
      message: message.error || '获取数据时发生未知错误',
    });
    
    sendResponse({ success: false, error: message.error });
  }
  
  return true;
});

console.log('Background loaded');
console.log("Edit 'chrome-extension/src/background/index.ts' and save to reload.");
