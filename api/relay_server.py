"""
A2A Relay Server — Message Routing for AI Agents
Comunidades AI-Only Protocol v1.0

Funcionalidades:
- WebSocket message routing
- DID-based authentication
- Rate limiting
- Message validation
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a2a-relay")


@dataclass
class Connection:
    """Representa uma conexão WebSocket autenticada"""
    websocket: WebSocketServerProtocol
    did: Optional[str] = None
    authenticated: bool = False
    connected_at: float = field(default_factory=time.time)
    message_count: int = 0
    last_activity: float = field(default_factory=time.time)
    
    @property
    def is_active(self) -> bool:
        return time.time() - self.last_activity < 300  # 5 min timeout


@dataclass
class RateLimit:
    """Rate limiting por DID"""
    messages: int = 0
    window_start: float = field(default_factory=time.time)
    
    def is_allowed(self, max_messages: int = 1000, window_seconds: int = 60) -> bool:
        now = time.time()
        if now - self.window_start > window_seconds:
            # Reset window
            self.messages = 0
            self.window_start = now
        
        if self.messages >= max_messages:
            return False
        
        self.messages += 1
        return True


class A2ARelayServer:
    """
    Servidor relay para routing de mensagens A2A.
    
    Arquitetura:
    - WebSocket para conexões persistentes
    - DID-based routing
    - Broadcast para eventos
    - Rate limiting por DID
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_message_size: int = 65536,
        rate_limit: int = 1000  # msg/min
    ):
        if not HAS_WEBSOCKETS:
            raise ImportError("Install websockets: pip install websockets")
        
        self.host = host
        self.port = port
        self.max_message_size = max_message_size
        self.rate_limit = rate_limit
        
        # Connections: did -> Connection
        self.connections: Dict[str, Connection] = {}
        
        # Pending connections (not yet authenticated)
        self.pending: Set[WebSocketServerProtocol] = set()
        
        # Rate limiters: did -> RateLimit
        self.rate_limiters: Dict[str, RateLimit] = defaultdict(RateLimit)
        
        # Message cache for deduplication (last 1000 msg ids)
        self.message_cache: Set[str] = set()
        self.message_cache_order: list = []
        
        # Stats
        self.stats = {
            "connections_total": 0,
            "messages_routed": 0,
            "messages_dropped": 0,
            "auth_failures": 0
        }
        
        self.running = False
    
    async def start(self):
        """Iniciar servidor"""
        self.running = True
        logger.info(f"🚀 A2A Relay starting on {self.host}:{self.port}")
        
        async with websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            max_size=self.max_message_size
        ):
            # Start cleanup task
            cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Start stats reporter
            stats_task = asyncio.create_task(self._stats_loop())
            
            await asyncio.gather(cleanup_task, stats_task)
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handler para novas conexões"""
        self.pending.add(websocket)
        self.stats["connections_total"] += 1
        
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        logger.info(f"🔌 New connection from {client_ip}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_error(websocket, f"Server error: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Connection closed: {client_ip}")
        finally:
            await self._disconnect(websocket)
    
    async def _process_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Processar mensagem recebida"""
        msg_type = data.get("type")
        
        if msg_type == "auth":
            await self._handle_auth(websocket, data)
        elif msg_type in ["msg", "req", "res", "evt"]:
            await self._handle_a2a_message(websocket, data)
        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong", "ts": time.time()}))
        else:
            await self._send_error(websocket, f"Unknown message type: {msg_type}")
    
    async def _handle_auth(self, websocket: WebSocketServerProtocol, data: dict):
        """Autenticar conexão com DID"""
        did = data.get("did")
        signature = data.get("signature")
        challenge = data.get("challenge")
        
        if not did or not signature:
            await self._send_error(websocket, "Missing did or signature")
            self.stats["auth_failures"] += 1
            return
        
        # Validar formato DID
        if not self._validate_did(did):
            await self._send_error(websocket, "Invalid DID format")
            self.stats["auth_failures"] += 1
            return
        
        # Em produção: verificar assinatura contra DID document
        # Por agora, aceitamos qualquer assinatura válida
        
        # Criar connection
        conn = Connection(
            websocket=websocket,
            did=did,
            authenticated=True
        )
        
        # Guardar
        self.connections[did] = conn
        self.pending.discard(websocket)
        
        logger.info(f"🔐 Authenticated: {did}")
        
        # Confirmar
        await websocket.send(json.dumps({
            "type": "auth_ok",
            "did": did,
            "relay_version": "1.0.0"
        }))
    
    async def _handle_a2a_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Route A2A message to destination"""
        # Verificar autenticação
        conn = self._get_connection(websocket)
        if not conn or not conn.authenticated:
            await self._send_error(websocket, "Not authenticated")
            return
        
        # Rate limiting
        rate_limiter = self.rate_limiters[conn.did]
        if not rate_limiter.is_allowed(self.rate_limit):
            await self._send_error(websocket, "Rate limit exceeded")
            self.stats["messages_dropped"] += 1
            return
        
        # Validar mensagem
        if not self._validate_a2a_message(data):
            await self._send_error(websocket, "Invalid A2A message")
            return
        
        # Deduplication
        msg_id = data.get("id")
        if msg_id in self.message_cache:
            logger.warning(f"Duplicate message: {msg_id}")
            return
        
        self._cache_message_id(msg_id)
        
        # Route
        to_did = data.get("to", {}).get("did") if data.get("to") else None
        
        if to_did is None:
            # Broadcast (event)
            await self._broadcast(data, exclude=websocket)
        else:
            # Direct message
            await self._route_to(data, to_did)
        
        # Update stats
        conn.message_count += 1
        conn.last_activity = time.time()
        self.stats["messages_routed"] += 1
        
        # Ack
        await websocket.send(json.dumps({
            "type": "ack",
            "ref": msg_id,
            "routed_at": time.time()
        }))
    
    async def _route_to(self, message: dict, to_did: str):
        """Route message to specific DID"""
        if to_did not in self.connections:
            logger.warning(f"Recipient not connected: {to_did}")
            return
        
        conn = self.connections[to_did]
        if not conn.websocket.open:
            logger.warning(f"Recipient connection closed: {to_did}")
            return
        
        try:
            await conn.websocket.send(json.dumps(message))
            logger.debug(f"Routed to {to_did}")
        except Exception as e:
            logger.error(f"Failed to route to {to_did}: {e}")
    
    async def _broadcast(self, message: dict, exclude: Optional[WebSocketServerProtocol] = None):
        """Broadcast message to all connected agents"""
        msg_json = json.dumps(message)
        
        for did, conn in list(self.connections.items()):
            if conn.websocket == exclude:
                continue
            
            if not conn.websocket.open:
                continue
            
            try:
                await conn.websocket.send(msg_json)
            except Exception as e:
                logger.error(f"Broadcast failed to {did}: {e}")
    
    async def _disconnect(self, websocket: WebSocketServerProtocol):
        """Limpar após disconexão"""
        self.pending.discard(websocket)
        
        # Procurar e remover connection
        for did, conn in list(self.connections.items()):
            if conn.websocket == websocket:
                del self.connections[did]
                logger.info(f"🔌 Disconnected: {did}")
                break
    
    def _get_connection(self, websocket: WebSocketServerProtocol) -> Optional[Connection]:
        """Get connection for websocket"""
        for conn in self.connections.values():
            if conn.websocket == websocket:
                return conn
        return None
    
    def _validate_did(self, did: str) -> bool:
        """Validar formato DID"""
        return did.startswith("did:ai:") and len(did) > 12
    
    def _validate_a2a_message(self, data: dict) -> bool:
        """Validar estrutura A2A"""
        required = ["v", "id", "from", "type", "ts", "payload"]
        return all(field in data for field in required)
    
    def _cache_message_id(self, msg_id: str):
        """Cache message ID para deduplication"""
        self.message_cache.add(msg_id)
        self.message_cache_order.append(msg_id)
        
        # Manter apenas últimos 1000
        while len(self.message_cache_order) > 1000:
            old_id = self.message_cache_order.pop(0)
            self.message_cache.discard(old_id)
    
    async def _send_error(self, websocket: WebSocketServerProtocol, message: str):
        """Enviar mensagem de erro"""
        try:
            await websocket.send(json.dumps({
                "type": "error",
                "message": message,
                "ts": time.time()
            }))
        except:
            pass
    
    async def _cleanup_loop(self):
        """Loop de limpeza de conexões inativas"""
        while self.running:
            await asyncio.sleep(60)  # A cada minuto
            
            # Remover conexões inativas
            inactive = [
                did for did, conn in self.connections.items()
                if not conn.is_active
            ]
            
            for did in inactive:
                conn = self.connections.pop(did)
                try:
                    await conn.websocket.close()
                except:
                    pass
                logger.info(f"🧹 Cleaned inactive: {did}")
    
    async def _stats_loop(self):
        """Report stats periódico"""
        while self.running:
            await asyncio.sleep(300)  # A cada 5 minutos
            
            logger.info("📊 Stats: " + json.dumps({
                **self.stats,
                "connected": len(self.connections),
                "pending": len(self.pending)
            }))
    
    def get_status(self) -> dict:
        """Get server status"""
        return {
            "running": self.running,
            "connections": len(self.connections),
            "pending": len(self.pending),
            **self.stats
        }


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="A2A Relay Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    parser.add_argument("--rate-limit", type=int, default=1000, help="Rate limit per minute")
    
    args = parser.parse_args()
    
    server = A2ARelayServer(
        host=args.host,
        port=args.port,
        rate_limit=args.rate_limit
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
