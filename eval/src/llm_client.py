"""
Provider-agnostische LLM client voor alle PoCs

Ondersteunt multiple providers (OpenAI, Anthropic, etc.) met:
- JSON mode en schema validatie
- Fallback naar client-side schema forcering
- Uniform interface voor alle providers
"""

import asyncio
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
import httpx
import time

load_dotenv()


class LLMClient(ABC):
    """Abstract base class voor LLM providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def generate(
        self, 
        system: str, 
        user: str, 
        json_mode: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """Genereer response van LLM"""
        pass
    
    @abstractmethod  
    async def judge(self, judge_prompt: str) -> Dict[str, Any]:
        """Specifieke judge call die altijd JSON teruggeeft"""
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude client implementatie"""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
    async def generate(
        self, 
        system: str, 
        user: str, 
        json_mode: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response via Anthropic API"""
        
        # Build messages
        messages = [{"role": "user", "content": user}]
        
        # Add JSON instruction if requested
        if json_mode:
            system += "\n\nGeef je antwoord uitsluitend in geldig JSON formaat."
            
        payload = {
            "model": self.model,
            "system": system,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error {response.status_code}: {response.text}")
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Client-side JSON validation if schema provided
            if schema and json_mode:
                try:
                    import jsonschema
                    parsed = json.loads(content)
                    jsonschema.validate(parsed, schema)
                except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                    raise Exception(f"Response failed schema validation: {e}")
            
            return content
        
    async def judge(self, judge_prompt: str) -> Dict[str, Any]:
        """Judge call that always returns JSON"""
        
        response = await self.generate(
            system="Je bent een professionele evaluator. Geef altijd geldig JSON terug.",
            user=judge_prompt,
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Fallback voor malformed JSON
            return {
                "error": "Invalid JSON response",
                "raw_response": response,
                "parse_error": str(e)
            }


class OpenAIClient(LLMClient):
    """OpenAI GPT client implementatie"""
    
    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    async def generate(
        self, 
        system: str, 
        user: str, 
        json_mode: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response via OpenAI API"""
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": 1000
            # temperature removed - gpt-5-mini only supports default (1)
        }
        
        # Use structured output if JSON mode and supported
        if json_mode and schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": schema
                }
            }
        elif json_mode:
            payload["response_format"] = {"type": "json_object"}
            messages[0]["content"] += "\n\nGeef je antwoord uitsluitend in geldig JSON formaat."
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error {response.status_code}: {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Client-side fallback validation if needed
            if schema and json_mode and "json_schema" not in payload.get("response_format", {}):
                try:
                    import jsonschema
                    parsed = json.loads(content)
                    jsonschema.validate(parsed, schema)
                except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                    raise Exception(f"Response failed schema validation: {e}")
            
            return content
        
    async def judge(self, judge_prompt: str) -> Dict[str, Any]:
        """Judge call that always returns JSON"""
        
        response = await self.generate(
            system="You are a professional evaluator. Always return valid JSON.",
            user=judge_prompt,
            json_mode=True
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Fallback voor malformed JSON
            return {
                "error": "Invalid JSON response", 
                "raw_response": response,
                "parse_error": str(e)
            }


def create_llm_client() -> LLMClient:
    """Factory function om LLM client te maken op basis van .env configuratie"""
    provider = os.getenv("PROVIDER", "anthropic")
    model = os.getenv("MODEL", "claude-3-5-sonnet-20241022")
    
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY niet gevonden in environment")
        return AnthropicClient(api_key, model)
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY") 
        if not api_key:
            raise ValueError("OPENAI_API_KEY niet gevonden in environment")
        return OpenAIClient(api_key, model)
        
    else:
        raise ValueError(f"Onbekende provider: {provider}")


# Convenience function voor sync gebruik
async def get_client() -> LLMClient:
    """Async wrapper voor client creation"""
    return create_llm_client()