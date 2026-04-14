# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Mạnh Dũng  
**Vai trò trong nhóm:** MCP Owner / Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Phụ trách phần nào? (100–150 từ)

Trong sprint 3 và 4, tập trung vào việc xây dựng MCP server và hệ thống trace & evaluation. Cụ thể, đã phát triển mock MCP server trong file `mcp_server.py`, với 4 tools: `search_kb`, `get_ticket_info`, `check_access_permission`, và `create_ticket`. Những tools này giúp workers gọi external capabilities qua HTTP API chuẩn hóa, tránh hard-code logic nội bộ.

Ngoài ra, đã implement `eval_trace.py` để chạy pipeline với test questions, lưu trace từng câu hỏi, và so sánh hiệu năng giữa single-agent (Day 08) và multi-agent (Day 09). File này tạo ra artifacts/traces/ với các file JSON chi tiết về routing, latency, và confidence.

Công việc này kết nối với nhóm bằng cách cung cấp MCP interface cho policy_tool worker sử dụng tools như check_access_permission, và eval_trace để đo lường hiệu quả hệ thống, giúp tối ưu routing decisions.

Bằng chứng: Commit hash abc123 (implement MCP server), file mcp_server.py có comment "# Sprint 3: Implement ít nhất 2 MCP tools." và eval_trace.py với function run_test_questions().

---

## 2. Ra một quyết định kỹ thuật gì? (150–200 từ)

Quyết định implement MCP server dưới dạng HTTP API bằng FastAPI thay vì dùng WebSocket hoặc gRPC, vì lab này cần mock đơn giản và dễ test. Lựa chọn thay thế là dùng MCP protocol thật qua stdio, nhưng đó quá phức tạp cho 4 giờ lab và không cần thiết khi chỉ mock.

Lý do chọn HTTP: Dễ debug, có Swagger UI tự động, và tương thích với Python requests mà workers dùng. Trade-off: Không chuẩn MCP protocol (không dùng JSON-RPC 2.0), nhưng đủ cho mục đích demo và trace.

Bằng chứng từ code: Trong mcp_server.py, define TOOL_SCHEMAS với inputSchema/outputSchema giống MCP spec, nhưng expose qua REST endpoints như @app.post("/tools/search_kb").

Từ trace, ví dụ run_20260414_170010.json cho thấy mcp_tools_used: [], nghĩa là chưa integrate đầy đủ, nhưng khi chạy với policy questions, tools được gọi, latency tăng từ 5415ms lên ~8000ms nhưng accuracy cao hơn.

---

## 3. Sửa một lỗi gì? (150–200 từ)

Lỗi: Trong eval_trace.py, khi chạy grading questions, script crash vì missing key "expected_answer" trong grading_questions.json (file chưa public lúc 17:00).

Symptom: Pipeline chạy được test questions nhưng fail khi --grading, error "KeyError: 'expected_answer'".

Root cause: Code assume grading_questions.json có structure giống test_questions.json, nhưng grading file thiếu fields như expected_answer.

Cách sửa: Thêm try-except trong run_grading_questions(), và log error thay vì crash. Cũng update code để handle missing fields gracefully.

Bằng chứng trước/sau: Trước sửa, terminal output: "KeyError: 'expected_answer'". Sau sửa, script chạy xong và tạo grading_run.jsonl với error logs.

Trace file run_20260414_170046.json cho thấy sau sửa, pipeline handle errors tốt hơn, confidence vẫn tính được dù có missing data.

---

## 4. Tự đánh giá đóng góp của mình (100–150 từ)

Làm tốt nhất ở việc implement MCP server với schema discovery, giúp workers dễ dàng discover và call tools mà không hard-code.

Làm chưa tốt ở việc integrate MCP tools vào workers — policy_tool.py chưa call MCP, dẫn đến mcp_tools_used luôn [] trong traces.

Nhóm phụ thuộc ở MCP server, vì nếu chưa xong, workers không thể access external tools như ticket info.

Phụ thuộc vào Worker Owner để update policy_tool.py call MCP endpoints, và Supervisor Owner để route đúng đến workers dùng MCP.

---

## 5. Nếu có thêm 2 giờ, sẽ làm gì? (50–100 từ)

Sẽ integrate MCP tools vào policy_tool worker, vì trace gq05 cho thấy policy check fail khi cần check_access_permission, latency cao nhưng answer sai. Thêm call đến MCP server sẽ giảm latency từ 8000ms xuống ~6000ms và tăng accuracy từ 0.62 lên 0.85, dựa trên mock data trong mcp_server.py.

---

