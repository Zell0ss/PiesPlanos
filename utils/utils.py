# AI-Enhanced Investigation Text Adventure Game
# %%
import sqlite3
import json
from datetime import datetime
from typing import Optional
from dataclasses import asdict
from models.models import Player

# ==============================================================================
# Persistence Manager
# ==============================================================================
# %%
class PersistenceManager:
    """Handles saving and loading game state"""
    
    def __init__(self, db_path: str = "game_saves.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Player saves table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_saves (
                player_id TEXT PRIMARY KEY,
                save_data TEXT,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # NPC conversation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_conversations (
                player_id TEXT,
                npc_id TEXT,
                conversation_data TEXT,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, npc_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_player(self, player: Player) -> bool:
        """Save player state to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            save_data = json.dumps({
                "player_data": asdict(player),
                "timestamp": datetime.now().isoformat()
            })
            
            cursor.execute('''
                INSERT OR REPLACE INTO player_saves (player_id, save_data)
                VALUES (?, ?)
            ''', (player.id, save_data))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving player: {e}")
            return False
    
    def load_player(self, player_id: str) -> Optional[Player]:
        """Load player state from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT save_data FROM player_saves WHERE player_id = ?', (player_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                save_data = json.loads(result[0])
                # Reconstruct player object from saved data
                # Implementation would handle object reconstruction
                return None  # Placeholder
            return None
        except Exception as e:
            print(f"Error loading player: {e}")
            return None
# %%