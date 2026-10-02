# ملف الوكلاء (AGENTS.md) — EduAssist V2
الغرض: دستور المشروع. أي مطور (بشري أو وكيل ذكاء اصطناعي) يعمل على هذا المستودع يجب أن يقرأ هذا الملف أولًا ويلتزم به.
الحالة: ملزم (Binding) — لا يُخالَف إلا بقرار موثق في docs/adr/ (سجل القرارات المعمارية).
آخر تحديث: 2026-10-02

## 0. قواعد عامة للتعامل
### 0.1 اللغة والتوثيق
- كل تعليق في الكود، وكل رسالة إيداع (Commit Message)، وكل وثيقة، تُكتب بالعربية.
- كل مصطلح تقني إنجليزي يُكتب بالعربية أولًا ثم الإنجليزي بين قوسين:
  مثال: المعمارية النظيفة (Clean Architecture).
- أسماء المتغيرات والدوال والفئات تبقى بالإنجليزية (لأنها اصطلاحات برمجية)، لكن مع تعليق عربي يشرح الغرض.
- لا يُستخدم مصطلح إنجليزي في النقاش أو التوثيق دون ترجمته.

### 0.2 قواعد الالتزام بالمعمارية
- المعمارية ليست اختيارية. كل كود جديد يجب أن يلتزم بالطبقات والمنافذ والمحولات.
- أي انحراف عن المعمارية يُرفض في مراجعة الكود (Code Review).
- أي قرار معماري جديد يُوثَّق في docs/adr/NNNN-title.md.

## 1. المعمارية المعتمدة (Approved Architecture)
المشروع يتبنى مزيجًا من ثلاث معماريات:

| المعمارية (Architecture) | أين تظهر |
|---|---|
| المعمارية النظيفة (Clean Architecture) | فصل القلب (core/) عن التفاصيل (adapters/) |
| المعمارية السداسية (Hexagonal Architecture) | ports/ + adapters/ في كل مجال |
| المعمارية المدفوعة بالأحداث (Event-Driven Architecture) | البث عبر StreamEvent |

بالإضافة إلى:

| النمط (Pattern) | أين يظهر |
|---|---|
| خط الأنابيب (Pipeline) | retrieve → rerank → grade → generate |
| آلة الحالة (State Machine) | AgentState + Checkpointer |
| النموذج-العرض-المتحكم (MVC) | الواجهة (Next.js) |

### 1.1 المخطط العام
```text
Next.js (PWA, RTL)  ←REST/SSE→  FastAPI + LangGraph  ←→  Postgres 16 + pgvector
                                       │
                              ┌────────┴─────────┐
                         assistant/graph    knowledge (ports/adapters)
                              (LangGraph)         (embedder/retriever/reranker)
```
خدمتان فقط. أي خدمة ثالثة تحتاج مبررًا مكتوبًا في docs/adr/.

## 2. القواعد الملزمة (Binding Rules)
### القاعدة 1: لانغ غراف (LangGraph) هو اللاعب المركزي
- كل تنسيق (Orchestration) يجب أن يمر عبر الرسم (Graph).
- ممنوع أي تنسيق يدوي: حلقات (Loops)، شروط متفرقة، حالة موزعة على ملفات.
- ممنوع وجود مسارين للبث (Stream + Non-Stream). استخدم astream_events واحدًا.
- كل عقدة (Node) يجب أن تكون دالة نقية (Pure Function) قابلة للاختبار منفردة.

```python
# ✅ صحيح
async def analyze_node(state: AgentState) -> AgentState:
    ...

# ❌ مرفوض
class ManualRouter:
    def route(self, question):
        if "اشرح" in question:
            return self.explain_handler(question)
```

### القاعدة 2: خدمتان فقط
- المسموح: frontend/ (Next.js) + backend/ (FastAPI + LangGraph).
- ممنوع: أي خدمة ثالثة (NestJS، Redis، Elasticsearch، ...) دون:
  - قرار موثق في docs/adr/.
  - مبرر مكتوب (حجم، أداء، متطلبات).
  - خطة ترحيل واضحة.
- استثناء: قاعدة البيانات (PostgreSQL) والبنية التحتية (Docker) ليست "خدمات" بالمعنى المعماري.

### القاعدة 3: نموذج تضمين واحد (Single Embedding Model)
- نموذج تضمين واحد فقط (One Embedding Model) في قاعدة البيانات.
- اسم النموذج يُسجَّل في كل صف: chunks.embedding_model.
- تغيير النموذج = فهرس جديد + إعادة تضمين كاملة. لا استثناءات.
- ممنوع الجمع بين بُعدين (384 + 768) أو أكثر.
- ممنوع حراس التوافق (Compatibility Guards) من نوع legacy_v2.

```sql
-- ✅ صحيح
SELECT * FROM chunks WHERE embedding_model = 'bge-m3' AND teacher_id = $1;

-- ❌ مرفوض
SELECT * FROM chunks WHERE embedding_dim IN (384, 768);
```

### القاعدة 4: البحث داخل القاعدة (In-Database Search)
- ممنوع البحث الخطي بـ numpy أو أي بحث خارج القاعدة.
- استخدم <=> (مسافة جيب التمام) + HNSW داخل PostgreSQL.
- البحث الهجين (Hybrid Search) = Dense + BM25 داخل القاعدة، مدموجان بـ RRF.

```sql
-- ✅ صحيح
SELECT * FROM chunks
WHERE teacher_id = $1
ORDER BY embedding <=> $2
LIMIT 40;

-- ❌ مرفوض
for chunk in all_chunks:
    score = cosine_similarity(chunk.embedding, query.embedding)
```

### القاعدة 5: teacher_id إجباري من السطر الأول
- كل استعلام (Query)، وكل فهرسة (Indexing)، وكل ذاكرة (Memory) يجب أن تحتوي teacher_id.
- teacher_id مطلوب في أول ترحيل (First Migration).
- ممنوع أي جدول بدون teacher_id (إلا الجداول المرجعية العامة).

```python
# ✅ صحيح
async def retrieve(query: str, teacher_id: str):
    ...

# ❌ مرفوض
async def retrieve(query: str):
    ...
```

### القاعدة 6: لا تغيير دون اجتياز بوابات التقييم
ممنوع تغيير نموذج التضمين (Embedding)، أو التقطيع (Chunking)، أو الرسم (Graph) دون:
- تشغيل بوابة التقييم (Evaluation Gate) مقابل evaluation/baseline.json.
- تحقيق العتبات: recall@10 ≥ 0.85 و faithfulness ≥ 0.90.
- توثيق النتائج في evaluation/results/.

### القاعدة 7: البث (Streaming) عبر حدث واحد
- ممنوع وجود مسارين للبث (Stream + Non-Stream).
- استخدم astream_events واحدًا يغذي SSE (أو أي نقل آخر عبر المنفذ).
- كل الأحداث تُمرر عبر StreamEvent موحد.

### القاعدة 8: "لا يوجد في كتبك" سلوك مطلوب
عند ضعف الأدلة (Weak Evidence)، يجب أن يرد النظام:
- "لا يوجد في كتبك ما يجيب على هذا السؤال."
- هذا سلوك مطلوب، وليس فشلًا.
- ممنوع التخمين أو التوليد بدون دليل.

### القاعدة 9: فصل النقل عن الرسم (Realtime Ports & Adapters) ★ جديدة
- الرسم (Graph) لا يعرف شيئًا عن النقل (SSE / WebSocket / NestJS).
- البث يمر عبر منفذ (Port) باسم RealtimeTransport.
- محول (Adapter) واحد فقط يعمل الآن: SSEAdapter.
- ممنوع بناء أكثر من محول قبل الحاجة الفعلية.
- التبديل بين المحولات = متغير بيئة فقط (REALTIME_ADAPTER).

```python
# ✅ صحيح: الرسم لا يعرف النقل
event_stream = graph.astream_events(...)
await dispatcher.dispatch(event_stream)

# ❌ مرفوض: الرسم يعرف SSE
return StreamingResponse(graph.astream(...))
```

### القاعدة 10: لا تجريد مبكر (No Premature Abstraction)
- لا تبنِ واجهة (Port) إلا إذا كان هناك تنفيذان محتملان على الأقل.
- لا تبنِ محولًا (Adapter) إلا عند الحاجة الفعلية.
- مبدأ YAGNI: "لن تحتاجه" (You Aren't Gonna Need It).

## 3. الهيكل المعتمد (Approved Structure)
### 3.1 الهيكل العام
```text
eduassist-v2/
├── frontend/                          # Next.js (PWA, RTL)
│
├── backend/                           # FastAPI + LangGraph
│   ├── core/                          # القلب الثابت
│   │   ├── domain/                    # منطق الأعمال
│   │   │   ├── users/
│   │   │   ├── orders/
│   │   │   └── lessons/
│   │   └── ports/                     # الواجهات
│   │       ├── embedder.py
│   │       ├── retriever.py
│   │       ├── reranker.py
│   │       ├── llm.py
│   │       └── transport.py
│   │
│   ├── adapters/                      # التنفيذات المتغيرة
│   │   ├── llm/
│   │   ├── embedder/
│   │   ├── retriever/
│   │   ├── reranker/
│   │   └── db/
│   │
│   ├── orchestration/                 # التنسيق (LangGraph)
│   │   ├── graphs/
│   │   │   ├── main.py
│   │   │   ├── rag_subgraph.py
│   │   │   └── generation_subgraph.py
│   │   ├── nodes/
│   │   ├── state/
│   │   └── events.py                  # StreamEvent
│   │
│   ├── realtime/                      # ★ طبقة البث
│   │   ├── contracts/
│   │   ├── ports/
│   │   ├── adapters/
│   │   ├── dispatcher.py
│   │   └── factory.py
│   │
│   ├── api/                           # الواجهة (REST/SSE)
│   │   ├── routes/
│   │   ├── deps.py
│   │   └── schemas/
│   │
│   ├── memory/                        # ذاكرة المدرس
│   │
│   ├── db/                            # قاعدة البيانات
│   │   ├── models/
│   │   ├── migrations/                # Alembic
│   │   └── session.py
│   │
│   ├── prompts/                       # مكتبة البرومبتات
│   ├── config/                        # الإعدادات
│   └── main.py                        # نقطة الدخول
│
├── packages/                          # مكتبات مشتركة
│   ├── arabic-text/                   # تطبيع عربي
│   └── shared-types/                  # أنواع مشتركة
│
├── data/                              # البيانات
│   ├── content/                       # المحتوى التعليمي
│   └── golden/                        # المجموعة الذهبية
│
├── evaluation/                        # ★ مشروع مستقل
│   ├── bakeoff/
│   ├── harness/
│   ├── baseline.json
│   └── results/
│
├── infra/                             # البنية التحتية
│   ├── docker/
│   └── ci/
│
├── docs/                              # الوثائق
│   ├── ARCHITECTURE.md
│   ├── adr/                           # سجل القرارات
│   └── glossary.md                    # المصطلحات
│
├── AGENTS.md                          # هذا الملف
├── README.md
└── docker-compose.yml                 # خدمتان فقط
```

### 3.2 قواعد الهيكل
- core/ لا يعتمد على أي شيء خارجي. لا استيراد من adapters/ أو orchestration/.
- adapters/ تعتمد على core/ports/ فقط.
- orchestration/ تعتمد على core/ وتمرر adapters/ عبر حقن التبعيات (Dependency Injection).
- api/ رقيقة جدًا. لا منطق أعمال، فقط ترجمة HTTP ↔ الرسم.
- realtime/ مستقلة تمامًا. لا تعرف عن الرسم سوى StreamEvent.

### 3.3 قاعدة الاعتماديات (Dependency Rule)
```text
api/ ─────────► orchestration/ ─────────► core/
                    │                       ▲
                    └──► adapters/ ─────────┘
                            │
                            └──► core/ports/
```
الاعتماديات تتجه دائمًا من الخارج إلى الداخل.

## 4. المصطلحات المعتمدة (Approved Glossary)
أي مصطلح جديد يجب أن يُضاف إلى docs/glossary.md أولًا، ثم يُستخدم.

### 4.1 المعمارية
| العربي | الإنجليزي |
|---|---|
| المعمارية | Architecture |
| الهيكل | Structure |
| المعمارية النظيفة | Clean Architecture |
| المعمارية السداسية | Hexagonal Architecture |
| المنافذ والمحولات | Ports and Adapters |
| المعمارية المدفوعة بالأحداث | Event-Driven Architecture |
| المعمارية الطبقية | Layered Architecture |
| التصميم المدفوع بالمجال | Domain-Driven Design (DDD) |
| خط الأنابيب | Pipeline |
| آلة الحالة | State Machine |

### 4.2 الذكاء الاصطناعي
| العربي | الإنجليزي |
|---|---|
| نموذج اللغة الكبير | Large Language Model (LLM) |
| نموذج التضمين | Embedding Model |
| إعادة الترتيب | Reranking |
| الاسترجاع المعزز بالتوليد | Retrieval-Augmented Generation (RAG) |
| البحث الهجين | Hybrid Search |
| دمج ترتيب المعاملة بالمثل | Reciprocal Rank Fusion (RRF) |
| الفهرسة | Indexing |
| التقطيع | Chunking |
| الهلوسة | Hallucination |
| الاستشهاد | Citation |
| الأمانة | Faithfulness |

### 4.3 لانغ غراف (LangGraph)
| العربي | الإنجليزي |
|---|---|
| الرسم | Graph |
| العقدة | Node |
| الحافة | Edge |
| الحالة | State |
| نقطة التفتيش | Checkpointer |
| البث غير المتزامن | Async Streaming |
| الأحداث | Events |

### 4.4 البث والنقل
| العربي | الإنجليزي |
|---|---|
| البث | Streaming |
| النقل | Transport |
| المنفذ | Port |
| المحول | Adapter |
| العقد | Contract |
| حدث البث | Stream Event |
| أحداث مرسلة من الخادم | Server-Sent Events (SSE) |
| مقبس الويب | WebSocket |
| الموزع | Dispatcher |
| المصنع | Factory |

### 4.5 قاعدة البيانات
| العربي | الإنجليزي |
|---|---|
| الترحيلات | Migrations |
| فهرس HNSW | HNSW Index |
| مسافة جيب التمام | Cosine Distance |
| البحث المتجهي | Vector Search |
| البحث النصي | Full-Text Search |
| الحاجز | Guard |
| الدين التقني | Technical Debt |

## 5. سير العمل (Workflow)
### 5.1 قبل البدء بأي مهمة
- اقرأ AGENTS.md (هذا الملف).
- اقرأ docs/ARCHITECTURE.md.
- راجع docs/adr/ للقرارات السابقة.
- تأكد أن مهمتك لا تخالف أي قاعدة ملزمة.

### 5.2 أثناء التطوير
- اختبار أولًا (Test First) عند الإمكان.
- دالة نقية (Pure Function) لكل عقدة (Node).
- منفذ (Port) لكل تبعية خارجية.
- توثيق عربي لكل دالة عامة.
- رسالة إيداع (Commit Message) بالعربية، بصيغة:

```text
نوع: وصف مختصر

تفاصيل إضافية إن لزم.
```
الأنواع: إضافة، إصلاح، إعادة هيكلة، توثيق، اختبار، أداء.

### 5.3 قبل الإيداع (Commit)
- □ كل الاختبارات تمر.
- □ لا انحراف عن المعمارية.
- □ لا مصطلحات إنجليزية غير مترجمة.
- □ رسالة الإيداع بالعربية.
- □ إذا كان هناك تغيير معماري: أضف ADR.

### 5.4 قبل الدمج (Merge)
- □ مراجعة كود (Code Review) من مطور آخر (أو وكيل آخر).
- □ بوابات التقييم (Evaluation Gates) تمر إن كان التغيير يمس الرسم أو التضمين.
- □ لا دين تقني جديد.

## 6. بوابات التقييم (Evaluation Gates)
### 6.1 العتبات الملزمة
| المقياس (Metric) | العتبة (Threshold) |
|---|---|
| استدعاء@10 (Recall@10) | ≥ 0.85 |
| الأمانة (Faithfulness) | ≥ 0.90 |
| زمن الاستجابة (Latency) | ≤ 2× زمن V1 |

### 6.2 متى تُشغَّل؟
- عند أي تغيير في: نموذج التضمين، التقطيع، الرسم، البرومبتات.
- في التكامل المستمر (CI) قبل الدمج إلى main.
- أسبوعيًا على main لرصد الانحدار (Regression).

### 6.3 أين تُخزَّن النتائج؟
- evaluation/baseline.json — خط الأساس الثابت.
- evaluation/results/YYYY-MM-DD-*.json — نتائج كل تشغيل.

## 7. المحظورات (Forbidden Practices)
| المحظور | السبب |
|---|---|
| التنسيق اليدوي خارج لانغ غراف | القاعدة 1 |
| خدمة ثالثة بلا قرار موثق | القاعدة 2 |
| نموذجا تضمين في نفس الوقت | القاعدة 3 |
| البحث الخطي بـ numpy | القاعدة 4 |
| استعلام بدون teacher_id | القاعدة 5 |
| تغيير بلا تقييم | القاعدة 6 |
| مسارا بث منفصلان | القاعدة 7 |
| التخمين عند ضعف الأدلة | القاعدة 8 |
| الرسم يعرف النقل | القاعدة 9 |
| تجريد مبكر | القاعدة 10 |
| مصطلح إنجليزي غير مترجم | القاعدة 0.1 |
| كود بلا اختبار | سير العمل |
| دين تقني جديد | سير العمل |

## 8. سجل القرارات المعمارية (ADRs)
كل قرار معماري يُوثَّق في docs/adr/NNNN-title.md بالصيغة:

```markdown
# ADR-0001: استخدام SSE كنقل أولي للبث

## الحالة
معتمد

## السياق
...

## القرار
...

## البدائل المدروسة
- WebSocket في FastAPI: ...
- NestJS: ...

## النتائج
- إيجابيات: ...
- سلبيات: ...

## خطة الترحيل
...
```

قرارات أولية مطلوبة:
- ADR-0001: اعتماد لانغ غراف (LangGraph) كمحرك تنسيق.
- ADR-0002: اعتماد نموذج التضمين بعد المقارنة المخبرية (Bakeoff).
- ADR-0003: اعتماد SSE كنقل أولي + المنافذ والمحولات للبث.
- ADR-0004: اعتماد المعمارية النظيفة + السداسية.
- ADR-0005: تقاعد خدمة نست جي إس (NestJS).

## 9. خارطة الطريق (Roadmap)
| المرحلة | العمل | بوابة القبول |
|---|---|---|
| 0. التأسيس | تجميد V1، المجموعة الذهبية، Bakeoff | قرار نموذج موثق بأرقام |
| 1. قلب الاسترجاع | Alembic، المخطط الجديد، المنافذ والمحولات | recall@10 ≥ 0.85 |
| 2. قلب الرسم | AgentState، الرسم الرئيسي، Checkpointer، البث | الواجهة تعمل بدون تعديل + faithfulness ≥ 0.90 |
| 3. النوايا الكاملة | التوليد المنظم، pedagogy، grammar، clarifier | تكافؤ وظيفي مع V1 |
| 4. الدمج والتقاعد | نقل الذاكرة، إيقاف realtime القديم، CI | خدمتان فقط + كل الاختبارات خضراء |

## 10. جهات الاتصال والمراجع
- المستودع: eduassist-v2
- النسخة المجمدة: v1 @ 674130bf
- الوثائق:
  - docs/ARCHITECTURE.md — المخطط المعماري الكامل.
  - docs/adr/ — سجل القرارات.
  - docs/glossary.md — المصطلحات.
  - evaluation/baseline.json — خط الأساس.
- الاجتماع الدوري: أسبوعيًا لمراجعة ADRs الجديدة.

## 11. القسم الأخير: تعهد الوكيل (Agent Pledge)
أنا، أي وكيل (بشري أو ذكاء اصطناعي) أعمل على هذا المستودع، أتعهد بـ:
- قراءة هذا الملف قبل أي عمل.
- الالتزام بالمعمارية والقواعد الملزمة.
- كتابة كل شيء بالعربية، وترجمة كل مصطلح إنجليزي.
- توثيق كل قرار معماري في ADR.
- عدم إضافة دين تقني.
- اختبار كل شيء قبل الإيداع.
- احترام عمل الآخرين، وعدم تدمير ما بنوه.
- إذا وجدت قاعدة خاطئة، لا تخالفها بصمت، بل افتح ADR لتغييرها.

هذا ليس ملف إرشادي، بل عقد ملزم.
