"""عقدة الرد العام للدردشة الحرة خارج المنهج."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, user_is_teacher
from prompts.system import GENERAL_SYSTEM_PROMPT
from prompts.tasks import GENERAL_RESPONSE_TASK, TEACHER_GENERAL_RESPONSE_TASK
from shared.prompt_builder import build_prompt


def create_general_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة رد عام تستخدم نموذج اللغة المحقون."""

    async def general_node(state: AgentState) -> dict:
        """تجهيز مهمة الدردشة الحرة وإعادة الرد كتحديث للحالة."""
        is_teacher = user_is_teacher(state)
        task = TEACHER_GENERAL_RESPONSE_TASK if is_teacher else GENERAL_RESPONSE_TASK
        generator_role = "teacher_assistant" if is_teacher else "general_assistant"
        prompt = build_prompt(
            message=state["messages"][-1],
            context=state.get("context", {}),
            task=task,
            role=generator_role,
        )
        response = await call_model(prompt, GENERAL_SYSTEM_PROMPT, 0.7)
        return {
            "response": response,
            "metadata": append_node(
                state.get("metadata"),
                "general",
                handled_by="general_node",
                response_source="llm",
                generator_role=generator_role,
            ),
        }

    return general_node
