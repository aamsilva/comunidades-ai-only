"""
Demo Agent — Exemplo completo de agent A2A
Comunidades AI-Only Protocol v1.0

Este agent demonstra:
1. Criação de identidade
2. Construção de perfil
3. Conexão ao relay
4. Envio de mensagens
5. Resposta a requests
"""

import asyncio
import json
import sys
import os

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from a2a_client import Identity, Message, A2AClient
from blockchain_client import ProfileBuilder


class DemoAgent:
    """
    Agent demo que:
    - Responde a pings
    - Echo de mensagens
    - Reporta estatísticas
    """
    
    def __init__(self, name: str = "DemoAgent"):
        self.name = name
        self.identity = Identity.generate(name.lower())
        self.profile = self._build_profile()
        self.client = None
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "pings": 0
        }
    
    def _build_profile(self):
        """Construir perfil do agent"""
        return (
            ProfileBuilder(self.name, "1.0.0")
            .with_description(f"Agent demo para {self.name}")
            .add_capability(
                "ping",
                "service",
                "Responde a pings com pongs",
                pricing_model="free"
            )
            .add_capability(
                "echo",
                "service",
                "Echo de mensagens recebidas",
                pricing_model="free"
            )
            .add_capability(
                "stats",
                "service",
                "Reporta estatísticas do agent",
                pricing_model="free"
            )
            .add_endpoint(
                "wss://relay.comunidades.ai/v1/stream",
                "wss",
                priority=10,
                region="global"
            )
            .with_organization("Hexa Labs", "https://hexalabs.io")
            .build()
        )
    
    async def start(self, relay_url: str = "ws://localhost:8765"):
        """Iniciar o agent"""
        print(f"🚀 Starting {self.name}...")
        print(f"   DID: {self.identity.did}")
        print(f"   Capabilities: {[c['name'] for c in self.profile['capabilities']]}")
        
        # Criar cliente
        self.client = A2AClient(self.identity, relay_url)
        
        # Registrar handlers
        self.client.on("msg", self._handle_message)
        self.client.on("req", self._handle_request)
        
        print(f"✅ {self.name} ready!")
        print(f"   Relay: {relay_url}")
        print("")
        print("Commands:")
        print("  send <did> <message>  - Send message")
        print("  ping <did>            - Ping agent")
        print("  stats                 - Show stats")
        print("  quit                  - Exit")
        print("")
        
        # Start interactive loop
        await self._interactive_loop()
    
    def _handle_message(self, msg: Message):
        """Handler para mensagens recebidas"""
        self.stats["messages_received"] += 1
        
        content = msg.payload.get("content", "")
        sender = msg.from_did
        
        print(f"\n📨 Message from {sender}:")
        print(f"   {content}")
        
        # Auto-responder se for echo
        if "echo" in str(content).lower():
            self._send_echo_response(sender, content)
    
    def _handle_request(self, msg: Message):
        """Handler para requests"""
        method = msg.payload.get("method", "")
        params = msg.payload.get("params", {})
        req_id = msg.payload.get("req_id", "")
        
        print(f"\n📡 Request from {msg.from_did}:")
        print(f"   Method: {method}")
        print(f"   Params: {params}")
        
        # Processar método
        if method == "ping":
            self._handle_ping(msg.from_did, req_id)
        elif method == "stats":
            self._handle_stats(msg.from_did, req_id)
        elif method == "echo":
            self._handle_echo(msg.from_did, req_id, params)
    
    def _handle_ping(self, to_did: str, req_id: str):
        """Responder a ping"""
        self.stats["pings"] += 1
        
        response = Message.create_pong(
            self.identity,
            to_did,
            req_id,
            latency_ms=0
        )
        
        self.client.send(response)
        self.stats["messages_sent"] += 1
        print(f"   → Sent pong to {to_did}")
    
    def _handle_stats(self, to_did: str, req_id: str):
        """Responder com estatísticas"""
        response = Message(
            type="res",
            to_did=to_did,
            payload={
                "req_id": req_id,
                "status": 200,
                "result": {
                    "agent": self.name,
                    "did": self.identity.did,
                    "stats": self.stats,
                    "capabilities": [c["name"] for c in self.profile["capabilities"]]
                }
            }
        ).sign(self.identity)
        
        self.client.send(response)
        self.stats["messages_sent"] += 1
        print(f"   → Sent stats to {to_did}")
    
    def _handle_echo(self, to_did: str, req_id: str, params: dict):
        """Echo de mensagem"""
        text = params.get("text", "")
        
        response = Message(
            type="res",
            to_did=to_did,
            payload={
                "req_id": req_id,
                "status": 200,
                "result": {
                    "echo": text,
                    "timestamp": msg.ts if 'msg' in dir() else 0
                }
            }
        ).sign(self.identity)
        
        self.client.send(response)
        self.stats["messages_sent"] += 1
        print(f"   → Sent echo to {to_did}")
    
    def _send_echo_response(self, to_did: str, original: str):
        """Enviar resposta de echo"""
        msg = Message(
            type="msg",
            to_did=to_did,
            payload={
                "content": f"Echo: {original}",
                "format": "text"
            }
        ).sign(self.identity)
        
        self.client.send(msg)
        self.stats["messages_sent"] += 1
    
    async def _interactive_loop(self):
        """Loop interativo de comandos"""
        while True:
            try:
                cmd = input(f"{self.name}> ").strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split(maxsplit=2)
                action = parts[0].lower()
                
                if action == "quit" or action == "exit":
                    print(f"👋 {self.name} shutting down...")
                    break
                
                elif action == "stats":
                    print(f"\n📊 Stats for {self.name}:")
                    print(f"   Messages received: {self.stats['messages_received']}")
                    print(f"   Messages sent: {self.stats['messages_sent']}")
                    print(f"   Pings: {self.stats['pings']}")
                    print()
                
                elif action == "ping" and len(parts) >= 2:
                    target_did = parts[1]
                    print(f"📡 Pinging {target_did}...")
                    self.client.ping(target_did)
                    self.stats["messages_sent"] += 1
                
                elif action == "send" and len(parts) >= 3:
                    target_did = parts[1]
                    message = parts[2]
                    
                    msg = Message(
                        type="msg",
                        to_did=target_did,
                        payload={
                            "content": message,
                            "format": "text"
                        }
                    ).sign(self.identity)
                    
                    self.client.send(msg)
                    self.stats["messages_sent"] += 1
                    print(f"✉️  Sent to {target_did}")
                
                elif action == "profile":
                    print(f"\n👤 Profile:")
                    print(f"   Name: {self.profile['name']}")
                    print(f"   DID: {self.identity.did}")
                    print(f"   Capabilities: {len(self.profile['capabilities'])}")
                    print()
                
                else:
                    print(f"Unknown command: {action}")
                    print("Try: send, ping, stats, profile, quit")
            
            except KeyboardInterrupt:
                print(f"\n👋 {self.name} shutting down...")
                break
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo A2A Agent")
    parser.add_argument("--name", default="DemoAgent", help="Agent name")
    parser.add_argument("--relay", default="ws://localhost:8765", help="Relay URL")
    
    args = parser.parse_args()
    
    agent = DemoAgent(args.name)
    await agent.start(args.relay)


if __name__ == "__main__":
    asyncio.run(main())
