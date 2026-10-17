"""عقدة الرد السريع الحتمي."""

from orchestration.state import AgentState

QUICK_REPLY_TEXT = "يسعدني ذلك، وأنا جاهز لمساعدتك."


def quick_reply_node(state: AgentState) -> dict:
    """إنتاج رد عام لأي صياغة يصنفها النموذج كرد سريع."""
    _ = state
    return {"response": QUICK_REPLY_TEXT}
