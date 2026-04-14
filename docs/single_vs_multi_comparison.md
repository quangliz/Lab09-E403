# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 9
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | N/A | 0.535 | N/A | |
| Avg latency (ms) | N/A | 5569 | N/A | |
| Abstain rate (%) | N/A | 6.7% (1/15) | N/A | % câu trả về "không đủ info" (câu q09) |
| Multi-hop accuracy | N/A | 0% (0/2) | N/A | % câu multi-hop trả lời đúng (q13, q15) |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | 30 phút | 5 phút | N/A | Thời gian tìm ra 1 bug |

> **Lưu ý:** Kết quả lab 8 là N/A. Lý do nhìn file eval của lab 8 không có sự tương đồng về metric (tập trung vào RAG tuning - chunking/hybrid/rerank thay vì agent routing/abstain), do đó không có cơ sở dữ liệu map 1-1 để so sánh trực tiếp các metric này.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | N/A | Cao (đáp ứng đúng expected_answer) |
| Latency | N/A (thường < 2s) | ~4000ms - 5000ms |
| Observation | Nhanh nhưng dễ bị phân tâm nếu prompt quá dài bao gồm nhiều rule. | Chậm hơn do tốn thêm 1 nhịp gọi LLM ở Supervisor trước khi vào Worker. |

**Kết luận:** Multi-agent KHÔNG có cải thiện đáng kể về độ chính xác đối với câu hỏi đơn giản, ngược lại còn làm tăng độ trễ (latency). Tuy nhiên, nó giúp duy trì cấu trúc module tốt.

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | N/A | Thấp (0%) |
| Routing visible? | ✗ | ✓ |
| Observation | Thường dễ bị trôi thông tin hoặc chỉ bám vào 1 document nếu chunk relevance không đều. | Supervisor định tuyến đúng, nhưng luồng đồ thị tĩnh (hardcode) và worker không có khả năng tự gọi tiếp các MCP tool (như check_access_permission) khiến đáp án bị thiếu context quan trọng. |

**Kết luận:** Multi-agent bộc lộ điểm yếu khi sử dụng "Static Routing". Việc hardcode luồng đi (Supervisor -> 1 Worker duy nhất -> Synthesis) khiến hệ thống không thể xử lý tốt các câu multi-hop cần thông tin từ nhiều nguồn và công cụ khác nhau. Cần chuyển sang "Dynamic Routing" để các worker tương tác chéo.

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | N/A | 100% đúng (câu q09) |
| Hallucination cases | N/A (thường dễ bị hallucinate bịa ra câu trả lời) | 0 |
| Observation | LLM có xu hướng "chiều lòng" user, dễ bịa nếu không cấm gắt. | Synthesis worker được cô lập hoàn toàn với một prompt cực kỳ strict về grounding. |

**Kết luận:** Multi-agent giải quyết bài toán Abstain triệt để hơn nhờ việc cô lập Synthesis Worker chỉ làm đúng 1 nhiệm vụ: "Nếu có chunk thì tổng hợp, không có chunk thì từ chối".

_________________

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 30 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 5 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_
Khi trace câu hỏi multi-hop q15 bị lỗi thiếu context, nhóm chỉ cần mở file trace `.json` và nhìn vào mảng `workers_called`. Nhóm phát hiện ra Supervisor đã gọi `human_review`, nhưng sau đó luồng Graph lại tự động chạy tiếp sang `retrieval_worker` thay vì `policy_tool_worker`. Việc khoanh vùng lỗi nằm ở luồng đồ thị diễn ra chưa tới 3 phút mà không cần phải debug từng dòng code prompt hay embedding.

_________________

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:**
Kiến trúc Supervisor-Worker ở Day 09 cực kỳ dễ mở rộng. Bằng chứng là khi thêm MCP server (HTTP API) ở Sprint 3, chúng ta hoàn toàn không phải đụng chạm gì đến Retrieval Worker hay Synthesis Worker, thậm chí Supervisor cũng không cần biết MCP là gì. Mọi thứ được gói gọn trong Policy Tool Worker.

_________________

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls (Supervisor + Synthesis) |
| Complex query | 1 LLM call | 3 LLM calls (Supervisor + Policy + Synthesis) |
| MCP tool call | N/A | 1 HTTP call (thêm 1-2s latency) |

**Nhận xét về cost-benefit:**
Mô hình Day 09 đánh đổi Cost (gấp đôi đến gấp ba số lượng token input/output do gọi nhiều LLM) và Latency (trung bình 5.5s so với 1-2s của Day 08) để lấy **Sự ổn định, Độ chính xác (nhất là abstain) và Khả năng bảo trì**. Đây là sự đánh đổi xứng đáng cho các hệ thống Enterprise.

_________________

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. **Bảo trì và Gỡ lỗi (Debuggability):** Phân tách logic rõ ràng, trace JSON lưu trữ chi tiết từng input/output của mỗi step, dễ dàng xác định nguyên nhân khi hệ thống sai.
2. **Ngăn chặn Hallucination (Abstain):** Chuyên biệt hóa LLM cho khâu Synthesis với bộ rules cực kỳ gắt gao giúp hệ thống từ chối trả lời chính xác khi không có đủ context.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. **Chi phí và Độ trễ (Cost & Latency):** Phải đi qua nhiều node (Routing -> Action -> Synthesis), khiến thời gian chờ lâu hơn đáng kể và tốn kém tài nguyên API (token) hơn nhiều so với việc chỉ gom tất cả vào một LLM call duy nhất.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi ứng dụng yêu cầu tính thời gian thực (Real-time) cực cao (ví dụ: Chatbot CSKH trực tuyến cần trả lời dưới 1s), hoặc bài toán có domain quá hẹp, đơn giản, chỉ cần truy vấn DB cơ bản mà không có rẽ nhánh logic nghiệp vụ (Policy/Approval).

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Chuyển đổi Graph từ luồng tĩnh (Static Routing: if/else hardcode) sang luồng động (Dynamic Graph / Multi-Agent Orchestration thực thụ). Nghĩa là Supervisor không chỉ route 1 lần rồi thôi, mà có thể lên Plan gọi song song nhiều Worker, hoặc Worker làm xong có thể trả State về cho Supervisor để đánh giá lại xem đã đủ thông tin chưa trước khi chuyển sang Synthesis.