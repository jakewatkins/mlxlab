"""
Metrics collection for MCP Host.

Tracks request counts, latencies, success/error rates per server.
"""

import asyncio
import logging
from typing import Dict, Optional
from .types import MetricsData

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and reports performance metrics."""
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._metrics: Dict[str, MetricsData] = {}
        self._lock = asyncio.Lock()
    
    async def record_request(
        self,
        server: str,
        method: str,
        latency: float,
        success: bool
    ) -> None:
        """
        Record a request metric.
        
        Args:
            server: Server name
            method: Request method
            latency: Request latency in seconds
            success: Whether request succeeded
        """
        async with self._lock:
            # Get or create metrics for this server
            if server not in self._metrics:
                self._metrics[server] = MetricsData()
            
            metrics = self._metrics[server]
            
            # Update metrics
            metrics.request_count += 1
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
            
            # Update latency stats
            metrics.total_latency += latency
            metrics.min_latency = min(metrics.min_latency, latency)
            metrics.max_latency = max(metrics.max_latency, latency)
            metrics.latencies.append(latency)
            
            # Keep only recent latencies (last 1000)
            if len(metrics.latencies) > 1000:
                metrics.latencies = metrics.latencies[-1000:]
    
    def record_request_sync(
        self,
        server: str,
        method: str,
        latency: float,
        success: bool
    ) -> None:
        """
        Synchronous version of record_request for use outside async context.
        
        Args:
            server: Server name
            method: Request method
            latency: Request latency in seconds
            success: Whether request succeeded
        """
        # Get or create metrics for this server
        if server not in self._metrics:
            self._metrics[server] = MetricsData()
        
        metrics = self._metrics[server]
        
        # Update metrics
        metrics.request_count += 1
        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
        
        # Update latency stats
        metrics.total_latency += latency
        metrics.min_latency = min(metrics.min_latency, latency)
        metrics.max_latency = max(metrics.max_latency, latency)
        metrics.latencies.append(latency)
        
        # Keep only recent latencies (last 1000)
        if len(metrics.latencies) > 1000:
            metrics.latencies = metrics.latencies[-1000:]
    
    def get_server_metrics(self, server: str) -> MetricsData:
        """
        Get metrics for a specific server.
        
        Args:
            server: Server name
            
        Returns:
            MetricsData for the server
        """
        return self._metrics.get(server, MetricsData())
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """
        Get metrics for all servers.
        
        Returns:
            Dictionary mapping server names to their metrics
        """
        result = {}
        for server, metrics in self._metrics.items():
            result[server] = {
                "request_count": metrics.request_count,
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
                "success_rate": metrics.success_rate,
                "error_rate": metrics.error_rate,
                "avg_latency": metrics.avg_latency,
                "min_latency": metrics.min_latency if metrics.min_latency != float('inf') else 0.0,
                "max_latency": metrics.max_latency,
                "p95_latency": metrics.p95_latency()
            }
        return result
    
    def reset_metrics(self, server: Optional[str] = None) -> None:
        """
        Reset metrics.
        
        Args:
            server: Server name to reset (resets all if None)
        """
        if server:
            if server in self._metrics:
                self._metrics[server] = MetricsData()
                logger.info(f"Reset metrics for server '{server}'")
        else:
            self._metrics.clear()
            logger.info("Reset all metrics")
