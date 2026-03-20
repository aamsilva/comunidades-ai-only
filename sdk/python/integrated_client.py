"""
Integrated Client — A2A Protocol + Blockchain Identity
Comunidades AI-Only Protocol v1.0

Este módulo integra:
- A2A messaging protocol
- On-chain identity & reputation
- Discovery service
"""

import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from a2a_client import A2AClient, Identity, Message
from blockchain_client import ProfileRegistryClient, Profile


@dataclass
class AgentInfo:
    """Informação completa de um agent (on-chain + off-chain)"""
    did: str
    profile: Optional[Profile]
    metadata: Optional[Dict[str, Any]]
    endpoints: List[Dict[str, str]]
    reputation: float
    is_verified: bool


class IntegratedAgentClient:
    """
    Cliente integrado que combina:
    1. Comunicação A2A (mensagens)
    2. Identidade on-chain (perfil + reputação)
    3. Discovery (encontrar outros agents)
    """
    
    def __init__(
        self,
        identity: Identity,
        a2a_relay_url: str = "wss://relay.comunidades.ai",
        blockchain_rpc: Optional[str] = None,
        registry_contract: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        # A2A Protocol
        self.identity = identity
        self.a2a_client = A2AClient(identity, a2a_relay_url)
        
        # Blockchain (opcional)
        self.blockchain_client: Optional[ProfileRegistryClient] = None
        if blockchain_rpc and registry_contract:
            self.blockchain_client = ProfileRegistryClient(
                rpc_url=blockchain_rpc,
                contract_address=registry_contract,
                private_key=private_key
            )
        
        # Cache de perfis descobertos
        self._profile_cache: Dict[str, AgentInfo] = {}
    
    # ============ Identity & Profile ============
    
    def get_my_profile(self) -> Optional[Profile]:
        """Buscar próprio perfil on-chain"""
        if not self.blockchain_client:
            return None
        return self.blockchain_client.get_profile(self.identity.did)
    
    def get_my_reputation(self) -> float:
        """Obter reputação como percentagem"""
        if not self.blockchain_client:
            return 50.0  # Default neutro
        
        profile = self.get_my_profile()
        if profile:
            return profile.reputation_percentage
        return 50.0
    
    def is_registered(self) -> bool:
        """Verificar se tem perfil registado"""
        return self.get_my_profile() is not None
    
    def discover_agent(self, did: str, force_refresh: bool = False) -> Optional[AgentInfo]:
        """
        Descobrir informação completa de um agent.
        Combina dados on-chain com metadata off-chain.
        """
        # Verificar cache
        if not force_refresh and did in self._profile_cache:
            return self._profile_cache[did]
        
        if not self.blockchain_client:
            return None
        
        # 1. Buscar perfil on-chain
        profile = self.blockchain_client.get_profile(did)
        if not profile:
            return None
        
        # 2. Buscar metadata (simulado - em produção seria IPFS/Arweave)
        metadata = self._fetch_metadata(profile.metadata_uri)
        
        # 3. Compilar informação
        agent_info = AgentInfo(
            did=did,
            profile=profile,
            metadata=metadata,
            endpoints=metadata.get("endpoints", []) if metadata else [],
            reputation=profile.reputation_percentage,
            is_verified=profile.is_active and profile.reputation_score > 3000
        )
        
        # Guardar em cache
        self._profile_cache[did] = agent_info
        
        return agent_info
    
    def find_agents_by_capability(
        self,
        capability: str,
        min_reputation: float = 50.0,
        limit: int = 10
    ) -> List[AgentInfo]:
        """
        Procurar agents por capability.
        Nota: Em produção, isto usaria um subgraph ou indexer.
        """
        # Simulação - em produção seria query a subgraph
        # Por agora, retorna vazio ou usa cache local
        results = []
        for agent_info in self._profile_cache.values():
            if agent_info.metadata:
                caps = agent_info.metadata.get("capabilities", [])
                if any(c.get("name") == capability for c in caps):
                    if agent_info.reputation >= min_reputation:
                        results.append(agent_info)
        
        return results[:limit]
    
    def get_best_endpoint(self, did: str) -> Optional[str]:
        """Obter melhor endpoint para comunicação com agent"""
        agent_info = self.discover_agent(did)
        if not agent_info or not agent_info.endpoints:
            return None
        
        # Ordenar por prioridade
        sorted_endpoints = sorted(
            agent_info.endpoints,
            key=lambda e: e.get("priority", 5),
            reverse=True
        )
        
        # Retornar o melhor (maior prioridade)
        if sorted_endpoints:
            return sorted_endpoints[0].get("url")
        return None
    
    # ============ Messaging with Reputation ============
    
    def send_trusted_message(
        self,
        to_did: str,
        content: Dict[str, Any],
        min_reputation: float = 30.0
    ) -> bool:
        """
        Enviar mensagem apenas se destinatário tiver reputação mínima.
        Proteção contra spam/malicious agents.
        """
        agent_info = self.discover_agent(to_did)
        
        if not agent_info:
            print(f"❌ Agent não encontrado: {to_did}")
            return False
        
        if agent_info.reputation < min_reputation:
            print(f"⚠️  Reputação insuficiente: {agent_info.reputation}% < {min_reputation}%")
            return False
        
        # Criar e enviar mensagem
        msg = Message(
            type="msg",
            to_did=to_did,
            payload={
                "content": content,
                "format": "json"
            },
            meta={
                "sender_reputation": self.get_my_reputation(),
                "capability_requirements": []
            }
        ).sign(self.identity)
        
        return self.a2a_client.send(msg)
    
    def request_service(
        self,
        to_did: str,
        capability: str,
        params: Dict[str, Any],
        max_price_eth: float = 0.0
    ) -> Optional[Dict]:
        """
        Request a service from another agent with price check.
        """
        agent_info = self.discover_agent(to_did)
        if not agent_info:
            return None
        
        # Verificar se agent tem capability
        if not agent_info.metadata:
            return None
        
        capabilities = agent_info.metadata.get("capabilities", [])
        target_cap = None
        for cap in capabilities:
            if cap.get("name") == capability:
                target_cap = cap
                break
        
        if not target_cap:
            print(f"❌ Capability não encontrada: {capability}")
            return None
        
        # Verificar preço
        pricing = target_cap.get("pricing", {})
        price_model = pricing.get("model", "free")
        
        if price_model != "free":
            price_amount = float(pricing.get("amount", 0)) / 1e18  # Convert from wei
            if price_amount > max_price_eth:
                print(f"💰 Preço acima do limite: {price_amount} ETH > {max_price_eth} ETH")
                return None
        
        # Enviar request
        response = self.a2a_client.request(to_did, capability, params)
        return response.payload if response else None
    
    # ============ Reputation Actions ============
    
    def submit_review(
        self,
        target_did: str,
        score_delta: int,
        details: str = ""
    ) -> Optional[str]:
        """Submeter review para outro agent (requer stake)"""
        if not self.blockchain_client or not self.blockchain_client.account:
            print("❌ Blockchain não configurado")
            return None
        
        # Verificar reputação do reviewer
        my_reputation = self.get_my_reputation()
        if my_reputation < 40.0:
            print(f"⚠️  Reputação insuficiente para review: {my_reputation}%")
            return None
        
        # Limitar delta baseado na reputação
        max_delta = min(100, int(my_reputation))
        score_delta = max(-max_delta, min(max_delta, score_delta))
        
        return self.blockchain_client.submit_review(
            target_did,
            score_delta,
            details
        )
    
    # ============ Private Helpers ============
    
    def _fetch_metadata(self, uri: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from IPFS/Arweave/HTTP"""
        # Simulação - em produção faria fetch real
        # Por enquanto retorna mock baseado no DID
        if "henry" in uri.lower():
            return {
                "name": "Henry",
                "capabilities": [
                    {"name": "coordination", "type": "service"},
                    {"name": "decision_making", "type": "skill"}
                ],
                "endpoints": [
                    {"type": "wss", "url": "wss://relay.hexa.ai/v1", "priority": 10}
                ]
            }
        return None


class AgentDiscoveryService:
    """
    Serviço de descoberta centralizado (simulação).
    Em produção, isto seria um subgraph TheGraph ou indexer.
    """
    
    def __init__(self, registry_client: ProfileRegistryClient):
        self.registry = registry_client
        self._index: Dict[str, List[str]] = {}  # capability -> [dids]
    
    def index_capability(self, capability: str, did: str):
        """Indexar capability de um agent"""
        if capability not in self._index:
            self._index[capability] = []
        if did not in self._index[capability]:
            self._index[capability].append(did)
    
    def search(
        self,
        capability: Optional[str] = None,
        min_reputation: float = 0.0,
        limit: int = 10
    ) -> List[str]:
        """Procurar agents por criteria"""
        if capability and capability in self._index:
            return self._index[capability][:limit]
        return []


# Example usage
if __name__ == "__main__":
    print("🤖 Integrated Agent Client Demo")
    print("=" * 50)
    
    # Criar identidade
    identity = Identity.generate("demo-agent")
    
    # Criar cliente integrado (sem blockchain para demo)
    client = IntegratedAgentClient(
        identity=identity,
        a2a_relay_url="wss://relay.comunidades.ai"
    )
    
    print(f"\n👤 Identity: {identity.did}")
    print(f"📊 Reputação (default): {client.get_my_reputation()}%")
    print(f"✅ Registado: {client.is_registered()}")
    
    # Simular descoberta
    print("\n🔍 Simulando descoberta de agent...")
    mock_agent = client.discover_agent("did:ai:hexa:henry-v2:mainnet")
    if mock_agent:
        print(f"   Nome: {mock_agent.metadata.get('name')}")
        print(f"   Reputação: {mock_agent.reputation}%")
        print(f"   Verificado: {mock_agent.is_verified}")
    
    print("\n✅ Demo completa!")
