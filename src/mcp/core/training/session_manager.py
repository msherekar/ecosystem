"""
Session management and training statistics for the training system.
Handles multi-session coordination and comprehensive statistics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from .storage import TrainingDataStorage
from .config import TrainingConfig
from .events import get_event_bus, EventType
from .collectors import ConversationCollector

class SessionManager:
    """Manages multiple conversation sessions and global statistics"""
    
    def __init__(self, storage: TrainingDataStorage, config: TrainingConfig):
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger("session_manager")
        self.event_bus = get_event_bus()
        
        # Active sessions
        self.active_sessions: Dict[str, ConversationCollector] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Statistics cache
        self._stats_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # 5-minute cache
    
    async def get_or_create_session(
        self, 
        session_id: str, 
        session_provider=None
    ) -> ConversationCollector:
        """Get existing session or create new one"""
        
        if session_id not in self.active_sessions:
            # Create new collector for this session
            collector = ConversationCollector(
                storage=self.storage,
                config=self.config,
                session_provider=session_provider
            )
            collector.current_session_id = session_id
            
            self.active_sessions[session_id] = collector
            self.session_metadata[session_id] = {
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "turn_count": 0
            }
            
            await self.event_bus.emit(
                EventType.SESSION_STARTED,
                {"session_id": session_id}
            )
            
            self.logger.info(f"Created new session: {session_id}")
        
        # Update last activity
        self.session_metadata[session_id]["last_activity"] = datetime.now()
        
        return self.active_sessions[session_id]
    
    async def finalize_session(self, session_id: str) -> bool:
        """Finalize and remove a session"""
        if session_id not in self.active_sessions:
            return False
        
        try:
            collector = self.active_sessions[session_id]
            await collector.finalize_session()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            del self.session_metadata[session_id]
            
            await self.event_bus.emit(
                EventType.SESSION_ENDED,
                {"session_id": session_id}
            )
            
            # Invalidate cache
            self._invalidate_cache()
            
            self.logger.info(f"Finalized session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to finalize session {session_id}: {e}")
            return False
    
    async def finalize_all_sessions(self) -> int:
        """Finalize all active sessions"""
        session_ids = list(self.active_sessions.keys())
        finalized_count = 0
        
        for session_id in session_ids:
            if await self.finalize_session(session_id):
                finalized_count += 1
        
        return finalized_count
    
    async def cleanup_inactive_sessions(self, max_idle_minutes: int = 60) -> int:
        """Clean up sessions that have been inactive"""
        cutoff_time = datetime.now() - timedelta(minutes=max_idle_minutes)
        inactive_sessions = []
        
        for session_id, metadata in self.session_metadata.items():
            if metadata["last_activity"] < cutoff_time:
                inactive_sessions.append(session_id)
        
        cleaned_count = 0
        for session_id in inactive_sessions:
            if await self.finalize_session(session_id):
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} inactive sessions")
        
        return cleaned_count
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.active_sessions)
    
    def get_session_list(self) -> List[Dict[str, Any]]:
        """Get list of all active sessions with metadata"""
        sessions = []
        
        for session_id, collector in self.active_sessions.items():
            metadata = self.session_metadata.get(session_id, {})
            stats = collector.get_session_statistics()
            
            sessions.append({
                "session_id": session_id,
                "created_at": metadata.get("created_at"),
                "last_activity": metadata.get("last_activity"),
                "turn_count": stats.get("total_turns", 0),
                "success_rate": stats.get("success_rate", 0),
                "analysis_types": stats.get("analysis_types", {}),
                "is_active": True
            })
        
        return sessions
    
    async def get_comprehensive_statistics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get comprehensive training statistics across all data"""
        
        # Check cache first
        if use_cache and self._is_cache_valid():
            return self._stats_cache
        
        try:
            stats = {
                "collection_summary": await self._get_collection_summary(),
                "active_sessions": self._get_active_session_stats(),
                "storage_statistics": await self._get_storage_statistics(),
                "dataset_analysis": await self._get_dataset_analysis(),
                "performance_metrics": await self._get_performance_metrics(),
                "generated_at": datetime.now().isoformat()
            }
            
            # Update cache
            self._stats_cache = stats
            self._cache_timestamp = datetime.now()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate comprehensive statistics: {e}")
            return {"error": str(e)}
    
    async def _get_collection_summary(self) -> Dict[str, Any]:
        """Get summary of data collection"""
        return {
            "active_sessions": len(self.active_sessions),
            "collection_enabled": self.config.collect_enabled,
            "data_directory": str(self.storage.data_dir),
            "auto_save_interval": self.config.auto_save_interval,
            "anonymization_enabled": self.config.anonymize_data
        }
    
    def _get_active_session_stats(self) -> Dict[str, Any]:
        """Get statistics for active sessions"""
        if not self.active_sessions:
            return {"total_sessions": 0}
        
        total_turns = 0
        analysis_types = defaultdict(int)
        pipeline_steps = defaultdict(int)
        success_count = 0
        total_success_turns = 0
        
        for collector in self.active_sessions.values():
            session_stats = collector.get_session_statistics()
            
            turns = session_stats.get("total_turns", 0)
            total_turns += turns
            
            if turns > 0:
                total_success_turns += turns
                success_count += session_stats.get("success_rate", 0) * turns
            
            # Aggregate analysis types
            for analysis_type, count in session_stats.get("analysis_types", {}).items():
                analysis_types[analysis_type] += count
            
            # Aggregate pipeline steps
            for step, count in session_stats.get("pipeline_steps", {}).items():
                pipeline_steps[step] += count
        
        return {
            "total_sessions": len(self.active_sessions),
            "total_active_turns": total_turns,
            "overall_success_rate": (success_count / total_success_turns) if total_success_turns > 0 else 0,
            "analysis_types": dict(analysis_types),
            "pipeline_steps": dict(pipeline_steps)
        }
    
    async def _get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage-related statistics"""
        try:
            storage_stats = self.storage.get_storage_statistics()
            
            # Add dataset count and details
            datasets = self.storage.list_datasets()
            
            return {
                **storage_stats,
                "dataset_count": len(datasets),
                "recent_datasets": datasets[:5] if datasets else []
            }
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {"error": str(e)}
    
    async def _get_dataset_analysis(self) -> Dict[str, Any]:
        """Analyze existing datasets for patterns"""
        try:
            datasets = self.storage.list_datasets()
            
            if not datasets:
                return {"total_datasets": 0}
            
            total_conversations = 0
            analysis_type_distribution = defaultdict(int)
            success_rates = []
            date_range = {"earliest": None, "latest": None}
            
            for dataset_info in datasets[:20]:  # Limit to recent 20 for performance
                try:
                    info = self.storage.get_dataset_info(dataset_info['filepath'])
                    
                    conv_count = info.get('total_conversations', 0)
                    total_conversations += conv_count
                    
                    success_rates.append(info.get('success_rate', 0))
                    
                    # Analysis types
                    for analysis_type, count in info.get('analysis_types', {}).items():
                        analysis_type_distribution[analysis_type] += count
                    
                    # Date range
                    dataset_range = info.get('date_range', {})
                    if dataset_range.get('earliest'):
                        if not date_range['earliest'] or dataset_range['earliest'] < date_range['earliest']:
                            date_range['earliest'] = dataset_range['earliest']
                    
                    if dataset_range.get('latest'):
                        if not date_range['latest'] or dataset_range['latest'] > date_range['latest']:
                            date_range['latest'] = dataset_range['latest']
                
                except Exception as e:
                    self.logger.warning(f"Failed to analyze dataset {dataset_info['filename']}: {e}")
            
            return {
                "total_datasets": len(datasets),
                "total_stored_conversations": total_conversations,
                "average_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
                "analysis_type_distribution": dict(analysis_type_distribution),
                "data_date_range": date_range,
                "datasets_analyzed": min(20, len(datasets))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze datasets: {e}")
            return {"error": str(e)}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            "cache_hit_rate": 1.0 if self._is_cache_valid() else 0.0,
            "active_sessions": len(self.active_sessions),
            "memory_usage_mb": self._estimate_memory_usage(),
            "avg_session_age_minutes": self._calculate_avg_session_age()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage of active sessions"""
        # Simple estimation: ~1KB per conversation turn
        total_turns = sum(
            len(collector.current_session_data) 
            for collector in self.active_sessions.values()
        )
        return total_turns * 1.0 / 1024  # Convert to MB
    
    def _calculate_avg_session_age(self) -> float:
        """Calculate average age of active sessions in minutes"""
        if not self.session_metadata:
            return 0.0
        
        now = datetime.now()
        total_age = sum(
            (now - metadata["created_at"]).total_seconds() / 60
            for metadata in self.session_metadata.values()
        )
        
        return total_age / len(self.session_metadata)
    
    def _is_cache_valid(self) -> bool:
        """Check if statistics cache is still valid"""
        if not self._stats_cache or not self._cache_timestamp:
            return False
        
        return datetime.now() - self._cache_timestamp < self._cache_ttl
    
    def _invalidate_cache(self) -> None:
        """Invalidate statistics cache"""
        self._stats_cache = None
        self._cache_timestamp = None
    
    async def export_session_report(self, session_id: str = None) -> Dict[str, Any]:
        """Export detailed report for a session or all sessions"""
        if session_id and session_id in self.active_sessions:
            collector = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "statistics": collector.get_session_statistics(),
                "conversations": [turn.to_dict() for turn in collector.get_current_session_turns()],
                "metadata": self.session_metadata.get(session_id, {})
            }
        else:
            # Export all sessions
            return {
                "all_sessions": {
                    sid: {
                        "statistics": collector.get_session_statistics(),
                        "metadata": self.session_metadata.get(sid, {})
                    }
                    for sid, collector in self.active_sessions.items()
                },
                "summary": await self.get_comprehensive_statistics()
            }


def main():
    """Test session manager"""
    import asyncio
    
    async def test_session_manager():
        print("Testing Session Manager")
        print("=" * 30)
        
        # Create session manager
        config = TrainingConfig(data_dir="data/test")
        storage = TrainingDataStorage("data/test", config)
        session_manager = SessionManager(storage, config)
        
        # Test session creation
        session1 = await session_manager.get_or_create_session("test_session_1")
        session2 = await session_manager.get_or_create_session("test_session_2")
        
        print(f"✓ Created sessions: {session_manager.get_active_session_count()}")
        
        # Test session list
        sessions = session_manager.get_session_list()
        print(f"✓ Session list: {len(sessions)} sessions")
        
        # Test statistics
        stats = await session_manager.get_comprehensive_statistics()
        print(f"✓ Statistics generated: {len(stats)} sections")
        
        # Test cleanup
        cleaned = await session_manager.cleanup_inactive_sessions(0)  # Immediate cleanup
        print(f"✓ Cleaned sessions: {cleaned}")
        
        # Test finalization
        finalized = await session_manager.finalize_all_sessions()
        print(f"✓ Finalized sessions: {finalized}")
    
    asyncio.run(test_session_manager())
    
if __name__ == "__main__":
    main()