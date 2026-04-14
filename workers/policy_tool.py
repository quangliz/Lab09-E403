"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import sys
from typing import Optional, List
from pydantic import BaseModel, Field

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool qua HTTP Server (FastAPI).
    """
    import requests
    from datetime import datetime

    url = "http://127.0.0.1:8000/tools/call"
    payload = {
        "tool": tool_name,
        "input": tool_input
    }

    try:
        response = requests.post(url, json=payload, timeout=5.0)
        response.raise_for_status()
        result = response.json().get("result")
        
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except requests.exceptions.RequestException as e:
        # Fallback to direct import if HTTP server is down (for testing convenience)
        try:
            from mcp_server import dispatch_tool
            result = dispatch_tool(tool_name, tool_input)
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": result,
                "error": None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as inner_e:
            return {
                "tool": tool_name,
                "input": tool_input,
                "output": None,
                "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
                "timestamp": datetime.now().isoformat(),
            }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

class PolicyException(BaseModel):
    type: str = Field(description="The type of exception, e.g., 'flash_sale_exception', 'digital_product_exception'")
    rule: str = Field(description="The specific policy rule that applies")
    source: str = Field(description="The source document of the rule")

class PolicyAnalysisResult(BaseModel):
    policy_applies: bool = Field(description="True if the action (like a refund or granting access) is allowed according to the policy context, False if it is blocked or falls under an exception.")
    policy_name: str = Field(description="Name of the applicable policy, e.g., 'refund_policy_v4'")
    exceptions_found: List[PolicyException] = Field(description="List of exceptions found in the context that apply to this task")
    policy_version_note: str = Field(description="Any notes regarding temporal scoping or specific versions applying (e.g., if order is before 01/02/2026)")
    explanation: str = Field(description="Brief explanation of the reasoning")

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks.

    Returns:
        dict with: policy_applies, policy_name, exceptions_found, source, policy_version_note, explanation
    """
    from langchain_openai import ChatOpenAI

    context_text = "\n\n".join([f"Source: {c.get('source', 'unknown')}\n{c.get('text', '')}" for c in chunks])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(PolicyAnalysisResult)
    
    prompt = f"""Bạn là một chuyên gia phân tích chính sách cho bộ phận IT/CS helpdesk.
Nhiệm vụ của bạn là phân tích tác vụ dựa trên ngữ cảnh được cung cấp và xác định xem hành động được yêu cầu có được phép theo chính sách hay không, đồng thời xác định bất kỳ ngoại lệ nào.

Tác vụ: {task}

Ngữ cảnh:
{context_text}

Các quy tắc cần xem xét (nếu áp dụng dựa trên ngữ cảnh):
- Các mặt hàng Flash Sale thường không được hoàn tiền.
- Các sản phẩm kỹ thuật số (mã bản quyền, gói đăng ký) thường không được hoàn tiền.
- Các sản phẩm đã kích hoạt thường không được hoàn tiền.
- Kiểm tra phạm vi thời gian (ví dụ: các đơn hàng trước ngày 01/02/2026 có thể sử dụng chính sách cũ hơn như v3).

Phân tích tác vụ so với ngữ cảnh. Nếu một hành động được yêu cầu và nó vi phạm chính sách hoặc rơi vào trường hợp ngoại lệ (như Flash Sale), hãy đặt `policy_applies` thành False và liệt kê các ngoại lệ.
"""

    result = structured_llm.invoke(prompt)
    
    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": result.policy_applies,
        "policy_name": result.policy_name,
        "exceptions_found": [ex.model_dump() for ex in result.exceptions_found],
        "source": sources,
        "policy_version_note": result.policy_version_note,
        "explanation": result.explanation,
    }


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với policy_result và mcp_tools_used
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Nếu chưa có chunks, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks
                # Refinement: Populate retrieved_sources from MCP chunks
                state["retrieved_sources"] = list({c.get("source", "unknown") for c in chunks})

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] policy_applies={policy_result['policy_applies']}, "
            f"exceptions={len(policy_result.get('exceptions_found', []))}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n▶ Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
