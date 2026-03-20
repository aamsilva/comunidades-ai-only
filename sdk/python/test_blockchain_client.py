"""
Testes para blockchain_client.py
Mock-based para não requerer conexão real
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from blockchain_client import (
    ProfileRegistryClient, 
    ProfileBuilder, 
    Profile,
    Profile
)


class TestProfileBuilder:
    """Testes para ProfileBuilder"""
    
    def test_basic_build(self):
        """Criar perfil básico"""
        profile = ProfileBuilder("TestAgent", "1.0.0").build()
        
        assert profile["name"] == "TestAgent"
        assert profile["version"] == "1.0.0"
        assert profile["capabilities"] == []
        assert profile["endpoints"] == []
        assert "created_at" in profile
        assert "updated_at" in profile
    
    def test_with_description(self):
        """Adicionar descrição"""
        profile = (
            ProfileBuilder("TestAgent")
            .with_description("Um agente de teste")
            .build()
        )
        assert profile["description"] == "Um agente de teste"
    
    def test_add_capability(self):
        """Adicionar capabilities"""
        profile = (
            ProfileBuilder("TestAgent")
            .add_capability("nlp", "service", "Processamento de linguagem")
            .add_capability("vision", "skill")
            .build()
        )
        
        assert len(profile["capabilities"]) == 2
        assert profile["capabilities"][0]["name"] == "nlp"
        assert profile["capabilities"][0]["type"] == "service"
    
    def test_add_endpoint(self):
        """Adicionar endpoints"""
        profile = (
            ProfileBuilder("TestAgent")
            .add_endpoint("wss://relay.test.ai", "wss", 10, "eu-west")
            .add_endpoint("https://api.test.ai", "https")
            .build()
        )
        
        assert len(profile["endpoints"]) == 2
        assert profile["endpoints"][0]["url"] == "wss://relay.test.ai"
        assert profile["endpoints"][0]["priority"] == 10


class TestProfileDataclass:
    """Testes para Profile dataclass"""
    
    def test_reputation_percentage(self):
        """Calcular percentagem de reputação"""
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
    
    def test_success_rate(self):
        """Calcular taxa de sucesso"""
        profile = Profile(
            did="did:ai:hexa:test:mainnet",
            owner="0x123",
            metadata_uri="ipfs://test",
            reputation_score=5000,
            total_interactions=100,
            successful_interactions=95,
            created_at=1700000000,
            is_active=True
        )
        
        assert profile.success_rate == 95.0
    
    def test_success_rate_zero_interactions(self):
        """Taxa de sucesso com zero interações"""
        profile = Profile(
            did="did:ai:hexa:test:mainnet",
            owner="0x123",
            metadata_uri="ipfs://test",
            reputation_score=5000,
            total_interactions=0,
            successful_interactions=0,
            created_at=1700000000,
            is_active=True
        )
        
        assert profile.success_rate == 0.0


class TestProfileRegistryClient:
    """Testes para ProfileRegistryClient (com mocks)"""
    
    @patch('blockchain_client.Web3')
    def test_init_without_key(self, mock_web3):
        """Inicializar sem private key (apenas leitura)"""
        mock_instance = MagicMock()
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.return_value = mock_instance
        mock_instance.eth.contract.return_value = MagicMock()
        
        client = ProfileRegistryClient(
            rpc_url="https://test.rpc",
            contract_address="0x1234567890123456789012345678901234567890"
        )
        
        assert client.account is None
    
    @patch('blockchain_client.Web3')
    @patch('blockchain_client.Account.from_key')
    def test_init_with_key(self, mock_from_key, mock_web3):
        """Inicializar com private key"""
        mock_account = MagicMock()
        mock_account.address = "0x123"
        mock_from_key.return_value = mock_account
        
        mock_instance = MagicMock()
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.return_value = mock_instance
        mock_instance.eth.contract.return_value = MagicMock()
        
        client = ProfileRegistryClient(
            rpc_url="https://test.rpc",
            contract_address="0x1234567890123456789012345678901234567890",
            private_key="0x" + "ab" * 32
        )
        
        assert client.account is not None
    
    @patch('blockchain_client.Web3')
    def test_get_profile_success(self, mock_web3):
        """Buscar perfil existente"""
        # Mock do contrato
        mock_contract = MagicMock()
        mock_contract.functions.getProfile.return_value.call.return_value = [
            "did:ai:hexa:test:mainnet",  # did
            "0x1234567890123456789012345678901234567890",  # owner
            "ipfs://QmTest",  # metadataURI
            9450,  # reputationScore
            100,   # totalInteractions
            95,    # successfulInteractions
            1700000000,  # createdAt
            True   # isActive
        ]
        
        mock_instance = MagicMock()
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.return_value = mock_instance
        mock_instance.eth.contract.return_value = mock_contract
        
        client = ProfileRegistryClient(
            rpc_url="https://test.rpc",
            contract_address="0x1234567890123456789012345678901234567890"
        )
        client.contract = mock_contract
        
        profile = client.get_profile("did:ai:hexa:test:mainnet")
        
        assert profile is not None
        assert profile.did == "did:ai:hexa:test:mainnet"
        assert profile.reputation_score == 9450
        assert profile.reputation_percentage == 94.50
    
    @patch('blockchain_client.Web3')
    def test_get_profile_not_found(self, mock_web3):
        """Buscar perfil inexistente"""
        mock_contract = MagicMock()
        mock_contract.functions.getProfile.return_value.call.side_effect = Exception("Not found")
        
        mock_instance = MagicMock()
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.return_value = mock_instance
        mock_instance.eth.contract.return_value = mock_contract
        
        client = ProfileRegistryClient(
            rpc_url="https://test.rpc",
            contract_address="0x1234567890123456789012345678901234567890"
        )
        client.contract = mock_contract
        
        profile = client.get_profile("did:ai:hexa:nonexistent:mainnet")
        
        assert profile is None
    
    @patch('blockchain_client.Web3')
    def test_get_min_stake(self, mock_web3):
        """Buscar stake mínimo"""
        mock_contract = MagicMock()
        mock_contract.functions.MIN_STAKE.return_value.call.return_value = 100000000000000000  # 0.1 ETH
        
        mock_instance = MagicMock()
        mock_instance.to_wei = MagicMock(return_value=100000000000000000)
        mock_instance.from_wei = MagicMock(return_value=Decimal("0.1"))
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.return_value = mock_instance
        mock_instance.eth.contract.return_value = mock_contract
        
        client = ProfileRegistryClient(
            rpc_url="https://test.rpc",
            contract_address="0x1234567890123456789012345678901234567890"
        )
        client.contract = mock_contract
        client.w3 = mock_instance
        
        min_stake = client.get_min_stake()
        
        assert min_stake == Decimal("0.1")
    
    def test_register_profile_no_account(self):
        """Tentar registar sem conta configurada"""
        with patch('blockchain_client.Web3') as mock_web3:
            mock_instance = MagicMock()
            mock_web3.HTTPProvider.return_value = MagicMock()
            mock_web3.return_value = mock_instance
            mock_instance.eth.contract.return_value = MagicMock()
            
            client = ProfileRegistryClient(
                rpc_url="https://test.rpc",
                contract_address="0x1234567890123456789012345678901234567890"
            )
            
            with pytest.raises(ValueError, match="No account configured"):
                client.register_profile("did:ai:hexa:test:mainnet", "ipfs://test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
