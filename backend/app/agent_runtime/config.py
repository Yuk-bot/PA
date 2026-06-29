import os
from pydantic_settings import BaseSettings

class RuntimeSettings(BaseSettings):
    # Model configuration
    DEFAULT_MODEL: str = "gemini-2.5-flash"
    
    # Timeouts (in seconds)
    DEFAULT_TIMEOUT_SEC: float = 30.0
    MAX_TIMEOUT_SEC: float = 120.0
    
    # Retry Policies
    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_BACKOFF_FACTOR: float = 1.5
    
    # Evaluation Limits
    EVALUATION_CONFIDENCE_THRESHOLD: float = 0.7
    MAX_REFINEMENT_LOOPS: int = 2
    
    # Firestore Paths
    FIRESTORE_SESSION_PREFIX: str = "users/{uid}/sessions"
    FIRESTORE_MEMORY_PREFIX: str = "users/{uid}/long_term_memory"
    FIRESTORE_CHECKPOINT_PREFIX: str = "users/{uid}/checkpoints"
    
    # Tracing
    ENABLE_TRACING: bool = True
    
    class Config:
        env_prefix = "AGENT_RUNTIME_"

settings = RuntimeSettings()
