"""عقدة الرد على الإساءة بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, current_user_role
from prompts import get_prompt
from shared.prompt_builder import build_prompt


def create_abuse_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة إساءة تستخدم نموذج اللغة المحقون."""

    async def abuse_node(state: AgentState) -> dict:
        """تجهيز مهمة الإساءة مع التصعيد اللطيف وإعادة رد النموذج."""
        count = int(state.get("abuse_count", 0)) + 1
        spec = get_prompt("abuse", current_user_role(state))
        prompt = build_prompt(
            message=state["messages"][-1],
            context={"occurrence": count},
            task=spec.task,
            role=spec.role,
        )
        response = await call_model(prompt, spec.system, spec.temperature)
        return {
            "response": response,
            "abuse_count": count,
            "metadata": append_node(
                state.get("metadata"),
                "abuse",
                handled_by="abuse_node",
                response_source="llm",
                generator_role=spec.role,
                abuse_count=count,
            ),
        }

    return abuse_node
