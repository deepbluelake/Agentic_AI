import os
import json
from typing import Dict, Tuple, Any
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

class NLPService:
    def __init__(self):
        self.api_key = "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"
        self.model = "llama-3.1-8b-instant"
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.client = Groq(api_key=self.api_key)
    
    def parse_request(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse natural language requests into intent and entities using Groq AI
        
        Args:
            text: Natural language request from user
            
        Returns:
            Tuple containing:
            - intent: String like "CREATE_VM", "DELETE_VM", "QUERY_USAGE"
            - entities: Dictionary of parameters for the action
        """
        prompt = f"""
        You are an AI assistant that helps with cloud infrastructure management.
        Extract the following information from this request:

        1. Operation type (create, read, update, delete)
        2. Resource type (VM, network, volume)
        3. Resource name (if specified)
        4. Properties (size, flavor, etc.)
        
        User request: "{text}"
        
        Format your response as JSON with these keys:
        - intent: A string like "CREATE_VM", "DELETE_VOLUME", "QUERY_USAGE", etc.
        - entities: An object with extracted parameters
        
        Example:
        {{
            "intent": "CREATE_VM",
            "entities": {{
                "name": "dev-box",
                "flavor": "S.4"
            }}
        }}
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Extract content from Groq response
            content = chat_completion.choices[0].message.content
            
            # Safely parse JSON 
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse Groq AI response as JSON: {content}")
            
            # Validate expected fields
            if "intent" not in parsed or "entities" not in parsed:
                raise ValueError(f"Groq AI response missing required fields: {parsed}")
                
            return parsed["intent"], parsed["entities"]
            
        except Exception as e:
            raise Exception(f"Error communicating with Groq AI: {str(e)}")
    
    def generate_confirmation_message(self, intent: str, entities: Dict[str, Any]) -> str:
        """
        Generate a human-readable confirmation message based on intent and entities
        """
        prompt = f"""
        You are an AI assistant that helps with cloud infrastructure management.
        Generate a confirmation message for this operation:

        Intent: {intent}
        Parameters: {json.dumps(entities, indent=2)}

        The message should:
        1. Be clear and concise
        2. Include all relevant parameters
        3. Ask for confirmation
        4. Be friendly and professional

        Format your response as a single string.
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=200
            )
            
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback to simple messages if Groq fails
            if intent == "CREATE_VM":
                return f"Are you sure you want to create a VM named {entities['name']} with flavor {entities['flavor']}?"
            elif intent == "DELETE_VM":
                return f"Are you sure you want to delete VM {entities['name']}?"
            elif intent == "RESIZE_VM":
                return f"Are you sure you want to resize VM {entities['name']} to flavor {entities['flavor']}?"
            elif intent == "QUERY_USAGE":
                return "I'll fetch the current usage information."
            else:
                return "I'll process your request."
    
    def generate_response(self, intent: str, result: Dict[str, Any]) -> str:
        """
        Generate a human-friendly response based on the intent and operation result
        """
        prompt = f"""
        You are an AI assistant that helps with cloud infrastructure management.
        Generate a response message for this completed operation:

        Intent: {intent}
        Result: {json.dumps(result, indent=2)}

        The message should:
        1. Be clear and concise
        2. Include all relevant information from the result
        3. Be friendly and professional
        4. Use natural language

        Format your response as a single string.
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=200
            )
            
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback to simple messages if Groq fails
            if intent == "CREATE_VM":
                return f"Created VM {result['name']} with ID {result['id']}. Status: {result['status']}, IP: {result['ip']}"
            elif intent == "DELETE_VM":
                return f"Deleted VM {result['name']} successfully."
            elif intent == "RESIZE_VM":
                return f"Resized VM {result['name']} to flavor {result['flavor']}. Status: {result['status']}"
            elif intent == "QUERY_USAGE":
                return f"Current usage: {result}"
            else:
                return f"Operation completed: {result}"