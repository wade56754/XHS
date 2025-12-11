import '@src/Popup.css';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner } from '@extension/ui';
import { useState, useEffect } from 'react';

const Popup = () => {
  const { isLight } = useStorage(exampleThemeStorage);
  const [currentUrl, setCurrentUrl] = useState<string>('');
  const [isXhsProfile, setIsXhsProfile] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    const getCurrentTab = async () => {
      const [tab] = await chrome.tabs.query({ currentWindow: true, active: true });
      if (tab.url) {
        setCurrentUrl(tab.url);
        setIsXhsProfile(tab.url.includes('https://www.xiaohongshu.com/user/profile/'));
      }
    };
    getCurrentTab();
  }, []);

  const handleGetAuthorData = async () => {
    if (!isXhsProfile) return;

    setIsLoading(true);

    try {
      const [tab] = await chrome.tabs.query({ currentWindow: true, active: true });

      // 先确保 content script 已注入
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id! },
          files: ['content/xiaohongshu.iife.js'],
        });

        // 等待一下让 content script 初始化
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (scriptError) {
        console.log('Content script 可能已经注入过了:', scriptError);
      }

      // 发送消息给 content script 开始获取数据
      const response = await chrome.tabs.sendMessage(tab.id!, {
        action: 'GET_XHS_AUTHOR_DATA',
        url: currentUrl,
      });

      if (response?.success) {
        // 打开 side panel 显示结果
        try {
          await chrome.sidePanel.open({ windowId: tab.windowId });
        } catch (sidePanelError) {
          // 如果 windowId 方式失败，尝试使用 tabId
          try {
            await chrome.sidePanel.open({ tabId: tab.id });
          } catch (tabIdError) {
            console.log('Side panel 打开失败，请手动打开侧边栏查看数据', tabIdError);
            // 显示提示信息
            chrome.notifications.create('side-panel-info', {
              type: 'basic',
              iconUrl: chrome.runtime.getURL('icon-34.png'),
              title: '数据已保存',
              message: '请右键点击插件图标，选择"打开侧边栏"查看数据',
            });
          }
        }
      }
    } catch (error) {
      console.error('获取作者数据失败:', error);
      chrome.notifications.create('get-data-error', {
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icon-34.png'),
        title: '获取数据失败',
        message: '请确保页面已完全加载，然后重试。',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn('App', isLight ? 'bg-slate-50' : 'bg-gray-800', 'min-w-[300px] p-4')}>
      <div className={cn('text-center', isLight ? 'text-gray-900' : 'text-gray-100')}>
        <h1 className="mb-4 text-lg font-bold">小红书数据获取</h1>

        <button
          className={cn(
            'w-full rounded-lg px-4 py-3 font-medium transition-all duration-200',
            isXhsProfile && !isLoading
              ? 'cursor-pointer bg-red-500 text-white shadow-lg hover:bg-red-600 hover:shadow-xl'
              : 'cursor-not-allowed bg-gray-300 text-gray-500',
            isLoading && 'opacity-75',
          )}
          onClick={handleGetAuthorData}
          disabled={!isXhsProfile || isLoading}>
          {isLoading ? '正在获取数据...' : '获取作者数据'}
        </button>

        {!isXhsProfile && (
          <p className={cn('mt-3 text-sm', isLight ? 'text-gray-600' : 'text-gray-400')}>请在小红书作者页面使用</p>
        )}

        {isXhsProfile && (
          <p className={cn('mt-3 text-sm', isLight ? 'text-green-600' : 'text-green-400')}>检测到小红书作者页面</p>
        )}
      </div>
    </div>
  );
};

export default withErrorBoundary(withSuspense(Popup, <LoadingSpinner />), ErrorDisplay);
