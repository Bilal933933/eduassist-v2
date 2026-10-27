# خطة: زر حذف المحادثة (واجهة + باك إند)

> **الحالة:** جاهزة للتنفيذ — لم يُنفَّذ منها شيء بعد.
> **التاريخ:** 2026-10-27.
> **النطاق:** مسار حذف واحد في الخلفية + زر ونافذة تأكيد في الشريط الجانبي.
> **مرجع الواجهة:** ADR-0015 (رموز الثيم) — أي صنف جديد يلتزم برموز الثيم.

## 0) ملخص تنفيذي للوكيل المنفّذ
- نفّذ الملفات في الجدول (القسم 4) **بالترتيب**، ولا تخرج عنها.
- لا تلمس: `components/theme-toggle.tsx`, `app/providers.tsx`, `app/globals.css`,
  `components/ui/*`, `launcher-dev-*.cjs`, `launcher-dev-web.js`, `.opencode/`.
- لا مكتبات جديدة، ولا هجرة مخطط جديدة، ولا تغيير في `conversations.status`.
- الحذف **نهائي** (hard delete) مع نافذة تأكيد، والرسائل تُحذف بـ`ON DELETE CASCADE`.
- معيار القبول: `uv run pytest -q` يمر، `npx tsc --noEmit` = 0، `npx eslint .` = 0 خطأ،
  والتحقق اليدوي في القسم 7.

---

## 1) التحليل — الحالة الحالية

| الطبقة | الموجود | الناقص |
|---|---|---|
| `api/routes/chat.py` | `POST /api/conversations`، `GET /api/conversations`، `GET /api/conversations/{id}/messages`، `POST /api/chat` | لا يوجد أي `DELETE` |
| `services/conversation_service.py` | `list_conversations`, `get_conversation_messages` | لا دالة حذف |
| `db/repositories/conversation_repository.py` | `create`, `get_owned`, `list_owned_page` | لا `delete` |
| قاعدة البيانات | `messages.conversation_id` → `conversations(id, user_id)` مع **`ON DELETE CASCADE`** (مُتحقَّق في `0003_create_messages.py`) | لا حاجة لتعديل مخطط |
| `lib/api.ts` | `createConversationRequest`, `listConversationsRequest`, … | لا `deleteConversationRequest` |
| `use-conversations.ts` | `useConversations`, `useCreateConversation`, `useConversation` | لا `useDeleteConversation` |
| `conversation-list.tsx` | صف = `<Link>` واحد يغطي كامل الصف | لا مكان لزر (عنصر تفاعلي داخل رابط = HTML غير صالح) |

**قيود تقنية يجب على المنفّذ معرفتها:**
1. `request()` في `lib/api.ts` يرمي استثناءً إذا كان `body.data === undefined`
   → **لا يجوز إرجاع 204 بجسم فارغ**؛ نُرجع `200` مع `{ "deleted": true }`.
2. CORS في `main.py` يستخدم `allow_methods=["*"]` → `DELETE` مدعوم بلا تعديل.
3. حماية CSRF = `require_trusted_origin` (نفس `POST /api/conversations`).
4. مكوّنات `components/ui` مبنية على **Base UI** → `render={<Button/>}` وليس `asChild`.
5. `AlertDialog` و`Button` و`Badge` جاهزة في `components/ui` — لا حاجة لمكتبات جديدة.
6. `conversations.status` يسمح فقط بـ`active|archived` (CheckConstraint) → الحذف حقيقي
   (hard delete)؛ "المحذوف" كحالة يحتاج هجرة + فلترة في كل الاستعلامات.
7. WebSocket: `realtime/routes.py` يغلق بـ`4404` لأي محادثة غير مملوكة → بعد الحذف
   يفشل الاتصال تلقائيًا (سلوك صحيح بلا تعديل).
8. رد متأخر من الرسم بعد الحذف: `_save_assistant_reply` يرمي
   `ConversationNotFoundError` و`run_chat` يلتقطه ويُرسل `failed` — لا تعطُّل ولا
   تسريب بيانات، فلا حاجة لمعالجة إضافية.
9. نقاط لانغ غراف تُقلَّم بعد كل رد (`ADR-0014`)، ويُستحسن `adelete_thread` عند الحذف
   (الدالة موجودة في `AsyncPostgresSaver` — تم التحقق).

---

## 2) التصميم

**التدفق:**
```text
زر الحذف (صف القائمة) → AlertDialog تأكيد → useDeleteConversation
   → DELETE /api/conversations/{id}  (cookie + Origin)
      → get_current_user (401) → require_trusted_origin (403)
      → conversation_service.delete_conversation
         → ConversationRepository.delete_owned (WHERE id AND user_id)
            → 0 صفوف ⇒ ConversationNotFoundError (404)
            → صف واحد ⇒ CASCADE يحذف الرسائل
         → commit
      → (best-effort) adelete_thread لنقاط الرسم
   → 200 { success: true, data: { deleted: true } }
→ الواجهة: removeQueries(messages) + invalidate(conversations) + toast
→ إن كانت المحادثة مفتوحة: router.replace("/chat/new") + إغلاق الشيت
```

**قرارات مثبَّتة (لا تُناقش أثناء التنفيذ):**
- حذف نهائي، بلا سلة محذوفات، مع نافذة تأكيد.
- الزر في صف الشريط الجانبي فقط (لا في هيدر المحادثة — خارج النطاق).
- إبطال الكاش بدل التحديث المتفائل (أبسط وأقل أخطاء).

---

## 3) عقد الـ API

```text
DELETE /api/conversations/{conversation_id}
Cookie: <AUTH_COOKIE_NAME>   Origin: <trusted>

200 → { "success": true, "data": { "deleted": true } }
401 → { "success": false, "error": { "code": "SESSION_INVALID", ... } }
403 → { "success": false, "error": { "code": "ORIGIN_NOT_ALLOWED", ... } }
404 → { "success": false, "error": { "code": "CONVERSATION_NOT_FOUND",
                                     "message": "المحادثة غير موجودة." } }
422 → معرّف ليس UUID
```
> `404` تُستخدم أيضًا للمحادثة المملوكة لمستخدم آخر (لا نكشف وجودها) — متسق مع
> `GET /api/conversations/{id}/messages`.

---

## 4) الهيكلة

| # | الملف | النوع | الدور |
|---|---|---|---|
| 1 | `backend/db/repositories/conversation_repository.py` | تعديل | `delete_owned()` — حذف مشروط بالمالك عبر SQL bulk |
| 2 | `backend/services/conversation_service.py` | تعديل | `delete_conversation()` — الملكية + الخطأ + commit |
| 3 | `backend/db/checkpointer.py` | تعديل | `delete_thread_checkpoints()` — تنظيف نقاط الرسم (best-effort) |
| 4 | `backend/api/schemas/chat.py` | تعديل | `ConversationDeleted` |
| 5 | `backend/api/routes/chat.py` | تعديل | مسار `DELETE` |
| 6 | `backend/tests/unit/test_conversation_service.py` | **جديد** | وحدة: ملكية/غائبة/commit |
| 7 | `backend/tests/integration/test_postgres_conversations.py` | تعديل | تكامل: الحذف يزيل الرسائل (CASCADE) |
| 8 | `frontend/lib/api.ts` | تعديل | `deleteConversationRequest()` |
| 9 | `frontend/features/conversations/hooks/use-conversations.ts` | تعديل | `useDeleteConversation()` |
| 10 | `frontend/features/conversations/components/conversation-list.tsx` | تعديل | إعادة هيكلة الصف + زر + `AlertDialog` |

---

## 5) شرح الملفات والدوال

### `conversation_repository.py`
```python
async def delete_owned(self, conversation_id: UUID, user_id: UUID) -> bool:
    """حذف محادثة مملوكة؛ يعيد True إن حُذف صف واحد."""
```
- `sqlalchemy.delete(Conversation).where(id==…, user_id==…)` + `await session.execute(...)`
- إرجاع `bool(result.rowcount)`
- **لا** تحمّل الرسائل: `ON DELETE CASCADE` في القاعدة يتولاها.
- الاستيراد: أضف `delete` إلى `from sqlalchemy import ...`

### `conversation_service.py`
```python
async def delete_conversation(session: AsyncSession, user_id: UUID, conversation_id: UUID) -> None:
    """حذف محادثة يملكها المستخدم أو رفع ConversationNotFoundError."""
```
- `deleted = await ConversationRepository(session).delete_owned(...)`
- `if not deleted: raise ConversationNotFoundError`
- `await session.commit()`

### `db/checkpointer.py`
```python
async def delete_thread_checkpoints(checkpointer: object | None, thread_id: str) -> None:
    """حذف نقاط الرسم الخاصة بخيط المحادثة (تجاهل الفشل)."""
```
- `if not hasattr(checkpointer, "adelete_thread"): return`
- `try: await checkpointer.adelete_thread(thread_id)` / `except Exception: logger.warning(...)`
- نفس أسلوب `prune_thread_checkpoints` الموجود (تعليق عربي، تسجيل تحذير فقط).

### `api/schemas/chat.py`
```python
class ConversationDeleted(BaseModel):
    """نتيجة حذف المحادثة."""
    deleted: bool
```

### `api/routes/chat.py`
```python
@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse[ConversationDeleted])
async def delete_owned_conversation(
    conversation_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_db),          # noqa: B008
    user: User = Depends(get_current_user),           # noqa: B008
    _: None = Depends(require_trusted_origin),        # noqa: B008
) -> dict:
```
- استدعاء `delete_conversation(session, user.id, conversation_id)`
- ثم best-effort:
  `await delete_thread_checkpoints(getattr(http_request.app.state.graph, "checkpointer", None), scoped_thread_id(str(user.id), str(conversation_id)))`
  — استيراد `scoped_thread_id` من `graph`
- `return ok(ConversationDeleted(deleted=True).model_dump(mode="json"))`

### `lib/api.ts`
```ts
export function deleteConversationRequest(conversationId: string) {
  return request<{ deleted: boolean }>(`/api/conversations/${conversationId}`, {
    method: "DELETE",
  });
}
```

### `use-conversations.ts`
```ts
export function useDeleteConversation() {
  // useMutation + useQueryClient + useRouter + usePathname
}
```
- `mutationFn: (conversationId: string) => deleteConversationRequest(conversationId)`
- `onSuccess(_, conversationId)`:
  - `queryClient.removeQueries({ queryKey: queryKeys.messages(conversationId) })`
  - `queryClient.invalidateQueries({ queryKey: queryKeys.conversations })`
  - `if (pathname === \`/chat/${conversationId}\`) router.replace("/chat/new")`
- `onError(error)`: إن كان `RequestFailedError.code === "HTTP_404"` اعتبره نجاحًا
  (نفّذ نفس خطوات `onSuccess`)، غير ذلك `toast.error(error.message)`.

### `conversation-list.tsx`
- إعادة هيكلة الصف: `<div class="group flex items-center …">` يحتوي
  `<Link class="min-w-0 flex-1 …">` + زر الحذف كشقيق (يمنع تداخل عناصر تفاعلية).
- زر: `Button variant="ghost" size="icon"` + `Trash2` من `lucide-react`،
  `aria-label={\`حذف ${title}\`}`، إظهار عند التحويم/التركيز على الشاشات الكبيرة فقط:
  `md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:group-focus-within:opacity-100`.
- `AlertDialog` + `AlertDialogTrigger render={<Button … />}`:
  - `AlertDialogTitle`: «حذف المحادثة؟»
  - `AlertDialogDescription`: «سيُحذف سجل المحادثة ورسائلها نهائيًا، ولا يمكن التراجع.»
  - `AlertDialogCancel`: «إلغاء» · `AlertDialogAction` (destructive): «حذف»
  - `onClick` على `AlertDialogAction` → `await deleteConversation.mutateAsync(id)` ثم
    `toast.success("تم حذف المحادثة.")` و`onSelect?.()`.
- حالة الانتظار: `disabled={deleteConversation.isPending}` + عند
  `isPending && variables === conversation.id` → نص «جارٍ الحذف...».
- ألوان برموز الثيم (ADR-0015):
  `text-muted-foreground hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400`
  — نفس نمط زر الخروج الموجود.
- أزل الاستيراد غير المستخدم `Separator` (تحذير ESLint قائم، تنظيف داخل ملف تعدله).

---

## 6) الاختبارات المطلوبة

**`tests/unit/test_conversation_service.py`** (جديد، بلا قاعدة بيانات — Mock):
| الاختبار | المخرجات المتوقعة |
|---|---|
| `delete_owned` يعيد `True` | لا استثناء + `session.commit` نُودي مرة |
| `delete_owned` يعيد `False` | `ConversationNotFoundError` + `commit` **لم** يُنادَ |

**`tests/integration/test_postgres_conversations.py`** (تكملة):
| الاختبار | المتوقع |
|---|---|
| حذف محادثة فيها رسائل | المحادثة والرسائل = 0 صفوف |
| حذف محادثة مستخدم آخر | `False` / `CONVERSATION_NOT_FOUND` والمحادثة باقية |

**`tests/integration/test_chat_api.py`** (نمط `_override_auth` الموجود):
| الاختبار | المتوقع |
|---|---|
| `DELETE` بجلسة صحيحة | `200` + `{"success": true, "data": {"deleted": true}}` |
| `DELETE` بلا مصادقة | `401` + `SESSION_INVALID` |
| `DELETE` لمحادثة غير مملوكة | `404` + `CONVERSATION_NOT_FOUND` |

---

## 7) ترتيب التنفيذ وأوامر التحقق

```text
1. conversation_repository.delete_owned
2. conversation_service.delete_conversation
3. checkpointer.delete_thread_checkpoints
4. schemas: ConversationDeleted
5. route: DELETE /api/conversations/{id}
6. tests (unit + integration)  →  cd backend && uv run pytest -q
7. lib/api.ts: deleteConversationRequest
8. use-conversations.ts: useDeleteConversation
9. conversation-list.tsx: الصف + AlertDialog
10. cd frontend && npx tsc --noEmit && npx eslint .
11. تحقق يدوي في المتصفح
```

```powershell
cd E:\heard\ai-grammar-tutor-v2\backend  ; uv run pytest -q
cd E:\heard\ai-grammar-tutor-v2\frontend ; npx tsc --noEmit ; npx eslint .
```

**التحقق اليدوي** (الخوادم عبر لوحة Heard: `dev-grammar2-web` على 3005،
`dev-grammar2-api` على 5002):
1. حذف محادثة غير مفتوحة → تختفي من القائمة فورًا + toast نجاح.
2. حذف المحادثة المفتوحة حاليًا → الانتقال إلى `/chat/new` بلا أخطاء كونسول.
3. إلغاء في النافذة → لا حذف ولا طلب شبكة.
4. فتح رابط المحادثة بعد الحذف → شاشة «محادثة غير موجودة» القائمة، لا انهيار.
5. الوضع الداكن: الزر والنافذة بلا ألوان ثابتة بيضاء.
6. الشبكة: `DELETE` مرة واحدة، `200`، ثم `GET /api/conversations`.

---

## 8) حالات الحافة (مغطاة بالتصميم)

| الحالة | السلوك |
|---|---|
| حذف أثناء رد المساعد قيد المعالجة | `_save_assistant_reply` يفشل بـ`ConversationNotFoundError` → `run_chat` يلتقطه ويرسل `failed`؛ لا تعطُّل |
| تبويب آخر يعرض المحادثة | السوكِت يُغلق بـ`4404` عند إعادة الاتصال؛ لا حاجة لبث حذف |
| `404` بسبب حذف مسبق (نقر مزدوج) | الواجهة تعتبره نجاحًا وتُبطل الكاش |
| صفوف checkpoints يتيمة | `adelete_thread` best-effort؛ الفشل لا يُفشل الطلب |
| الصفحات القديمة (`next_cursor`) | الإبطال يعيد الصفحة الأولى فقط — مقبول (نفس سلوك الإنشاء) |

---

## 9) Definition of Done

- [ ] `DELETE /api/conversations/{id}` يعمل: `200` للمالك، `404` لغيره، `401` بلا جلسة،
      `403` لمصدر غير موثوق.
- [ ] الرسائل تُحذف تلقائيًا (لا حذف يدوي ولا هجرة جديدة).
- [ ] `uv run pytest -q` يمر بلا فشل.
- [ ] `npx tsc --noEmit` = 0 · `npx eslint .` = 0 خطأ.
- [ ] زر الحذف يعمل في الوضعين الفاتح والداكن، بلوحة المفاتيح، وبقارئ شاشة
      (`aria-label` + عنوان/وصف للنافذة).
- [ ] لا تعديل في ملفات خارج الجدول في القسم 4.
