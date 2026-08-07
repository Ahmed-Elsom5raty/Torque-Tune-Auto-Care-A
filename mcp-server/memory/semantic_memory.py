import json
from typing import List, Dict, Any
from databases.db import get_connection

class SemanticMemory:
    """
    Manages long-term, consolidated knowledge backed by the database. 
    It supports versioning, updating existing facts, and resolving conflicts automatically.
    """
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def consolidate_episodes(self, episodes: List[Dict[str, Any]]) -> None:
        """
        Analyzes multiple episodes to extract new facts or update existing ones.
        """
        # Placeholder for LLM extraction logic:
        # extracted_facts = self.llm_client.extract_facts(episodes)
        
        # Mocking the consolidation for demonstration:
        extracted_facts = [
            {"key": "preferred_communication", "value": "Email"}
        ]

        # Apply the extracted facts to the database
        for fact_data in extracted_facts:
            self.update_fact(fact_data["key"], fact_data["value"])

    def update_fact(self, key: str, new_value: Any) -> None:
        """
        Updates an existing fact in the database. 
        It sets the current active version to inactive and creates a new active version.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            new_value_json = json.dumps(new_value)
            
            # 1. Retrieve the currently active version of this fact (if any)
            cursor.execute(
                "SELECT id, fact_value, version FROM SemanticMemory WHERE fact_key = ? AND is_active = 1",
                (key,)
            )
            active_row = cursor.fetchone()
            
            if active_row:
                current_id, current_val_json, current_version = active_row
                
                # Check if the value is identical to avoid creating redundant versions
                if current_val_json == new_value_json:
                    return
                
                # Set the old version to inactive
                cursor.execute(
                    "UPDATE SemanticMemory SET is_active = 0 WHERE id = ?",
                    (current_id,)
                )
                new_version = current_version + 1
            else:
                new_version = 1
                
            # 2. Insert the newly updated fact as the active version
            cursor.execute(
                """
                INSERT INTO SemanticMemory (fact_key, fact_value, version, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (key, new_value_json, new_version)
            )
            
            conn.commit()
        finally:
            conn.close()

    def get_active_facts(self) -> Dict[str, Any]:
        """
        Retrieves only the currently active facts for the LLM to use.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT fact_key, fact_value FROM SemanticMemory WHERE is_active = 1"
            )
            rows = cursor.fetchall()
            
            active_knowledge = {}
            for row in rows:
                fact_key = row[0]
                fact_value = json.loads(row[1])
                active_knowledge[fact_key] = fact_value
                
            return active_knowledge
        finally:
            conn.close()
