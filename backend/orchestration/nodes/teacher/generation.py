"""عقدة توليد المعلم: تحقن خلاصة البروفايل في السياق."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState
from prompts.system import SYSTEM_PROMPT
from shared.prompt_builder import build_prompt


def create_teacher_generation_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """عقدة توليد المعلم: تحقن خلاصة البروفايل في السياق."""

    async def teacher_generation_node(state: AgentState) -> dict:
        """إرسال الرسالة مع سياق المعلم وإعادة الرد."""
        context = dict(state.get("context", {}))
        brief = context.get("teacher_brief", "")
        view = dict(context.get("generator_view", {"history": context.get("history", [])}))
        if brief:
            view["teacher_brief"] = brief
        if state.get("summary"):
            view["summary"] = state["summary"]
        prompt = build_prompt(
            message=state["messages"][-1],
            context=view,
            task=state.get("task", "answer"),
            role="teacher_assistant",
        )
        response = await call_model(prompt, SYSTEM_PROMPT, 0.2)
        return {
            "response": response,
            "metadata": {
                **state.get("metadata", {}),
                "handled_by": "teacher_generation_node",
                "intent": state.get("intent"),
                "generator_role": "teacher_assistant",
            },
        }

    return teacher_generation_node
