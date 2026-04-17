"""
LLM Interface - 双模式LLM接口
支持 OpenAI API 模式和内置模拟引擎模式
"""
import os
import json


class LLMInterface:
    """LLM接口封装，支持 OpenAI API 和 模拟演示 两种模式"""

    def __init__(self):
        self.mode = "simulation"  # 默认模拟模式
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.model = "gpt-3.5-turbo"
        self.conversation_history = []

    def set_mode(self, mode):
        if mode == "openai" and not self.api_key:
            return False
        self.mode = mode
        return True

    def get_mode(self):
        return self.mode

    def chat(self, system_prompt, user_message, context=None):
        """统一聊天接口"""
        if self.mode == "openai":
            return self._openai_chat(system_prompt, user_message, context)
        else:
            return self._simulation_chat(system_prompt, user_message, context)

    def _openai_chat(self, system_prompt, user_message, context=None):
        """大模型 API 模式"""
        try:
            from openai import OpenAI
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
                
            client = OpenAI(**client_kwargs)

            messages = [{"role": "system", "content": system_prompt}]
            if context:
                # 如果上下文最后一个消息就是当前用户的消息，排除它避免重复
                ctx = context[:-1] if (len(context) > 0 and context[-1].get("content") == user_message) else context
                for msg in ctx[-8:]:  # 稍微增加上下文轮次
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            # 返回明确的错误信息，不再静默退回模拟模式
            return f"⚠️ **大模型服务连接失败**\n\n原因: `{str(e)}`\n\n请检查 API Key、Base URL 或网络连接是否正确。当前已默认提供模拟回复："

    def _simulation_chat(self, system_prompt, user_message, context=None):
        """模拟引擎模式 - 基于规则和模板的回复生成"""
        # 由各Agent自行实现模拟逻辑
        return None


# 全局单例
llm = LLMInterface()
