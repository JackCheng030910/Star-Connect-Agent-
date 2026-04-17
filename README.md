# BenzMind — Mercedes-Benz AI Agent Platform

基于多智能体（Multi-Agent）协作架构的“梅赛德斯-奔驰智能客户体验平台”。该项目为【德勤精英赛】（Deloitte Elite Challenge）而打造，融合了 MoE 门控制导网络、LoRA 领域微调模拟以及大模型 RAG（检索增强生成）机制，覆盖了车辆销售、个性化配置、售后服务和座舱体验的全生命周期。

当前版本已经补齐了最小可用的业务闭环：
线索登记 -> 展厅试驾 -> 报价/成交推进 -> 售后转接，并提供企业微信 / CRM / DMS 的 webhook 骨架接口。

## 🌟 核心技术亮点

1. **MoE 门控制导路由 (Mixture of Experts)**
   后端 `orchestrator.py` 充当智能意图网关，能够精准捕获用户意图，并将请求切分投递给对应的独立专家节点（销售、配车、售后、体验）。
2. **动态 LoRA 权重挂载 (Low-Rank Adaptation)**
   系统在切换不同业务流时，自动挂载与领域相关的 LoRA 微调权重，保证各个 Agent（售后顾问、销售顾问）在专业术语上的精准性。
3. **真实公共销售数据集 RAG 增强**
   无缝融合 HuggingFace 的公共汽车销售话术数据集，销售节点可以直接以它为思考依托点进行话术优化对练。
4. **全端业务联动**
   售后顾问发现高频维修老旧车型，会自动引导引流，触发销售节点接管，实现真实的商业闭环（Trade-in 老车置换转化）。
5. **生命周期事件流**
   系统会记录线索阶段、事件时间线和自动转接信号，便于在前端数据面板中查看客户旅程状态。

## 💡 快速开始 (复现步骤)

### 1. 环境准备
请确保你的电脑上已经安装了 **Python 3.8** 或以上版本。
建议在虚拟环境 (venv/conda) 中运行。

### 2. 克隆仓库
```bash
git clone https://github.com/JackCheng030910/Star-Connect-Agent-.git
cd Star-Connect-Agent-
```

### 3. 安装依赖包
项目依赖 `Flask` 框架及一系列用于数据处理和 API 交互的通用库。只需执行：
```bash
pip install -r requirements.txt
```
*(当前核心依赖：Flask, flask-cors, python-dotenv, openai)*

### 4. 启动后端引擎
在项目根目录执行：
```bash
python server.py
```
> 你应该在终端中看到 `[*] Server starting on http://localhost:5000` 的提示，说明服务启动成功。

> 如果你的系统里 `python` 命令不可用，请直接使用 Python 可执行文件启动，例如：
> `C:/Users/jackcheng030910/AppData/Local/Programs/Python/Python311/python.exe server.py`

### 5. 访问前端界面
打开你的浏览器，访问以下地址进入 BenzMind 操作控制台：
```
http://localhost:5000
```

### 6. 业务闭环入口
前端数据面板现在提供三个直接入口：
* `登记线索` — 创建客户线索并同步阶段
* `预约试驾` — 生成试驾预约和事件记录
* `生成报价` — 推进成交阶段并记录报价事件

### 7. Webhook 骨架接口
后端已预留三个外部系统接入入口，用于后续和企业微信、CRM、DMS 打通：
* `POST /api/webhooks/wecom`
* `POST /api/webhooks/crm`
* `POST /api/webhooks/dms`

同时提供生命周期查询与动作接口：
* `GET /api/lifecycle`
* `POST /api/lead/capture`
* `POST /api/test-drive/request`
* `POST /api/deal/quote`

---

## 🛠️ 关于接入真实大模型 (OpenAI / Kimi)

平台默认以**“模拟演示”**模式启动，可用于脱机审查和安全展示。为了在演示中展现完整的动态大模型生成能力：

1. 在左侧边栏，将**【引擎模式】**从“模拟演示”切换至“OpenAI”。
2. 系统会弹出一个提示框：
   - **Kimi 模型配置示例**：
     - **API Base URL**：`https://api.moonshot.cn/v1`
     - **模型名称**：`moonshot-v1-8k`
     - **API Key**：请填入你在开放平台申请的 `sk-...` 密钥。
3. 填入参数并点击【确认】。此时系统底层的 RAG 分析和自然聊天将完全通过你配置的真实大模型引擎驱动。

## 📁 目录结构摘要
* `agents/` — 核心 AI 行为层（销售、配置、售后、路由协调器）。
* `data/` — 结构化的车辆知识库（vehicles.json）、配置选装数据及真实渲染车型实景图。
* `server.py` — Flask API 总线及静态资源代理。
* `index.html` / `app.js` / `styles.css` — 纯原生构建、开箱即用的前端交互端点。

## 运行提示
* 模拟模式默认可离线演示。
* 切换到 OpenAI 模式前，请先配置 API Key 与 Base URL。
* 如果你在 Windows 下遇到 `python` 命令不可用，优先使用完整 Python 路径启动。
