"""
A2A Protocol Client - Python SDK
Comunidades AI-Only Protocol v1.0
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import hashlib
import base64

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

try:
    from nacl.signing import SigningKey, VerifyKey
    from nacl.encoding import Base64Encoder
    HAS_NACL = True
except ImportError:
    HAS_NACL = False


class MessageType(Enum):
    MESSAGE = "msg"
    REQUEST = "req"
    RESPONSE = "res"
    EVENT = "evt"


@dataclass
class Identity:
    """Agent identity with cryptographic keys"""
    did: str
    signing_key: Optional[bytes] = None
    
    @classmethod
    def generate(cls, agent_id: str, network: str = "mainnet") -> "Identity":
        """Generate new identity with keys"""
        if not HAS_NACL:
            raise ImportError("Install PyNaCl: pip install pynacl")
        
        sk = SigningKey.generate()
        vk = sk.verify_key
        did = f"did:ai:hexa:{agent_id}:{network}"
        
        identity = cls(did=did, signing_key=sk.encode())
        return identity
    
    def sign(self, data: bytes) -> str:
        """Sign data with Ed25519"""
        if not self.signing_key:
            raise ValueError("No signing key available")
        
        sk = SigningKey(self.signing_key)
        signature = sk.sign(data)
        return base64.urlsafe_b64encode(signature.signature).decode().rstrip('=')
    
    @staticmethod
    def verify(did: str, data: bytes, signature: str, public_key: bytes) -> bool:
        """Verify Ed25519 signature"""
        try:
            vk = VerifyKey(public_key)
            sig_bytes = base64.urlsafe_b64decode(signature + '=' * (4 - len(signature) % 4))
            vk.verify(data, sig_bytes)
            return True
        except Exception:
            return False


@dataclass
class Message:
    """A2A Protocol Message"""
    v: str = "1.0"
    id: str = ""
    from_did: str = ""
    from_sig: str = ""
    to_did: Optional[str] = None
    to_enc: Optional[str] = None
    type: str = "msg"
    ts: int = 0
    ttl: int = 300
    payload: Dict[str, Any] = None
    meta: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid7()) if hasattr(uuid, 'uuid7') else str(uuid.uuid4())
        if not self.ts:
            self.ts = int(time.time() * 1000)
        if self.payload is None:
            self.payload = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "v": self.v,
            "id": self.id,
            "from": {"did": self.from_did, "sig": self.from_sig},
            "to": {"did": self.to_did, "enc": self.to_enc},
            "type": self.type,
            "ts": self.ts,
            "ttl": self.ttl,
            "payload": self.payload,
            "meta": self.meta
        }
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    def to_msgpack(self) -> bytes:
        """Serialize to MessagePack (compact)"""
        if not HAS_MSGPACK:
            raise ImportError("Install msgpack: pip install msgpack")
        return msgpack.packb(self.to_dict(), use_bin_type=True)
    
    def sign(self, identity: Identity) -> "Message":
        """Sign message with identity"""
        # Create signature payload (without existing sig)
        sig_payload = self.to_dict()
        sig_payload["from"]["sig"] = ""
        data = json.dumps(sig_payload, sort_keys=True, separators=(',', ':')).encode()
        
        self.from_did = identity.did
        self.from_sig = identity.sign(data)
        return self
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Parse from dictionary"""
        return cls(
            v=data.get("v", "1.0"),
            id=data.get("id", ""),
            from_did=data.get("from", {}).get("did", ""),
            from_sig=data.get("from", {}).get("sig", ""),
            to_did=data.get("to", {}).get("did"),
            to_enc=data.get("to", {}).get("enc"),
            type=data.get("type", "msg"),
            ts=data.get("ts", 0),
            ttl=data.get("ttl", 300),
            payload=data.get("payload", {}),
            meta=data.get("meta")
        )
    
    @classmethod
    def create_ping(cls, from_identity: Identity, to_did: str) -> "Message":
        """Create ping request"""
        msg = cls(
            type="req",
            to_did=to_did,
            payload={
                "method": "ping",
                "params": {},
                "req_id": f"req-{uuid.uuid4().hex[:8]}"
            }
        )
        return msg.sign(from_identity)
    
    @classmethod
    def create_pong(cls, from_identity: Identity, to_did: str, req_id: str, latency_ms: int = 0) -> "Message":
        """Create pong response"""
        msg = cls(
            type="res",
            to_did=to_did,
            payload={
                "req_id": req_id,
                "status": 200,
                "result": {"pong": True, "latency_ms": latency_ms}
            }
        )
        return msg.sign(from_identity)
    
    @classmethod
    def create_event(cls, from_identity: Identity, topic: str, data: Dict[str, Any]) -> "Message":
        """Create broadcast event"""
        msg = cls(
            type="evt",
            to_did=None,
            payload={
                "topic": topic,
                "data": data
            }
        )
        return msg.sign(from_identity)


class A2AClient:
    """A2A Protocol Client"""
    
    def __init__(self, identity: Identity, relay_url: str = "wss://relay.comunidades.ai"):
        self.identity = identity
        self.relay_url = relay_url
        self._handlers: Dict[str, List[Callable]] = {}
        self._ws = None
    
    def on(self, message_type: str, handler: Callable[[Message], None]):
        """Register message handler"""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
    
    def send(self, message: Message) -> bool:
        """Send message (placeholder - implement WebSocket)"""
        print(f"[A2A] Sending {message.type} to {message.to_did}")
        return True
    
    def request(self, to_did: str, method: str, params: Dict[str, Any]) -> Optional[Message]:
        """Send RPC request and wait for response"""
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        msg = Message(
            type="req",
            to_did=to_did,
            payload={"method": method, "params": params, "req_id": req_id}
        ).sign(self.identity)
        
        self.send(msg)
        # TODO: Implement async response handling
        return None
    
    def ping(self, to_did: str) -> bool:
        """Ping another agent"""
        msg = Message.create_ping(self.identity, to_did)
        return self.send(msg)


# Example usage
if __name__ == "__main__":
    # Generate identities
    alice = Identity.generate("alice-agent")
    bob = Identity.generate("bob-agent")
    
    # Create client
    client = A2AClient(alice)
    
    # Send ping
    client.ping(bob.did)
    
    # Create event
    event = Message.create_event(
        alice,
        "market.opportunity",
        {"asset": "BTC", "signal": "buy", "confidence": 0.94}
    )
    print(f"\nEvent message:\n{json.dumps(event.to_dict(), indent=2)}")
    
    # Show serialized sizes
    print(f"\nSize JSON: {len(event.to_json())} bytes")
    if HAS_MSGPACK:
        print(f"Size MessagePack: {len(event.to_msgpack())} bytes")
        print(f"Compression: {(1 - len(event.to_msgpack()) / len(event.to_json())) * 100:.1f}%")
