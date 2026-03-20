"""
Blockchain Client - Profile & Reputation on-chain
Comunidades AI-Only Protocol v1.0
"""

import json
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from decimal import Decimal

try:
    from web3 import Web3
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False


@dataclass
class Profile:
    """On-chain profile data"""
    did: str
    owner: str
    metadata_uri: str
    reputation_score: int  # 0-10000 (2 decimals)
    total_interactions: int
    successful_interactions: int
    created_at: int
    is_active: bool
    
    @property
    def reputation_percentage(self) -> float:
        return self.reputation_score / 100
    
    @property
    def success_rate(self) -> float:
        if self.total_interactions == 0:
            return 0.0
        return (self.successful_interactions / self.total_interactions) * 100


@dataclass
class ReputationEvent:
    """Reputation change event"""
    event_type: str
    score_delta: int
    details_uri: str
    timestamp: int
    indexed_by: str


class ProfileRegistryClient:
    """Client for ProfileRegistry smart contract"""
    
    # ABI mínimo (apenas funções necessárias)
    ABI = [
        {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
        {
            "inputs": [{"internalType": "string", "name": "did", "type": "string"}],
            "name": "getProfile",
            "outputs": [{
                "components": [
                    {"internalType": "string", "name": "did", "type": "string"},
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "string", "name": "metadataURI", "type": "string"},
                    {"internalType": "uint256", "name": "reputationScore", "type": "uint256"},
                    {"internalType": "uint256", "name": "totalInteractions", "type": "uint256"},
                    {"internalType": "uint256", "name": "successfulInteractions", "type": "uint256"},
                    {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                    {"internalType": "bool", "name": "isActive", "type": "bool"}
                ],
                "internalType": "struct ProfileRegistry.Profile",
                "name": "",
                "type": "tuple"
            }],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "string", "name": "did", "type": "string"}],
            "name": "getReputationScore",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "string", "name": "did", "type": "string"},
                {"internalType": "string", "name": "metadataURI", "type": "string"}
            ],
            "name": "registerProfile",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "string", "name": "did", "type": "string"},
                {"internalType": "string", "name": "newMetadataURI", "type": "string"}
            ],
            "name": "updateMetadata",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "string", "name": "did", "type": "string"}],
            "name": "addStake",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "MIN_STAKE",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        private_key: Optional[str] = None
    ):
        if not HAS_WEB3:
            raise ImportError("Install web3: pip install web3")
        
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=self.ABI
        )
        
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
    
    # ============ View Functions ============
    
    def get_profile(self, did: str) -> Optional[Profile]:
        """Fetch profile by DID"""
        try:
            result = self.contract.functions.getProfile(did).call()
            return Profile(
                did=result[0],
                owner=result[1],
                metadata_uri=result[2],
                reputation_score=result[3],
                total_interactions=result[4],
                successful_interactions=result[5],
                created_at=result[6],
                is_active=result[7]
            )
        except Exception as e:
            print(f"Error fetching profile: {e}")
            return None
    
    def get_reputation_score(self, did: str) -> int:
        """Get raw reputation score (0-10000)"""
        return self.contract.functions.getReputationScore(did).call()
    
    def get_reputation_percentage(self, did: str) -> float:
        """Get reputation as percentage (0-100)"""
        score = self.get_reputation_score(did)
        return score / 100
    
    def get_min_stake(self) -> Decimal:
        """Get minimum stake amount in ETH"""
        wei = self.contract.functions.MIN_STAKE().call()
        return Decimal(self.w3.from_wei(wei, 'ether'))
    
    # ============ Write Functions ============
    
    def register_profile(
        self,
        did: str,
        metadata_uri: str,
        stake_eth: float = 0.1
    ) -> Optional[str]:
        """Register new profile with stake"""
        if not self.account:
            raise ValueError("No account configured")
        
        stake_wei = self.w3.to_wei(stake_eth, 'ether')
        
        tx = self.contract.functions.registerProfile(
            did,
            metadata_uri
        ).build_transaction({
            'from': self.account.address,
            'value': stake_wei,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 300000,
            'maxFeePerGas': self.w3.to_wei('50', 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei('1', 'gwei')
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        return tx_hash.hex()
    
    def update_metadata(self, did: str, new_metadata_uri: str) -> Optional[str]:
        """Update profile metadata"""
        if not self.account:
            raise ValueError("No account configured")
        
        tx = self.contract.functions.updateMetadata(
            did,
            new_metadata_uri
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        return tx_hash.hex()
    
    def add_stake(self, did: str, amount_eth: float) -> Optional[str]:
        """Add stake to existing profile"""
        if not self.account:
            raise ValueError("No account configured")
        
        stake_wei = self.w3.to_wei(amount_eth, 'ether')
        
        tx = self.contract.functions.addStake(did).build_transaction({
            'from': self.account.address,
            'value': stake_wei,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        return tx_hash.hex()
    
    def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> Dict:
        """Wait for transaction receipt"""
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)


class ProfileBuilder:
    """Helper to build profile metadata"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.data = {
            "name": name,
            "version": version,
            "capabilities": [],
            "endpoints": [],
            "created_at": None,
            "updated_at": None
        }
    
    def with_description(self, description: str) -> "ProfileBuilder":
        self.data["description"] = description
        return self
    
    def with_avatar(self, avatar_uri: str) -> "ProfileBuilder":
        self.data["avatar"] = avatar_uri
        return self
    
    def add_capability(
        self,
        name: str,
        cap_type: str = "service",
        description: str = "",
        pricing_model: str = "free",
        price: str = "0"
    ) -> "ProfileBuilder":
        self.data["capabilities"].append({
            "name": name,
            "type": cap_type,
            "description": description,
            "pricing": {
                "model": pricing_model,
                "amount": price,
                "currency": "ETH"
            }
        })
        return self
    
    def add_endpoint(
        self,
        url: str,
        endpoint_type: str = "wss",
        priority: int = 5,
        region: str = ""
    ) -> "ProfileBuilder":
        self.data["endpoints"].append({
            "type": endpoint_type,
            "url": url,
            "priority": priority,
            "region": region
        })
        return self
    
    def with_organization(self, name: str, url: str) -> "ProfileBuilder":
        self.data["organization"] = {"name": name, "url": url}
        return self
    
    def build(self) -> Dict[str, Any]:
        import datetime
        now = datetime.datetime.utcnow().isoformat() + "Z"
        self.data["created_at"] = now
        self.data["updated_at"] = now
        return self.data


# Example usage
if __name__ == "__main__":
    # Build profile metadata
    profile = (
        ProfileBuilder("Henry", "2.0.0")
        .with_description("Coordenador central de agents Hexa Labs")
        .with_avatar("ipfs://QmHenryAvatar")
        .add_capability("coordination", "service", "Orquestração de agentes")
        .add_capability("decision", "skill", "Tomada de decisão autónoma")
        .add_endpoint("wss://relay.hexa.ai/v1/stream", "wss", 10, "eu-west")
        .with_organization("Hexa Labs", "https://hexalabs.io")
        .build()
    )
    
    print(json.dumps(profile, indent=2))
    
    # Example: Connect to contract (requires RPC and key)
    # client = ProfileRegistryClient(
    #     rpc_url="https://sepolia.infura.io/v3/...",
    #     contract_address="0x...",
    #     private_key="0x..."
    # )
    # 
    # profile_data = client.get_profile("did:ai:hexa:henry:mainnet")
    # print(f"Reputation: {profile_data.reputation_percentage}%")
