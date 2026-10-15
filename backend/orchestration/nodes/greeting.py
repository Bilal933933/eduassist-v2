"""عقدة الرد على تحية المستخدم بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState
from prompts.system import SYSTEM_PROMPT
from prompts.tasks import GREETING_RESPONSE_TASK
from shared.prompt_builder import build_prompt


def create_greeting_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة تحية تستخدم نموذج اللغة المحقون."""

    async def greeting_node(state: AgentState) -> dict:
        """تجهيز مهمة التحية وإعادة رد النموذج كتحديث للحالة."""
        prompt = build_prompt(
            message=state["messages"][-1],
            context=state.get("context", {}),
            task=GREETING_RESPONSE_TASK,
            role="educational_assistant",
        )
        response = await call_model(prompt, SYSTEM_PROMPT, 0.3)
        return {"response": response}

    return greeting_node
