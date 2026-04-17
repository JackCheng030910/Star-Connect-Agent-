"""
Experience Designer Agent - 体验设计师
负责MBUX功能介绍、智能座舱特性、驾驶模式推荐、个性化设置建议
"""
import json
from agents.llm_interface import llm


class ExperienceDesigner:
    """体验设计师Agent"""

    SYSTEM_PROMPT = """你是梅赛德斯-奔驰的智能座舱体验设计师"灵感"，精通所有MBUX和车辆体验功能。
你的风格：充满科技感、未来感、富于想象力，聊天像是一个懂科技的极客兼生活家，不死板。
你的任务：
1. 介绍MBUX虚拟助理和车载智能系统
2. 讲解各种驾驶模式及其适用场景
3. 提供个性化座舱设置建议
4. 展示奔驰科技创新亮点

规则：
- 始终用中文回复，充满科技感和未来感
- 不要每次都像背书一样列出大量功能，要有重点、有场景感
- 会用生动的例子（比如下雨天配合蓝色氛围灯和爵士乐）带给用户沉浸式的感受
- 根据用户的提问灵活应答，避免格式化、套路化的输出"""

    MBUX_FEATURES = {
        "voice_assistant": {
            "name": "MBUX 语音助理",
            "description": "支持自然语言对话，无需'你好奔驰'唤醒词即可连续对话",
            "highlights": [
                "多轮上下文对话，像与副驾对话一样自然",
                "整合 Google Gemini + ChatGPT 4o 双AI引擎",
                "支持控制空调、导航、音乐、车窗等200+功能",
                "情绪感知，根据语气调整回应方式"
            ]
        },
        "hyperscreen": {
            "name": "MBUX Hyperscreen 超联屏",
            "description": "56英寸一体式曲面屏幕，从A柱延伸至A柱",
            "highlights": [
                "三块OLED屏幕无缝整合",
                "副驾专属娱乐屏（行驶中可观看视频）",
                "零层级界面，AI预测你想用的功能",
                "8核CPU + 46.4GB内存的强大算力"
            ]
        },
        "ar_hud": {
            "name": "增强现实抬头显示 AR-HUD",
            "description": "将导航箭头投射到真实道路上,仿佛道路本身在指引你",
            "highlights": [
                "77英寸等效显示面积",
                "导航箭头叠加在真实街景上",
                "显示车速、限速、距离等关键信息",
                "夜间和雨天同样清晰"
            ]
        },
        "ambient_lighting": {
            "name": "64色环境氛围灯",
            "description": "覆盖整个座舱的沉浸式光效",
            "highlights": [
                "64色随心变换",
                "随音乐节奏律动",
                "与驾驶模式联动（运动=红色/舒适=蓝色）",
                "十大灯光主题可选"
            ]
        },
        "driving_modes": {
            "name": "DYNAMIC SELECT 驾驶模式",
            "modes": [
                {"name": "Comfort 舒适", "desc": "柔和的悬挂和转向，适合日常通勤和城市驾驶", "icon": "🛋️"},
                {"name": "Sport 运动", "desc": "更紧绷的悬挂，更灵敏的油门响应，尽享驾驶乐趣", "icon": "🏎️"},
                {"name": "Sport+ 运动+", "desc": "最极致的动态表现，赛道级换挡逻辑（仅AMG车型）", "icon": "🔥"},
                {"name": "Eco 节能", "desc": "优化能耗，延长续航，适合长途旅行", "icon": "🌱"},
                {"name": "Individual 个性化", "desc": "自定义悬挂、转向、油门、氛围灯等偏好组合", "icon": "⚙️"},
                {"name": "Offroad 越野", "desc": "提升离地间隙，调整四驱分配（SUV/G级专属）", "icon": "🏔️"},
                {"name": "Maybach 迈巴赫", "desc": "极致后排舒适，空气悬挂最柔模式（S级迈巴赫专属）", "icon": "👑"}
            ]
        },
        "safety": {
            "name": "智能安全系统",
            "features": [
                {"name": "PRE-SAFE® 预防性安全", "desc": "碰撞前自动预紧安全带、关闭车窗、调整座椅"},
                {"name": "主动制动辅助", "desc": "检测行人、车辆、自行车，必要时自动刹车"},
                {"name": "盲点监测", "desc": "变道时监测侧后方盲区，危险时主动纠正方向"},
                {"name": "Cabin Guardian 座舱守护", "desc": "监测车内遗留的儿童或宠物，高温时自动报警"}
            ]
        }
    }

    def handle(self, message, context=None, user_profile=None):
        """处理体验相关消息"""
        if llm.get_mode() == "openai":
            enhanced_prompt = self.SYSTEM_PROMPT + "\n\nMBUX功能数据：\n" + \
                json.dumps(self.MBUX_FEATURES, ensure_ascii=False, indent=2)
            result = llm.chat(enhanced_prompt, message, context)
            if result:
                return {"reply": result, "agent": "experience_designer"}

        return self._simulation_response(message)

    def _simulation_response(self, message):
        """模拟模式回复"""
        message_lower = message.lower()

        # MBUX / 语音
        if any(w in message_lower for w in ["mbux", "语音", "助理", "对话", "ai"]):
            feature = self.MBUX_FEATURES["voice_assistant"]
            reply = f"🗣️ **{feature['name']}**\n\n"
            reply += f"{feature['description']}\n\n"
            reply += "核心能力：\n"
            for h in feature["highlights"]:
                reply += f"  ✨ {h}\n"
            reply += "\n🎯 **实际场景示例：**\n"
            reply += "• 「导航去最近的充电站，顺便把空调调到23度」\n"
            reply += "• 「今天天气怎么样？帮我播放适合下雨天的音乐」\n"
            reply += "• 「朝阳附近有没有评分高的日料店？」\n\n"
            reply += "2026款集成了 Google Gemini 和 ChatGPT 4o 双引擎，"
            reply += "导航用 Gemini 更精准，知识问答用 ChatGPT 更渊博！"
            return {"reply": reply, "agent": "experience_designer"}

        # 屏幕
        if any(w in message_lower for w in ["屏幕", "显示", "hyperscreen", "超联屏"]):
            feature = self.MBUX_FEATURES["hyperscreen"]
            reply = f"🖥️ **{feature['name']}**\n\n"
            reply += f"{feature['description']}\n\n"
            for h in feature["highlights"]:
                reply += f"  ✨ {h}\n"
            reply += "\n这块屏幕的震撼感文字很难传达，建议到店亲自体验！"
            return {"reply": reply, "agent": "experience_designer"}

        # 驾驶模式
        if any(w in message_lower for w in ["驾驶模式", "运动模式", "舒适模式", "模式"]):
            modes = self.MBUX_FEATURES["driving_modes"]
            reply = f"🎮 **{modes['name']}**\n\n每种模式为您打造截然不同的驾驶体验：\n\n"
            for m in modes["modes"]:
                reply += f"{m['icon']} **{m['name']}**\n   {m['desc']}\n\n"
            reply += "💡 **推荐搭配：**\n"
            reply += "• 早晨通勤 → Comfort + Jazz音乐 + 蓝色氛围灯\n"
            reply += "• 周末山路 → Sport + 引擎声浪 + 红色氛围灯\n"
            reply += "• 长途出行 → Eco + 有声书 + 暖色氛围灯"
            return {"reply": reply, "agent": "experience_designer"}

        # 氛围灯
        if any(w in message_lower for w in ["氛围灯", "灯光", "氛围"]):
            feature = self.MBUX_FEATURES["ambient_lighting"]
            reply = f"💡 **{feature['name']}**\n\n"
            reply += f"{feature['description']}\n\n"
            for h in feature["highlights"]:
                reply += f"  ✨ {h}\n"
            reply += "\n🌈 最受欢迎的主题：「星空蓝」+ 柏林之声音响 = 移动音乐厅！"
            return {"reply": reply, "agent": "experience_designer"}

        # 安全
        if any(w in message_lower for w in ["安全", "辅助驾驶", "刹车", "碰撞"]):
            safety = self.MBUX_FEATURES["safety"]
            reply = f"🛡️ **{safety['name']}**\n\n奔驰始终将安全放在第一位：\n\n"
            for f in safety["features"]:
                reply += f"  🔒 **{f['name']}**\n     {f['desc']}\n\n"
            reply += "奔驰是全球第一家获得 L3 级自动驾驶量产认证的车企。在S级和EQS上，"
            reply += "高速公路60km/h以下可真正\"放手\"驾驶！"
            return {"reply": reply, "agent": "experience_designer"}

        # HUD
        if any(w in message_lower for w in ["hud", "抬头", "投影"]):
            feature = self.MBUX_FEATURES["ar_hud"]
            reply = f"🔮 **{feature['name']}**\n\n"
            reply += f"{feature['description']}\n\n"
            for h in feature["highlights"]:
                reply += f"  ✨ {h}\n"
            reply += "\n这个功能特别适合不认路的朋友，导航箭头直接'画'在路上！"
            return {"reply": reply, "agent": "experience_designer"}

        # 默认
        reply = ("🧠 我是体验设计师「灵感」，带您探索奔驰智能座舱的无限可能。\n\n"
                 "我可以为您介绍：\n"
                 "🗣️ **MBUX语音助理** — AI双引擎自然对话\n"
                 "🖥️ **Hyperscreen超联屏** — 56寸沉浸式体验\n"
                 "🎮 **驾驶模式** — 一键切换驾驶性格\n"
                 "💡 **氛围灯** — 64色沉浸光效\n"
                 "🔮 **AR-HUD** — 增强现实导航\n"
                 "🛡️ **安全科技** — 守护每一程\n\n"
                 "请问您想了解哪个方面？")
        return {"reply": reply, "agent": "experience_designer"}


# 全局单例
experience_designer = ExperienceDesigner()
