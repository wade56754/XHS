# AI 图像生成中文字体异形修复指南

## 问题描述

AI 图像生成模型（Stable Diffusion、Midjourney、Banana Pro 等）生成的图片中，中文字符经常出现：
- 笔画错误/缺失
- 结构变形
- 生成"类汉字"的乱码（异形体）

**根本原因**：大多数图像生成模型训练数据以英文为主，对中文字符学习不足。

---

## 解决方案概览

| 方案 | 难度 | 效果 | 适用场景 |
|------|------|------|----------|
| 更换模型 | ⭐ | ⭐⭐⭐⭐ | 最推荐，一劳永逸 |
| Prompt 优化 | ⭐⭐ | ⭐⭐⭐ | 配合使用 |
| 后期叠加文字 | ⭐ | ⭐⭐⭐⭐⭐ | 专业设计场景 |
| ControlNet 修复 | ⭐⭐⭐⭐ | ⭐⭐⭐ | SD 用户 |
| 专用文字模型 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 技术能力强 |

---

## 方案一：更换对中文友好的模型（推荐）

### 1.1 Google Gemini 3 Pro Image

**推荐指数**：⭐⭐⭐⭐⭐

原生支持中文 prompt 和文字渲染，RedInk 项目的首选方案。

```python
# 配置示例
IMAGE_PROVIDER = "google_genai"
GOOGLE_API_KEY = "your-api-key"
MODEL = "gemini-3-pro-image-preview"
```

### 1.2 通义万相（阿里）

**推荐指数**：⭐⭐⭐⭐⭐

国产模型，中文优化最好。

- 官网：https://tongyi.aliyun.com/wanxiang
- API：通过阿里云 DashScope 调用

### 1.3 文心一格（百度）

**推荐指数**：⭐⭐⭐⭐

- 官网：https://yige.baidu.com
- 中文理解能力强

### 1.4 Kolors（快手）

**推荐指数**：⭐⭐⭐⭐

- GitHub：https://github.com/Kwai-Kolors/Kolors
- 开源可本地部署

### 1.5 腾讯混元 HunyuanImage

**推荐指数**：⭐⭐⭐⭐

- GitHub：https://github.com/Tencent-Hunyuan/HunyuanImage-2.1
- 17B 参数，支持 2K 分辨率

---

## 方案二：Prompt 优化技巧

在生成 prompt 中明确指定文字渲染要求：

### 2.1 中文 Prompt 模板

```
生成一张小红书风格的图片，要求：
- 文字清晰可读，字号适中
- 排版美观，留白合理
- 所有文字内容必须完整呈现，不可缺字漏字
- 中文字体工整规范，无变形
- 竖版 3:4 比例，适合手机竖屏观看

标题文字：「你的标题」
正文内容：「你的内容」
```

### 2.2 英文 Prompt 增强

```
Generate an image with Chinese text.
Requirements:
- Chinese characters must be clear, legible, and properly formed
- Use standard Chinese font style (similar to Microsoft YaHei or PingFang)
- Text should be crisp with no distortion or missing strokes
- Maintain proper stroke order and character structure
```

### 2.3 避免的做法

❌ 直接在 prompt 中写大段中文让模型渲染
❌ 使用复杂的艺术字体
❌ 文字太小或太密集

✅ 简短的标题文字
✅ 大字号、高对比度
✅ 简单的字体风格

---

## 方案三：后期叠加文字（最可靠）

**适用场景**：专业设计、商业用途

### 3.1 工作流程

```
1. AI 生成不含文字的纯背景图
2. 使用设计工具叠加中文文字
3. 导出最终成品
```

### 3.2 推荐工具

| 工具 | 特点 | 适用人群 |
|------|------|----------|
| Photoshop | 专业级，功能最全 | 专业设计师 |
| Figma | 在线协作，免费 | 团队协作 |
| Canva | 模板丰富，上手快 | 新手友好 |
| 美图秀秀 | 中文字体多 | 快速处理 |
| 小红书编辑器 | 原生支持 | 直接发布 |

### 3.3 自动化方案

使用 Python 批量叠加文字：

```python
from PIL import Image, ImageDraw, ImageFont

def add_chinese_text(image_path, text, output_path):
    """在图片上叠加中文文字"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # 使用系统中文字体
    font = ImageFont.truetype("msyh.ttc", 48)  # 微软雅黑

    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (img.width - text_width) // 2
    y = img.height - text_height - 50

    # 绘制文字（带描边效果）
    draw.text((x-2, y-2), text, font=font, fill="black")
    draw.text((x+2, y+2), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")

    img.save(output_path)

# 使用示例
add_chinese_text("background.png", "你的标题文字", "output.png")
```

---

## 方案四：ControlNet 修复（SD 用户）

### 4.1 GlyphControl（推荐）

专门解决 AI 生成文字变形问题。

- GitHub：https://github.com/AIGText/GlyphControl-release
- 原理：通过字形条件信息增强文字渲染
- 要求：16GB+ 显存（推荐 32GB）

```bash
# 安装
git clone https://github.com/AIGText/GlyphControl-release.git
cd GlyphControl-release
pip install -r requirements.txt
```

### 4.2 ControlNet Tile 修复

使用 ControlNet Tile 模型修复文字细节：

1. 生成初版图片（可能有变形）
2. 使用 ControlNet Tile 模式
3. 控制权重设置 **≥ 0.6**（低于会继续变形）
4. 配合 Tiled Diffusion 放大修复

### 4.3 文字蒙版 Inpaint

1. 生成不带文字的背景图
2. 用 Photoshop 创建文字蒙版
3. 使用 ControlNet Inpaint 在指定区域渲染文字
4. 配合中文字体参考图

---

## 方案五：专用文字生成模型

### 5.1 FontDiffuser

- GitHub：https://github.com/yeungchenwa/FontDiffuser
- 论文：AAAI 2024
- 特点：支持复杂汉字生成，可跨语言

### 5.2 DiffSynth-Studio

- GitHub：https://github.com/modelscope/DiffSynth-Studio
- 特点：包含 16 万张中文文字渲染数据集
- 可训练专用中文 ControlNet

### 5.3 Qwen-Image

- HuggingFace：https://huggingface.co/Qwen/Qwen-Image
- 特点：阿里通义出品，原生双语支持

---

## RedInk 项目的实践方案

RedInk 采用的策略：

### 配置文件

```yaml
# image_providers.yaml
providers:
  google_genai:
    api_key: ${GOOGLE_API_KEY}
    model: gemini-3-pro-image-preview  # 首选
  banana_pro:
    api_key: ${BANANA_API_KEY}  # 备选
```

### Prompt 模板

```text
# backend/prompts/image_prompt.txt 关键指令

- 文字清晰可读，字号适中
- 排版美观，留白合理
- 所有文字内容必须完整呈现
- 竖版 3:4 比例，竖屏观看的排版
- 不能左右旋转或者是倒置
```

### 风格一致性

通过参考图片传递上下文：
```python
# 中文风格增强指令
"保持相似的色调和氛围...保持一致的画面质感"
```

---

## 快速决策指南

```
你的情况是？

├─ 偶尔需要中文图片
│   └─ → 方案三：后期叠加文字（最简单可靠）
│
├─ 批量生成小红书图文
│   └─ → 方案一：换用 Gemini 3 或通义万相
│
├─ 使用 Stable Diffusion 不想换模型
│   └─ → 方案四：ControlNet + GlyphControl
│
├─ 技术能力强，想彻底解决
│   └─ → 方案五：训练专用中文模型
│
└─ 商业项目，要求高质量
    └─ → 方案三 + 专业设计师
```

---

## 常见问题

### Q1: Banana Pro 还是 Gemini 3 更好？

**Gemini 3 Pro Image** 对中文支持更好。如果 Banana Pro 经常出现异形字，建议切换。

### Q2: 为什么加了 prompt 要求还是变形？

模型能力限制。Prompt 只能提高成功率，不能保证 100%。建议：
1. 减少单张图片的文字量
2. 使用更大的字号
3. 多次重试选最佳

### Q3: 有没有完全不变形的方案？

**后期叠加文字** 是唯一 100% 可靠的方案。AI 生成文字目前都存在概率性问题。

### Q4: 如何在 n8n 工作流中处理？

```javascript
// Code 节点示例：后期叠加文字
const sharp = require('sharp');

// 1. 获取 AI 生成的背景图
const backgroundImage = $input.first().binary.image;

// 2. 使用 sharp 叠加文字（需要配合 text-to-svg）
// 或调用外部 API 处理
```

---

## 参考资源

- [GlyphControl - 文字生成专用](https://github.com/AIGText/GlyphControl-release)
- [FontDiffuser - 字体生成](https://github.com/yeungchenwa/FontDiffuser)
- [DiffSynth-Studio - 中文数据集](https://github.com/modelscope/DiffSynth-Studio)
- [HunyuanImage - 腾讯混元](https://github.com/Tencent-Hunyuan/HunyuanImage-2.1)
- [ControlNet 中文字效教程](https://www.shejidaren.com/sd-controlnet-zi-xiao.html)
- [Diffusion 文字生成论文集](https://github.com/yeungchenwa/Recommendations-Diffusion-Text-Image)
