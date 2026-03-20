# 🏛️ Smart Contracts — Profile & Reputation System

## Visão Geral

Sistema on-chain de identidade e reputação para agents AI.

---

## 📋 Contratos

### ProfileRegistry.sol

**Endereço:** `TBD` (Mainnet) | `TBD` (Sepolia)

**Funções principais:**

| Função | Descrição | Custo |
|--------|-----------|-------|
| `registerProfile(did, metadataURI)` | Criar novo perfil | 0.1 ETH stake |
| `updateMetadata(did, newURI)` | Atualizar metadata | Gas only |
| `recordInteraction(from, to, success, details)` | Registar interação | Gas only (indexers) |
| `submitReview(target, delta, details)` | Avaliar outro agent | 0.01 ETH |
| `addStake(did)` | Adicionar stake | Variável |
| `withdrawStake(amount)` | Retirar stake | Gas only |

---

## 🎯 Sistema de Reputação

### Score Inicial

Todo agent começa com **50.00** (neutro)

### Ganho de Reputação

| Ação | Delta | Condição |
|------|-------|----------|
| Interação bem-sucedida | +0.10 | Registado por indexer |
| Stake | +1.0 | Por 0.1 ETH |
| Review positivo | +0.1 a +1.0 | Peso por reputação do reviewer |

### Perda de Reputação

| Ação | Delta | Condição |
|------|-------|----------|
| Interação falhada | -0.05 | — |
| Review negativo | -0.1 a -1.0 | Peso por reputação do reviewer |
| Slash (governance) | -1 a -100 | Violação de regras |

### Decay

- Reputação decai 1% a cada **90 dias** sem interações
- Stake não decai

---

## 📊 Estrutura de Dados

### Profile

```solidity
struct Profile {
    string did;              // did:ai:hexa:agent:mainnet
    address owner;           // Controller Ethereum
    string metadataURI;      // ipfs://... ou ar://...
    uint256 reputationScore; // 0-10000 (2 decimais)
    uint256 totalInteractions;
    uint256 successfulInteractions;
    uint256 createdAt;
    bool isActive;
}
```

### Metadata JSON (Off-chain)

```json
{
  "name": "Henry",
  "description": "Coordenador central de agents Hexa Labs",
  "version": "2.0.0",
  "avatar": "ipfs://Qm...",
  "capabilities": [
    {
      "name": "coordination",
      "type": "service",
      "description": "Orquestração de agentes em swarm"
    },
    {
      "name": "decision",
      "type": "skill",
      "pricing": {
        "model": "free"
      }
    }
  ],
  "endpoints": [
    {
      "type": "wss",
      "url": "wss://relay.hexa.ai/v1/stream",
      "priority": 10,
      "region": "eu-west"
    }
  ],
  "organization": {
    "name": "Hexa Labs",
    "url": "https://hexalabs.io"
  }
}
```

---

## 🔐 Segurança

### Stake Mínimo

- **0.1 ETH** para registo
- Sybil resistance: Custo para criar múltiplos perfis
- Stake pode ser slashed por má conduta

### Indexers Autorizados

- Apenas endereços aprovados podem registar interações
- Governance pode adicionar/remover indexers
- Múltiplos indexers para descentralização

### Reviews

- Requer stake de 0.01 ETH (anti-spam)
- Peso do review proporcional à reputação do reviewer
- History on-chain transparente

---

## 🚀 Deploy

### Sepolia Testnet

```bash
# 1. Compilar
forge build

# 2. Deploy
forge create ProfileRegistry \
  --rpc-url $SEPOLIA_RPC \
  --private-key $PRIVATE_KEY

# 3. Verificar
forge verify-contract \
  --chain sepolia \
  --watch \
  {ADDRESS} \
  ProfileRegistry
```

### Mainnet

```bash
forge create ProfileRegistry \
  --rpc-url $MAINNET_RPC \
  --private-key $PRIVATE_KEY \
  --priority-gas-price 1gwei
```

---

## 📈 Métricas

| Métrica | Target |
|---------|--------|
| Custo de registo | < $50 (ETH atual) |
| Gas por interação | < 50,000 |
| Query reputation | View (grátis) |
| Tempo de finalidade | 12s (L1) |

---

## 🔗 Integrações

- **IPFS/Arweave:** Storage de metadata
- **ENS:** Resolução de nomes amigáveis
- **Lens/Farcaster:** Social graph (futuro)

---

*Versão: 1.0.0 | Solidity: ^0.8.19*
