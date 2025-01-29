"""State persistence module for analysis state management."""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
import json
import sqlite3
from contextlib import contextmanager

@dataclass
class SchemaInfo:
    """Schema information for persistence."""
    schema_type: str
    schema_id: str
    version: str
    content: dict
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class Checkpoint:
    """Analysis checkpoint information."""
    timestamp: datetime
    completed_services: List[str]
    completed_schemas: List[str]
    stage: str
    metadata: Dict[str, str]

@dataclass
class AnalysisState:
    """Represents the current state of analysis."""
    services_analyzed: Dict[str, bool] = field(default_factory=dict)
    schemas_detected: Dict[str, SchemaInfo] = field(default_factory=dict)
    dependencies_mapped: Set[Tuple[str, str]] = field(default_factory=set)
    checkpoints: List[Checkpoint] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization."""
        return {
            **asdict(self),
            'dependencies_mapped': list(self.dependencies_mapped),
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AnalysisState':
        """Create state from dictionary."""
        data['dependencies_mapped'] = set(tuple(x) for x in data['dependencies_mapped'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class StateManager:
    """Manages analysis state persistence."""
    
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / 'analysis_state.db'
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for state persistence."""
        with self._get_db() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS analysis_state (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    state_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY,
                    state_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    stage TEXT NOT NULL,
                    metadata_json TEXT,
                    FOREIGN KEY (state_id) REFERENCES analysis_state(id)
                );

                CREATE TABLE IF NOT EXISTS schema_cache (
                    schema_id TEXT PRIMARY KEY,
                    schema_type TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')

    @contextmanager
    def _get_db(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_state(self, state: AnalysisState) -> int:
        """Save current analysis state."""
        with self._get_db() as conn:
            cursor = conn.execute(
                'INSERT INTO analysis_state (state_json) VALUES (?)',
                [json.dumps(state.to_dict())]
            )
            state_id = cursor.lastrowid
            
            # Save checkpoints
            for checkpoint in state.checkpoints:
                conn.execute(
                    '''INSERT INTO checkpoints 
                       (state_id, stage, metadata_json, timestamp)
                       VALUES (?, ?, ?, ?)''',
                    [state_id, checkpoint.stage,
                     json.dumps(checkpoint.metadata),
                     checkpoint.timestamp.isoformat()]
                )
            
            return state_id

    def load_latest_state(self) -> Optional[AnalysisState]:
        """Load the most recent analysis state."""
        with self._get_db() as conn:
            row = conn.execute('''
                SELECT state_json 
                FROM analysis_state 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''').fetchone()
            
            if row:
                return AnalysisState.from_dict(json.loads(row['state_json']))
            return None

    def save_schema(self, schema: SchemaInfo):
        """Cache schema information."""
        with self._get_db() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO schema_cache
                (schema_id, schema_type, version, content_json, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', [
                schema.schema_id,
                schema.schema_type,
                schema.version,
                json.dumps(schema.content),
                schema.last_updated.isoformat()
            ])

    def get_schema(self, schema_id: str) -> Optional[SchemaInfo]:
        """Retrieve cached schema information."""
        with self._get_db() as conn:
            row = conn.execute(
                'SELECT * FROM schema_cache WHERE schema_id = ?',
                [schema_id]
            ).fetchone()
            
            if row:
                return SchemaInfo(
                    schema_id=row['schema_id'],
                    schema_type=row['schema_type'],
                    version=row['version'],
                    content=json.loads(row['content_json']),
                    last_updated=datetime.fromisoformat(row['last_updated'])
                )
            return None