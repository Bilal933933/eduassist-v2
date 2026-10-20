"""اختبارات تكاملية لعقدة تحضير الدرس الكاملة."""
from __future__ import annotations

import json
from typing import Any

import pytest

from orchestration.nodes.teacher.lesson_prep_node import create_lesson_prep_node

from .conftest import FakeCallModel, FakeRetrievalService


class TestLessonPrepNodeSections:
    """اختبارات نقل الأقسام بين AgentState و LessonPrepState."""

    @pytest.mark.asyncio
    async def test_passes_sections_to_subgraph(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تمرر sections من AgentState إلى الرسم الفرعي."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
            "sections": {"basic_info": "القسم الأساسي موجود مسبقاً"},
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert "sections" in result
        assert isinstance(result["sections"], dict)
        assert len(result["sections"]) > 0

    @pytest.mark.asyncio
    async def test_empty_sections_defaults(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تستخدم sections فارغة افتراضياً."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert "sections" in result
        assert isinstance(result["sections"], dict)

    @pytest.mark.asyncio
    async def test_returns_final_lesson_plan(
        self,
        lesson_prep_node,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تعيد الخطة النهائية في response."""
        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await lesson_prep_node(input_state)

        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0


class TestLessonPrepNodeQualityRetry:
    """اختبارات حلقة إعادة الكتابة بناءً على جودة الخطة."""

    @pytest.mark.asyncio
    async def test_high_quality_goes_to_assembler(
        self,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن الخطة عالية الجودة تنتقل مباشرة للمجمع."""
        call_model = FakeCallModel(
            responses={
                "قيّم جودة خطة الدرس": '{"score": 0.9, "section": null}',
            }
        )
        retrieval_service = FakeRetrievalService()

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        # الناقد تم استدعاؤه واعطى نتيجة عالية
        critic_calls = [
            c for c in call_model.calls if "قيّم جودة خطة الدرس" in c[0]
        ]
        assert len(critic_calls) >= 1

    @pytest.mark.asyncio
    async def test_custom_topic_from_messages(
        self,
        fake_call_model: FakeCallModel,
        fake_retrieval_service: FakeRetrievalService,
        base_context,
    ) -> None:
        """يتحقق من أن الموضوع يُؤخذ من آخر رسالة إذا لم يكن في السياق."""
        node = create_lesson_prep_node(
            call_model=fake_call_model,
            retrieval_service=fake_retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": ["أفعال الناقص في النحو العربي"],
            "context": {
                **base_context,
                "topic": "",  # topic فارغ، يجب استخدام الرسالة
            },
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result


    @pytest.mark.asyncio
    async def test_second_prep_does_not_inherit_previous_sections(self) -> None:
        """يتحقق من أن التحضير الثاني لا يرث أقسام التحضير الأول."""
        prompts: list[str] = []
        counter = {"n": 0}

        async def call_model(task: str, system_prompt: str, temperature: float) -> str:
            _ = system_prompt, temperature
            prompts.append(task)
            counter["n"] += 1
            if "قيّم جودة خطة الدرس" in task:
                return '{"score": 0.9, "section": null}'
            return f"قسم-{counter['n']:02d}"

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=None,
        )
        context = {"subject": "اللغة العربية", "grade": "الثاني المتوسط"}

        first = await node({"messages": ["كان وأخواتها"], "context": context})
        assert first["sections"], "لم يُنتج التحضير الأول أقساماً"

        await node({
            "messages": ["كان وأخواتها"],
            "context": context,
            "sections": first["sections"],
            "retried_sections": first["retried_sections"],
        })

        critic_prompts = [p for p in prompts if "قيّم جودة خطة الدرس" in p]
        assert len(critic_prompts) == 2
        first_section = first["sections"]["basic_info"]
        assert first_section in critic_prompts[0]
        assert first_section not in critic_prompts[1]

    @pytest.mark.asyncio
    async def test_second_prep_retries_section_again(self) -> None:
        """يتحقق من أن إعادة كتابة قسم في التحضير الأول لا تمنعها في الثاني."""
        prompts: list[str] = []

        async def call_model(task: str, system_prompt: str, temperature: float) -> str:
            _ = system_prompt, temperature
            prompts.append(task)
            if "قيّم جودة خطة الدرس" in task:
                return '{"score": 0.3, "section": "lesson_flow"}'
            return "محتوى تجريبي"

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=None,
        )
        context = {"subject": "اللغة العربية", "grade": "الثاني المتوسط"}

        first = await node({"messages": ["كان وأخواتها"], "context": context})
        assert first["retried_sections"] == ["lesson_flow"]

        prompts.clear()
        await node({
            "messages": ["كان وأخواتها"],
            "context": context,
            "retried_sections": first["retried_sections"],
        })

        flow_calls = [p for p in prompts if "اكتب سير درس" in p]
        assert len(flow_calls) == 2, "لم يُعد الناقد كتابة قسم سير الدرس في التحضير الثاني"


class TestLessonPrepNodeIterationBudget:
    """اختبارات سقف iterations عند طلب الناقد لإعادة كتابة كل الأقسام."""

    @pytest.mark.asyncio
    async def test_final_plan_survives_retry_of_every_section(self) -> None:
        """يتحقق من أن الخطة النهائية تُنتج حتى مع إعادة كتابة كل الأقسام."""
        pending = [
            "basic_info",
            "objectives",
            "prior_knowledge",
            "materials",
            "lesson_flow",
            "assessment",
            "homework",
            "differentiation",
            "notes",
        ]

        async def call_model(task: str, system_prompt: str, temperature: float) -> str:
            _ = system_prompt, temperature
            if "قيّم جودة خطة الدرس" in task:
                if pending:
                    section = pending.pop(0)
                    return json.dumps({"score": 0.3, "section": section})
                return json.dumps({"score": 0.9, "section": None})
            return "محتوى تجريبي"

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=None,
        )

        result = await node({
            "messages": ["كان وأخواتها"],
            "context": {"subject": "اللغة العربية", "grade": "الثاني المتوسط"},
        })

        assert result["response"], "لم تُنتج خطة نهائية رغم اكتمال دورات التقييم"
        assert pending == [], "لم يطلب الناقد كل الأقسام"
        assert result["retried_sections"]


class TestLessonPrepNodeRetrievalFailure:
    """اختبارات سلوك العقدة عند فشل خدمة الاسترجاع."""

    @pytest.mark.asyncio
    async def test_retrieval_service_none(
        self,
        fake_call_model: FakeCallModel,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تعمل حتى عند عدم وجود خدمة استرجاع."""
        node = create_lesson_prep_node(
            call_model=fake_call_model,
            retrieval_service=None,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result

    @pytest.mark.asyncio
    async def test_retrieval_returns_chunks(
        self,
        base_context,
        base_messages,
    ) -> None:
        """يتحقق من أن العقدة تتعامل مع نتائج الاسترجاع غير الفارغة."""
        retrieval_service = FakeRetrievalService(
            chunks=[
                {
                    "text": "كان وأخواتها أفعال ناقصة تدخل على الجملة الاسمية",
                    "source_type": "document",
                }
            ]
        )
        call_model = FakeCallModel()

        node = create_lesson_prep_node(
            call_model=call_model,
            retrieval_service=retrieval_service,
        )

        input_state: dict[str, Any] = {
            "messages": base_messages,
            "context": base_context,
        }

        result = await node(input_state)

        assert "response" in result
        assert "sections" in result
        # المسترجع تم استدعاؤه
        assert len(call_model.calls) > 0
