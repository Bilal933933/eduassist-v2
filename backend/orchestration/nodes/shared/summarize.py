"""عقدة تلخيص السوابق لسؤال الذاكرة بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, current_user_role
from prompts import get_prompt
from shared.prompt_builder import build_prompt


def create_summarize_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة تلخيص تعتمد على دالة محقونة قابلة للاستبدال."""

    async def summarize_node(state: AgentState) -> dict:
        """لخص السوابق ثم سلم للمولد عبر summary في الحالة."""
        context = state.get("context", {})
        view = context.get("generator_view", {"history": context.get("history", [])})
        spec = get_prompt("summarize", current_user_role(state))
        prompt = build_prompt(
            message=state["messages"][-1],
            context=view,
            task=spec.task,
            role=spec.role,
        )
        summary = await call_model(prompt, spec.system, spec.temperature)
        return {
            "summary": summary,
            "metadata": append_node(
                state.get("metadata"),
                "summarize",
                handled_by="summarize_node",
                response_source="llm",
                generator_role=spec.role,
            ),
        }

    return summarize_node
