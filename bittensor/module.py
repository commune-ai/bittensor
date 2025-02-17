import commune as c
import os
from typing import List, Dict, Any, Optional
class SubtensorModule:
    """Interface module for Subtensor network operations and wallet management"""
    
    def __init__(self, network: str = "finney"):
        """Initialize the Subtensor module
        Args:
            network (str): Network to connect to (e.g. finney, test)
        """
        self.network = network
        self.subtensor = c.obj('bittensor.core.subtensor.Subtensor')(network=network)
        
    def wallets(self) -> List[str]:
        """List all available wallets
        Returns:
            List of wallet names
        """
        return self.list_wallets()
    def create_wallet(self, name: str, hotkey: str = None) -> Dict:
        """Create a new wallet
        Args:
            name (str): Name of the wallet
            hotkey (str): Optional hotkey name
        Returns:
            Wallet information dictionary
        """
        wallet = self.subtensor.create_wallet(name=name, hotkey=hotkey)
        return wallet.info()
    def get_wallet(self, name: str) -> Dict:
        """Get wallet information
        Args:
            name (str): Name of the wallet
        Returns:
            Wallet information dictionary
        """
        wallet = self.subtensor.get_wallet(name)
        return wallet.info()
    def list_wallets(self) -> List[str]:
        """List all available wallets
        Returns:
            List of wallet names
        """
        return self.subtensor.list_wallets()
    def get_balance(self, address: str) -> float:
        """Get balance for an address
        Args:
            address (str): Wallet address
        Returns:
            Balance in TAO
        """
        return self.subtensor.get_balance(address)
    def transfer(self, 
                wallet_name: str,
                dest_address: str,
                amount: float) -> bool:
        """Transfer TAO between wallets
        Args:
            wallet_name (str): Source wallet name
            dest_address (str): Destination address
            amount (float): Amount to transfer
        Returns:
            Success boolean
        """
        wallet = self.subtensor.get_wallet(wallet_name)
        return self.subtensor.transfer(
            wallet=wallet,
            dest=dest_address,
            amount=amount
        )
    def get_network_info(self) -> Dict:
        """Get current network information
        Returns:
            Dictionary with network stats
        """
        return {
            'block_number': self.subtensor.get_current_block(),
            'difficulty': self.subtensor.difficulty,
            'total_stake': self.subtensor.total_stake,
            'total_issuance': self.subtensor.total_issuance,
            'registrations_per_block': self.subtensor.registrations_per_block
        }