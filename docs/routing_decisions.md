# Routing Decisions Log — Lab Day 09

**Nhóm:** 9
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> Ai phải phê duyệt để cấp quyền Level 3?

- **Worker được chọn:** `policy_tool_worker`
- **Route reason (từ trace):** `Tác vụ yêu cầu phê duyệt cấp quyền level 3, liên quan đến việc cấp quyền truy cập, do đó cần được xử lý bởi policy_tool_worker.`  
- **MCP tools được gọi:** `search_kb`  
- **Workers called sequence:** `policy_tool_worker`, `synthesis_worker`

- **Kết quả thực tế:**
    - final_answer (ngắn): Để cấp quyền Level 3, cần có sự phê duyệt của Line Manager, IT Admin và IT Security [2].
    - confidence: 0.56
    - Correct routing? Yes

- **Nhận xét:** Routing này hoàn toàn chính xác. Yêu cầu về "cấp quyền" (access) là một tác vụ liên quan đến chính sách bảo mật, do đó Supervisor đã nhận diện đúng từ khóa và điều hướng tới `policy_tool_worker`. Kết quả cuối cùng trả lời chính xác dựa vào chính sách được truy xuất.

---

## Routing Decision #2

**Task đầu vào:**
> Nhân viên được làm remote tối đa mấy ngày mỗi tuần?

- **Worker được chọn:** `retrieval_worker`  
- **Route reason (từ trace):** `Câu hỏi về số ngày làm remote không liên quan đến các từ khóa rủi ro cao hoặc chính sách cụ thể nào. Đây là một yêu cầu thông thường và có thể được xử lý bởi bộ phận hỗ trợ khách hàng.`  
- **MCP tools được gọi:** Không có  
- **Workers called sequence:** `retrieval_worker`, `synthesis_worker`

- **Kết quả thực tế:**
    - final_answer (ngắn): Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần. Lịch remote phải được Team Lead phê duyệt...
    - confidence: 0.61
    - Correct routing? Yes

- **Nhận xét:** Đúng. Câu hỏi này mang tính tra cứu thông tin (FAQ / HR Policy) thông thường, không thuộc về phân quyền nhạy cảm hay liên quan đến việc xử lý hoàn tiền, vì vậy điều hướng thẳng tới `retrieval_worker` là tối ưu để giảm độ trễ và chi phí.

---

## Routing Decision #3

**Task đầu vào:**
> Store credit khi hoàn tiền có giá trị bao nhiêu so với tiền gốc?

- **Worker được chọn:** `policy_tool_worker`  
- **Route reason (từ trace):** `Tác vụ liên quan đến việc hoàn tiền và store credit, có từ khóa 'hoàn tiền' trong yêu cầu, do đó cần phải tham khảo chính sách để xác định giá trị store credit so với tiền gốc.`  
- **MCP tools được gọi:** `search_kb`  
- **Workers called sequence:** `policy_tool_worker`, `synthesis_worker`

- **Kết quả thực tế:**
    - final_answer (ngắn): Store credit khi hoàn tiền có giá trị 110% so với số tiền gốc...
    - confidence: 0.35
    - Correct routing? Yes

- **Nhận xét:** Đúng. Từ khóa "hoàn tiền" đã kích hoạt rule điều hướng tới `policy_tool_worker`. Mặc dù bài toán này cuối cùng chỉ là lấy một con số (110%), việc đưa qua policy check giúp hệ thống kiểm tra các ngoại lệ (ví dụ như digital product) theo đúng thiết kế an toàn của hệ thống. Confidence khá thấp do mâu thuẫn giữa thông tin chi tiết và context được retrieved, nhưng đáp án vẫn đúng.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình.

- **Worker được chọn:** `human_review` (sau đó tự động chuyển qua `retrieval_worker`)  
- **Route reason:** `Tác vụ yêu cầu cấp quyền truy cập tạm thời cho contractor trong tình huống khẩn cấp vào lúc 2am, điều này có thể dẫn đến rủi ro cao về bảo mật... | human approved → retrieval`

- **Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Routing này **chưa hoàn hảo**. Đây là câu hỏi "Multi-hop" yêu cầu thông tin từ cả 2 domain: SLA (retrieval) và Cấp quyền (policy_tool). 
Supervisor đã làm rất tốt khi nhận diện từ khóa nhạy cảm ("2am", "khẩn cấp", "cấp quyền") để kích hoạt `human_review` vì risk cao. Tuy nhiên, sau khi Human duyệt, luồng hiện tại của `graph.py` (graph flow tĩnh) lại ép buộc ("hardcode") chuyển thẳng sang `retrieval_worker`, bỏ qua bước kiểm tra policy trong `policy_tool_worker`. Điều này khiến câu trả lời bị thiếu sự xác nhận từ MCP check permissions, phơi bày điểm yếu của hệ thống "Single Path Routing". Đây là trường hợp chứng minh cần thiết phải cho phép Supervisor lên kế hoạch linh hoạt (gọi nhiều worker song song hoặc tuần tự).

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53.3% |
| policy_tool_worker | 6 | 40% |
| human_review | 1 | 6.7% |

*(Lưu ý: Phân bổ này dựa trên 15 test questions. human_review chiếm 1 câu tương đương ~6.7%, retrieval 8 câu tương đương ~53.3%, policy_tool 6 câu tương đương 40%.)*

### Routing Accuracy

> Trong số 15 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 14 / 15
- Câu route sai (đã sửa bằng cách nào?): 1 (Câu q15 bị hardcode ép luồng sau human_review về retrieval thay vì cho phép đi qua policy_tool. Cách sửa: cập nhật logic graph để đánh giá lại node tiếp theo sau human_review hoặc cho phép gọi nhiều worker song song).
- Câu trigger HITL: 1 (Câu q15)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  

1. **Sử dụng LLM Classifier (Structured Output qua Pydantic)**: Việc dùng LLM thay vì chỉ match keyword cứng nhắc giúp `route_reason` trở nên cực kỳ linh hoạt và có ngữ cảnh rõ ràng. LLM có thể hiểu câu hỏi phức tạp và đánh giá rủi ro (risk_high) tốt hơn rất nhiều so với Regex.
2. **Nguy cơ của luồng Graph tĩnh (Static Routing)**: Việc "hardcode" luồng đi sau node HITL (luôn đi tới retrieval_worker) là một sai lầm kiến trúc trong các bài toán phức tạp. Pipeline cần phải là "Dynamic Routing", cho phép agent quyết định bước đi tiếp theo dựa trên State hiện tại ở bất kỳ thời điểm nào.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  
> Nếu chưa, nhóm sẽ cải tiến format route_reason thế nào?

Các `route_reason` hiện tại (ví dụ: *"Tác vụ yêu cầu phê duyệt cấp quyền level 3, liên quan đến việc cấp quyền truy cập, do đó cần được xử lý bởi policy_tool_worker"*) là **khá tốt và đủ thông tin để debug**. Chúng chỉ ra cụ thể yếu tố nào trong câu hỏi kích hoạt quyết định.
**Cải tiến:** Có thể thêm định dạng JSON cho `route_reason` chứa các trường cụ thể như `{"triggered_keywords": ["cấp quyền", "Level 3"], "explanation": "..."}` để việc parse và analyze trace tự động dễ dàng hơn.