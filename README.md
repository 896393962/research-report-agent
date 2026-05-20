# 面向复杂主题的科研调研报告生成系统

基于 LangGraph Deep Research Agent 思路实现的科研调研报告生成服务。项目采用 Orchestrator-Workers 架构，面向需要多轮搜索、交叉验证和结构化输出的复杂主题，支持任务拆解、并发搜索、来源评估、报告生成、质量评分和 SSE 进度输出。

## 功能特性

- Orchestrator 将复杂主题拆解为多个可并发执行的子任务。
- Worker 围绕子任务执行多轮检索，并记录 OODA 风格执行过程。
- 使用 ThreadPoolExecutor 并发调度多个 Worker，提高资料收集效率。
- 汇总并去重来源，生成带引用信息的 Markdown 调研报告。
- Reviewer 根据来源数量、章节数量和引用覆盖率计算质量分。
- 使用 LangGraph StateGraph 组织 Orchestrator、Workers、Writer、Reviewer 节点。
- 提供普通报告接口和 SSE 流式事件接口。

## 技术栈

- Python 3.10+
- FastAPI / Uvicorn
- LangGraph
- ThreadPoolExecutor
- Markdown 报告生成

## 系统流程

```text
调研主题
  -> Orchestrator 拆解子任务
  -> Workers 并发检索和补充搜索
  -> Writer 生成结构化报告
  -> Reviewer 计算质量分
  -> 返回报告、引用、质量分和 trace
```

## 快速开始

```powershell
cd projects/research_report_agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8103
```

启动后访问：

- Swagger 文档：http://127.0.0.1:8103/docs
- 健康检查：http://127.0.0.1:8103/health
- 集成状态：http://127.0.0.1:8103/integrations/status

## API 示例

### 生成报告

```http
POST /report
Content-Type: application/json

{
  "topic": "RAG 与 Agent 在智能问答系统中的结合方式",
  "max_workers": 3
}
```

### 流式报告

```http
POST /report/stream
Content-Type: application/json

{
  "topic": "多 Agent 深度研究系统的架构设计",
  "max_workers": 4
}
```

## 返回内容

报告接口返回：

- `report`：Markdown 格式调研报告
- `citations`：去重后的来源引用
- `trace`：各节点执行状态
- `quality_score`：报告质量分

## 项目结构

```text
app/
  main.py          # FastAPI 入口
  workflow.py      # Orchestrator / Workers / Writer / Reviewer 工作流
  corpus.py        # 调研语料和引用模型
  integrations.py  # Planner 和 trace 集成
  schemas.py       # API 数据模型
data/
  sample_sources.json
```

## 设计重点

项目强调复杂任务拆解、并发资料收集和可观测报告生成。Orchestrator 负责规划子任务，Workers 负责并发检索和信息整理，Writer 负责结构化报告输出，Reviewer 负责质量评分和引用覆盖检查。每个节点都会写入 trace，便于追踪报告生成过程。
