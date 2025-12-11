import '@src/SidePanel.css';
import { useStorage, withErrorBoundary, withSuspense } from '@extension/shared';
import { exampleThemeStorage, xhsAuthorStorage, type XhsAuthorDataType } from '@extension/storage';
import { cn, ErrorDisplay, LoadingSpinner } from '@extension/ui';
import { useState, useEffect } from 'react';

// Toast 通知组件
const Toast = ({ message, isVisible, onClose }: { message: string; isVisible: boolean; onClose: () => void }) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  return (
    <div
      className={`fixed top-4 right-4 z-50 transition-all duration-300 transform ${
        isVisible ? 'translate-y-0 opacity-100' : '-translate-y-2 opacity-0 pointer-events-none'
      }`}
    >
      <div className="bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
        <span className="text-lg">✓</span>
        <span>{message}</span>
      </div>
    </div>
  );
};

const AuthorCard = ({ 
  author, 
  onDelete, 
  isLight,
  showToast
}: { 
  author: any; 
  onDelete: (id: string) => void;
  isLight: boolean;
  showToast: (message: string) => void;
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // 单条记录同步功能
  const handleSyncSingle = async () => {
    setIsSyncing(true);
    
    try {
      const apiUrl = process.env.CEB_N8N_API_URL;
      if (!apiUrl) {
        throw new Error('未配置API地址');
      }

      const response = await fetch(`${apiUrl}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(author),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      showToast('数据已成功同步到云端');
    } catch (error) {
      showToast(`同步失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className={cn(
      'border rounded-lg p-4 mb-4 transition-all duration-200',
      isLight ? 'border-gray-200 bg-white' : 'border-gray-600 bg-gray-700'
    )}>
      {/* 基本信息 */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className={cn('font-bold text-lg', isLight ? 'text-gray-900' : 'text-white')}>
            {author.userName}
          </h3>
          <p className={cn('text-sm', isLight ? 'text-gray-600' : 'text-gray-300')}>
            {author.userId}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSyncSingle}
            disabled={isSyncing}
            className={cn(
              'px-3 py-1 text-sm rounded transition-colors flex items-center gap-1',
              isSyncing 
                ? 'bg-gray-400 text-white cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            )}>
            {isSyncing ? (
              <>
                <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                同步中
              </>
            ) : (
              '同步'
            )}
          </button>
          <button
            onClick={() => onDelete(author.id)}
            className={cn(
              'px-3 py-1 text-sm rounded hover:opacity-80 transition-opacity',
              'bg-red-500 text-white'
            )}>
            删除
          </button>
        </div>
      </div>

      {/* 统计数据 */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className={cn('text-center p-2 rounded', isLight ? 'bg-gray-50' : 'bg-gray-600')}>
          <div className={cn('font-semibold', isLight ? 'text-gray-900' : 'text-white')}>
            {author.subscribers}
          </div>
          <div className={cn('text-xs', isLight ? 'text-gray-600' : 'text-gray-300')}>
            关注
          </div>
        </div>
        <div className={cn('text-center p-2 rounded', isLight ? 'bg-gray-50' : 'bg-gray-600')}>
          <div className={cn('font-semibold', isLight ? 'text-gray-900' : 'text-white')}>
            {author.followers}
          </div>
          <div className={cn('text-xs', isLight ? 'text-gray-600' : 'text-gray-300')}>
            粉丝
          </div>
        </div>
        <div className={cn('text-center p-2 rounded', isLight ? 'bg-gray-50' : 'bg-gray-600')}>
          <div className={cn('font-semibold', isLight ? 'text-gray-900' : 'text-white')}>
            {author.likes}
          </div>
          <div className={cn('text-xs', isLight ? 'text-gray-600' : 'text-gray-300')}>
            获赞
          </div>
        </div>
      </div>

      {/* 笔记统计 */}
      <div className={cn('text-sm mb-3', isLight ? 'text-gray-600' : 'text-gray-300')}>
        共 {author.allTitles.length} 篇笔记，获取了前 {author.top10Notes.length} 篇详情
      </div>

      {/* 展开/收起按钮 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full py-2 px-4 rounded text-sm font-medium transition-colors',
          isLight 
            ? 'bg-blue-50 text-blue-600 hover:bg-blue-100' 
            : 'bg-blue-900 text-blue-300 hover:bg-blue-800'
        )}>
        {isExpanded ? '收起详情' : '查看详情'}
      </button>

      {/* 详细信息 */}
      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* 所有标题 */}
          <div>
            <h4 className={cn('font-semibold mb-2', isLight ? 'text-gray-900' : 'text-white')}>
              所有笔记标题 ({author.allTitles.length})
            </h4>
            <div className={cn(
              'max-h-32 overflow-y-auto p-2 rounded text-xs',
              isLight ? 'bg-gray-50' : 'bg-gray-600'
            )}>
              {author.allTitles.map((title, index) => (
                <div key={index} className={cn('mb-1', isLight ? 'text-gray-700' : 'text-gray-200')}>
                  {index + 1}. {title}
                </div>
              ))}
            </div>
          </div>

          {/* 前10篇详情 */}
          <div>
            <h4 className={cn('font-semibold mb-2', isLight ? 'text-gray-900' : 'text-white')}>
              前 {author.top10Notes.length} 篇笔记详情
            </h4>
            <div className="space-y-2">
              {author.top10Notes.map((note, index) => (
                <div key={index} className={cn(
                  'p-2 rounded text-xs',
                  isLight ? 'bg-gray-50' : 'bg-gray-600'
                )}>
                  <div className={cn('font-medium mb-1', isLight ? 'text-gray-900' : 'text-white')}>
                    {note.title || '无标题'}
                  </div>
                  <div className={cn('mb-1', isLight ? 'text-gray-600' : 'text-gray-300')}>
                    {note.desc ? note.desc.substring(0, 100) + (note.desc.length > 100 ? '...' : '') : '无描述'}
                  </div>
                  <div className={cn('flex gap-4', isLight ? 'text-gray-500' : 'text-gray-400')}>
                    <span>❤️ {note.like}</span>
                    <span>⭐ {note.collect}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* JSON 数据 */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <h4 className={cn('font-semibold', isLight ? 'text-gray-900' : 'text-white')}>
                JSON 数据
              </h4>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(author, null, 2)).then(() => {
                    showToast('JSON数据已复制到剪贴板');
                  }).catch(() => {
                    showToast('复制失败，请手动复制');
                  });
                }}
                className={cn(
                  'px-3 py-1 text-xs rounded transition-colors',
                  'bg-blue-500 text-white hover:bg-blue-600'
                )}>
                复制JSON
              </button>
            </div>
            <pre className={cn(
              'text-xs p-2 rounded overflow-auto max-h-40',
              isLight ? 'bg-gray-50 text-gray-700' : 'bg-gray-600 text-gray-200'
            )}>
              {JSON.stringify(author, null, 2)}
            </pre>
          </div>

          {/* 时间信息 */}
          <div className={cn('text-xs', isLight ? 'text-gray-500' : 'text-gray-400')}>
            获取时间: {new Date(author.createdAt).toLocaleString('zh-CN')}
          </div>
        </div>
      )}
    </div>
  );
};

const SidePanel = () => {
  const { isLight } = useStorage(exampleThemeStorage);
  const authorData = useStorage(xhsAuthorStorage);
  const [toastMessage, setToastMessage] = useState('');
  const [showToastVisible, setShowToastVisible] = useState(false);

  const showToast = (message: string) => {
    setToastMessage(message);
    setShowToastVisible(true);
  };

  const hideToast = () => {
    setShowToastVisible(false);
  };

  // 监听来自content script的消息
  useEffect(() => {
    const handleMessage = (message: any) => {
      if (message.action === 'XHS_DATA_SAVED') {
        const { syncResult } = message;
        
        if (syncResult) {
          if (syncResult.success) {
            showToast('数据已成功同步到云端');
          } else {
            showToast(`云端同步失败: ${syncResult.error}`);
          }
        }
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);
    
    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, []);

  const handleDeleteAuthor = async (id: string) => {
    if (confirm('确定删除这条数据吗？')) {
      await xhsAuthorStorage.removeAuthor(id);
    }
  };

  const handleClearAll = async () => {
    if (confirm('确定清空所有数据吗？此操作不可恢复！')) {
      await xhsAuthorStorage.clearAll();
    }
  };

  return (
    <div className={cn('min-h-screen', isLight ? 'bg-gray-50' : 'bg-gray-800')}>
      <div className={cn('p-4')}>
        <div className="flex justify-between items-center mb-6">
          <h1 className={cn('text-xl font-bold', isLight ? 'text-gray-900' : 'text-white')}>
            小红书作者数据
          </h1>
          {authorData && authorData.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
              清空所有
            </button>
          )}
        </div>

        {!authorData || authorData.length === 0 ? (
          <div className={cn('text-center py-12', isLight ? 'text-gray-500' : 'text-gray-400')}>
            <div className="text-4xl mb-4">📝</div>
            <p>暂无数据</p>
            <p className="text-sm mt-2">请在小红书作者页面使用插件获取数据</p>
          </div>
        ) : (
          <div>
            <div className={cn('text-sm mb-4', isLight ? 'text-gray-600' : 'text-gray-300')}>
              共 {authorData.length} 条记录
            </div>
            {authorData.map((author) => (
              <AuthorCard
                key={author.id}
                author={author}
                onDelete={handleDeleteAuthor}
                isLight={isLight}
                showToast={showToast}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Toast 通知 */}
      <Toast
        message={toastMessage}
        isVisible={showToastVisible}
        onClose={hideToast}
      />
    </div>
  );
};

export default withErrorBoundary(withSuspense(SidePanel, <LoadingSpinner />), ErrorDisplay);
