"""عقدة توليد المعلم: تحقن خلاصة البروفايل في السياق."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node
from orchestration.nodes.shared.retrieval import format_chunks
from prompts import get_prompt
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
        references = format_chunks(state.get("retrieved_chunks", []))
        if references:
            view["references"] = references
        if state.get("summary"):
            view["summary"] = state["summary"]
        # هذه العقدة مركّبة في رسم المعلم فقط، فالدور ثابت هنا.
        spec = get_prompt("generation", "teacher")
        prompt = build_prompt(
            message=state["messages"][-1],
            context=view,
            task=spec.task or state.get("task", "answer"),
            role=spec.role,
        )
        response = await call_model(prompt, spec.system, spec.temperature)
        return {
            "response": response,
            "metadata": append_node(
                state.get("metadata"),
                "generation",
                handled_by="teacher_generation_node",
                response_source="llm",
                generator_role=spec.role,
                recalled=bool(state.get("summary")),
            ),
        }

    return teacher_generation_node
