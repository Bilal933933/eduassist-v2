"""عقدة الرد على الإساءة بواسطة نموذج اللغة."""

from collections.abc import Awaitable, Callable

from orchestration.state import AgentState, append_node
from prompts.system import ABUSE_SYSTEM_PROMPT
from prompts.tasks import ABUSE_ESCALATION_TASK, ABUSE_RESPONSE_TASK
from shared.prompt_builder import build_prompt


def create_abuse_node(
    call_model: Callable[[str, str, float], Awaitable[str]],
):
    """إنشاء عقدة إساءة تستخدم نموذج اللغة المحقون."""

    async def abuse_node(state: AgentState) -> dict:
        """تجهيز مهمة الإساءة مع التصعيد اللطيف وإعادة رد النموذج."""
        count = int(state.get("abuse_count", 0)) + 1
        prompt = build_prompt(
            message=state["messages"][-1],
            context={"occurrence": count},
            task=f"{ABUSE_RESPONSE_TASK}\n{ABUSE_ESCALATION_TASK}",
            role="educational_assistant",
        )
        response = await call_model(prompt, ABUSE_SYSTEM_PROMPT, 0.2)
        return {
            "response": response,
            "abuse_count": count,
            "metadata": append_node(
                state.get("metadata"),
                "abuse",
                handled_by="abuse_node",
                response_source="llm",
                generator_role="educational_assistant",
                abuse_count=count,
            ),
        }

    return abuse_node
