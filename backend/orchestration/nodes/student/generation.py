"""عقدة توليد الرد بواسطة نموذج اللغة الكبير."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node, current_user_role
from orchestration.nodes.shared.retrieval import format_chunks
from prompts import get_prompt
from shared.prompt_builder import build_prompt


def create_generation_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة توليد تعتمد على دالة محقونة قابلة للاستبدال في الاختبارات."""

    async def generation_node(state: AgentState) -> dict:
        """إرسال أحدث رسالة إلى النموذج وإعادة الرد كتحديث للحالة."""
        context = state.get("context", {})
        view = dict(context.get("generator_view", context))
        references = format_chunks(state.get("retrieved_chunks", []))
        if references:
            view["references"] = references
        if state.get("summary"):
            view["summary"] = state["summary"]
        spec = get_prompt("generation", current_user_role(state))
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
                handled_by="student_generation_node",
                response_source="llm",
                generator_role=spec.role,
                recalled=bool(state.get("summary")),
            ),
        }

    return generation_node
