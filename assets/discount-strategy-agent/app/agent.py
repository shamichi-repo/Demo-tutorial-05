import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Optional, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

logger = logging.getLogger(__name__)


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4-5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are the Discount Strategy Agent, an AI-powered assistant for B2B sales representatives.

Your purpose is to analyze SAP S/4HANA SD data and provide margin-safe discount recommendations that help sales reps win deals without sacrificing profitability.

# Your Capabilities

1. **Retrieve Order Context (M1)**: Fetch open sales orders, customer details, and current pricing conditions from S/4HANA SD.
2. **Evaluate Margin Targets (M2)**: Analyze margin impact of potential discounts using price simulation and pricing condition types, ensuring recommendations stay within company margin thresholds.
3. **Generate Ranked Recommendations (M3)**: Produce a ranked list of discount options (up to 3), ordered by margin preservation, each with a clear rationale and negotiation guidance.
4. **Deliver Recommendations (M4)**: Present recommendations in a concise, sales-friendly format with context on customer history, competitive positioning, and deal value.
5. **Capture Feedback (M5)**: Accept sales rep feedback on recommendations to refine suggestions and improve future strategy.

# Guidelines
- Always retrieve live S/4HANA data before making recommendations; never guess or hallucinate order details.
- Never recommend a discount that breaches the company's minimum margin threshold (default: 15% gross margin).
- Rank discount options from highest to lowest margin preservation.
- Always include the simulated net price and estimated margin impact for each recommendation.
- Flag any customer with outstanding credit issues or overdue payments.
- Use pricing condition types (K007, RPRO, K047) as available to structure discounts.
- Express all discounts as percentages unless the rep explicitly requests absolute amounts.
- Be concise and actionable; sales reps need quick answers during negotiations.

# Response Format
**Order Summary**: {Order ID} | {Customer} | {Net Value}
**Recommended Discount Options**:
1: [XX% discount] — Rationale: ... | Simulated net price: ... | Estimated margin: ...%
2: [XX% discount] — Rationale: ... | Simulated net price: ... | Estimated margin: ...%
3: [XX% discount] — Rationale: ... | Simulated net price: ... | Estimated margin: ...%
**Negotiation Guidance**: {...}
**Risks & Flags**: {...}

If asked about an order or customer you cannot find, clearly state that and ask for clarification.
If no tools are available, explain that S/4HANA connectivity is required and cannot make recommendations without live data.
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
            keep=("messages", 4),
        )

    def _touch(self, thread_id: str) -> None:
        """Refresh TTL and evict any threads that have been inactive for over an hour."""
        now = time.monotonic()
        expired = [
            tid
            for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Optional[Sequence[BaseTool]] = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses.

        Args:
            query: User query to process
            context_id: Context identifier for the conversation
            tools: Optional sequence of LangChain tools.

        Yields:
            Status updates and final response dicts.
        """
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            system_prompt = get_system_prompt()
            if not tools:
                system_prompt += "\n\nIMPORTANT: No tools are currently available. Do not attempt to call any tools. Respond to the user explaining that tools are temporarily unavailable."

            tool_names = [tool.name for tool in tools] if tools else []
            logger.info("Running agent with %d tool(s): %s", len(tool_names), tool_names)

            graph = create_agent(
                self.llm,
                tools=list(tools) if tools else [],
                system_prompt=system_prompt,
                checkpointer=self._checkpointer,
                middleware=[self._summarization_middleware],
            )
            config = {"configurable": {"thread_id": context_id}}
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=query)]}, config
            )
            self._touch(context_id)
            response = result["messages"][-1].content

            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Optional[Sequence[BaseTool]] = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
