"""عقدة الرد العام للدردشة الحرة خارج المنهج."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState
from prompts.system import GENERAL_SYSTEM_PROMPT
from prompts.tasks import GENERAL_RESPONSE_TASK
from shared.prompt_builder import build_prompt


def create_general_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة رد عام تستخدم نموذج اللغة المحقون."""

    async def general_node(state: AgentState) -> dict:
        """تجهيز مهمة الدردشة الحرة وإعادة رد النموذج كتحديث للحالة."""
        prompt = build_prompt(
            message=state["messages"][-1],
            context=state.get("context", {}),
            task=GENERAL_RESPONSE_TASK,
            role="general_assistant",
        )
        response = await call_model(prompt, GENERAL_SYSTEM_PROMPT, 0.7)
        return {"response": response}

    return general_node
