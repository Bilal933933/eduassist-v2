"""عقدة توليد الرد بواسطة نموذج اللغة الكبير."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState
from prompts.system import SYSTEM_PROMPT
from shared.prompt_builder import build_prompt


def create_generation_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة توليد تعتمد على دالة محقونة قابلة للاستبدال في الاختبارات."""

    async def generation_node(state: AgentState) -> dict:
        """إرسال أحدث رسالة إلى النموذج وإعادة الرد كتحديث للحالة."""
        prompt = build_prompt(
            message=state["messages"][-1],
            context=state.get("context", {}),
            task=state.get("task", "answer"),
            role=state.get("role", "educational_assistant"),
        )
        response = await call_model(prompt, SYSTEM_PROMPT, 0.2)
        return {"response": response}

    return generation_node
