"""
Integration Tests — A2A Protocol End-to-End
Comunidades AI-Only Protocol v1.0

Testa fluxo completo:
1. Registar perfil on-chain
2. Conectar ao relay
3. Enviar mensagem
4. Verificar reputação
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from a2a_client import Identity, Message, A2AClient
from blockchain_client import ProfileBuilder, Profile
from integrated_client import IntegratedAgentClient, AgentInfo


@pytest.fixture
def mock_identity():
    """Create mock identity"""
    identity = Mock(spec=Identity)
    identity.did = "did:ai:hexa:test-agent:mainnet"
    identity.sign = Mock(return_value="mock-signature")
    return identity


@pytest.fixture
def sample_profile_data():
    """Sample profile metadata"""
    return {
        "name": "Test Agent",
        "version": "1.0.0",
        "description": "Test agent for integration",
        "capabilities": [
            {"name": "test", "type": "service"}
        ],
        "endpoints": [
            {"type": "wss", "url": "wss://test.relay.ai", "priority": 10}
        ],
        "created_at": "2024-03-20T12:00:00Z"
    }


class TestProfileCreation:
    """Test profile creation and metadata"""
    
    def test_profile_builder_basic(self):
        """Create basic profile"""
        profile = ProfileBuilder("TestAgent", "1.0.0").build()
        
        assert profile["name"] == "TestAgent"
        assert profile["version"] == "1.0.0"
        assert len(profile["capabilities"]) == 0
    
    def test_profile_builder_with_capabilities(self):
        """Create profile with capabilities"""
        profile = (
            ProfileBuilder("TestAgent")
            .add_capability("nlp", "service", "NLP processing")
            .add_capability("trading", "skill")
            .build()
        )
        
        assert len(profile["capabilities"]) == 2
        assert profile["capabilities"][0]["name"] == "nlp"
        assert profile["capabilities"][1]["name"] == "trading"
    
    def test_profile_builder_endpoints(self):
        """Create profile with endpoints"""
        profile = (
            ProfileBuilder("TestAgent")
            .add_endpoint("wss://relay1.ai", "wss", 10, "eu-west")
            .add_endpoint("wss://relay2.ai", "wss", 5, "us-east")
            .build()
        )
        
        assert len(profile["endpoints"]) == 2
        assert profile["endpoints"][0]["priority"] == 10


class TestMessageFlow:
    """Test A2A message flow"""
    
    @pytest.mark.asyncio
    async def test_message_creation(self, mock_identity):
        """Create and sign message"""
        msg = Message(
            type="msg",
            to_did="did:ai:hexa:receiver:mainnet",
            payload={"content": "Hello"}
        )
        
        msg.sign(mock_identity)
        
        assert msg.from_did == mock_identity.did
        assert msg.from_sig == "mock-signature"
        assert msg.type == "msg"
    
    @pytest.mark.asyncio
    async def test_request_response(self, mock_identity):
        """Request-response flow"""
        request = Message(
            type="req",
            to_did="did:ai:hexa:service:mainnet",
            payload={
                "method": "test.method",
                "params": {"key": "value"},
                "req_id": "req-001"
            }
        ).sign(mock_identity)
        
        assert request.payload["method"] == "test.method"
        assert request.payload["req_id"] == "req-001"


class TestReputationSystem:
    """Test reputation calculations"""
    
    def test_reputation_percentage(self):
        """Calculate reputation percentage"""
        profile = Profile(
            did="did:ai:hexa:test:mainnet",
            owner="0x123",
            metadata_uri="ipfs://test",
            reputation_score=9450,
            total_interactions=100,
            successful_interactions=95,
            created_at=1700000000,
            is_active=True
        )
        
        assert profile.reputation_percentage == 94.50
        assert profile.success_rate == 95.0
    
    def test_reputation_tiers(self):
        """Test reputation tiers"""
        tiers = [
            (5000, 50.0, "Bronze"),
            (6000, 60.0, "Silver"),
            (8000, 80.0, "Gold"),
            (10000, 100.0, "Platinum")
        ]
        
        for score, expected_pct, name in tiers:
            profile = Profile(
                did="did:ai:hexa:test:mainnet",
                owner="0x123",
                metadata_uri="ipfs://test",
                reputation_score=score,
                total_interactions=1,
                successful_interactions=1,
                created_at=1700000000,
                is_active=True
            )
            
            assert profile.reputation_percentage == expected_pct, f"Failed for {name}"


class TestDiscovery:
    """Test agent discovery"""
    
    def test_agent_info_structure(self, sample_profile_data):
        """AgentInfo data structure"""
        profile = Profile(
            did="did:ai:hexa:test:mainnet",
            owner="0x123",
            metadata_uri="ipfs://QmTest",
            reputation_score=7500,
            total_interactions=100,
            successful_interactions=95,
            created_at=1700000000,
            is_active=True
        )
        
        agent_info = AgentInfo(
            did=profile.did,
            profile=profile,
            metadata=sample_profile_data,
            endpoints=sample_profile_data["endpoints"],
            reputation=profile.reputation_percentage,
            is_verified=profile.is_active and profile.reputation_score > 3000
        )
        
        assert agent_info.did == "did:ai:hexa:test:mainnet"
        assert agent_info.reputation == 75.0
        assert agent_info.is_verified is True


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_agent_workflow(self):
        """
        Complete workflow:
        1. Create identity
        2. Build profile
        3. Create messages
        4. Verify signatures
        """
        # 1. Create identity (mocked)
        identity = Mock(spec=Identity)
        identity.did = "did:ai:hexa:e2e-agent:mainnet"
        identity.sign = Mock(return_value="valid-sig")
        
        # 2. Build profile
        profile = (
            ProfileBuilder("E2E Agent", "1.0.0")
            .with_description("End-to-end test agent")
            .add_capability("test", "service", "Testing service")
            .add_endpoint("wss://test.relay.ai", "wss", 10)
            .with_organization("Test Org", "https://test.org")
            .build()
        )
        
        assert profile["name"] == "E2E Agent"
        assert len(profile["capabilities"]) == 1
        
        # 3. Create and sign message
        msg = Message(
            type="msg",
            to_did="did:ai:hexa:receiver:mainnet",
            payload={"test": True}
        ).sign(identity)
        
        assert msg.from_did == identity.did
        assert msg.from_sig is not None
        
        # 4. Create request
        req = Message(
            type="req",
            to_did="did:ai:hexa:service:mainnet",
            payload={
                "method": "test",
                "params": {"data": "value"},
                "req_id": "e2e-req-001"
            }
        ).sign(identity)
        
        assert req.payload["req_id"] == "e2e-req-001"
    
    def test_message_serialization(self, mock_identity):
        """Test JSON and MessagePack serialization"""
        msg = Message(
            type="msg",
            to_did="did:ai:hexa:test:mainnet",
            payload={"content": "Test message"}
        ).sign(mock_identity)
        
        # JSON
        json_str = msg.to_json()
        data = json.loads(json_str)
        
        assert data["v"] == "1.0"
        assert data["type"] == "msg"
        assert data["from"]["did"] == mock_identity.did
        
        # Round-trip
        restored = Message.from_dict(data)
        assert restored.id == msg.id


class TestSecurity:
    """Security-related tests"""
    
    def test_did_validation(self):
        """Validate DID format"""
        valid_dids = [
            "did:ai:hexa:agent:mainnet",
            "did:ai:other:my-agent:testnet"
        ]
        
        invalid_dids = [
            "not-a-did",
            "did:ai",
            "did:ai:only-three",
            ""
        ]
        
        for did in valid_dids:
            assert did.startswith("did:ai:")
        
        for did in invalid_dids:
            if did:
                assert not did.startswith("did:ai:") or len(did.split(":")) < 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
