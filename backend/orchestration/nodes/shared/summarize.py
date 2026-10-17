"""عقدة تلخيص السوابق لسؤال الذاكرة بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState
from prompts.system import SYSTEM_PROMPT
from prompts.tasks import RECALL_TASK
from shared.prompt_builder import build_prompt


def create_summarize_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة تلخيص تعتمد على دالة محقونة قابلة للاستبدال."""

    async def summarize_node(state: AgentState) -> dict:
        """لخص السوابق ثم سلم للمولد عبر summary في الحالة."""
        context = state.get("context", {})
        view = context.get("generator_view", {"history": context.get("history", [])})
        prompt = build_prompt(
            message=state["messages"][-1],
            context=view,
            task=RECALL_TASK,
            role="educational_assistant",
        )
        summary = await call_model(prompt, SYSTEM_PROMPT, 0.2)
        return {"summary": summary}

    return summarize_node
