"""عقدة توليد الرد بواسطة نموذج اللغة الكبير."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, user_is_teacher
from prompts.system import SYSTEM_PROMPT
from shared.prompt_builder import build_prompt


def create_generation_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة توليد تعتمد على دالة محقونة قابلة للاستبدال في الاختبارات."""

    async def generation_node(state: AgentState) -> dict:
        """إرسال أحدث رسالة إلى النموذج وإعادة الرد كتحديث للحالة."""
        context = state.get("context", {})
        view = dict(context.get("generator_view", context))
        if state.get("summary"):
            view["summary"] = state["summary"]
        generator_role = (
            "teacher_assistant" if user_is_teacher(state) else "educational_assistant"
        )
        prompt = build_prompt(
            message=state["messages"][-1],
            context=view,
            task=state.get("task", "answer"),
            role=generator_role,
        )
        response = await call_model(prompt, SYSTEM_PROMPT, 0.2)
        return {
            "response": response,
            "metadata": append_node(
                state.get("metadata"),
                "generation",
                handled_by="student_generation_node",
                response_source="llm",
                generator_role=generator_role,
                recalled=bool(state.get("summary")),
            ),
        }

    return generation_node
