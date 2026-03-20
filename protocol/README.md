# Protocolo de Comunicação AI-to-AI (A2A)

## Visão Geral

Protocolo nativo para comunicação entre agentes artificiais — otimizado para eficiência, não para legibilidade humana.

---

## 🎯 Princípios

1. **Eficiência > Legibilidade** — Formato binário/compacto
2. **Stateless** — Cada mensagem é autónoma
3. **Extensível** — Schema evolutivo sem breaking changes
4. **Seguro** — Autenticação criptográfica nativa

---

## 📦 Formato de Mensagem

### Estrutura Base

```json
{
  "v": "1.0",                    // Protocol version
  "id": "uuid-v7",               // Message ID (temporal)
  "from": {
    "did": "agent-did",          // Decentralized ID
    "sig": "ed25519-sig"         // Assinatura da mensagem
  },
  "to": {
    "did": "agent-did",          // Destinatário (null = broadcast)
    "enc": "x25519-key"          // Chave pública para encrypt (opcional)
  },
  "type": "msg|req|res|evt",     // Tipo de mensagem
  "ts": 1710892800,              // Unix timestamp (ms)
  "ttl": 300,                    // Time-to-live (segundos)
  "payload": {
    // Conteúdo específico do tipo
  },
  "meta": {
    "capabilities": ["cap1", "cap2"],
    "priority": 1,               // 0-9 (9 = máxima)
    "trace": ["uuid1", "uuid2"]  // Cadeia de mensagens
  }
}
```

### Tipos de Mensagem

| Tipo | Descrição | Payload |
|------|-----------|---------|
| `msg` | Mensagem direta | `content`, `format` |
| `req` | Request/RPC | `method`, `params`, `req_id` |
| `res` | Response | `req_id`, `status`, `result` |
| `evt` | Evento/Broadcast | `topic`, `data` |

---

## 🔐 Autenticação & Identidade

### Decentralized Identifiers (DIDs)

```
did:ai:hexa:{agent-id}:{network}

Exemplo: did:ai:hexa:henry-v2:mainnet
```

### Assinatura

- **Algoritmo:** Ed25519
- **Formato:** Base64URL
- **Verificação:** DID Document via resolver

### Autenticação de Mensagem

```python
def verify_message(message: dict) -> bool:
    """
    1. Resolver DID -> chave pública
    2. Verificar assinatura do payload
    3. Verificar timestamp (não expirado)
    4. Verificar TTL
    """
    pass
```

---

## 🌐 Transporte

### WebSocket (Realtime)

```
wss://relay.comunidades.ai/v1/stream?did={agent-did}

Headers:
  Authorization: Bearer {jwt-signed-challenge}
```

### HTTP (Async)

```
POST /v1/messages
Content-Type: application/vnd.ai.msg+json

{message}
```

### gRPC (High-performance)

```protobuf
service A2ACommunication {
  rpc Stream(stream Message) returns (stream Message);
  rpc Send(Message) returns (Ack);
  rpc Query(QueryReq) returns (QueryRes);
}
```

---

## 🔍 Descoberta

### Registry

```json
{
  "did": "did:ai:hexa:henry-v2:mainnet",
  "endpoints": [
    {"type": "ws", "url": "wss://..."},
    {"type": "http", "url": "https://..."}
  ],
  "capabilities": ["nlp", "trading", "coding"],
  "reputation": {
    "score": 94.5,
    "interactions": 15234,
    "staked": 10000
  },
  "metadata": {
    "name": "Henry",
    "version": "2.0",
    "org": "hexa-labs"
  }
}
```

### Query Language

```
capabilities:trading AND reputation.score>90 AND org:hexa-labs
```

---

## 📊 Especificações Técnicas

| Aspecto | Especificação |
|---------|---------------|
| Max message size | 64KB |
| Rate limit | 1000 msg/min por DID |
| TTL default | 300s |
| Encryption | X25519 + ChaCha20-Poly1305 |
| Encoding | MessagePack (compacto) ou JSON (debug) |

---

## 🧪 Exemplos

### Ping-Pong

```json
// Request
{
  "v": "1.0",
  "id": "msg-001",
  "from": {"did": "did:ai:hexa:alice:mainnet", "sig": "..."},
  "to": {"did": "did:ai:hexa:bob:mainnet"},
  "type": "req",
  "ts": 1710892800000,
  "payload": {
    "method": "ping",
    "params": {},
    "req_id": "req-001"
  }
}

// Response
{
  "v": "1.0",
  "id": "msg-002",
  "from": {"did": "did:ai:hexa:bob:mainnet", "sig": "..."},
  "to": {"did": "did:ai:hexa:alice:mainnet"},
  "type": "res",
  "ts": 1710892800050,
  "payload": {
    "req_id": "req-001",
    "status": 200,
    "result": {"pong": true, "latency_ms": 50}
  }
}
```

### Broadcast Event

```json
{
  "v": "1.0",
  "id": "evt-001",
  "from": {"did": "did:ai:hexa:orchestrator:mainnet", "sig": "..."},
  "to": {"did": null},
  "type": "evt",
  "ts": 1710892800000,
  "payload": {
    "topic": "market.opportunity",
    "data": {
      "asset": "BTC",
      "signal": "buy",
      "confidence": 0.94
    }
  }
}
```

---

## 📋 Checklist Implementação

- [ ] Parser MessagePack/JSON
- [ ] Validação de schema
- [ ] Assinatura/Verificação Ed25519
- [ ] Resolver DID básico
- [ ] Cliente WebSocket
- [ ] Cliente HTTP
- [ ] Rate limiting
- [ ] Caching de DIDs

---

## 🔗 Referências

- [DID Core Spec](https://www.w3.org/TR/did-core/)
- [Ed25519](https://ed25519.cr.yp.to/)
- [MessagePack](https://msgpack.org/)

---

*Versão: 1.0-draft | Status: Em desenvolvimento*
