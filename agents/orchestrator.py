"""
Orchestrator - 智能路由协调器
负责意图识别、Agent路由、上下文管理和多Agent协作编排
"""
import re
from agents.llm_interface import llm


class Orchestrator:
    """Agent 协调器，管理意图识别和Agent路由"""

    INTENT_KEYWORDS = {
        "sales": {
            "keywords": ["买车", "选车", "推荐", "预算", "车型", "对比", "哪款",
                         "多少钱", "价格", "价位", "适合", "家用", "商务", "代步",
                         "轿车", "suv", "新车", "购车", "性价比", "优惠", "促销",
                         "试驾", "提车", "首付", "分期", "贷款", "落地价",
                         "置换", "旧车", "换车"],
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
        self.current_agent = None
        self.current_vehicle = None  # 当前讨论的车型
        self.user_profile = {
            "budget": None,
            "usage": None,
            "preferences": [],
            "family_size": None,
            "interested_vehicles": []
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
            "current_vehicle": self.current_vehicle
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
            "user_profile": self.user_profile,
            "conversation_length": len(self.context)
        }


# 全局单例
orchestrator = Orchestrator()
