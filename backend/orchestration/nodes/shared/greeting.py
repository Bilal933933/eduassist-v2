"""عقدة الرد على تحية المستخدم بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, current_user_role
from prompts import get_prompt
from shared.prompt_builder import build_prompt


def create_greeting_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة تحية تستخدم نموذج اللغة المحقون."""

    async def greeting_node(state: AgentState) -> dict:
        """تجهيز مهمة التحية وإعادة رد النموذج كتحديث للحالة."""
        spec = get_prompt("greeting", current_user_role(state))
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
                "greeting",
                handled_by="greeting_node",
                response_source="llm",
                generator_role=spec.role,
            ),
        }

    return greeting_node
