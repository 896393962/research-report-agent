from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .schemas import ReportRequest, ReportResponse
from .workflow import DeepResearchWorkflow


app = FastAPI(title="Deep Research Report Agent", version="1.0.0")
workflow = DeepResearchWorkflow()


@app.get("/health")
def health():
    return {"status": "ok", "project": "research_report_agent"}


@app.get("/integrations/status")
def integrations_status():
    return {
        "worker_execution": {
            "concurrent": workflow.concurrent_workers,
            "max_workers_limit": 5,
            "executor": "ThreadPoolExecutor",
        },
        "planner": {"provider": workflow.planner.provider, "status": workflow.planner.last_status},
    }


@app.post("/report", response_model=ReportResponse)
def report(request: ReportRequest):
    state = workflow.run(request.topic, request.max_workers)
    return {
        "report": state["report"],
        "citations": state["citations"],
        "trace": state["trace"],
        "quality_score": state["quality_score"],
    }


@app.post("/report/stream")
def report_stream(request: ReportRequest):
    state = workflow.run(request.topic, request.max_workers)

    def events():
        for event in state["trace"]:
            yield f"event: {event['node']}\n"
            yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
        yield "event: completed\n"
        yield "data: " + json.dumps(
            {"report": state["report"], "citations": state["citations"], "quality_score": state["quality_score"]},
            ensure_ascii=False,
        ) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8103)
