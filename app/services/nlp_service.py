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
                # Format usage information nicely
                summary = result.get('summary', {})
                quotas = result.get('compute_quotas', {})
                servers = result.get('servers', [])
                volumes = result.get('volumes', [])
                
                response = "**PROJECT USAGE SUMMARY**\n\n"
                
                # Main Summary Section - Enhanced with more details
                response += "📊 **Resource Overview:**\n"
                response += f"• Total Servers: {summary.get('total_servers', 0)}\n"
                response += f"• Active Servers: {summary.get('active_servers', 0)}\n"
                response += f"• Total vCPUs Used: {summary.get('total_vcpus_used', 0)}\n"
                response += f"• Total RAM Used: {summary.get('total_ram_used_gb', 0)} GB\n"
                response += f"• Total Volumes: {summary.get('total_volumes', 0)}\n"
                response += f"• Total Storage: {summary.get('total_storage_gb', 0)} GB\n\n"
                
                # Compute Quotas Section - Enhanced with percentage used if available
                response += "💻 **Compute Quotas:**\n"
                
                vcpus = quotas.get('vcpus', {})
                vcpu_used = vcpus.get('used', 0)
                vcpu_limit = vcpus.get('limit', 'unlimited')
                if vcpu_limit != 'unlimited' and isinstance(vcpu_limit, (int, float)) and vcpu_limit > 0:
                    vcpu_percent = (vcpu_used / vcpu_limit) * 100
                    response += f"• vCPUs: {vcpu_used} used out of {vcpu_limit} ({vcpu_percent:.1f}%)\n"
                else:
                    response += f"• vCPUs: {vcpu_used} used out of {vcpu_limit}\n"
                
                ram = quotas.get('ram_gb', {})
                ram_used = ram.get('used', 0)
                ram_limit = ram.get('limit', 'unlimited')
                if ram_limit != 'unlimited' and isinstance(ram_limit, (int, float)) and ram_limit > 0:
                    ram_percent = (ram_used / ram_limit) * 100
                    response += f"• RAM: {ram_used} GB used out of {ram_limit} GB ({ram_percent:.1f}%)\n"
                else:
                    response += f"• RAM: {ram_used} GB used out of {ram_limit} GB\n"
                
                instances = quotas.get('instances', {})
                instances_used = instances.get('used', 0)
                instances_limit = instances.get('limit', 'unlimited')
                if instances_limit != 'unlimited' and isinstance(instances_limit, (int, float)) and instances_limit > 0:
                    instances_percent = (instances_used / instances_limit) * 100
                    response += f"• Instances: {instances_used} used out of {instances_limit} ({instances_percent:.1f}%)\n\n"
                else:
                    response += f"• Instances: {instances_used} used out of {instances_limit}\n\n"
                
                # Detailed Server Section - Enhanced with more server details
                if servers:
                    response += "🖥️ **Server Details:**\n"
                    for i, server in enumerate(servers):
                        server_name = server.get('name', 'unknown')
                        server_id = server.get('id', 'unknown')
                        server_status = server.get('status', 'unknown')
                        server_flavor = server.get('flavor', 'unknown')
                        server_created = server.get('created', 'unknown')
                        
                        response += f"• Server #{i+1}: {server_name}\n"
                        response += f"  - ID: {server_id}\n"
                        response += f"  - Status: {server_status}\n"
                        response += f"  - Flavor: {server_flavor}\n"
                        response += f"  - Created: {server_created}\n"
                        
                        # Add a separator between servers except for the last one
                        if i < len(servers) - 1:
                            response += "  ---\n"
                
                # Detailed Volume Section - Enhanced with more volume details and status indicators
                if volumes:
                    response += "\n💾 **Volume Details:**\n"
                    for i, volume in enumerate(volumes):
                        volume_name = volume.get('name', 'unknown')
                        volume_id = volume.get('id', 'unknown')
                        volume_size = volume.get('size_gb', 0)
                        volume_status = volume.get('status', 'unknown')
                        
                        # Status indicator
                        status_indicator = "🟢" if volume_status.lower() == "available" else "🔴" if volume_status.lower() == "error" else "🟡"
                        
                        response += f"• Volume #{i+1}: {volume_name} {status_indicator}\n"
                        response += f"  - ID: {volume_id}\n"
                        response += f"  - Size: {volume_size} GB\n"
                        response += f"  - Status: {volume_status}\n"
                        
                        # Show attachment information if available
                        attachments = volume.get('attached_to', [])
                        if attachments:
                            response += f"  - Attached to: {', '.join(attachments)}\n"
                        else:
                            response += f"  - Not attached\n"
                            
                        # Add a separator between volumes except for the last one
                        if i < len(volumes) - 1:
                            response += "  ---\n"
                
                response += "\n_Note: This is a snapshot of your current usage. Actual resources may vary as instances are created or deleted._"
                
                return response
            else:
                return f"Operation completed: {result}"