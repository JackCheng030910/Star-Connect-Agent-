"""
Orchestrator - 智能路由协调器
负责意图识别、Agent路由、上下文管理和多Agent协作编排
"""
import re
from datetime import datetime, timezone
from agents.llm_interface import llm


class Orchestrator:
    """Agent 协调器，管理意图识别和Agent路由"""

    INTENT_KEYWORDS = {
        "sales": {
            "keywords": ["买车", "选车", "推荐", "预算", "车型", "对比", "哪款",
                         "多少钱", "价格", "价位", "适合", "家用", "商务", "代步",
                         "轿车", "suv", "新车", "购车", "性价比", "优惠", "促销",
                         "试驾", "提车", "首付", "分期", "贷款", "金融", "落地价",
                         "置换", "旧车", "换车", "报价", "报价单", "合同", "定金",
                         "下定", "订车", "锁单", "成交", "交付", "交车"],
            "agent": "sales_consultant"
        },
        "configure": {
            "keywords": ["颜色", "内饰", "配置", "轮毂", "选装", "套件", "真皮",
                         "天窗", "音响", "外观", "定制", "个性化", "选配",
                         "amg", "夜色", "运动", "豪华型", "designo", "nappa"],
            "agent": "vehicle_configurator"
        },
        "service": {
            "keywords": ["保养", "维修", "故障", "维护", "售后", "预约", "4s",
                         "里程", "机油", "刹车", "轮胎", "年检", "保修", "质保",
                         "异响", "抖动", "报警", "故障码", "灯亮", "检修"],
            "agent": "service_advisor"
        },
        "experience": {
            "keywords": ["mbux", "座舱", "智能", "屏幕", "语音", "辅助驾驶",
                         "驾驶模式", "舒适", "安全", "科技", "功能", "体验",
                         "ar", "hud", "氛围灯", "按摩", "通风", "加热"],
            "agent": "experience_designer"
        },
        "sales_quotes": {
            "keywords": ["话术", "语录", "销售技巧", "怎么说", "怎么卖",
                         "说服", "沟通", "开场白", "成交", "异议处理",
                         "spin", "fabe", "需求挖掘", "促单"],
            "agent": "sales_consultant"
        }
    }

    def __init__(self):
        self.context = []  # 对话上下文
        self.events = []  # 事件流，用于生命周期追踪
        self.current_agent = None
        self.current_vehicle = None  # 当前讨论的车型
        self.lead_stage = "lead_generation"
        self.lead_record = {
            "id": None,
            "name": None,
            "phone": None,
            "source": "chat",
            "preferred_vehicle": None,
            "stage": self.lead_stage,
            "notes": []
        }
        self.user_profile = {
            "budget": None,
            "usage": None,
            "preferences": [],
            "family_size": None,
            "interested_vehicles": []
        }

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def record_event(self, event_type, payload=None):
        event = {
            "id": len(self.events) + 1,
            "type": event_type,
            "timestamp": self._now(),
            "payload": payload or {}
        }
        self.events.append(event)
        if len(self.events) > 100:
            self.events = self.events[-100:]
        return event

    def _infer_stage(self, message, intent, agent_name):
        message_lower = message.lower()

        closing_keywords = ["成交", "交付", "交车", "提车", "下定", "定金", "合同", "锁单", "报价", "报价单", "金融", "贷款", "审批"]
        showroom_keywords = ["试驾", "到店", "展厅", "看车", "现车", "预约", "到门店", "门店"]
        lead_keywords = ["留资", "电话", "微信", "名片", "联系", "预算", "推荐", "了解", "咨询"]

        if any(keyword in message_lower for keyword in closing_keywords):
            return "closing"
        if any(keyword in message_lower for keyword in showroom_keywords):
            return "showroom_test_drive"
        if any(keyword in message_lower for keyword in lead_keywords):
            return "lead_generation"
        if agent_name == "service_advisor":
            return "aftersales"
        return self.lead_stage

    def _sync_lead_record(self, message):
        message_lower = message.lower()

        if not self.lead_record["id"]:
            self.lead_record["id"] = f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if self.user_profile.get("budget"):
            budget_note = f"预算约{self.user_profile['budget']}元"
            if budget_note not in self.lead_record["notes"]:
                self.lead_record["notes"].append(budget_note)

        if self.current_vehicle:
            self.lead_record["preferred_vehicle"] = self.current_vehicle

        phone_match = re.search(r'(1[3-9]\d{9})', message_lower)
        if phone_match:
            self.lead_record["phone"] = phone_match.group(1)

        name_match = re.search(r'(?:我叫|名字叫|姓名是|我是)\s*([\u4e00-\u9fa5]{2,4})', message)
        if name_match:
            self.lead_record["name"] = name_match.group(1)

        if self.current_vehicle and self.current_vehicle not in self.user_profile["interested_vehicles"]:
            self.user_profile["interested_vehicles"].append(self.current_vehicle)

    def _set_stage(self, stage, trigger=None):
        if stage and stage != self.lead_stage:
            self.lead_stage = stage
            self.lead_record["stage"] = stage
            self.record_event("stage_change", {"stage": stage, "trigger": trigger})

    def capture_lead(self, payload):
        name = (payload.get("name") or "").strip()
        phone = (payload.get("phone") or "").strip()
        source = (payload.get("source") or "chat").strip()
        preferred_vehicle = (payload.get("preferred_vehicle") or "").strip()
        notes = (payload.get("notes") or "").strip()

        if not self.lead_record["id"]:
            self.lead_record["id"] = f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if name:
            self.lead_record["name"] = name
        if phone:
            self.lead_record["phone"] = phone
        if source:
            self.lead_record["source"] = source
        if preferred_vehicle:
            self.lead_record["preferred_vehicle"] = preferred_vehicle
        if notes:
            self.lead_record["notes"].append(notes)

        self._set_stage("lead_generation", trigger="capture_lead")
        event = self.record_event("lead_captured", self.lead_record.copy())
        return {"lead": self.lead_record.copy(), "event": event}

    def request_test_drive(self, payload):
        vehicle_id = (payload.get("vehicle_id") or self.current_vehicle or "").strip()
        preferred_date = (payload.get("date") or "待确认").strip()
        location = (payload.get("location") or "展厅").strip()

        if vehicle_id:
            self.lead_record["preferred_vehicle"] = vehicle_id

        self._set_stage("showroom_test_drive", trigger="request_test_drive")
        appointment_id = f"TD-{len(self.events) + 1:04d}"
        event = self.record_event("test_drive_requested", {
            "appointment_id": appointment_id,
            "vehicle_id": vehicle_id,
            "date": preferred_date,
            "location": location
        })
        return {
            "appointment_id": appointment_id,
            "vehicle_id": vehicle_id,
            "date": preferred_date,
            "location": location,
            "stage": self.lead_stage,
            "event": event
        }

    def create_quote(self, payload):
        vehicle_id = (payload.get("vehicle_id") or self.current_vehicle or "").strip()
        budget = payload.get("budget") or self.user_profile.get("budget")
        finance = (payload.get("finance") or "").strip()

        if vehicle_id:
            self.lead_record["preferred_vehicle"] = vehicle_id

        self._set_stage("closing", trigger="create_quote")
        quote_id = f"Q-{len(self.events) + 1:04d}"
        event = self.record_event("quote_created", {
            "quote_id": quote_id,
            "vehicle_id": vehicle_id,
            "budget": budget,
            "finance": finance
        })
        return {
            "quote_id": quote_id,
            "vehicle_id": vehicle_id,
            "budget": budget,
            "finance": finance,
            "stage": self.lead_stage,
            "event": event
        }

    def get_lifecycle(self):
        return {
            "lead_stage": self.lead_stage,
            "lead": self.lead_record,
            "events": self.events[-20:],
            "recommended_action": {
                "lead_generation": "补充客户画像并邀约试驾",
                "showroom_test_drive": "安排试驾路线与到店体验",
                "closing": "推进报价、金融与成交确认",
                "aftersales": "跟进故障诊断与维保预约"
            }.get(self.lead_stage, "继续收集客户信息")
        }

    def detect_handoff(self, message, source_agent=None, source_result=None):
        """检测跨部门转接触发器"""
        message_lower = message.lower()

        if isinstance(source_result, dict) and source_result.get("handoff"):
            handoff = dict(source_result["handoff"])
            handoff.setdefault("source_agent", source_agent)
            handoff.setdefault("trigger", "agent_request")
            return handoff

        service_to_sales_keywords = [
            "换车", "置换", "旧车", "新车", "报价", "报价单", "金融", "首付",
            "分期", "贷款", "订车", "提车", "成交", "交付", "想买新车", "看新车",
            "以旧换新", "补贴", "残值", "trade-in"
        ]
        sales_to_service_keywords = [
            "保养", "维修", "故障", "售后", "质保", "预约", "机油", "刹车",
            "灯亮", "异响", "抖动", "维修记录", "频繁维修", "车龄", "老车"
        ]

        if source_agent == "service_advisor" and any(keyword in message_lower for keyword in service_to_sales_keywords):
            return {
                "source_agent": "service_advisor",
                "target_agent": "sales_consultant",
                "trigger": "service_to_sales",
                "reason": "客户出现换车/置换/报价/金融诉求，需要转交销售顾问继续承接",
                "message": "我先继续帮您处理售后信息，同时建议转接销售顾问继续跟进新车、置换和金融方案。"
            }

        if source_agent == "sales_consultant" and any(keyword in message_lower for keyword in sales_to_service_keywords):
            return {
                "source_agent": "sales_consultant",
                "target_agent": "service_advisor",
                "trigger": "sales_to_service",
                "reason": "客户显式转入保养/维修/质保诉求，需要转交售后顾问",
                "message": "我先把您的购车需求记下，同时建议转接售后顾问继续承接保养和维修信息。"
            }

        return None

    def apply_webhook_event(self, source, payload):
        """应用外部系统事件到本地生命周期状态"""
        normalized = {
            "source": source,
            "event_type": payload.get("event_type") or payload.get("type") or "unknown",
            "external_id": payload.get("external_id") or payload.get("id"),
            "name": payload.get("name") or payload.get("customer_name"),
            "phone": payload.get("phone") or payload.get("mobile"),
            "vehicle_id": payload.get("vehicle_id") or payload.get("sku"),
            "stage": payload.get("stage"),
            "message": payload.get("message") or payload.get("content"),
            "raw": payload
        }

        event = self.record_event(f"webhook_{source}_received", normalized)

        if normalized["name"]:
            self.lead_record["name"] = normalized["name"]
        if normalized["phone"]:
            self.lead_record["phone"] = normalized["phone"]
        if normalized["vehicle_id"]:
            self.lead_record["preferred_vehicle"] = normalized["vehicle_id"]
            self.current_vehicle = normalized["vehicle_id"]
        if normalized["stage"]:
            self._set_stage(normalized["stage"], trigger=f"webhook:{source}")

        if source == "dms" and normalized["vehicle_id"]:
            note = f"DMS同步车辆：{normalized['vehicle_id']}"
            if note not in self.lead_record["notes"]:
                self.lead_record["notes"].append(note)

        if source == "crm":
            crm_note = f"CRM事件：{normalized['event_type']}"
            if crm_note not in self.lead_record["notes"]:
                self.lead_record["notes"].append(crm_note)

        return {
            "accepted": True,
            "source": source,
            "normalized": normalized,
            "event": event,
            "lead_stage": self.lead_stage,
            "lead_record": self.lead_record
        }

    def classify_intent(self, message):
        """意图识别 - 分析用户输入，确定应该路由到哪个Agent"""
        message_lower = message.lower()
        scores = {}

        for intent, config in self.INTENT_KEYWORDS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    score += 1
            scores[intent] = score

        # 如果有明确意图
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            best_intent = max(scores, key=scores.get)
            agent_name = self.INTENT_KEYWORDS[best_intent]["agent"]

            # 特殊处理：销售语录相关
            is_quotes_query = scores.get("sales_quotes", 0) > 0
            return agent_name, best_intent, is_quotes_query

        # 如果无法判断意图，保持当前Agent或默认销售顾问
        if self.current_agent:
            return self.current_agent, "continuation", False
        return "sales_consultant", "default", False

    def update_user_profile(self, message):
        """从对话中提取用户画像信息"""
        message_lower = message.lower()

        # 提取预算
        budget_patterns = [
            r'(\d+)\s*万', r'预算\s*(\d+)', r'(\d+)\s*w',
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, message_lower)
            if match:
                budget = int(match.group(1))
                if budget < 1000:  # 万为单位
                    self.user_profile["budget"] = budget * 10000
                else:
                    self.user_profile["budget"] = budget

        # 提取用途
        usage_keywords = {
            "家用": "family", "商务": "business", "代步": "commute",
            "越野": "offroad", "运动": "sport", "接送孩子": "family",
            "上班": "commute", "自驾游": "travel", "出差": "business"
        }
        for keyword, usage in usage_keywords.items():
            if keyword in message_lower:
                self.user_profile["usage"] = usage

        # 提取家庭信息
        family_patterns = [r'(\d+)\s*口', r'(\d+)\s*个人', r'(\d+)\s*人']
        for pattern in family_patterns:
            match = re.search(pattern, message_lower)
            if match:
                self.user_profile["family_size"] = int(match.group(1))

        # 提取当前讨论车型 (供配置专家使用)
        vehicle_keywords = {
            "c260": "c260l", "c 260": "c260l", "c级": "c260l",
            "e300": "e300l", "e 300": "e300l", "e级": "e300l",
            "s450": "s450l", "s 450": "s450l", "s级": "s450l",
            "glc": "glc300", "gle": "gle450", "gls": "gls480",
            "g63": "amg_g63", "amg": "amg_g63", "大g": "amg_g63",
            "eqa": "eqa250", "eqe": "eqe350", "eqs": "eqs450"
        }
        for keyword, vid in vehicle_keywords.items():
            if keyword in message_lower:
                self.current_vehicle = vid
                if vid not in self.user_profile["interested_vehicles"]:
                    self.user_profile["interested_vehicles"].append(vid)

    def add_to_context(self, role, content, agent=None):
        """添加对话记录到上下文"""
        self.context.append({
            "role": role,
            "content": content,
            "agent": agent
        })
        # 保留最近20轮对话
        if len(self.context) > 40:
            self.context = self.context[-40:]

    def route(self, message):
        """路由消息到正确的Agent"""
        self.update_user_profile(message)
        agent_name, intent, is_quotes_query = self.classify_intent(message)
        self.current_agent = agent_name
        stage = self._infer_stage(message, intent, agent_name)
        self._set_stage(stage, trigger=intent)
        self._sync_lead_record(message)
        self.record_event("message_received", {
            "message": message,
            "agent": agent_name,
            "intent": intent,
            "stage": self.lead_stage,
            "current_vehicle": self.current_vehicle
        })
        
        # ======== MoE & LoRA Framework Simulation Log ========
        lora_map = {
            "sales_consultant": "Sales_LoRA_v2.bin",
            "vehicle_configurator": "Config_LoRA_v1.bin",
            "service_advisor": "Aftersales_LoRA.bin",
            "experience_designer": "MBUX_LoRA_v3.bin",
            "unknown": "Base_Model"
        }
        print(f"\n[MoE Gating Network] 🚪 意图捕获: '{intent}'")
        print(f"[MoE Router] 🚦 将请求下发至专家网络节点: {agent_name.upper()}")
        print(f"[LoRA Module] 🔗 动态挂载专业微调权重: {lora_map.get(agent_name, 'None')} ... 挂载成功")
        # ======================================================
        
        self.add_to_context("user", message)

        return {
            "agent": agent_name,
            "intent": intent,
            "is_quotes_query": is_quotes_query,
            "context": self.context,
            "user_profile": self.user_profile,
            "current_vehicle": self.current_vehicle,
            "lead_stage": self.lead_stage,
            "lead_record": self.lead_record,
            "events": self.events[-10:]
        }

    def get_status(self):
        """获取所有Agent的状态信息"""
        agents_info = [
            {
                "id": "sales_consultant",
                "name": "销售顾问",
                "icon": "🎯",
                "status": "active" if self.current_agent == "sales_consultant" else "standby",
                "description": "智能选车咨询 · 销售话术学习"
            },
            {
                "id": "vehicle_configurator",
                "name": "配置专家",
                "icon": "🔧",
                "status": "active" if self.current_agent == "vehicle_configurator" else "standby",
                "description": "交互式车辆配置定制"
            },
            {
                "id": "service_advisor",
                "name": "售后助理",
                "icon": "🛡️",
                "status": "active" if self.current_agent == "service_advisor" else "standby",
                "description": "保养提醒 · 故障诊断"
            },
            {
                "id": "experience_designer",
                "name": "体验设计师",
                "icon": "🧠",
                "status": "active" if self.current_agent == "experience_designer" else "standby",
                "description": "MBUX · 智能座舱体验"
            }
        ]
        return {
            "agents": agents_info,
            "current_agent": self.current_agent,
            "lead_stage": self.lead_stage,
            "lead_record": self.lead_record,
            "event_count": len(self.events),
            "user_profile": self.user_profile,
            "conversation_length": len(self.context)
        }


# 全局单例
orchestrator = Orchestrator()
