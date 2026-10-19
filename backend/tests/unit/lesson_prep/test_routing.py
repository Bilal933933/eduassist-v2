"""اختبارات توجيه مشرف تحضير الدرس."""
from __future__ import annotations

from langgraph.graph import END

from orchestration.lesson_prep.supervisor import MAX_ITERATIONS, route_next


def test_route_next_retriever_when_no_chunks() -> None:
    state = {"iteration": 0}
    result = route_next(state)
    assert result.goto == "retriever"


def test_route_next_basic_info_when_no_section_1() -> None:
    state = {"iteration": 0, "retrieved_chunks": [{"text": "test"}]}
    result = route_next(state)
    assert result.goto == "basic_info"


def test_route_next_objectives_when_no_section_2() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
    }
    result = route_next(state)
    assert result.goto == "objectives"


def test_route_next_prior_knowledge_when_no_section_3() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
    }
    result = route_next(state)
    assert result.goto == "prior_knowledge"


def test_route_next_materials_when_no_section_4() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
    }
    result = route_next(state)
    assert result.goto == "materials"


def test_route_next_lesson_flow_when_no_section_5() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
    }
    result = route_next(state)
    assert result.goto == "lesson_flow"


def test_route_next_assessment_when_no_section_6() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
    }
    result = route_next(state)
    assert result.goto == "assessment"


def test_route_next_homework_when_no_section_7() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
    }
    result = route_next(state)
    assert result.goto == "homework"


def test_route_next_differentiation_when_no_section_8() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
    }
    result = route_next(state)
    assert result.goto == "differentiation"


def test_route_next_notes_when_no_section_9() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
    }
    result = route_next(state)
    assert result.goto == "notes"


def test_route_next_critic_when_no_final_plan() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
        "section_9_notes": "notes",
    }
    result = route_next(state)
    assert result.goto == "critic"


def test_route_next_critic_low_quality_returns_to_section() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
        "section_9_notes": "notes",
        "quality_score": 0.3,
        "needs_improvement": "lesson_flow",
    }
    result = route_next(state)
    assert result.goto == "lesson_flow"


def test_route_next_critic_high_quality_goes_to_assembler() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
        "section_9_notes": "notes",
        "quality_score": 0.9,
        "needs_improvement": "",
    }
    result = route_next(state)
    assert result.goto == "assembler"


def test_route_next_end_when_all_complete() -> None:
    state = {
        "iteration": 0,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
        "section_9_notes": "notes",
        "final_lesson_plan": "plan",
    }
    result = route_next(state)
    assert result.goto == END


def test_route_next_end_when_max_iterations_reached() -> None:
    state = {"iteration": MAX_ITERATIONS}
    result = route_next(state)
    assert result.goto == END


def test_route_next_increments_iteration() -> None:
    state = {"iteration": 24}
    result = route_next(state)
    assert result.update["iteration"] == 25


def test_route_next_critic_low_quality_resets_score() -> None:
    """يتحقق من إعادة تعيين quality_score عند إعادة كتابة القسم."""
    state = {
        "iteration": 2,
        "retrieved_chunks": [{"text": "test"}],
        "section_1_basic": "basic",
        "section_2_objectives": "objectives",
        "section_3_prior": "prior",
        "section_4_materials": "materials",
        "section_5_flow": "flow",
        "section_6_assessment": "assessment",
        "section_7_homework": "homework",
        "section_8_differentiation": "differentiation",
        "section_9_notes": "notes",
        "quality_score": 0.3,
        "needs_improvement": "basic_info",
    }
    result = route_next(state)
    assert result.goto == "basic_info"
    assert result.update["quality_score"] is None
    assert result.update["iteration"] == 3
    assert result.update["retried_sections"] == ["basic_info"]


def test_route_next_final_plan_ends_before_quality_branch() -> None:
    """وجود الخطة النهائية ينهي الرسم حتى مع بقاء quality_score."""
    state = {
        "iteration": 16,
        "quality_score": 0.9,
        "needs_improvement": "",
        "final_lesson_plan": "الخطة النهائية",
    }
    result = route_next(state)
    assert result.goto == END


def test_route_next_invalid_section_goes_to_assembler() -> None:
    """قسم غير معروف من الناقد لا يُستخدم كاسم عقدة."""
    state = {
        "iteration": 3,
        "quality_score": 0.2,
        "needs_improvement": "not_a_node",
    }
    result = route_next(state)
    assert result.goto == "assembler"
    assert result.update["quality_score"] is None
