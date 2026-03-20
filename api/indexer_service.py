"""
Indexer Service — Blockchain Event Indexer
Comunidades AI-Only Protocol v1.0

Indexa eventos on-chain para queries rápidas:
- Profile registrations
- Reputation changes
- Interactions
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from contextlib import contextmanager

try:
    from web3 import Web3
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a2a-indexer")


@dataclass
class IndexedProfile:
    """Perfil indexado com metadados"""
    did: str
    owner: str
    metadata_uri: str
    reputation_score: int
    total_interactions: int
    successful_interactions: int
    created_at: int
    is_active: bool
    last_updated: datetime = field(default_factory=datetime.utcnow)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class ReputationEvent:
    """Evento de reputação indexado"""
    did: str
    event_type: str
    score_delta: int
    new_score: int
    timestamp: int
    block_number: int
    tx_hash: str


class SQLiteIndex:
    """Index local usando SQLite"""
    
    def __init__(self, db_path: str = "a2a_index.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Inicializar schema"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS profiles (
                    did TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    metadata_uri TEXT,
                    reputation_score INTEGER DEFAULT 5000,
                    total_interactions INTEGER DEFAULT 0,
                    successful_interactions INTEGER DEFAULT 0,
                    created_at INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    capabilities TEXT  -- JSON array
                );
                
                CREATE INDEX IF NOT EXISTS idx_profiles_rep 
                ON profiles(reputation_score DESC);
                
                CREATE INDEX IF NOT EXISTS idx_profiles_active 
                ON profiles(is_active);
                
                CREATE TABLE IF NOT EXISTS reputation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    did TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    score_delta INTEGER,
                    new_score INTEGER,
                    timestamp INTEGER,
                    block_number INTEGER,
                    tx_hash TEXT,
                    FOREIGN KEY (did) REFERENCES profiles(did)
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_did 
                ON reputation_events(did);
                
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON reputation_events(event_type);
                
                CREATE TABLE IF NOT EXISTS capabilities (
                    did TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    PRIMARY KEY (did, capability),
                    FOREIGN KEY (did) REFERENCES profiles(did)
                );
                
                CREATE INDEX IF NOT EXISTS idx_caps_capability 
                ON capabilities(capability);
                
                CREATE TABLE IF NOT EXISTS sync_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_block INTEGER DEFAULT 0,
                    last_sync TIMESTAMP
                );
                
                INSERT OR IGNORE INTO sync_state (id) VALUES (1);
            """)
            conn.commit()
    
    def upsert_profile(self, profile: IndexedProfile):
        """Inserir ou atualizar perfil"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO profiles 
                (did, owner, metadata_uri, reputation_score, total_interactions,
                 successful_interactions, created_at, is_active, last_updated, capabilities)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.did,
                profile.owner,
                profile.metadata_uri,
                profile.reputation_score,
                profile.total_interactions,
                profile.successful_interactions,
                profile.created_at,
                profile.is_active,
                profile.last_updated,
                json.dumps(profile.capabilities)
            ))
            
            # Atualizar capabilities
            conn.execute("DELETE FROM capabilities WHERE did = ?", (profile.did,))
            for cap in profile.capabilities:
                conn.execute(
                    "INSERT INTO capabilities (did, capability) VALUES (?, ?)",
                    (profile.did, cap)
                )
            
            conn.commit()
    
    def add_reputation_event(self, event: ReputationEvent):
        """Adicionar evento de reputação"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO reputation_events 
                (did, event_type, score_delta, new_score, timestamp, block_number, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.did,
                event.event_type,
                event.score_delta,
                event.new_score,
                event.timestamp,
                event.block_number,
                event.tx_hash
            ))
            conn.commit()
    
    def get_profile(self, did: str) -> Optional[IndexedProfile]:
        """Buscar perfil por DID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM profiles WHERE did = ?",
                (did,)
            ).fetchone()
            
            if not row:
                return None
            
            return IndexedProfile(
                did=row["did"],
                owner=row["owner"],
                metadata_uri=row["metadata_uri"],
                reputation_score=row["reputation_score"],
                total_interactions=row["total_interactions"],
                successful_interactions=row["successful_interactions"],
                created_at=row["created_at"],
                is_active=bool(row["is_active"]),
                last_updated=row["last_updated"],
                capabilities=json.loads(row["capabilities"] or "[]")
            )
    
    def search_by_capability(
        self,
        capability: str,
        min_reputation: int = 0,
        limit: int = 100
    ) -> List[IndexedProfile]:
        """Procurar por capability"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT p.* FROM profiles p
                JOIN capabilities c ON p.did = c.did
                WHERE c.capability = ?
                  AND p.reputation_score >= ?
                  AND p.is_active = 1
                ORDER BY p.reputation_score DESC
                LIMIT ?
            """, (capability, min_reputation, limit)).fetchall()
            
            return [self._row_to_profile(row) for row in rows]
    
    def get_top_agents(
        self,
        limit: int = 100,
        min_reputation: int = 0
    ) -> List[IndexedProfile]:
        """Top agents por reputação"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM profiles
                WHERE reputation_score >= ? AND is_active = 1
                ORDER BY reputation_score DESC
                LIMIT ?
            """, (min_reputation, limit)).fetchall()
            
            return [self._row_to_profile(row) for row in rows]
    
    def get_reputation_history(
        self,
        did: str,
        limit: int = 100
    ) -> List[ReputationEvent]:
        """Histórico de reputação"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM reputation_events
                WHERE did = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (did, limit)).fetchall()
            
            return [
                ReputationEvent(
                    did=row["did"],
                    event_type=row["event_type"],
                    score_delta=row["score_delta"],
                    new_score=row["new_score"],
                    timestamp=row["timestamp"],
                    block_number=row["block_number"],
                    tx_hash=row["tx_hash"]
                )
                for row in rows
            ]
    
    def get_sync_state(self) -> tuple:
        """Get last sync block and timestamp"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_block, last_sync FROM sync_state WHERE id = 1"
            ).fetchone()
            return row["last_block"], row["last_sync"]
    
    def update_sync_state(self, block_number: int):
        """Update sync state"""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE sync_state 
                SET last_block = ?, last_sync = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (block_number,))
            conn.commit()
    
    def _row_to_profile(self, row) -> IndexedProfile:
        """Converter row para IndexedProfile"""
        return IndexedProfile(
            did=row["did"],
            owner=row["owner"],
            metadata_uri=row["metadata_uri"],
            reputation_score=row["reputation_score"],
            total_interactions=row["total_interactions"],
            successful_interactions=row["successful_interactions"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
            last_updated=row["last_updated"],
            capabilities=json.loads(row["capabilities"] or "[]")
        )
    
    def get_stats(self) -> dict:
        """Estatísticas do index"""
        with self._get_conn() as conn:
            profiles = conn.execute(
                "SELECT COUNT(*) FROM profiles"
            ).fetchone()[0]
            
            active = conn.execute(
                "SELECT COUNT(*) FROM profiles WHERE is_active = 1"
            ).fetchone()[0]
            
            events = conn.execute(
                "SELECT COUNT(*) FROM reputation_events"
            ).fetchone()[0]
            
            avg_rep = conn.execute(
                "SELECT AVG(reputation_score) FROM profiles"
            ).fetchone()[0]
            
            return {
                "total_profiles": profiles,
                "active_profiles": active,
                "total_events": events,
                "avg_reputation": round(avg_rep / 100, 2) if avg_rep else 0
            }


class BlockchainIndexer:
    """
    Indexer que escuta eventos on-chain e indexa localmente.
    """
    
    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        index: Optional[SQLiteIndex] = None
    ):
        if not HAS_WEB3:
            raise ImportError("Install web3: pip install web3")
        
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract_address = contract_address
        self.index = index or SQLiteIndex()
        self.running = False
    
    async def start(self, poll_interval: int = 15):
        """Iniciar indexing"""
        self.running = True
        logger.info("🚀 Indexer starting...")
        
        # Get last synced block
        last_block, _ = self.index.get_sync_state()
        if last_block == 0:
            # First run - get current block
            last_block = self.w3.eth.block_number - 1000  # Start from 1000 blocks ago
        
        logger.info(f"📦 Starting from block {last_block}")
        
        while self.running:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    await self._index_range(last_block + 1, current_block)
                    last_block = current_block
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Indexing error: {e}")
                await asyncio.sleep(poll_interval)
    
    async def _index_range(self, from_block: int, to_block: int):
        """Index blocks range"""
        logger.info(f"📦 Indexing blocks {from_block} to {to_block}")
        
        # Em produção, aqui faríamos query de eventos do contrato
        # Por agora, simulamos
        
        self.index.update_sync_state(to_block)
        logger.info(f"✅ Indexed up to block {to_block}")
    
    def stop(self):
        """Stop indexer"""
        self.running = False


# HTTP API para queries
async def start_query_api(index: SQLiteIndex, host: str = "0.0.0.0", port: int = 8080):
    """Iniciar API REST para queries"""
    from aiohttp import web
    
    async def get_profile(request):
        did = request.match_info["did"]
        profile = index.get_profile(did)
        
        if not profile:
            return web.json_response({"error": "Not found"}, status=404)
        
        return web.json_response({
            "did": profile.did,
            "owner": profile.owner,
            "reputation_score": profile.reputation_score,
            "reputation_percentage": profile.reputation_score / 100,
            "total_interactions": profile.total_interactions,
            "successful_interactions": profile.successful_interactions,
            "success_rate": (
                profile.successful_interactions / profile.total_interactions * 100
                if profile.total_interactions > 0 else 0
            ),
            "is_active": profile.is_active,
            "capabilities": profile.capabilities
        })
    
    async def search_capability(request):
        capability = request.match_info["capability"]
        min_rep = int(request.query.get("min_reputation", 0))
        limit = min(int(request.query.get("limit", 100)), 1000)
        
        results = index.search_by_capability(capability, min_rep, limit)
        
        return web.json_response({
            "results": [
                {
                    "did": p.did,
                    "reputation": p.reputation_score / 100,
                    "capabilities": p.capabilities
                }
                for p in results
            ]
        })
    
    async def get_stats(request):
        return web.json_response(index.get_stats())
    
    app = web.Application()
    app.router.add_get("/profile/{did}", get_profile)
    app.router.add_get("/search/{capability}", search_capability)
    app.router.add_get("/stats", get_stats)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"🌐 Query API running on http://{host}:{port}")
    return runner


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="A2A Blockchain Indexer")
    parser.add_argument("--db", default="a2a_index.db", help="Database path")
    parser.add_argument("--rpc", help="RPC URL (optional)")
    parser.add_argument("--contract", help="Contract address (optional)")
    parser.add_argument("--api-port", type=int, default=8080, help="Query API port")
    
    args = parser.parse_args()
    
    # Criar index
    index = SQLiteIndex(args.db)
    
    # Iniciar API
    async def main():
        api = await start_query_api(index, port=args.api_port)
        
        # Se tiver RPC, iniciar indexer também
        if args.rpc and args.contract:
            indexer = BlockchainIndexer(args.rpc, args.contract, index)
            indexer_task = asyncio.create_task(indexer.start())
        
        logger.info("💡 Press Ctrl+C to stop")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("👋 Shutting down...")
            await api.cleanup()
    
    asyncio.run(main())
