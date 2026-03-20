// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ProfileRegistry
 * @notice Sistema de identidade e reputação on-chain para agents AI
 * @version 1.0.0
 */
contract ProfileRegistry {
    
    // ============ Structs ============
    
    struct Profile {
        string did;              // did:ai:hexa:{agent}:{network}
        address owner;           // Endereço Ethereum que controla o perfil
        string metadataURI;      // IPFS/Arweave hash com metadata JSON
        uint256 reputationScore; // 0-10000 (2 decimais: 9450 = 94.50)
        uint256 totalInteractions;
        uint256 successfulInteractions;
        uint256 createdAt;
        bool isActive;
    }
    
    struct ReputationEvent {
        string eventType;        // "interaction", "review", "stake", "slash"
        int256 scoreDelta;       // Mudança no score (-1000 a +1000)
        string detailsURI;       // URI com detalhes do evento
        uint256 timestamp;
        address indexedBy;       // Quem registou o evento
    }
    
    // ============ State Variables ============
    
    mapping(string => Profile) public profiles;           // did => Profile
    mapping(address => string) public ownerToDID;         // owner => did
    mapping(string => ReputationEvent[]) public reputationHistory; // did => events
    
    uint256 public constant MIN_STAKE = 0.1 ether;
    uint256 public constant MAX_SCORE = 10000;
    uint256 public constant REPUTATION_DECAY_DAYS = 90;
    
    address public governance;
    mapping(address => bool) public authorizedIndexers;
    
    // ============ Events ============
    
    event ProfileRegistered(
        string indexed did,
        address indexed owner,
        string metadataURI,
        uint256 staked
    );
    
    event ProfileUpdated(
        string indexed did,
        string metadataURI
    );
    
    event ReputationChanged(
        string indexed did,
        int256 delta,
        uint256 newScore,
        string eventType
    );
    
    event InteractionRecorded(
        string indexed fromDID,
        string indexed toDID,
        bool success,
        uint256 timestamp
    );
    
    // ============ Modifiers ============
    
    modifier onlyGovernance() {
        require(msg.sender == governance, "Only governance");
        _;
    }
    
    modifier onlyIndexer() {
        require(authorizedIndexers[msg.sender] || msg.sender == governance, "Unauthorized");
        _;
    }
    
    modifier onlyProfileOwner(string calldata did) {
        require(profiles[did].owner == msg.sender, "Not owner");
        _;
    }
    
    modifier validDID(string calldata did) {
        require(bytes(did).length > 0, "Empty DID");
        require(bytes(profiles[did].did).length == 0, "DID exists");
        _;
    }
    
    // ============ Constructor ============
    
    constructor() {
        governance = msg.sender;
    }
    
    // ============ Core Functions ============
    
    /**
     * @notice Registar novo perfil de agent
     * @param did Identificador descentralizado
     * @param metadataURI URI para metadata JSON (IPFS/Arweave)
     */
    function registerProfile(
        string calldata did,
        string calldata metadataURI
    ) external payable validDID(did) {
        require(msg.value >= MIN_STAKE, "Insufficient stake");
        require(bytes(metadataURI).length > 0, "Empty metadata");
        
        // Validar formato DID: did:ai:hexa:{agent}:{network}
        require(_validateDID(did), "Invalid DID format");
        
        profiles[did] = Profile({
            did: did,
            owner: msg.sender,
            metadataURI: metadataURI,
            reputationScore: 5000, // Score inicial neutro: 50.00
            totalInteractions: 0,
            successfulInteractions: 0,
            createdAt: block.timestamp,
            isActive: true
        });
        
        ownerToDID[msg.sender] = did;
        
        emit ProfileRegistered(did, msg.sender, metadataURI, msg.value);
    }
    
    /**
     * @notice Atualizar metadata do perfil
     */
    function updateMetadata(
        string calldata did,
        string calldata newMetadataURI
    ) external onlyProfileOwner(did) {
        require(bytes(newMetadataURI).length > 0, "Empty metadata");
        
        profiles[did].metadataURI = newMetadataURI;
        
        emit ProfileUpdated(did, newMetadataURI);
    }
    
    /**
     * @notice Registar interação entre agents (apenas indexers autorizados)
     */
    function recordInteraction(
        string calldata fromDID,
        string calldata toDID,
        bool success,
        string calldata detailsURI
    ) external onlyIndexer {
        require(profiles[fromDID].isActive, "From profile inactive");
        require(profiles[toDID].isActive, "To profile inactive");
        
        profiles[fromDID].totalInteractions++;
        profiles[toDID].totalInteractions++;
        
        if (success) {
            profiles[fromDID].successfulInteractions++;
            profiles[toDID].successfulInteractions++;
            
            // Bonus de reputação por interação bem-sucedida
            _updateReputation(fromDID, 10, "interaction", detailsURI);
            _updateReputation(toDID, 10, "interaction", detailsURI);
        } else {
            // Penalidade leve por interação falhada
            _updateReputation(fromDID, -5, "interaction", detailsURI);
        }
        
        emit InteractionRecorded(fromDID, toDID, success, block.timestamp);
    }
    
    /**
     * @notice Registar review/avaliação (com stake)
     */
    function submitReview(
        string calldata targetDID,
        int256 scoreDelta,
        string calldata detailsURI
    ) external payable {
        require(msg.value >= 0.01 ether, "Review requires stake");
        require(scoreDelta >= -100 && scoreDelta <= 100, "Delta out of range");
        require(profiles[targetDID].isActive, "Target inactive");
        
        string memory reviewerDID = ownerToDID[msg.sender];
        require(bytes(reviewerDID).length > 0, "Reviewer not registered");
        
        // Reviews de agents com maior reputação têm mais peso
        uint256 reviewerScore = profiles[reviewerDID].reputationScore;
        int256 weightedDelta = (scoreDelta * int256(reviewerScore)) / 10000;
        
        _updateReputation(targetDID, weightedDelta, "review", detailsURI);
    }
    
    /**
     * @notice Adicionar stake ao perfil (aumenta reputação)
     */
    function addStake(string calldata did) external payable onlyProfileOwner(did) {
        require(msg.value > 0, "Must send ETH");
        
        // +1 ponto de reputação por 0.1 ETH staked
        uint256 repBonus = (msg.value * 10) / 1 ether;
        _updateReputation(did, int256(repBonus), "stake", "");
    }
    
    /**
     * @notice Retirar stake (com cooldown de 7 dias)
     */
    function withdrawStake(uint256 amount) external {
        string memory did = ownerToDID[msg.sender];
        require(bytes(did).length > 0, "No profile");
        
        // Implementar lógica de cooldown e slashing se necessário
        // (Simplificado para MVP)
        
        payable(msg.sender).transfer(amount);
    }
    
    // ============ View Functions ============
    
    function getProfile(string calldata did) external view returns (Profile memory) {
        return profiles[did];
    }
    
    function getReputationScore(string calldata did) external view returns (uint256) {
        return profiles[did].reputationScore;
    }
    
    function getReputationPercentage(string calldata did) external view returns (uint256) {
        return profiles[did].reputationScore / 100;
    }
    
    function getReputationHistory(string calldata did) 
        external 
        view 
        returns (ReputationEvent[] memory) 
    {
        return reputationHistory[did];
    }
    
    function calculateSuccessRate(string calldata did) external view returns (uint256) {
        Profile memory p = profiles[did];
        if (p.totalInteractions == 0) return 0;
        return (p.successfulInteractions * 10000) / p.totalInteractions;
    }
    
    // ============ Admin Functions ============
    
    function setIndexer(address indexer, bool authorized) external onlyGovernance {
        authorizedIndexers[indexer] = authorized;
    }
    
    function slashReputation(
        string calldata did,
        uint256 amount,
        string calldata reason
    ) external onlyGovernance {
        _updateReputation(did, -int256(amount), "slash", reason);
    }
    
    // ============ Internal Functions ============
    
    function _updateReputation(
        string memory did,
        int256 delta,
        string memory eventType,
        string memory detailsURI
    ) internal {
        Profile storage p = profiles[did];
        
        uint256 oldScore = p.reputationScore;
        
        if (delta > 0) {
            p.reputationScore = uint256(
                int256(p.reputationScore) + delta > int256(MAX_SCORE) 
                    ? int256(MAX_SCORE) 
                    : int256(p.reputationScore) + delta
            );
        } else {
            uint256 absDelta = uint256(-delta);
            p.reputationScore = p.reputationScore > absDelta 
                ? p.reputationScore - absDelta 
                : 0;
        }
        
        reputationHistory[did].push(ReputationEvent({
            eventType: eventType,
            scoreDelta: delta,
            detailsURI: detailsURI,
            timestamp: block.timestamp,
            indexedBy: msg.sender
        }));
        
        emit ReputationChanged(did, delta, p.reputationScore, eventType);
    }
    
    function _validateDID(string memory did) internal pure returns (bool) {
        // Formato: did:ai:hexa:{agent-id}:{network}
        bytes memory didBytes = bytes(did);
        
        // Mínimo: "did:ai:x:y:z" = 12 chars
        if (didBytes.length < 12) return false;
        
        // Verificar prefixo "did:ai:"
        bytes memory prefix = "did:ai:";
        for (uint i = 0; i < prefix.length; i++) {
            if (didBytes[i] != prefix[i]) return false;
        }
        
        // Verificar número de colunas (mínimo 4)
        uint256 colons = 0;
        for (uint i = 0; i < didBytes.length; i++) {
            if (didBytes[i] == ':') colons++;
        }
        
        return colons >= 4;
    }
}
