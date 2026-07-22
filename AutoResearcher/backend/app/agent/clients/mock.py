"""
Mock client implementations for running the real graph pipeline without API calls.
Activated via USE_MOCK=true environment variable.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any


class MockLLMClient:
    """Mock LLM that generates realistic responses based on the system prompt context."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        return json.dumps(self._pick_response(messages))

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        query = self._extract_query(messages)
        report = self._generate_report(query)
        for char in report:
            yield char
            await asyncio.sleep(0.008)

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return self._pick_response(messages)

    def _pick_response(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        system = messages[0].get("content", "") if messages else ""
        query = self._extract_query(messages)

        if "planning" in system.lower() or "decompose" in system.lower():
            return self._planner_response(query)
        elif "critic" in system.lower() or "quality" in system.lower():
            return self._critic_response()
        return {}

    def _planner_response(self, query: str) -> dict[str, Any]:
        short = query[:20] if len(query) > 20 else query
        return {
            "outline": [
                "背景与现状",
                "核心技术分析",
                "主流方案对比",
                "实际应用案例",
                "未来趋势与展望",
            ],
            "sub_tasks": [
                {"id": "task_1", "query": f"{short} 背景介绍与发展历程"},
                {"id": "task_2", "query": f"{short} 核心技术原理"},
                {"id": "task_3", "query": f"{short} 主流方案对比评测"},
                {"id": "task_4", "query": f"{short} 企业实际应用案例"},
            ],
        }

    def _critic_response(self) -> dict[str, Any]:
        return {
            "has_conflicts": False,
            "conflicts": [],
            "missing_aspects": [],
            "confidence_score": 0.85,
            "recommendation": "proceed",
        }

    def _extract_query(self, messages: list[dict[str, str]]) -> str:
        for msg in messages:
            if msg.get("role") == "user":
                content = msg["content"]
                if "Research question:" in content:
                    return content.split("Research question:")[1].split("\n")[0].strip()
                if len(content) < 200:
                    return content
        return "研究主题"

    def _generate_report(self, query: str) -> str:
        return f"""# {query}

## 1. 背景与现状

近年来，{query}领域取得了显著进展。随着技术的不断演进和应用场景的持续拓展，该领域已成为学术界和产业界共同关注的焦点 [1]。

从全球范围来看，相关技术的研发投入持续增长，2024 年全球市场规模已突破千亿级别。主要参与者包括科技巨头和创新型初创企业，竞争格局日趋多元化。

## 2. 核心技术分析

### 2.1 技术架构

当前主流技术方案主要基于以下几个核心组件：

- **基础模型层**：提供底层能力支撑，决定了系统的上限
- **中间件层**：负责任务调度、资源管理和接口适配
- **应用层**：面向终端用户，提供具体的功能和服务

### 2.2 关键指标

| 指标 | 方案 A | 方案 B | 方案 C |
|:---|:---|:---|:---|
| 准确率 | 92.3% | 88.7% | 85.1% |
| 响应速度 | 120ms | 85ms | 200ms |
| 可扩展性 | 优秀 | 良好 | 一般 |
| 成本效率 | 中等 | 高 | 低 |

## 3. 主流方案对比

目前业界主要存在三种技术路线 [2]：

1. **路线 A**：以高精度为导向，适用于对准确性要求极高的场景。代表性实现包括系统 X 和框架 Y。
2. **路线 B**：以效率为导向，在保证基本质量的前提下最大化吞吐量。适合大规模批处理场景。
3. **路线 C**：以灵活性为导向，支持快速定制和二次开发。适合中小型团队快速落地。

## 4. 实际应用案例

### 案例一：某科技公司的落地实践
该公司在生产环境中部署了基于路线 A 的解决方案，经过 6 个月的运行，核心业务指标提升 35%，人工成本降低 40% [3]。

### 案例二：某金融机构的创新尝试
采用路线 B 方案处理海量数据分析需求，日处理量从 10 万条提升至 500 万条，同时错误率维持在 0.1% 以下。

## 5. 未来趋势

- **多模态融合**将成为下一阶段的核心方向
- **边缘计算**场景下的轻量化部署将带来新的增长点
- **安全与合规**要求将推动技术标准化进程加速
- 预计到 2026 年，相关市场规模将达到当前的 **3-5 倍**

## 参考来源

1. [{query} 行业发展报告 2024](https://example.com/report-2024)
2. [技术方案对比研究](https://example.com/comparison)
3. [企业落地实践白皮书](https://example.com/whitepaper)

---

*本报告由 AutoResearcher 自动生成，请核实关键数据。*
"""


class MockSearchClient:
    """Mock search client that returns realistic-looking results based on the query."""

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        await asyncio.sleep(0.3)
        return [
            {
                "title": f"{query} — 最新研究进展综述",
                "url": f"https://example.com/research/{hash(query) % 10000}",
                "content": f"本文全面综述了{query}领域的最新进展，涵盖技术原理、应用场景和发展趋势。研究表明该领域在过去一年中取得了显著突破，多项核心指标实现了翻倍增长。",
                "score": 0.95,
            },
            {
                "title": f"{query} 技术对比与评测报告",
                "url": f"https://example.com/benchmark/{hash(query) % 10000}",
                "content": f"针对{query}领域的主流技术方案进行了系统性评测。测试覆盖准确率、响应速度、可扩展性等维度，为技术选型提供数据支撑。",
                "score": 0.91,
            },
            {
                "title": f"{query} 在企业中的实践案例分析",
                "url": f"https://example.com/cases/{hash(query) % 10000}",
                "content": f"收集整理了 15 个{query}在不同行业的落地案例。数据显示，成功应用的企业平均效率提升 30-50%，成本降低 20-40%。",
                "score": 0.88,
            },
        ]
