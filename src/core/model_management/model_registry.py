"""
Model Registry for CALES Entity Extraction Service

This module provides comprehensive model version management, deployment tracking,
and rollback capabilities for the CALES system.
"""

import os
import json
import sqlite3
import logging
import yaml
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import threading
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Model deployment status"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelStage(Enum):
    """Model lifecycle stages"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    model_name: str
    version: str
    base_model: str
    architecture: str
    entity_types: List[str]
    training_date: str
    performance_metrics: Dict[str, float]
    hyperparameters: Dict[str, Any]
    dataset_info: Dict[str, Any]
    deployment_status: DeploymentStatus
    stage: ModelStage
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    checksum: Optional[str] = None
    model_path: Optional[str] = None
    deployment_history: List[Dict] = field(default_factory=list)
    rollback_points: List[Dict] = field(default_factory=list)


@dataclass
class DeploymentRecord:
    """Deployment record for tracking model deployments"""
    deployment_id: str
    model_id: str
    version: str
    environment: str  # staging, production
    deployed_at: str
    deployed_by: str
    status: str  # active, rolled_back, replaced
    metrics_before: Optional[Dict[str, float]] = None
    metrics_after: Optional[Dict[str, float]] = None
    rollback_reason: Optional[str] = None
    rolled_back_at: Optional[str] = None


class ModelRegistry:
    """
    Comprehensive model registry for version management, deployment tracking,
    and rollback capabilities.
    """
    
    def __init__(self, 
                 config_path: str = "/srv/luris/be/entity-extraction-service/config/models_config.yaml",
                 db_path: Optional[str] = None):
        """
        Initialize the ModelRegistry.
        
        Args:
            config_path: Path to models configuration
            db_path: Path to registry database (uses config default if None)
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Set database path
        if db_path:
            self.db_path = db_path
        else:
            # Use path from config or default
            conn_string = self.config['model_registry'].get('connection_string', '')
            if conn_string.startswith('sqlite:///'):
                self.db_path = conn_string.replace('sqlite:///', '')
            else:
                self.db_path = "/srv/luris/models/registry.db"
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Model repository paths
        self.base_path = Path(self.config['model_repository']['base_path'])
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self.lock = threading.RLock()
        
        logger.info(f"ModelRegistry initialized with database at {self.db_path}")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _init_database(self):
        """Initialize the registry database"""
        with self._get_db() as conn:
            cursor = conn.cursor()
            
            # Create models table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    base_model TEXT,
                    architecture TEXT,
                    entity_types TEXT,
                    training_date TEXT,
                    performance_metrics TEXT,
                    hyperparameters TEXT,
                    dataset_info TEXT,
                    deployment_status TEXT,
                    stage TEXT,
                    tags TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    checksum TEXT,
                    model_path TEXT,
                    deployment_history TEXT,
                    rollback_points TEXT,
                    UNIQUE(model_name, version)
                )
            """)
            
            # Create deployments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    deployment_id TEXT PRIMARY KEY,
                    model_id TEXT,
                    version TEXT,
                    environment TEXT,
                    deployed_at TEXT,
                    deployed_by TEXT,
                    status TEXT,
                    metrics_before TEXT,
                    metrics_after TEXT,
                    rollback_reason TEXT,
                    rolled_back_at TEXT,
                    FOREIGN KEY (model_id) REFERENCES models(model_id)
                )
            """)
            
            # Create metrics history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT,
                    timestamp TEXT,
                    metrics TEXT,
                    environment TEXT,
                    FOREIGN KEY (model_id) REFERENCES models(model_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_name ON models(model_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_version ON models(version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage ON models(stage)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deployment_status ON models(deployment_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deployment_model ON deployments(model_id)")
            
            conn.commit()
    
    @contextmanager
    def _get_db(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def register_model(self, model_version: ModelVersion) -> bool:
        """
        Register a new model version in the registry.
        
        Args:
            model_version: ModelVersion object with model information
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    # Convert to dictionary for storage
                    model_dict = asdict(model_version)
                    
                    # Serialize complex fields to JSON
                    json_fields = ['entity_types', 'performance_metrics', 'hyperparameters',
                                  'dataset_info', 'tags', 'deployment_history', 'rollback_points']
                    for field in json_fields:
                        if field in model_dict:
                            model_dict[field] = json.dumps(model_dict[field])
                    
                    # Convert enums to strings
                    model_dict['deployment_status'] = model_dict['deployment_status'].value if isinstance(model_dict['deployment_status'], Enum) else model_dict['deployment_status']
                    model_dict['stage'] = model_dict['stage'].value if isinstance(model_dict['stage'], Enum) else model_dict['stage']
                    
                    # Insert or update model
                    cursor.execute("""
                        INSERT OR REPLACE INTO models (
                            model_id, model_name, version, base_model, architecture,
                            entity_types, training_date, performance_metrics, hyperparameters,
                            dataset_info, deployment_status, stage, tags, created_at,
                            updated_at, checksum, model_path, deployment_history, rollback_points
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        model_dict['model_id'], model_dict['model_name'], model_dict['version'],
                        model_dict['base_model'], model_dict['architecture'], model_dict['entity_types'],
                        model_dict['training_date'], model_dict['performance_metrics'],
                        model_dict['hyperparameters'], model_dict['dataset_info'],
                        model_dict['deployment_status'], model_dict['stage'], model_dict['tags'],
                        model_dict['created_at'], model_dict['updated_at'], model_dict['checksum'],
                        model_dict['model_path'], model_dict['deployment_history'],
                        model_dict['rollback_points']
                    ))
                    
                    conn.commit()
                    logger.info(f"Registered model: {model_version.model_id} v{model_version.version}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to register model: {e}")
                return False
    
    def get_model(self, model_id: str) -> Optional[ModelVersion]:
        """
        Get a specific model by ID.
        
        Args:
            model_id: Model ID
            
        Returns:
            ModelVersion object or None
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM models WHERE model_id = ?", (model_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_model_version(row)
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to get model: {e}")
                return None
    
    def get_model_by_name_version(self, model_name: str, version: str) -> Optional[ModelVersion]:
        """
        Get a model by name and version.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            ModelVersion object or None
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM models WHERE model_name = ? AND version = ?",
                        (model_name, version)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_model_version(row)
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to get model by name and version: {e}")
                return None
    
    def get_latest_model(self, model_name: str, 
                        stage: Optional[ModelStage] = None) -> Optional[ModelVersion]:
        """
        Get the latest version of a model.
        
        Args:
            model_name: Model name
            stage: Optional stage filter
            
        Returns:
            ModelVersion object or None
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    if stage:
                        cursor.execute("""
                            SELECT * FROM models 
                            WHERE model_name = ? AND stage = ?
                            ORDER BY created_at DESC LIMIT 1
                        """, (model_name, stage.value))
                    else:
                        cursor.execute("""
                            SELECT * FROM models 
                            WHERE model_name = ?
                            ORDER BY created_at DESC LIMIT 1
                        """, (model_name,))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_model_version(row)
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to get latest model: {e}")
                return None
    
    def list_models(self, 
                   model_name: Optional[str] = None,
                   stage: Optional[ModelStage] = None,
                   deployment_status: Optional[DeploymentStatus] = None) -> List[ModelVersion]:
        """
        List models with optional filters.
        
        Args:
            model_name: Filter by model name
            stage: Filter by stage
            deployment_status: Filter by deployment status
            
        Returns:
            List of ModelVersion objects
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM models WHERE 1=1"
                    params = []
                    
                    if model_name:
                        query += " AND model_name = ?"
                        params.append(model_name)
                    
                    if stage:
                        query += " AND stage = ?"
                        params.append(stage.value)
                    
                    if deployment_status:
                        query += " AND deployment_status = ?"
                        params.append(deployment_status.value)
                    
                    query += " ORDER BY created_at DESC"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    return [self._row_to_model_version(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                return []
    
    def update_model_stage(self, model_id: str, new_stage: ModelStage) -> bool:
        """
        Update the lifecycle stage of a model.
        
        Args:
            model_id: Model ID
            new_stage: New stage
            
        Returns:
            True if successful
        """
        with self.lock:
            try:
                # Get current model
                model = self.get_model(model_id)
                if not model:
                    logger.error(f"Model {model_id} not found")
                    return False
                
                # Check stage transition rules
                if not self._validate_stage_transition(model.stage, new_stage):
                    logger.error(f"Invalid stage transition from {model.stage} to {new_stage}")
                    return False
                
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE models 
                        SET stage = ?, updated_at = ?
                        WHERE model_id = ?
                    """, (new_stage.value, datetime.now().isoformat(), model_id))
                    
                    conn.commit()
                    logger.info(f"Updated model {model_id} stage to {new_stage.value}")
                    
                    # Handle stage-specific actions
                    self._handle_stage_change(model_id, model.stage, new_stage)
                    
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to update model stage: {e}")
                return False
    
    def deploy_model(self, model_id: str, environment: str, 
                    deployed_by: str = "system") -> Optional[str]:
        """
        Deploy a model to a specific environment.
        
        Args:
            model_id: Model ID to deploy
            environment: Target environment (staging, production)
            deployed_by: User or system deploying
            
        Returns:
            Deployment ID if successful, None otherwise
        """
        with self.lock:
            try:
                # Get model
                model = self.get_model(model_id)
                if not model:
                    logger.error(f"Model {model_id} not found")
                    return None
                
                # Validate deployment
                if not self._validate_deployment(model, environment):
                    return None
                
                # Create deployment record
                deployment_id = f"deploy_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                deployment = DeploymentRecord(
                    deployment_id=deployment_id,
                    model_id=model_id,
                    version=model.version,
                    environment=environment,
                    deployed_at=datetime.now().isoformat(),
                    deployed_by=deployed_by,
                    status="active"
                )
                
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    # Mark previous deployments as replaced
                    cursor.execute("""
                        UPDATE deployments 
                        SET status = 'replaced'
                        WHERE model_id = ? AND environment = ? AND status = 'active'
                    """, (model_id, environment))
                    
                    # Insert new deployment
                    cursor.execute("""
                        INSERT INTO deployments (
                            deployment_id, model_id, version, environment,
                            deployed_at, deployed_by, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        deployment.deployment_id, deployment.model_id, deployment.version,
                        deployment.environment, deployment.deployed_at, deployment.deployed_by,
                        deployment.status
                    ))
                    
                    # Update model deployment status
                    new_status = DeploymentStatus.PRODUCTION if environment == "production" else DeploymentStatus.STAGING
                    cursor.execute("""
                        UPDATE models 
                        SET deployment_status = ?, updated_at = ?
                        WHERE model_id = ?
                    """, (new_status.value, datetime.now().isoformat(), model_id))
                    
                    # Add to deployment history
                    model.deployment_history.append({
                        "deployment_id": deployment_id,
                        "environment": environment,
                        "deployed_at": deployment.deployed_at,
                        "deployed_by": deployed_by
                    })
                    
                    cursor.execute("""
                        UPDATE models 
                        SET deployment_history = ?
                        WHERE model_id = ?
                    """, (json.dumps(model.deployment_history), model_id))
                    
                    conn.commit()
                    
                    # Physically deploy the model
                    self._deploy_model_files(model, environment)
                    
                    logger.info(f"Deployed model {model_id} to {environment}")
                    return deployment_id
                    
            except Exception as e:
                logger.error(f"Failed to deploy model: {e}")
                return None
    
    def rollback_deployment(self, deployment_id: str, 
                          reason: str = "Manual rollback") -> bool:
        """
        Rollback a deployment.
        
        Args:
            deployment_id: Deployment ID to rollback
            reason: Reason for rollback
            
        Returns:
            True if successful
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    # Get deployment
                    cursor.execute(
                        "SELECT * FROM deployments WHERE deployment_id = ?",
                        (deployment_id,)
                    )
                    deployment_row = cursor.fetchone()
                    
                    if not deployment_row:
                        logger.error(f"Deployment {deployment_id} not found")
                        return False
                    
                    if deployment_row['status'] != 'active':
                        logger.error(f"Deployment {deployment_id} is not active")
                        return False
                    
                    # Get previous deployment
                    cursor.execute("""
                        SELECT * FROM deployments 
                        WHERE environment = ? AND status = 'replaced'
                        ORDER BY deployed_at DESC LIMIT 1
                    """, (deployment_row['environment'],))
                    
                    previous_deployment = cursor.fetchone()
                    
                    # Update current deployment
                    cursor.execute("""
                        UPDATE deployments 
                        SET status = 'rolled_back', 
                            rollback_reason = ?, 
                            rolled_back_at = ?
                        WHERE deployment_id = ?
                    """, (reason, datetime.now().isoformat(), deployment_id))
                    
                    # Reactivate previous deployment if exists
                    if previous_deployment:
                        cursor.execute("""
                            UPDATE deployments 
                            SET status = 'active'
                            WHERE deployment_id = ?
                        """, (previous_deployment['deployment_id'],))
                        
                        # Update model deployment status
                        cursor.execute("""
                            UPDATE models 
                            SET deployment_status = ?, updated_at = ?
                            WHERE model_id = ?
                        """, (
                            DeploymentStatus.PRODUCTION.value 
                            if previous_deployment['environment'] == 'production' 
                            else DeploymentStatus.STAGING.value,
                            datetime.now().isoformat(),
                            previous_deployment['model_id']
                        ))
                        
                        # Restore previous model files
                        previous_model = self.get_model(previous_deployment['model_id'])
                        if previous_model:
                            self._deploy_model_files(previous_model, 
                                                    previous_deployment['environment'])
                    
                    conn.commit()
                    logger.info(f"Rolled back deployment {deployment_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to rollback deployment: {e}")
                return False
    
    def create_rollback_point(self, model_id: str, 
                            description: str = "Manual checkpoint") -> bool:
        """
        Create a rollback point for a model.
        
        Args:
            model_id: Model ID
            description: Description of the rollback point
            
        Returns:
            True if successful
        """
        with self.lock:
            try:
                model = self.get_model(model_id)
                if not model:
                    logger.error(f"Model {model_id} not found")
                    return False
                
                # Create rollback point
                rollback_point = {
                    "timestamp": datetime.now().isoformat(),
                    "description": description,
                    "model_path": model.model_path,
                    "performance_metrics": model.performance_metrics,
                    "deployment_status": model.deployment_status.value,
                    "stage": model.stage.value
                }
                
                # Backup model files
                if model.model_path:
                    backup_path = self._backup_model_files(model)
                    rollback_point["backup_path"] = str(backup_path)
                
                model.rollback_points.append(rollback_point)
                
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE models 
                        SET rollback_points = ?, updated_at = ?
                        WHERE model_id = ?
                    """, (
                        json.dumps(model.rollback_points),
                        datetime.now().isoformat(),
                        model_id
                    ))
                    conn.commit()
                
                logger.info(f"Created rollback point for model {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create rollback point: {e}")
                return False
    
    def get_deployment_history(self, model_id: Optional[str] = None,
                              environment: Optional[str] = None) -> List[Dict]:
        """
        Get deployment history.
        
        Args:
            model_id: Filter by model ID
            environment: Filter by environment
            
        Returns:
            List of deployment records
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM deployments WHERE 1=1"
                    params = []
                    
                    if model_id:
                        query += " AND model_id = ?"
                        params.append(model_id)
                    
                    if environment:
                        query += " AND environment = ?"
                        params.append(environment)
                    
                    query += " ORDER BY deployed_at DESC"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    return [dict(row) for row in rows]
                    
            except Exception as e:
                logger.error(f"Failed to get deployment history: {e}")
                return []
    
    def record_metrics(self, model_id: str, metrics: Dict[str, float],
                      environment: str = "production"):
        """
        Record performance metrics for a model.
        
        Args:
            model_id: Model ID
            metrics: Performance metrics
            environment: Environment where metrics were collected
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO metrics_history (model_id, timestamp, metrics, environment)
                        VALUES (?, ?, ?, ?)
                    """, (
                        model_id,
                        datetime.now().isoformat(),
                        json.dumps(metrics),
                        environment
                    ))
                    conn.commit()
                    
                logger.info(f"Recorded metrics for model {model_id}")
                
            except Exception as e:
                logger.error(f"Failed to record metrics: {e}")
    
    def get_metrics_history(self, model_id: str, 
                          days: int = 30) -> List[Dict]:
        """
        Get metrics history for a model.
        
        Args:
            model_id: Model ID
            days: Number of days of history to retrieve
            
        Returns:
            List of metrics records
        """
        with self.lock:
            try:
                with self._get_db() as conn:
                    cursor = conn.cursor()
                    
                    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                    
                    cursor.execute("""
                        SELECT * FROM metrics_history 
                        WHERE model_id = ? AND timestamp > ?
                        ORDER BY timestamp DESC
                    """, (model_id, cutoff_date))
                    
                    rows = cursor.fetchall()
                    
                    return [
                        {
                            "timestamp": row["timestamp"],
                            "metrics": json.loads(row["metrics"]),
                            "environment": row["environment"]
                        }
                        for row in rows
                    ]
                    
            except Exception as e:
                logger.error(f"Failed to get metrics history: {e}")
                return []
    
    def _row_to_model_version(self, row: sqlite3.Row) -> ModelVersion:
        """Convert database row to ModelVersion object"""
        data = dict(row)
        
        # Parse JSON fields
        json_fields = ['entity_types', 'performance_metrics', 'hyperparameters',
                      'dataset_info', 'tags', 'deployment_history', 'rollback_points']
        for field in json_fields:
            if field in data and data[field]:
                try:
                    data[field] = json.loads(data[field])
                except:
                    data[field] = [] if field in ['entity_types', 'tags', 
                                                  'deployment_history', 'rollback_points'] else {}
        
        # Convert string enums
        data['deployment_status'] = DeploymentStatus(data['deployment_status'])
        data['stage'] = ModelStage(data['stage'])
        
        return ModelVersion(**data)
    
    def _validate_stage_transition(self, current: ModelStage, 
                                  new: ModelStage) -> bool:
        """Validate stage transition is allowed"""
        allowed_transitions = {
            ModelStage.DEVELOPMENT: [ModelStage.TESTING],
            ModelStage.TESTING: [ModelStage.STAGING, ModelStage.DEVELOPMENT],
            ModelStage.STAGING: [ModelStage.PRODUCTION, ModelStage.TESTING],
            ModelStage.PRODUCTION: [ModelStage.DEPRECATED, ModelStage.STAGING],
            ModelStage.DEPRECATED: [ModelStage.ARCHIVED],
            ModelStage.ARCHIVED: []
        }
        
        return new in allowed_transitions.get(current, [])
    
    def _validate_deployment(self, model: ModelVersion, environment: str) -> bool:
        """Validate model is ready for deployment"""
        # Check performance metrics meet thresholds
        required_metrics = self.config['lifecycle']['stages']
        
        for stage_config in required_metrics:
            if stage_config['name'] == environment:
                required = stage_config.get('required_metrics', {})
                
                for metric, threshold in required.items():
                    if metric in model.performance_metrics:
                        if model.performance_metrics[metric] < threshold:
                            logger.error(f"Model {model.model_id} does not meet "
                                       f"{metric} threshold: {model.performance_metrics[metric]} < {threshold}")
                            return False
        
        return True
    
    def _handle_stage_change(self, model_id: str, old_stage: ModelStage, 
                           new_stage: ModelStage):
        """Handle stage-specific actions"""
        if new_stage == ModelStage.ARCHIVED:
            # Move model files to archive
            self._archive_model_files(model_id)
        elif new_stage == ModelStage.PRODUCTION:
            # Create automatic rollback point
            self.create_rollback_point(model_id, "Automatic checkpoint before production")
    
    def _deploy_model_files(self, model: ModelVersion, environment: str):
        """Deploy model files to target environment"""
        if not model.model_path:
            return
        
        source_path = Path(model.model_path)
        target_path = self.base_path / environment.lower() / model.model_name
        
        if source_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(source_path, target_path)
            logger.info(f"Deployed model files to {target_path}")
    
    def _backup_model_files(self, model: ModelVersion) -> Path:
        """Create backup of model files"""
        if not model.model_path:
            return Path()
        
        source_path = Path(model.model_path)
        backup_path = self.base_path / "backups" / model.model_id / datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if source_path.exists():
            backup_path.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_path, backup_path, dirs_exist_ok=True)
            logger.info(f"Created backup at {backup_path}")
        
        return backup_path
    
    def _archive_model_files(self, model_id: str):
        """Archive model files"""
        model = self.get_model(model_id)
        if not model or not model.model_path:
            return
        
        source_path = Path(model.model_path)
        archive_path = self.base_path / "archived" / model.model_id
        
        if source_path.exists():
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            if archive_path.exists():
                shutil.rmtree(archive_path)
            shutil.move(str(source_path), str(archive_path))
            logger.info(f"Archived model files to {archive_path}")


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Registry")
    parser.add_argument("--register", help="Register a model (provide JSON file)")
    parser.add_argument("--list", action="store_true", help="List all models")
    parser.add_argument("--get", help="Get specific model by ID")
    parser.add_argument("--deploy", help="Deploy model ID")
    parser.add_argument("--environment", help="Deployment environment", default="staging")
    parser.add_argument("--rollback", help="Rollback deployment ID")
    parser.add_argument("--history", help="Show deployment history for model ID")
    parser.add_argument("--update-stage", help="Update model stage (model_id:new_stage)")
    
    args = parser.parse_args()
    
    registry = ModelRegistry()
    
    if args.register:
        # Load model info from JSON file
        with open(args.register, 'r') as f:
            model_data = json.load(f)
        
        model_version = ModelVersion(**model_data)
        success = registry.register_model(model_version)
        print(f"Registration {'successful' if success else 'failed'}")
    
    if args.list:
        models = registry.list_models()
        for model in models:
            print(f"{model.model_id} v{model.version} - Stage: {model.stage.value}, "
                  f"Status: {model.deployment_status.value}")
    
    if args.get:
        model = registry.get_model(args.get)
        if model:
            print(json.dumps(asdict(model), indent=2, default=str))
        else:
            print(f"Model {args.get} not found")
    
    if args.deploy:
        deployment_id = registry.deploy_model(args.deploy, args.environment)
        if deployment_id:
            print(f"Deployment successful: {deployment_id}")
        else:
            print("Deployment failed")
    
    if args.rollback:
        success = registry.rollback_deployment(args.rollback)
        print(f"Rollback {'successful' if success else 'failed'}")
    
    if args.history:
        history = registry.get_deployment_history(model_id=args.history)
        print(json.dumps(history, indent=2))
    
    if args.update_stage:
        model_id, new_stage = args.update_stage.split(':')
        success = registry.update_model_stage(model_id, ModelStage(new_stage))
        print(f"Stage update {'successful' if success else 'failed'}")