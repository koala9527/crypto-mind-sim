# 前端代码结构说明

## 📁 目录结构

```
static/
├── index.html              # 原始完整HTML文件（保留作为备份）
├── index_modular.html      # 模块化后的HTML入口文件
├── index.html.old          # 备份文件
├── css/
│   └── styles.css          # 所有CSS样式（主题、组件、动画等）
└── js/
    ├── global.js           # 全局变量定义
    ├── toast.js            # 通知/提示系统
    ├── theme.js            # 主题切换功能
    ├── modals.js           # 模态框控制
    ├── auth.js             # 用户认证（登录/注册/登出）
    ├── chart.js            # 价格图表相关
    ├── data.js             # 数据更新（用户信息、持仓、排行榜等）
    ├── trading.js          # 交易操作（开仓、平仓、AI分析）
    ├── public.js           # 公开内容（未登录时显示）
    ├── components.js       # HTML组件生成器
    └── init.js             # 页面初始化
```

## 🎯 模块化优势

### 1. **分离关注点**
每个JS文件负责单一功能，便于维护和调试：
- `auth.js` - 只处理认证逻辑
- `trading.js` - 只处理交易逻辑
- `chart.js` - 只处理图表逻辑

### 2. **复用性强**
- CSS样式独立，可在多个页面复用
- JS模块可单独引入或组合使用

### 3. **易于扩展**
需要添加新功能时：
- 创建新的JS模块文件
- 在 `index_modular.html` 中引入
- 无需修改其他模块

### 4. **便于协作**
多人开发时可分别负责不同模块，减少代码冲突

## 📝 各模块详细说明

### CSS模块 (`css/styles.css`)
包含所有样式定义：
- 主题变量（日间/夜间模式）
- 基础样式（卡片、按钮、输入框）
- 组件样式（标签页、徽章、通知）
- 动画效果（滑入、淡入淡出）
- 模态框、FAQ、页脚等样式

### JavaScript模块

#### 1. `global.js` - 全局变量
```javascript
currentUser      // 当前登录用户
priceChart       // 图表实例
updateInterval   // 定时更新器
currentTheme     // 当前主题
isLoginMode      // 登录/注册模式切换
```

#### 2. `toast.js` - 通知系统
```javascript
showToast(message, type, title)  // 显示通知
// type: 'success' | 'error' | 'warning' | 'info'
```

#### 3. `theme.js` - 主题管理
```javascript
toggleTheme()      // 切换主题
initTheme()        // 初始化主题
updateChartTheme() // 更新图表主题色
```

#### 4. `modals.js` - 模态框控制
```javascript
showLoginModal()   // 显示登录框
showAboutModal()   // 显示项目介绍
showGuideModal()   // 显示使用说明
showFaqModal()     // 显示常见问题
toggleFaq(index)   // FAQ折叠切换
```

#### 5. `auth.js` - 用户认证
```javascript
handleLogin()      // 处理登录/注册
updateUserArea()   // 更新用户显示区
logout()           // 退出登录
initApp()          // 登录后初始化
```

#### 6. `chart.js` - 价格图表
```javascript
initPriceChart()    // 初始化图表
updatePriceChart()  // 更新图表数据
```

#### 7. `data.js` - 数据更新
```javascript
updateData()            // 更新所有数据
updateUserInfo()        // 更新用户信息
updatePositions()       // 更新持仓
updateTradeHistory()    // 更新交易历史
updateLeaderboard()     // 更新排行榜
updateStats()           // 更新统计
updatePrompts()         // 更新AI策略
```

#### 8. `trading.js` - 交易操作
```javascript
switchTab(tab)          // 切换标签页
runAIAnalysis()         // 运行AI分析
executeAITrade()        // 执行AI交易
openPosition()          // 开仓
closePosition(id)       // 平仓
activatePrompt(id)      // 激活策略
```

#### 9. `public.js` - 公开内容
```javascript
loadTopCryptoData()        // 加载Top10币种
loadPublicLeaderboard()    // 加载公开排行榜
```

#### 10. `components.js` - 组件生成
```javascript
loadModalsComponent()    // 加载模态框HTML
loadPublicContent()      // 加载公开内容HTML
loadMainContent()        // 加载主内容HTML
initComponents()         // 初始化所有组件
```

#### 11. `init.js` - 初始化
页面加载时的初始化逻辑

## 🚀 使用方式

### 方式1：使用原始完整文件
```html
<!-- 访问 index.html -->
所有代码在一个文件中，适合快速部署
```

### 方式2：使用模块化版本
```html
<!-- 访问 index_modular.html -->
代码分离清晰，适合开发和维护
```

### 在main.py中切换
```python
@app.get("/")
async def read_root():
    # 返回模块化版本
    return FileResponse("static/index_modular.html")

    # 或返回原始版本
    # return FileResponse("static/index.html")
```

## 🔧 修改指南

### 修改样式
编辑 `css/styles.css`

### 修改主题色
编辑 `css/styles.css` 中的 `:root` 和 `[data-theme="dark"]` 变量

### 添加新功能
1. 在 `js/` 目录创建新模块文件
2. 在 `index_modular.html` 中引入
3. 在 `init.js` 中初始化（如需要）

### 修改HTML结构
编辑 `components.js` 中对应的函数

## ⚠️ 注意事项

1. **加载顺序很重要**：`index_modular.html` 中JS文件的引入顺序按依赖关系排列，不要随意调整
2. **全局变量**：定义在 `global.js` 中，所有模块可访问
3. **事件监听**：避免重复绑定，建议在 `init.js` 中统一管理
4. **兼容性**：两个版本功能完全一致，可随时切换

## 📊 性能优化建议

1. **按需加载**：将不常用的模块改为异步加载
2. **代码压缩**：生产环境使用压缩后的JS/CSS
3. **缓存策略**：为静态资源添加版本号
4. **CDN加速**：将CSS/JS部署到CDN

## 🎨 自定义主题

编辑 `css/styles.css` 中的CSS变量即可快速更改主题：

```css
:root {
    --bg-primary: #your-color;
    --text-primary: #your-color;
    --success: #your-color;
    /* ... 其他变量 */
}
```
