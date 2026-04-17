"""
Sales Consultant Agent - 智能销售顾问
负责需求采集、车型推荐、对比分析、销售语录分析与学习
"""
import json
import os
import random
from agents.llm_interface import llm

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class SalesConsultant:
    """销售顾问Agent"""

    SYSTEM_PROMPT = """你是梅赛德斯-奔驰的金牌销售顾问"星辰"，拥有10年高端汽车销售经验。
你的风格：专业、亲和、善于倾听、注重客户体验。像真正的人类顾问一样自然聊天，避免机械化、死板的重复格式。
你的任务：
1. 了解客户的用车需求（预算、用途、家庭情况、偏好等）
2. 基于需求智能推荐最匹配的奔驰车型
3. 提供车型对比分析
4. 引导客户试驾或进一步了解
5. 在对话中自然运用销售话术技巧

规则：
- 始终保持奔驰品牌的尊贵感和专业形象，但语气要像朋友一样温暖、自然
- 推荐要有理有据，不要强推，基于客户输入进行个性化回复
- 如果客户提到竞品，客观分析差异而非贬低对手
- 不要每次都用相同的开场白或固定句式，根据上下文灵活回复
- 避免一次性扔出大量参数，挑选最适合该客户的2-3个亮点进行说明
- 用中文回复，使用适当的Emoji增强亲和感"""

    def __init__(self):
        self.vehicles = self._load_vehicles()
        self.dataset = self._load_public_dataset()

    def _load_vehicles(self):
        try:
            with open(os.path.join(DATA_DIR, "vehicles.json"), "r", encoding="utf-8") as f:
                return json.load(f)["vehicles"]
        except Exception:
            return []

    def _load_public_dataset(self):
        try:
            with open(os.path.join(DATA_DIR, "public_sales_dataset.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def handle(self, message, context=None, user_profile=None, is_quotes_query=False):
        """处理用户消息"""
        # 如果涉及销售技巧学习/语录，直接从公共数据集中检索作为背景知识
        retrieved_knowledge = ""
        if is_quotes_query and self.dataset:
            # 简单的关键词匹配搜索
            keywords = message.replace("？", "").replace("什么是", "").replace("怎么", "").split()
            matched = []
            for d in self.dataset:
                q_text = d.get("question", "").lower() + " " + d.get("response", "").lower()
                if any(k in q_text for k in keywords):
                    matched.append(d)
                if len(matched) >= 3:
                    break
            if not matched:
                matched = self.dataset[:3] # fallback
                
            retrieved_knowledge = "\n\n【检索到的真实销售培训公共数据】\n"
            for i, md in enumerate(matched, 1):
                retrieved_knowledge += f"Q: {md.get('question')}\nA: {md.get('response')}\n(评估分: {md.get('helpfulness', 0)})\n\n"
            retrieved_knowledge += "请基于以上真实的培训数据集内容，针对用户的疑问进行专业解答和提取话术建议。不要直接把原文抛出，要归纳转化。"

        # 尝试 OpenAI 模式
        if llm.get_mode() == "openai":
            enhanced_prompt = self.SYSTEM_PROMPT
            if is_quotes_query:
                enhanced_prompt += retrieved_knowledge
            else:
                enhanced_prompt += "\n\n可用车型数据：\n" + json.dumps(self.vehicles[:5], ensure_ascii=False, indent=2)
                
            if user_profile:
                enhanced_prompt += f"\n\n当前用户画像：{json.dumps(user_profile, ensure_ascii=False)}"
                
            result = llm.chat(enhanced_prompt, message, context)
            if result:
                response = result
                recommendations = self._extract_recommendations(message, user_profile) if not is_quotes_query else []
                return {"reply": response, "recommendations": recommendations, "agent": "sales_consultant"}

        # 模拟模式
        return self._simulation_response(message, user_profile, is_quotes_query)

    def _simulation_response(self, message, user_profile=None, is_quotes_query=False):
        """模拟模式回复"""
        message_lower = message.lower()
        
        if is_quotes_query:
            reply = "📚 **公共数据集检索 (模拟)**\n\n已为您在开源数据库中检索到真实销售策略：\n\n"
            if self.dataset:
                sample = self.dataset[0]
                reply += f"❓ **场景问题**: {sample.get('question')}\n"
                reply += f"💡 **推荐话术/策略**: {sample.get('response')}\n"
                reply += f"📊 *(回答质量得分: {sample.get('helpfulness', 0):.1f})*\n\n"
            reply += "*(注：当前为模拟模式，完整 RAG 生成建议请在左下角连接大模型 API)*"
            return {"reply": reply, "agent": "sales_consultant"}

        recommendations = self._extract_recommendations(message, user_profile)

        # 预算相关
        if user_profile and user_profile.get("budget"):
            budget = user_profile["budget"]
            matched = [v for v in self.vehicles if v["price"] <= budget * 1.2]
            if matched:
                matched.sort(key=lambda x: abs(x["price"] - budget))
                top_picks = matched[:3]
                reply = f"根据您{budget // 10000}万左右的预算，我为您精选了以下几款车型：\n\n"
                for i, v in enumerate(top_picks, 1):
                    reply += f"**{i}. {v['name']}** — {v['priceRange']}\n"
                    reply += f"   {v['engine']} · {v['power']} · {v['bodyType']}\n"
                    reply += f"   ✨ 亮点：{'、'.join(v['highlights'][:3])}\n"
                    reply += f"   🎯 适合：{v['targetAudience']}\n\n"
                reply += "您对哪款比较感兴趣？我可以为您详细介绍，或者安排试驾体验。"
                return {"reply": reply, "recommendations": top_picks, "agent": "sales_consultant"}

        # SUV相关
        if any(w in message_lower for w in ["suv", "越野", "空间大"]):
            suvs = [v for v in self.vehicles if v["category"] == "SUV"]
            reply = "奔驰SUV家族阵容非常强大，从城市精英到越野传奇应有尽有：\n\n"
            for v in suvs[:4]:
                reply += f"🚙 **{v['name']}** — {v['priceRange']}\n"
                reply += f"   {v['engine']} · {v['bodyType']} · {'、'.join(v['highlights'][:2])}\n\n"
            reply += "请问您更偏向哪个价位区间？主要的用车场景是什么？这样我能更精准地为您推荐。"
            return {"reply": reply, "recommendations": suvs[:4], "agent": "sales_consultant"}

        # 纯电相关
        if any(w in message_lower for w in ["电动", "纯电", "eq", "新能源", "环保"]):
            evs = [v for v in self.vehicles if v["category"] == "纯电EQ"]
            reply = "欢迎了解奔驰EQ纯电家族！这是梅赛德斯在电动化时代的全新篇章：\n\n"
            for v in evs:
                reply += f"⚡ **{v['name']}** — {v['priceRange']}\n"
                reply += f"   续航 {v.get('range', 'N/A')} · {v['power']} · {v.get('batteryCapacity', 'N/A')}\n"
                reply += f"   ✨ {'、'.join(v['highlights'][:2])}\n\n"
            reply += "纯电车型不仅环保，用车成本也非常低。您对哪款更感兴趣？"
            return {"reply": reply, "recommendations": evs, "agent": "sales_consultant"}

        # 对比相关
        if any(w in message_lower for w in ["对比", "比较", "区别", "vs", "还是"]):
            reply = "好的！请告诉我您想对比哪两款车型，比如「GLC 和 GLE 有什么区别」或「E级和5系怎么选」，我会从动力、空间、配置、价格等维度为您做详细的对比分析。"
            return {"reply": reply, "recommendations": [], "agent": "sales_consultant"}

        # 默认欢迎
        reply = ("您好！欢迎来到梅赛德斯-奔驰，我是您的专属销售顾问「星辰」。🌟\n\n"
                 "我可以帮您：\n"
                 "🚗 **智能选车** — 告诉我您的预算和用途，精准推荐\n"
                 "📊 **对比分析** — 多款车型横向对比，清晰明了\n"
                 "🎓 **销售话术** — 浏览学习专业汽车销售技巧\n\n"
                 "请问有什么可以帮到您的？比如您可以说：\n"
                 "• 「50万预算想买SUV」\n"
                 "• 「E级和5系怎么选」\n"
                 "• 「看看销售开场白话术」")
        return {"reply": reply, "recommendations": [], "agent": "sales_consultant"}

    def get_public_dataset(self):
        """获取公共数据集"""
        return self.dataset

    def _extract_recommendations(self, message, user_profile=None):
        """基于消息和用户画像提取推荐车型"""
        if not user_profile:
            return []
        budget = user_profile.get("budget")
        if budget:
            matched = [v for v in self.vehicles if v["price"] <= budget * 1.3]
            matched.sort(key=lambda x: abs(x["price"] - budget))
            return matched[:3]
        return []


# 全局单例
sales_consultant = SalesConsultant()
