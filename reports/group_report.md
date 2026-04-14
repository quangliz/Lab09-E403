# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** AI Wizards  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Văn Quang | Supervisor Owner / Worker Owner | - |
| Nguyễn Mạnh Dũng | MCP Owner / Trace & Docs Owner | - |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/quangliz/Lab09-E403.git  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

Hệ thống nhóm xây dựng theo mô hình Supervisor-Worker với 1 supervisor và 3 workers: retrieval, policy_tool, synthesis. Supervisor dùng keyword-based routing để quyết định worker dựa trên task type.

Hệ thống tổng quan: Pipeline bắt đầu từ supervisor nhận task, route đến worker phù hợp, workers xử lý và trả về, cuối cùng synthesis tổng hợp answer.

Routing logic cốt lõi: Supervisor check keywords như "SLA", "policy", "ticket" để route. Nếu không match, dùng fallback.

MCP tools đã tích hợp: search_kb, get_ticket_info, check_access_permission, create_ticket. Ví dụ trace run_20260414_170010.json: mcp_tools_used: [], nhưng trong policy questions, get_ticket_info được gọi.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

Quyết định: Chọn keyword-based routing thay vì LLM classifier cho supervisor.

Bối cảnh vấn đề: Lab 4 giờ, cần routing nhanh và chính xác cho 5 categories, nhưng LLM chậm.

Các phương án đã cân nhắc:

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Keyword matching | Nhanh (~5ms), dễ implement | Có thể miss edge cases |
| LLM classifier | Chính xác cao, handle complex | Chậm (~800ms), cần API key |

Phương án đã chọn và lý do: Keyword matching vì phù hợp lab, đủ tốt cho categories đơn giản.

Bằng chứng từ trace/code: Trong `graph.py`, `supervisor_node` dùng keyword routing theo nhóm câu hỏi. Trace `run_20260414_170010.json` ghi rõ `route_reason` liên quan SLA/P1 và route đến `retrieval_worker`, với `latency_ms = 5415`.

---

## 3. Kết quả grading questions (150–200 từ)

Kết quả tổng quan từ `artifacts/grading_run.jsonl`: pipeline trả lời đủ 10/10 câu grading, confidence trung bình xấp xỉ 0.56 và latency dao động khoảng 3170–9466ms.

Câu pipeline xử lý tốt nhất: gq05 — Route đúng đến retrieval cho tình huống SLA P1, confidence 0.68, latency 3354ms.

Câu pipeline fail hoặc partial: gq09 — Đây là câu multi-hop (SLA + cấp quyền tạm thời), trace có HITL (`hitl_triggered = true`) và kết quả mới trả lời được một phần yêu cầu.

Câu gq07 (abstain): Hệ thống abstain hợp lý với confidence 0.30 khi không đủ bằng chứng về mức phạt tài chính cụ thể trong tài liệu nội bộ.

Câu gq09 (multi-hop khó nhất): Trace cho thấy chuỗi `human_review -> retrieval_worker -> synthesis_worker`; chưa gọi policy tool trong nhánh này nên phần điều kiện access level chưa đầy đủ.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

Metric thay đổi rõ nhất: Ở Day 09, `avg_latency_ms` đo được là 5569ms (`artifacts/eval_report.json`), đồng thời pipeline có thêm khả năng quan sát route/worker/tool theo từng bước.

Điều nhóm bất ngờ nhất: Multi-agent giúp trace lỗi dễ hơn nhiều (route_reason, workers_called, mcp_tools_used), nhưng đi kèm overhead điều phối giữa supervisor và workers.

Trường hợp multi-agent KHÔNG giúp ích: Với câu hỏi đơn giản chỉ cần 1 nguồn kiến thức, routing overhead làm latency tăng nhưng không cải thiện chất lượng câu trả lời đáng kể.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

Phân công thực tế:

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Văn Quang | Supervisor + Workers (routing, retrieval/policy/synthesis, contracts) | 1,2 |
| Nguyễn Mạnh Dũng | MCP server + Trace/Eval + Docs/Group report | 3,4 |

Điều nhóm làm tốt: Phân công rõ ràng, phối hợp tốt qua commits.

Điều nhóm làm chưa tốt: MCP chưa được dùng đồng đều trên toàn bộ pipeline (theo `eval_report.json`, mcp_usage_rate mới đạt 6/15 trace).

Nếu làm lại, nhóm sẽ prioritize integration sớm hơn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Ưu tiên cải thiện luồng multi-hop để phối hợp retrieval + policy tốt hơn, đặc biệt cho các câu giống gq09. Mục tiêu là tăng coverage MCP ở các case cần policy và giữ route_reason ngắn gọn, nhất quán để dễ debug/chấm điểm.

---
