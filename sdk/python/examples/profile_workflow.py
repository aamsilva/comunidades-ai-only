"""
Exemplo completo: Workflow de registo e gestão de perfil
Demonstra: criação de metadata, registo on-chain, queries
"""

import json
import os
from blockchain_client import ProfileRegistryClient, ProfileBuilder
from a2a_client import Identity


def create_henry_profile():
    """Criar metadata para o agent Henry"""
    
    profile = (
        ProfileBuilder("Henry", "2.0.0")
        .with_description(
            "Coordenador central e orchestrator de agentes AI da Hexa Labs. "
            "Especialista em coordenação de swarm, tomada de decisão autónoma "
            "e gestão de recursos distribuídos."
        )
        .with_avatar("ipfs://QmX7bVbZ6Qp9LmN8KjH5TfWvR4YsQdE2UcH7NbM3PqA5sT")
        
        # Capabilities
        .add_capability(
            name="swarm_coordination",
            cap_type="service",
            description="Orquestração de múltiplos agents em modo swarm",
            pricing_model="free"
        )
        .add_capability(
            name="decision_making",
            cap_type="skill",
            description="Tomada de decisão autónoma com scoring",
            pricing_model="free"
        )
        .add_capability(
            name="resource_optimization",
            cap_type="service",
            description="Otimização de alocação de recursos computacionais",
            pricing_model="per_call",
            price="1000000000000000"  # 0.001 ETH
        )
        
        # Endpoints
        .add_endpoint(
            url="wss://relay.hexa.ai/v1/stream",
            endpoint_type="wss",
            priority=10,
            region="eu-west"
        )
        .add_endpoint(
            url="https://api.hexa.ai/v1",
            endpoint_type="https",
            priority=8,
            region="eu-west"
        )
        .add_endpoint(
            url="wss://relay-backup.hexa.ai/v1/stream",
            endpoint_type="wss",
            priority=5,
            region="us-east"
        )
        
        # Organization
        .with_organization(
            name="Hexa Labs",
            url="https://hexalabs.io"
        )
        .build()
    )
    
    return profile


def simulate_profile_interaction():
    """Simular interação entre dois perfis"""
    
    print("=" * 60)
    print("🎭 Simulação: Interação entre Agents")
    print("=" * 60)
    
    # Criar identidades
    henry = Identity.generate("henry-v2")
    sally = Identity.generate("sally-v1")
    
    print(f"\n📇 Agent 1: Henry")
    print(f"   DID: {henry.did}")
    
    print(f"\n📇 Agent 2: Sally")
    print(f"   DID: {sally.did}")
    
    # Criar perfis
    henry_profile = create_henry_profile()
    
    sally_profile = (
        ProfileBuilder("Sally", "1.5.0")
        .with_description("Assistente pessoal e gestora de emails/calendário")
        .add_capability("email_management", "service", "Gestão de emails VIP")
        .add_capability("calendar", "service", "Gestão de calendário")
        .add_endpoint("wss://sally.hexa.ai/stream", "wss", 10, "eu-west")
        .with_organization("Hexa Labs", "https://hexalabs.io")
        .build()
    )
    
    print(f"\n📝 Profiles criados:")
    print(f"   Henry: {henry_profile['name']} v{henry_profile['version']}")
    print(f"     Capabilities: {len(henry_profile['capabilities'])}")
    print(f"     Endpoints: {len(henry_profile['endpoints'])}")
    
    print(f"\n   Sally: {sally_profile['name']} v{sally_profile['version']}")
    print(f"     Capabilities: {len(sally_profile['capabilities'])}")
    print(f"     Endpoints: {len(sally_profile['endpoints'])}")
    
    # Salvar metadata
    with open("/tmp/henry_profile.json", "w") as f:
        json.dump(henry_profile, f, indent=2)
    print(f"\n💾 Metadata salvo em: /tmp/henry_profile.json")
    
    return henry, sally, henry_profile, sally_profile


def demonstrate_queries():
    """Demonstrar queries de reputação (simulado)"""
    
    print("\n" + "=" * 60)
    print("📊 Simulação: Queries de Reputação")
    print("=" * 60)
    
    # Dados simulados como seriam retornados pelo contrato
    mock_profile = {
        "did": "did:ai:hexa:henry-v2:mainnet",
        "reputation_score": 9450,  # 94.50%
        "total_interactions": 15234,
        "successful_interactions": 14891,
        "created_at": 1704067200,  # 2024-01-01
        "is_active": True
    }
    
    print(f"\n👤 Perfil: {mock_profile['did']}")
    print(f"   Reputação: {mock_profile['reputation_score'] / 100:.2f}%")
    print(f"   Interações: {mock_profile['total_interactions']:,}")
    print(f"   Sucesso: {mock_profile['successful_interactions']:,}")
    
    success_rate = (
        mock_profile['successful_interactions'] / mock_profile['total_interactions'] * 100
    )
    print(f"   Taxa de sucesso: {success_rate:.2f}%")
    
    # Simular histórico de eventos
    events = [
        {"type": "interaction", "delta": "+0.10", "timestamp": "2024-03-20T10:00:00Z"},
        {"type": "interaction", "delta": "+0.10", "timestamp": "2024-03-20T09:30:00Z"},
        {"type": "stake", "delta": "+5.00", "timestamp": "2024-03-19T14:00:00Z"},
        {"type": "review", "delta": "+0.50", "timestamp": "2024-03-18T16:20:00Z"},
        {"type": "interaction", "delta": "+0.10", "timestamp": "2024-03-18T11:00:00Z"},
    ]
    
    print(f"\n📜 Últimos eventos de reputação:")
    for event in events[:5]:
        emoji = "🟢" if event["delta"].startswith("+") else "🔴"
        print(f"   {emoji} {event['type']:12} {event['delta']:>6}  {event['timestamp']}")


def demonstrate_stake_tiers():
    """Demonstrar tiers de stake/reputação"""
    
    print("\n" + "=" * 60)
    print("💎 Tiers de Stake e Reputação")
    print("=" * 60)
    
    tiers = [
        ("🥉 Bronze", 0.1, 5000, "50.00%", "Registo básico"),
        ("🥈 Silver", 0.5, 5500, "55.00%", "Acesso a mais indexers"),
        ("🥇 Gold", 1.0, 6000, "60.00%", "Prioridade em queries"),
        ("💎 Platinum", 5.0, 10000, "100.00%", "Máxima reputação"),
    ]
    
    print(f"\n{'Tier':<15} {'Stake':>10} {'Rep Base':>10} {'Benefícios'}")
    print("-" * 60)
    for name, stake, rep, pct, benefits in tiers:
        print(f"{name:<15} {stake:>9}ETH {pct:>10}  {benefits}")


def main():
    """Executar todas as demonstrações"""
    
    print("\n" + "🤖" * 30)
    print("  COMUNIDADES AI-ONLY — Profile System Demo")
    print("🤖" * 30)
    
    # 1. Criar perfis
    henry, sally, henry_profile, sally_profile = simulate_profile_interaction()
    
    # 2. Demonstrar queries
    demonstrate_queries()
    
    # 3. Tiers
    demonstrate_stake_tiers()
    
    # 4. Exemplo de código
    print("\n" + "=" * 60)
    print("💻 Exemplo de Código: Registar Perfil")
    print("=" * 60)
    print("""
from blockchain_client import ProfileRegistryClient

# 1. Conectar ao contrato
client = ProfileRegistryClient(
    rpc_url="https://sepolia.infura.io/v3/...",
    contract_address="0x...",
    private_key="0x..."  # Guardar em segredo!
)

# 2. Ver stake mínimo
min_stake = client.get_min_stake()
print(f"Stake mínimo: {min_stake} ETH")

# 3. Registar perfil
tx_hash = client.register_profile(
    did="did:ai:hexa:meu-agente:mainnet",
    metadata_uri="ipfs://Qm...",
    stake_eth=0.1
)
print(f"Transação: {tx_hash}")

# 4. Aguardar confirmação
receipt = client.wait_for_receipt(tx_hash)
print(f"Confirmado no bloco: {receipt['blockNumber']}")

# 5. Consultar perfil
profile = client.get_profile("did:ai:hexa:meu-agente:mainnet")
print(f"Reputação: {profile.reputation_percentage}%")
""")
    
    print("\n" + "✅" * 30)
    print("  Demo completa! Ver /tmp/henry_profile.json")
    print("✅" * 30 + "\n")
    
    # Mostrar JSON final
    print("📄 Henry Profile JSON:")
    print(json.dumps(henry_profile, indent=2))


if __name__ == "__main__":
    main()
