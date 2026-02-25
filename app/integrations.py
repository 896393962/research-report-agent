from __future__ import annotations

import os
import time
from typing import Any


class TraceRecorder:
    def __init__(self, initial: list[dict[str, Any]] | None = None) -> None:
        self.events = initial if initial is not None else []

    def add(self, node: str, message: str, **extra: Any) -> None:
        self.events.append({"node": node, "message": message, "ts": round(time.time(), 3), **extra})


class ResearchPlanner:
    """Optional LLM planner with deterministic fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.enabled = os.getenv("USE_DASHSCOPE", "true").lower() in {"1", "true", "yes", "on"} and bool(self.api_key)
        self.provider = "dashscope" if self.enabled else "template-fallback"
        self.last_status = "ready" if self.enabled else "missing DASHSCOPE_API_KEY or disabled"

    def plan(self, topic: str, max_workers: int) -> list[str]:
        defaults = ["研究背景与问题定义", "代表方法与核心论文", "应用场景与工程局限", "未来方向与改进建议", "评估方法与指标"]
        if not self.enabled:
            return defaults[:max_workers]
        try:
            import requests

            response = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("DASHSCOPE_CHAT_MODEL", "qwen-plus"),
                    "messages": [
                        {"role": "system", "content": "你是科研调研任务规划器，只输出 JSON 数组。"},
                        {"role": "user", "content": f"将主题拆成 {max_workers} 个调研子任务：{topic}"},
                    ],
                    "temperature": 0.2,
                },
                timeout=8,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            import json

            items = json.loads(content)
            if isinstance(items, list) and items:
                self.last_status = f"planned {len(items[:max_workers])} subtasks"
                return [str(item) for item in items[:max_workers]]
        except Exception as exc:  # pragma: no cover - depends on external API
            self.provider = "template-fallback"
            self.last_status = f"planner fallback: {exc.__class__.__name__}"
        return defaults[:max_workers]
