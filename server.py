"""
BenzMind Server - Flask REST API
Mercedes-Benz 智能客户体验 AI Agent 后端服务
"""
import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.orchestrator import orchestrator
from agents.llm_interface import llm
from agents.sales_consultant import sales_consultant
from agents.vehicle_configurator import vehicle_configurator
from agents.service_advisor import service_advisor
from agents.experience_designer import experience_designer

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ============ Static Files ============

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)


def _normalize_webhook_payload(source, payload):
    event_type = payload.get("event_type") or payload.get("type") or "unknown"
    return {
        "source": source,
        "event_type": event_type,
        "external_id": payload.get("external_id") or payload.get("id") or payload.get("event_id"),
        "name": payload.get("name") or payload.get("customer_name") or payload.get("contact_name"),
        "phone": payload.get("phone") or payload.get("mobile") or payload.get("contact_phone"),
        "vehicle_id": payload.get("vehicle_id") or payload.get("sku") or payload.get("model_id"),
        "stage": payload.get("stage") or payload.get("lead_stage"),
        "message": payload.get("message") or payload.get("content") or payload.get("summary"),
        "raw": payload
    }


def _handle_webhook(source):
    payload = request.json or {}
    normalized = _normalize_webhook_payload(source, payload)
    result = orchestrator.apply_webhook_event(source, normalized)
    return jsonify(result)


# ============ Chat API ============

@app.route("/api/chat", methods=["POST"])
def chat():
    """主聊天端点 — 接收消息，路由到Agent，返回回复"""
    data = request.json
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    # 路由到正确的Agent
    route_info = orchestrator.route(message)
    agent_name = route_info["agent"]
    intent = route_info["intent"]
    is_quotes_query = route_info["is_quotes_query"]
    context = route_info["context"]
    user_profile = route_info["user_profile"]

    # 调用对应Agent
    try:
        if agent_name == "sales_consultant":
            result = sales_consultant.handle(
                message, context=context, user_profile=user_profile,
                is_quotes_query=is_quotes_query
            )
        elif agent_name == "vehicle_configurator":
            result = vehicle_configurator.handle(
                message, context=context, user_profile=user_profile,
                current_vehicle=orchestrator.current_vehicle
            )
        elif agent_name == "service_advisor":
            result = service_advisor.handle(
                message, context=context, user_profile=user_profile
            )
        elif agent_name == "experience_designer":
            result = experience_designer.handle(
                message, context=context, user_profile=user_profile
            )
        else:
            result = {"reply": "抱歉，我暂时无法处理这个问题。请换个方式问我？", "agent": "unknown"}
    except Exception as e:
        result = {"reply": f"处理请求时出现错误：{str(e)}", "agent": agent_name}

    handoff = orchestrator.detect_handoff(message, source_agent=agent_name, source_result=result)
    if handoff:
        orchestrator.record_event("handoff_triggered", handoff)
        result["handoff"] = handoff

    # 记录Agent回复到上下文
    orchestrator.add_to_context("assistant", result.get("reply", ""), agent=agent_name)

    # 返回结果
    response = {
        "reply": result.get("reply", ""),
        "agent": result.get("agent", agent_name),
        "intent": intent,
        "user_profile": user_profile,
        "lead_stage": route_info.get("lead_stage", orchestrator.lead_stage),
        "lead_record": route_info.get("lead_record", orchestrator.lead_record),
        "events": route_info.get("events", []),
        **{k: v for k, v in result.items() if k not in ("reply", "agent")}
    }
    return jsonify(response)


# ============ Agent Status API ============

@app.route("/api/agents/status", methods=["GET"])
def agents_status():
    """获取所有Agent状态"""
    return jsonify(orchestrator.get_status())


# ============ Vehicle APIs ============

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    """获取车型列表"""
    try:
        with open(os.path.join(DATA_DIR, "vehicles.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        category = request.args.get("category")
        if category:
            data["vehicles"] = [v for v in data["vehicles"] if v["category"] == category]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vehicles/<vehicle_id>/configure", methods=["POST"])
def configure_vehicle(vehicle_id):
    """车辆配置"""
    options = request.json or {}
    result = vehicle_configurator.configure(vehicle_id, options)
    return jsonify(result)


# ============ Lifecycle APIs ============

@app.route("/api/lifecycle", methods=["GET"])
def get_lifecycle():
    """获取当前线索生命周期状态"""
    return jsonify(orchestrator.get_lifecycle())


@app.route("/api/lead/capture", methods=["POST"])
def capture_lead():
    """登记线索"""
    payload = request.json or {}
    return jsonify(orchestrator.capture_lead(payload))


@app.route("/api/test-drive/request", methods=["POST"])
def request_test_drive():
    """发起试驾预约"""
    payload = request.json or {}
    result = orchestrator.request_test_drive(payload)

    # 顺带调用售后预约能力，复用已有门店数据
    service_result = service_advisor.create_appointment(
        payload.get("center_id", "sh_pudong"),
        payload.get("date", result["date"]),
        payload.get("service_type", "试驾预约")
    )
    result["service_booking"] = service_result
    return jsonify(result)


@app.route("/api/deal/quote", methods=["POST"])
def create_quote():
    """生成报价/推进成交"""
    payload = request.json or {}
    return jsonify(orchestrator.create_quote(payload))


# ============ Service APIs ============

@app.route("/api/service/diagnose", methods=["POST"])
def diagnose():
    """故障诊断"""
    data = request.json
    symptoms = data.get("symptoms", "")
    results = service_advisor.diagnose(symptoms)
    return jsonify({"results": results})


@app.route("/api/service/appointment", methods=["POST"])
def create_appointment():
    """预约服务"""
    data = request.json
    result = service_advisor.create_appointment(
        data.get("center_id", ""),
        data.get("date", ""),
        data.get("service_type", "")
    )
    return jsonify(result)


# ============ Webhook Skeletons ============

@app.route("/api/webhooks/wecom", methods=["POST"])
def wecom_webhook():
    """企业微信 webhook 骨架"""
    return _handle_webhook("wecom")


@app.route("/api/webhooks/crm", methods=["POST"])
def crm_webhook():
    """CRM webhook 骨架"""
    return _handle_webhook("crm")


@app.route("/api/webhooks/dms", methods=["POST"])
def dms_webhook():
    """DMS webhook 骨架"""
    return _handle_webhook("dms")


# ============ Public Sales Dataset API ============

@app.route("/api/sales/dataset", methods=["GET"])
def get_public_dataset():
    """获取公共汽车销售数据集"""
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 15))
    search = request.args.get("search", "").lower()
    
    dataset = sales_consultant.get_public_dataset()
    
    if search:
        dataset = [d for d in dataset if search in d.get("question", "").lower() or search in d.get("response", "").lower()]
        
    total = len(dataset)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    return jsonify({
        "dataset": dataset[start_idx:end_idx],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    })


# ============ User Profile API ============

@app.route("/api/user/profile", methods=["GET"])
def get_user_profile():
    """获取用户偏好画像"""
    return jsonify(orchestrator.user_profile)


# ============ Mode Switch API ============

@app.route("/api/mode/switch", methods=["POST"])
def switch_mode():
    """切换LLM/模拟模式"""
    data = request.json
    mode = data.get("mode", "simulation")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")
    model = data.get("model", "")

    if mode == "openai" and api_key:
        llm.api_key = api_key
        if base_url:
            llm.base_url = base_url
        if model:
            llm.model = model

    success = llm.set_mode(mode)
    return jsonify({
        "success": success,
        "current_mode": llm.get_mode(),
        "message": f"已切换至{'OpenAI/大模型' if mode == 'openai' else '模拟演示'}模式"
    })


# ============ Run Server ============

if __name__ == "__main__":
    import sys
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("\n" + "=" * 60)
    print("  [*] BenzMind - Mercedes-Benz AI Agent Platform")
    print("  [*] Server starting on http://localhost:5000")
    print("  [*] Mode:", "OpenAI API" if llm.get_mode() == "openai" else "Simulation")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
