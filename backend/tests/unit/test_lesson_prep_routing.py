"""اختبارات توجيه مشرف تحضير الدرس."""

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


def test_route_next_assembler_when_no_final_plan() -> None:
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
    assert result.goto == "END"


def test_route_next_end_when_max_iterations_reached() -> None:
    state = {"iteration": MAX_ITERATIONS}
    result = route_next(state)
    assert result.goto == "END"


def test_route_next_increments_iteration() -> None:
    state = {"iteration": 5}
    result = route_next(state)
    assert result.update["iteration"] == 6
