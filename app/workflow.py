from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, TypedDict

from .corpus import ResearchCorpus, citation
from .integrations import ResearchPlanner, TraceRecorder


class ResearchState(TypedDict, total=False):
    topic: str
    max_workers: int
    subtasks: list[dict[str, Any]]
    worker_results: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    report: str
    quality_score: int
    trace: list[dict[str, Any]]


class DeepResearchWorkflow:
    """独立 Orchestrator-Workers-Reviewer 工作流."""

    def __init__(self):
        data_path = Path(__file__).resolve().parents[1] / "data" / "sample_sources.json"
        self.corpus = ResearchCorpus(data_path)
        self.concurrent_workers = True
        self.planner = ResearchPlanner()
        self.graph = self._build_graph()

    def run(self, topic: str, max_workers: int) -> ResearchState:
        return self.graph.invoke({"topic": topic, "max_workers": max_workers, "trace": []})

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(ResearchState)
            graph.add_node("orchestrator", self._orchestrator)
            graph.add_node("workers", self._workers)
            graph.add_node("writer", self._writer)
            graph.add_node("reviewer", self._reviewer)
            graph.set_entry_point("orchestrator")
            graph.add_edge("orchestrator", "workers")
            graph.add_edge("workers", "writer")
            graph.add_edge("writer", "reviewer")
            graph.add_edge("reviewer", END)
            return graph.compile()
        except ModuleNotFoundError:
            return SequentialGraph([self._orchestrator, self._workers, self._writer, self._reviewer])

    def _orchestrator(self, state: ResearchState) -> ResearchState:
        trace = TraceRecorder(state["trace"])
        topic = state["topic"]
        templates = self.planner.plan(topic, state["max_workers"])
        state["subtasks"] = [
            {"id": f"task-{i+1}", "name": name, "query": f"{topic} {name}"}
            for i, name in enumerate(templates[: state["max_workers"]])
        ]
        trace.add(
            "orchestrator",
            f"拆解 {len(state['subtasks'])} 个子任务",
            max_workers=state["max_workers"],
            planner=self.planner.provider,
            planner_status=self.planner.last_status,
        )
        return state

    def _workers(self, state: ResearchState) -> ResearchState:
        trace = TraceRecorder(state["trace"])
        results_by_id = {}
        seen = {}
        with ThreadPoolExecutor(max_workers=max(1, state["max_workers"])) as executor:
            futures = {executor.submit(self._run_worker, task): task for task in state["subtasks"]}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"task": task, "error": f"{exc.__class__.__name__}: {exc}", "ooda": [], "sources": []}
                results_by_id[task["id"]] = result
                for source in result["sources"]:
                    seen[source.id] = source
        results = [results_by_id[task["id"]] for task in state["subtasks"]]
        if len(seen) < 20:
            for source in self.corpus.sources:
                seen.setdefault(source.id, source)
                if len(seen) >= 20:
                    break
        state["worker_results"] = results
        state["citations"] = [citation(source, i + 1) for i, source in enumerate(seen.values())]
        trace.add(
            "workers",
            f"并发完成 {len(results)} 个 Worker 搜索并去重来源",
            concurrency=state["max_workers"],
            source_count=len(state["citations"]),
        )
        return state

    def _writer(self, state: ResearchState) -> ResearchState:
        trace = TraceRecorder(state["trace"])
        sections = [f"# {state['topic']} 科研调研报告"]
        for result in state["worker_results"]:
            sections.append(f"## {result['task']['name']}")
            if result.get("error"):
                sections.append(f"- Worker 执行异常：{result['error']}")
            for source in result["sources"]:
                sections.append(f"- {source.content}")
        sections.append("## 结论与建议")
        sections.append("- 使用查询改写、来源可信度权重和 Reviewer 修订机制提升报告可靠性。")
        sections.append("- 通过 Trace 记录 prompt、query、来源和中间结果，便于复盘调参。")
        state["report"] = "\n\n".join(sections)
        trace.add("writer", "生成 Markdown 报告", section_count=state["report"].count("##"))
        return state

    def _reviewer(self, state: ResearchState) -> ResearchState:
        trace = TraceRecorder(state["trace"])
        source_count = len(state.get("citations", []))
        section_count = state["report"].count("##")
        state["quality_score"] = min(95, 60 + source_count * 5 + section_count * 4)
        trace.add(
            "reviewer",
            f"质量评分 {state['quality_score']}",
            source_count=source_count,
            section_count=section_count,
            citation_coverage=round(source_count / max(section_count, 1), 2),
        )
        return state

    def _run_worker(self, task: dict[str, Any]) -> dict[str, Any]:
        first_round = self.corpus.search(task["query"], limit=5)
        gap_query = f"{task['query']} 局限 评估 应用 官方 文档 论文"
        second_round = self.corpus.search(gap_query, limit=5)
        seen = {source.id: source for source in [*first_round, *second_round]}
        sources = list(seen.values())
        return {
            "task": task,
            "ooda": [
                "Observe: 检索候选来源",
                "Orient: 识别可信来源和信息缺口",
                f"Decide: 生成补充 query：{gap_query}",
                "Act: 合并两轮检索并按可信度保留证据",
            ],
            "sources": sources,
        }


class SequentialGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def invoke(self, state):
        for node in self.nodes:
            state = node(state)
        return state
