"""
Service Advisor Agent - 售后服务助理
负责保养提醒、故障诊断、维修预约、服务费用估算
"""
import json
import os
from agents.llm_interface import llm

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class ServiceAdvisor:
    """售后服务助理Agent"""

    HANDOFF_KEYWORDS = [
        "换车", "置换", "旧车", "新车", "报价", "报价单", "金融", "首付",
        "分期", "贷款", "订车", "提车", "成交", "交付", "以旧换新", "补贴",
        "残值", "trade-in", "想买新车", "看新车"
    ]

    SYSTEM_PROMPT = """你是梅赛德斯-奔驰的专属售后服务顾问"守护"，**你的职责仅限且专注于售后服务领域**（保养提醒、维修预约、故障诊断、质保查询等）。

你的风格：专业、关怀、可靠、有同理心，避免机械死板和格式化的长篇大论。

【跨部门管家联动机制 - 与“销售顾问”的联动】：
如果你在沟通中发现车主的车辆频繁维修、车龄较高，或者车主主动提到“想换新车”、“了解旧车置换”、“新车报价”等涉及销售业务的需求，请务必执行联动：
1. 坚守售后专家身份，不要强行跨界去为客户做新车选型或报价。
2. 以关怀的语气提醒客户，可以享受官方认证二手车的高额置换补贴。
3. 引导客户在这个无缝对话窗口中直接召唤你的同伴——【销售顾问】（例如提示客户发送：“帮我叫销售顾问星辰” 或 “最近买新车有什么推荐的”），实现全业务链转接。

规则：
- 始终用中文回复，语气带有人文关怀。
- 绝不重复固定死板格式。碰到故障要先安抚，再给出专业判断。"""

    def __init__(self):
        self.service_rules = self._load_service_rules()

    def _load_service_rules(self):
        try:
            with open(os.path.join(DATA_DIR, "service_rules.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _detect_handoff(self, message):
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in self.HANDOFF_KEYWORDS):
            return {
                "target_agent": "sales_consultant",
                "trigger": "service_to_sales",
                "reason": "客户出现换车、置换、报价或金融诉求，需要销售顾问继续承接",
                "message": "这个需求已经从售后延伸到换新和置换了，我建议直接转接销售顾问星辰继续帮您承接。"
            }
        return None

    def handle(self, message, context=None, user_profile=None):
        """处理售后服务消息"""
        handoff = self._detect_handoff(message)
        if handoff:
            return {
                "reply": handoff["message"],
                "agent": "service_advisor",
                "handoff": handoff
            }

        if llm.get_mode() == "openai":
            enhanced_prompt = self.SYSTEM_PROMPT + "\n\n服务规则：\n" + \
                json.dumps(self.service_rules, ensure_ascii=False, indent=2)
            result = llm.chat(enhanced_prompt, message, context)
            if result:
                return {"reply": result, "agent": "service_advisor"}

        return self._simulation_response(message)

    def _simulation_response(self, message):
        """模拟模式回复"""
        message_lower = message.lower()

        handoff = self._detect_handoff(message)
        if handoff:
            reply = (
                "我先继续帮您处理当前售后信息，同时这个需求已经更偏向换车/置换/金融方案。"
                "我建议直接转接销售顾问星辰继续跟进，避免信息重复。"
            )
            return {"reply": reply, "agent": "service_advisor", "handoff": handoff}

        # 保养相关
        if any(w in message_lower for w in ["保养", "多久", "里程", "机油"]):
            schedule = self.service_rules.get("maintenance_schedule", [])
            reply = "🔧 **梅赛德斯-奔驰标准保养周期**\n\n"
            reply += "奔驰采用「A/B保养交替」体系：\n\n"
            for s in schedule:
                reply += f"📍 **{s['mileage']//1000}千公里 / {s['months']}个月**（{s['type']}）\n"
                reply += f"   项目：{'、'.join(s['items'][:3])}\n"
                reply += f"   预估费用：¥{s['estimatedCost']:,} · 耗时：{s['duration']}\n\n"
            reply += "💡 **温馨提示**：以里程或时间为准，先到为准。首保免费！\n"
            reply += "请问您的爱车目前行驶了多少公里？我帮您看看该做什么保养。"
            return {"reply": reply, "agent": "service_advisor"}

        # 故障相关
        if any(w in message_lower for w in ["故障", "报警", "灯亮", "异响", "抖动", "故障码"]):
            faults = self.service_rules.get("common_faults", [])

            # 检查是否提到了具体故障码
            import re
            code_match = re.search(r'[PCU]\d{4}', message.upper())
            if code_match:
                code = code_match.group()
                fault = next((f for f in faults if f["code"] == code), None)
                if fault:
                    severity_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(fault["severity"], "⚪")
                    reply = f"🔍 **故障码 {fault['code']} 解读**\n\n"
                    reply += f"**描述：** {fault['description']}\n"
                    reply += f"**严重程度：** {severity_icon} {fault['severity']}\n\n"
                    reply += "**可能原因：**\n"
                    for cause in fault["possibleCauses"]:
                        reply += f"  • {cause}\n"
                    reply += f"\n**建议：** {fault['suggestedAction']}\n"
                    reply += f"**预估费用：** {fault['estimatedCost']}\n\n"
                    reply += "⚠️ 以上仅供参考，具体需到店用专业诊断设备确认。需要我帮您预约检修吗？"
                    return {"reply": reply, "agent": "service_advisor",
                            "fault_info": fault}

            # 通用故障引导
            reply = "🔍 **故障诊断助手**\n\n"
            reply += "请描述您遇到的问题，我可以帮您初步分析：\n\n"
            reply += "📌 如果仪表盘亮了故障灯，请告诉我故障码（如 P0300）\n"
            reply += "📌 也可以描述症状：「发动机抖动」「异响」「油耗突然增加」等\n\n"
            reply += "常见故障码速查：\n"
            for f in faults[:3]:
                severity_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(f["severity"], "⚪")
                reply += f"  {severity_icon} **{f['code']}** — {f['description']}\n"
            reply += "\n我会为您分析严重程度和处理建议。"
            return {"reply": reply, "agent": "service_advisor"}

        # 预约相关
        if any(w in message_lower for w in ["预约", "4s", "门店", "地址"]):
            centers = self.service_rules.get("service_centers", [])
            reply = "📍 **附近的梅赛德斯-奔驰授权服务中心**\n\n"
            for c in centers:
                reply += f"🏢 **{c['name']}**\n"
                reply += f"   📍 {c['address']}\n"
                reply += f"   📞 {c['phone']}\n"
                reply += f"   🕐 {c['openHours']}\n\n"
            reply += "请选择最方便的门店，我帮您预约保养/维修时间。"
            return {"reply": reply, "agent": "service_advisor",
                    "service_centers": centers}

        # 质保相关
        if any(w in message_lower for w in ["质保", "保修", "保证", "warranty"]):
            warranty = self.service_rules.get("warranty", {})
            reply = "🛡️ **梅赛德斯-奔驰质保政策**\n\n"
            labels = {
                "basic": "整车质保", "powertrain": "动力总成",
                "battery_ev": "电池质保(EQ)", "paint": "漆面质保",
                "rust": "车身防锈"
            }
            for key, value in warranty.items():
                label = labels.get(key, key)
                reply += f"✅ **{label}：** {value}\n"
            reply += "\n💡 质保期内非人为损坏均可免费维修。更多详情可到店咨询。"
            return {"reply": reply, "agent": "service_advisor"}

        # 默认
        reply = ("🛡️ 我是售后服务助理「守护」，为您的爱车保驾护航。\n\n"
                 "我可以帮您：\n"
                 "🔧 **保养提醒** — 查看保养周期和费用\n"
                 "🔍 **故障诊断** — 解读故障码和异常症状\n"
                 "📅 **预约维修** — 查找附近门店并预约\n"
                 "🛡️ **质保查询** — 了解质保范围和政策\n\n"
                 "请问有什么可以帮到您的？")
        return {"reply": reply, "agent": "service_advisor"}

    def diagnose(self, symptoms):
        """故障诊断"""
        faults = self.service_rules.get("common_faults", [])
        matched = []
        symptoms_lower = symptoms.lower()
        for f in faults:
            for cause in f["possibleCauses"]:
                if any(word in symptoms_lower for word in cause):
                    matched.append(f)
                    break
        return matched if matched else faults[:2]

    def create_appointment(self, center_id, date, service_type):
        """创建预约（模拟）"""
        centers = self.service_rules.get("service_centers", [])
        center = next((c for c in centers if c["id"] == center_id), None)
        if not center:
            return {"error": "服务中心未找到"}

        return {
            "appointment_id": f"BZ-{center_id[:2].upper()}-2026-{hash(date) % 10000:04d}",
            "center": center["name"],
            "address": center["address"],
            "date": date,
            "service_type": service_type,
            "status": "已预约",
            "reminder": "请提前15分钟到店，携带行驶证和保养手册"
        }


# 全局单例
service_advisor = ServiceAdvisor()
