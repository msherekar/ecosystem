"""
Agent learning system for continuous improvement based on user interactions.
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import streamlit as st

class AgentLearningSystem:
    """System for learning from user interactions and improving agent responses"""
    
    def __init__(self, db_path: str = "data/agent_learning.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the learning database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_input TEXT,
                agent_response TEXT,
                tools_used TEXT,
                analysis_type TEXT,
                context_state TEXT,
                user_feedback INTEGER,  -- 1 for positive, -1 for negative, 0 for neutral
                success_indicators TEXT  -- JSON of success metrics
            )
        """)
        
        # Command patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE,
                intended_tool TEXT,
                confidence_score REAL,
                usage_count INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.5
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_interaction(self, user_input: str, agent_response: str, tools_used: List[str], 
                       analysis_type: str, context_state: Dict[str, Any], 
                       user_feedback: int = 0, success_indicators: Dict[str, Any] = None):
        """Log a user-agent interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_interactions 
            (timestamp, user_input, agent_response, tools_used, analysis_type, 
             context_state, user_feedback, success_indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_input,
            agent_response,
            json.dumps(tools_used),
            analysis_type,
            json.dumps(context_state),
            user_feedback,
            json.dumps(success_indicators or {})
        ))
        
        conn.commit()
        conn.close()
    
    def learn_command_pattern(self, user_input: str, successful_tool: str):
        """Learn from successful command-tool mappings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract key phrases from user input
        patterns = self._extract_patterns(user_input)
        
        for pattern in patterns:
            cursor.execute("""
                INSERT OR REPLACE INTO command_patterns 
                (pattern, intended_tool, confidence_score, usage_count, success_rate)
                VALUES (?, ?, 
                    COALESCE((SELECT confidence_score FROM command_patterns WHERE pattern = ?), 0.5) + 0.1,
                    COALESCE((SELECT usage_count FROM command_patterns WHERE pattern = ?), 0) + 1,
                    COALESCE((SELECT success_rate FROM command_patterns WHERE pattern = ?), 0.5) + 0.05
                )
            """, (pattern, successful_tool, pattern, pattern, pattern))
        
        conn.commit()
        conn.close()
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract meaningful patterns from user input"""
        import re
        
        text = text.lower()
        patterns = []
        
        # Common command patterns
        command_patterns = [
            r"perform.*next.*step",
            r"advance.*step", 
            r"continue.*analysis",
            r"move.*next",
            r"run.*analysis",
            r"analyze.*plot",
            r"get.*insight"
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, text):
                patterns.append(pattern)
        
        return patterns
    
    def get_suggested_tool(self, user_input: str) -> Optional[str]:
        """Get suggested tool based on learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = self._extract_patterns(user_input)
        best_tool = None
        best_score = 0
        
        for pattern in patterns:
            cursor.execute("""
                SELECT intended_tool, confidence_score, success_rate 
                FROM command_patterns 
                WHERE pattern = ?
                ORDER BY confidence_score * success_rate DESC
                LIMIT 1
            """, (pattern,))
            
            result = cursor.fetchone()
            if result:
                tool, confidence, success_rate = result
                score = confidence * success_rate
                if score > best_score:
                    best_score = score
                    best_tool = tool
        
        conn.close()
        return best_tool if best_score > 0.6 else None

# Global learning system instance
learning_system = AgentLearningSystem() 