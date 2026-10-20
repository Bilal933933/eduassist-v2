"""عقدة الرد العام للدردشة الحرة خارج المنهج."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, current_user_role
from prompts import get_prompt
from shared.prompt_builder import build_prompt


def create_general_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة رد عام تستخدم نموذج اللغة المحقون."""

    async def general_node(state: AgentState) -> dict:
        """تجهيز مهمة الدردشة الحرة وإعادة الرد كتحديث للحالة."""
        spec = get_prompt("general", current_user_role(state))
        prompt = build_prompt(
            message=state["messages"][-1],
            context=state.get("context", {}),
            task=spec.task,
            role=spec.role,
        )
        response = await call_model(prompt, spec.system, spec.temperature)
        return {
            "response": response,
            "metadata": append_node(
                state.get("metadata"),
                "general",
                handled_by="general_node",
                response_source="llm",
                generator_role=spec.role,
            ),
        }

    return general_node
