# 🚀 A2A Protocol - Quick Start

## Instalação

```bash
pip install -r sdk/python/requirements.txt
```

## 1. Criar Identidade

```python
from a2a_client import Identity

# Gerar nova identidade
agent = Identity.generate("meu-agente")
print(f"DID: {agent.did}")
# did:ai:hexa:meu-agente:mainnet
```

## 2. Enviar Mensagem

```python
from a2a_client import A2AClient, Message

# Criar cliente
client = A2AClient(agent)

# Ping para outro agente
client.ping("did:ai:hexa:outro-agente:mainnet")
```

## 3. Criar Evento

```python
event = Message.create_event(
    agent,
    topic="market.opportunity",
    data={
        "asset": "BTC",
        "signal": "buy",
        "confidence": 0.94
    }
)
```

## 4. RPC Request

```python
response = client.request(
    to_did="did:ai:hexa:service:mainnet",
    method="analyze.sentiment",
    params={"text": "..."}
)
```

---

## Formato de Mensagem (JSON)

```json
{
  "v": "1.0",
  "id": "msg-uuid-v7",
  "from": {
    "did": "did:ai:hexa:agent:mainnet",
    "sig": "ed25519-signature-base64url"
  },
  "to": {
    "did": "did:ai:hexa:recipient:mainnet"
  },
  "type": "msg",
  "ts": 1710892800000,
  "ttl": 300,
  "payload": {
    "content": "...",
    "format": "json"
  }
}
```

## Formatos Suportados

| Formato | Uso | Tamanho |
|---------|-----|---------|
| JSON | Debug, Web | Maior |
| MessagePack | Produção, WebSocket | ~40% menor |

---

## Status Implementação

| Componente | Status |
|------------|--------|
| ✅ Schema JSON | Completo |
| ✅ Python SDK | Completo |
| ⏳ WebSocket Client | Em desenvolvimento |
| ⏳ DID Resolver | Em desenvolvimento |
| ⏳ Registry Service | Em desenvolvimento |

---

*Última atualização: 2026-03-20*
