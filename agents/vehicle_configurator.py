"""
Vehicle Configurator Agent - 车辆配置专家
负责交互式配置、方案生成、价格计算、配置冲突检测
"""
import json
import os
from agents.llm_interface import llm

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class VehicleConfigurator:
    """车辆配置专家Agent"""

    SYSTEM_PROMPT = """你是梅赛德斯-奔驰的车辆配置专家"晨曦"，精通所有奔驰车型的配置方案。
你的风格：专业、有品位、热情、像真实顾问一样自然对话，不机械死板。
你的任务：
1. 帮助客户选择外观颜色、轮毂、内饰材质
2. 推荐适合的选装包
3. 计算配置总价
4. 检测配置兼容性

规则：
- 始终用中文回复，专业且有品位
- 根据客户的问题和上下文灵活回复，避免每次都用相同的格式输出长串配置
- 推荐配置时，说明理由（如"这款海神蓝能更好凸显运动感"），增加人情味
- 不要死板地罗列不需要的选项"""

    def __init__(self):
        self.vehicles = self._load_vehicles()
        self.configurations = self._load_configurations()
        self.current_config = {}

    def _load_vehicles(self):
        try:
            with open(os.path.join(DATA_DIR, "vehicles.json"), "r", encoding="utf-8") as f:
                return json.load(f)["vehicles"]
        except Exception:
            return []

    def _load_configurations(self):
        try:
            with open(os.path.join(DATA_DIR, "configurations.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def handle(self, message, context=None, user_profile=None, current_vehicle=None):
        """处理配置相关消息"""
        message_lower = message.lower()

        # LLM模式
        if llm.get_mode() == "openai":
            enhanced_prompt = self.SYSTEM_PROMPT
            
            if current_vehicle:
                vehicle_data = next((v for v in self.vehicles if v["id"] == current_vehicle), None)
                if vehicle_data:
                    enhanced_prompt += f"\n\n【重要上下文】当前客户正在关注的车型是：{vehicle_data['name']}\n基础车价：¥{vehicle_data['price']:,}。\n请基于此计算总价！\n"

            enhanced_prompt += "\n\n选配选项知识库（包含颜色、轮毂、内饰及套装配件）：\n" + \
                json.dumps(self.configurations, ensure_ascii=False, indent=2)

            result = llm.chat(enhanced_prompt, message, context)
            if result:
                return {"reply": result, "agent": "vehicle_configurator", "config": self.current_config}

        # 模拟模式
        return self._simulation_response(message, current_vehicle)

    def _simulation_response(self, message, current_vehicle=None):
        """模拟模式回复"""
        message_lower = message.lower()

        # 颜色查询
        if any(w in message_lower for w in ["颜色", "车漆", "喷漆", "外观色"]):
            colors = self.configurations.get("colors", [])
            reply = "🎨 **梅赛德斯-奔驰色彩臻选**\n\n"

            standard = [c for c in colors if c["type"] in ("solid", "metallic")]
            designo = [c for c in colors if c["type"] == "designo"]

            reply += "**标准 & 金属漆**\n"
            for c in standard:
                price_text = "标配" if c["price"] == 0 else f"+¥{c['price']:,}"
                reply += f"  ● {c['name']} `{c['hex']}` — {price_text}\n"

            reply += "\n**designo 臻选漆面**（手工调制）\n"
            for c in designo:
                reply += f"  ◆ {c['name']} `{c['hex']}` — +¥{c['price']:,}\n"

            reply += "\n✨ 最受欢迎的组合：**曜岩黑 + 夜色套件** 或 **北极白 + AMG Line**\n"
            reply += "请问您偏好哪种风格？稳重商务还是动感运动？"
            return {"reply": reply, "agent": "vehicle_configurator",
                    "config_options": {"type": "colors", "options": colors}}

        # 内饰查询
        if any(w in message_lower for w in ["内饰", "真皮", "座椅", "nappa"]):
            interiors = self.configurations.get("interiors", [])
            reply = "🪑 **内饰材质臻选**\n\n"
            for i in interiors:
                price_text = "标配" if i["price"] == 0 else f"+¥{i['price']:,}"
                reply += f"● **{i['name']}**\n"
                reply += f"  材质：{i['material']} · 色调：{i['color']} · {price_text}\n\n"
            reply += "💡 推荐：**Nappa真皮 马鞍棕** 搭配深色外观，营造极致温馨的车内氛围。\n"
            reply += "请问您倾向哪种内饰风格？"
            return {"reply": reply, "agent": "vehicle_configurator",
                    "config_options": {"type": "interiors", "options": interiors}}

        # 轮毂查询
        if any(w in message_lower for w in ["轮毂", "轮圈", "轮胎", "尺寸"]):
            wheels = self.configurations.get("wheels", [])
            reply = "🛞 **轮毂方案**\n\n"
            for w in wheels:
                price_text = "标配" if w["price"] == 0 else f"+¥{w['price']:,}"
                reply += f"● **{w['name']}** — {w['style']}风格 · {price_text}\n"
            reply += "\n🏎️ 运动风格推荐 20寸AMG多辐式，商务范推荐 19寸五辐双拼色。"
            return {"reply": reply, "agent": "vehicle_configurator",
                    "config_options": {"type": "wheels", "options": wheels}}

        # 选装包查询
        if any(w in message_lower for w in ["选装", "套件", "amg", "夜色", "包", "选配"]):
            packages = self.configurations.get("packages", [])
            reply = "📦 **选装套件推荐**\n\n"
            for p in packages:
                reply += f"**{p['name']}** — ¥{p['price']:,}\n"
                reply += f"  {p['description']}\n"
                reply += f"  包含：{'、'.join(p['includes'][:3])}\n\n"
            reply += "💡 人气TOP3：AMG Line + 夜色套件 + Burmester音响\n"
            reply += "告诉我您的需求，我帮您搭配最佳方案！"
            return {"reply": reply, "agent": "vehicle_configurator",
                    "config_options": {"type": "packages", "options": packages}}

        # 配置方案生成
        if any(w in message_lower for w in ["方案", "总价", "配置单", "汇总"]):
            return self._generate_config_summary()

        # 默认
        reply = ("🔧 我是配置专家「晨曦」，可以帮您打造专属座驾。\n\n"
                 "您可以问我：\n"
                 "🎨 「有什么颜色可选」\n"
                 "🪑 「内饰材质有哪些」\n"
                 "🛞 「轮毂怎么选」\n"
                 "📦 「推荐选装套件」\n"
                 "📋 「生成配置方案总价」\n\n"
                 "请问您想从哪个部分开始定制？")
        return {"reply": reply, "agent": "vehicle_configurator"}

    def configure(self, vehicle_id, options):
        """提交配置选择"""
        vehicle = next((v for v in self.vehicles if v["id"] == vehicle_id), None)
        if not vehicle:
            return {"error": "车型未找到"}

        base_price = vehicle["price"]
        total_addon = 0
        selected = []

        configs = self.configurations
        for key, value in options.items():
            if key == "color":
                color = next((c for c in configs.get("colors", []) if c["id"] == value), None)
                if color:
                    total_addon += color["price"]
                    selected.append({"type": "颜色", "name": color["name"], "price": color["price"]})
            elif key == "interior":
                interior = next((i for i in configs.get("interiors", []) if i["id"] == value), None)
                if interior:
                    total_addon += interior["price"]
                    selected.append({"type": "内饰", "name": interior["name"], "price": interior["price"]})
            elif key == "wheel":
                wheel = next((w for w in configs.get("wheels", []) if w["id"] == value), None)
                if wheel:
                    total_addon += wheel["price"]
                    selected.append({"type": "轮毂", "name": wheel["name"], "price": wheel["price"]})
            elif key == "packages":
                for pkg_id in value:
                    pkg = next((p for p in configs.get("packages", []) if p["id"] == pkg_id), None)
                    if pkg:
                        total_addon += pkg["price"]
                        selected.append({"type": "选装包", "name": pkg["name"], "price": pkg["price"]})

        self.current_config = {
            "vehicle": vehicle["name"],
            "base_price": base_price,
            "selections": selected,
            "addon_total": total_addon,
            "total_price": base_price + total_addon
        }
        return self.current_config

    def _generate_config_summary(self):
        """生成配置汇总"""
        if not self.current_config:
            reply = "📋 您还没有选择任何配置。请先告诉我您想配置哪款车型，然后我们一步步来定制！"
            return {"reply": reply, "agent": "vehicle_configurator"}

        c = self.current_config
        reply = f"📋 **{c['vehicle']} 定制配置方案**\n\n"
        reply += f"🚗 基础车价：¥{c['base_price']:,}\n\n"
        reply += "**个性化选配：**\n"
        for s in c["selections"]:
            reply += f"  ● {s['type']}：{s['name']} — +¥{s['price']:,}\n"
        reply += f"\n选配合计：¥{c['addon_total']:,}\n"
        reply += f"━━━━━━━━━━━━\n"
        reply += f"**💰 总价：¥{c['total_price']:,}**\n\n"
        reply += "如需调整，请随时告诉我！"
        return {"reply": reply, "agent": "vehicle_configurator", "config": c}


# 全局单例
vehicle_configurator = VehicleConfigurator()
