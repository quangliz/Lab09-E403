# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Văn Quang
**Vai trò trong nhóm:** Supervisor Owner & Worker Owner
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

Trong Lab này, tôi chịu trách nhiệm chính thiết kế kiến trúc điều phối tổng thể (Orchestration) và xây dựng nền tảng cho các Worker xử lý domain knowledge. Cụ thể, tôi đã đảm nhận Sprint 1 và Sprint 2.

**Module/file tôi chịu trách nhiệm:**
- File chính: `graph.py`, `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py`
- Functions tôi implement:
  - `supervisor_node()` và `build_graph()` trong `graph.py`.
  - Hàm `retrieve_dense()` để query ChromaDB trong `retrieval.py`.
  - Hàm `analyze_policy()` với LLM Structured Output trong `policy_tool.py`.
  - Hàm `synthesize()` với grounding rules nghiêm ngặt trong `synthesis.py`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi tạo ra khung đồ thị (LangGraph) và định nghĩa `AgentState`. Các bạn làm Sprint 3 (MCP Owner) sẽ viết các tool HTTP API, và tôi sẽ gọi các API đó từ bên trong `policy_tool_worker`. Bạn làm Trace & Eval (Sprint 4) phụ thuộc hoàn toàn vào cấu trúc dữ liệu trả về từ `run_graph()` của tôi để tính toán metrics.

**Bằng chứng:**
Commit hash `49d3f2d837a5fde5649cc45e8cb22475dbad6687`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Sử dụng LLM (GPT-4o-mini) với Structured Output (Pydantic) làm Supervisor Classifier thay vì dùng Keyword-matching (If/Else).

**Lý do:**
Ban đầu, template cung cấp một đoạn code dùng keyword cơ bản (`if any(kw in task...)`). Tuy nhiên, yêu cầu bài toán là phải có `route_reason` cực kỳ cụ thể để debug, và phải bắt được các ngữ cảnh rủi ro ẩn (high risk). Keyword matching quá cứng nhắc và dễ bị bypass (ví dụ câu hỏi: "Tôi không muốn hoàn tiền, tôi muốn bảo hành" có chứa chữ "hoàn tiền" nhưng lại route nhầm vào policy hoàn tiền). Dùng LLM với schema `RouteDecision` đảm bảo logic phân loại dựa trên "ý định" (intent) thực sự của câu hỏi, đồng thời ép LLM giải thích lý do cụ thể.

**Trade-off đã chấp nhận:**
Đánh đổi độ trễ (Latency) và Chi phí (Cost). Keyword matching chỉ tốn ~1ms và 0 token. Gọi LLM tốn khoảng ~1000-2000ms và tiêu tốn token đầu vào/đầu ra cho mỗi câu hỏi trước khi nó kịp chạm đến worker.

**Bằng chứng từ trace/code:**
Trong trace `run_20260414_170053.json` (Câu q10 về hoàn tiền Store Credit):
```json
  "route_reason": "Tác vụ liên quan đến việc hoàn tiền và store credit, có từ khóa 'hoàn tiền' trong yêu cầu, do đó cần phải tham khảo chính sách để xác định giá trị store credit so với tiền gốc.",
  "risk_high": false,
  "needs_tool": true,
  "supervisor_route": "policy_tool_worker"
```
LLM đã trả về một lý do rất chi tiết và context-aware, điều mà Keyword matching khó làm được với chất lượng ngôn ngữ tự nhiên tương tự.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Trace file bị thiếu `retrieved_sources` khi câu hỏi được route vào `policy_tool_worker`.

**Symptom (pipeline làm gì sai?):**
Khi chạy pipeline với các câu hỏi về policy (như q03, q10), trace lưu mảng `retrieved_sources: []` mặc dù Synthesis Worker vẫn tổng hợp được câu trả lời trích dẫn nguồn. Điều này làm bài lab bị trừ điểm do vi phạm I/O contract.

**Root cause (lỗi nằm ở đâu):**
Lỗi nằm ở luồng (flow) dữ liệu trong `workers/policy_tool.py`. Khi Supervisor đẩy câu hỏi vào `policy_tool_worker`, worker này gọi MCP `search_kb` để lấy `chunks` và lưu vào `state["retrieved_chunks"]`. Tuy nhiên, tôi đã quên extract mảng `sources` từ đống chunks đó để gán vào `state["retrieved_sources"]` giống như cách `retrieval.py` đang làm. Hệ quả là Synthesis Worker vẫn đọc được chunks để trả lời, nhưng biến trace `retrieved_sources` lại bị trống.

**Cách sửa:**
Trong `workers/policy_tool.py`, ngay sau khi parse kết quả từ MCP, tôi bổ sung thêm 1 dòng code trích xuất nguồn từ metadata của chunk và gán lại vào `AgentState`.

**Bằng chứng trước/sau:**
*Trích đoạn code đã sửa (dòng 155):*
```python
if mcp_result.get("output") and mcp_result["output"].get("chunks"):
    chunks = mcp_result["output"]["chunks"]
    state["retrieved_chunks"] = chunks
    # Refinement: Populate retrieved_sources from MCP chunks
    state["retrieved_sources"] = list({c.get("source", "unknown") for c in chunks})
```
Sau khi sửa, trace file của câu q03 (`run_20260414_170020.json`) đã hiện `retrieved_sources: ["access_control_sop.txt"]`.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã thiết kế các file AgentState và worker I/O cực kỳ chặt chẽ, tuân thủ đúng định dạng mà file YAML contract yêu cầu. Việc chuyển hóa các system prompts phức tạp sang tiếng Việt để điều khiển LLM abstain và route chính xác cũng là điểm mạnh của tôi.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do chia luồng đồ thị tĩnh (hardcode Graph edges: `if route == "human_review" -> retrieval_worker`), tôi đã vô tình làm hệ thống thất bại hoàn toàn ở 2 câu hỏi Multi-hop (q13, q15). Luồng Graph của tôi thiếu tính linh hoạt (dynamic routing) để gọi tuần tự hoặc song song các Worker khác nhau.

**Nhóm phụ thuộc vào tôi ở đâu?**
Toàn bộ dự án bị block cho đến khi tôi xong `graph.py` và `AgentState`, vì đó là "xương sống" để MCP Server và Evaluation Script có thể gắn vào và bắt đầu đo đạc.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần bạn làm MCP (Sprint 3) cung cấp đúng chuẩn JSON format cho API `tools/call` để `policy_tool_worker` của tôi có thể phân tích response mà không bị crash.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thiết kế lại `graph.py` thành dạng **Dynamic Multi-Agent**. Cụ thể, thay vì Supervisor chỉ chọn 1 Worker rồi đi thẳng tới Synthesis, tôi sẽ cho Supervisor tạo ra một `Execution Plan` (danh sách tuần tự: ví dụ `[policy_tool, retrieval]`). Sau khi mỗi Worker chạy xong, State sẽ quay lại Supervisor để check xem đã hết Plan chưa. Lý do là vì trace của câu q15 cho thấy tỷ lệ Multi-hop accuracy của hệ thống đang là 0% do Static Routing giới hạn việc gọi nhiều công cụ chéo domain.