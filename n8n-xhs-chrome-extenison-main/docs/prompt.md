
# 我的需求

## Popup区域UI修改
帮我开发一个浏览器插件，修改当前的Popup区域，只保留一个按钮【获取作者数据】。

如果用户是在 `https://www.xiaohongshu.com/user/profile/`这个页面，pop就的按钮就可点击。

- 例如：`https://www.xiaohongshu.com/user/profile/5d74084200000000010091f4?xsec_token=AB5b2KVC2m77IcXe_79kUlIs3smfAiUShgrVLXKbo24M0=&xsec_source=pc_note`在这个页面，匹配到`https://www.xiaohongshu.com/user/profile/`，这就可以点击。

如果是在其他页面，则按钮置灰，不可点击。下方显示提示：请在小红书作者页面使用。


## Popup按钮点击后

按钮点击后，获取当前页面上的以下数据，保存为一个对象

- userName: 小红书的用户名，选择器为`document.querySelector('.user-name').innerText`
- userId: 小红书的id，选择器为`document.querySelector('.user-redId').innerText`
- subscribers: 它的关注数，`document.querySelectorAll('.user-interactions .count')[0].innerText`
- followers: 它的粉丝数，`document.querySelectorAll('.user-interactions .count')[1].innerText`
- likes: 它的获赞+收藏数，`document.querySelectorAll('.user-interactions .count')[2].innerText`
- allTitles: 它的所有标题笔记的数组，`document.querySelectorAll('#userPostedFeeds .footer .title')`，然后遍历数组，获取每个笔记的标题，并保存到数组中。
- top10Notes: 他的前10篇笔记的数组对象，首先获取`document.querySelectorAll('#userPostedFeeds .note-item')`，然后挨个点击卡片，等待2s后，分别获取单个笔记的以下对象，分别：
  - title: 笔记的标题：`document.querySelector('#detail-title').innerText`
  - desc: 笔记的描述：`document.querySelector('#detail-desc.desc').innerText`
  - like: 笔记的喜欢数： `document.querySelector('.interaction-container .like-wrapper .count').innerText`
  - collect: 笔记的收藏数： `document.querySelector('.interaction-container .collect-wrapper .count').innerText`



注意：`top10Notes`需要每个卡片依次点击，然后等待2s后，获取数据，获取数据后，触发`document.querySelector('.close-circle').click()`关闭卡片，然后继续点击下一个卡片，直到获取到10篇笔记，或者笔记全部获取完毕。

然后将这个数据，保存在本地存储，并且在side-panel中以卡片方式显示，展开后可以查看数据JSON格式。本地数据可以点击删除。










