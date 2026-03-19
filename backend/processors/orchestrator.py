"""Processor Orchestrator - Run all microservices together.

Coordinates all processors in the pipeline:
- Ingestion → Normalization → Features → Clustering → Trending

Each processor runs independently and communicates via Kafka topics.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, List, Dict, Any

import click

from backend.processors.processor_ingestion import run_ingestion_processor
from backend.processors.processor_normalization import run_normalization_processor
from backend.processors.processor_features import run_features_processor
from backend.processors.processor_clustering import run_clustering_processor
from backend.processors.processor_trending import run_trending_processor
from backend.processors.historical_loader import backfill_historical

logger = logging.getLogger(__name__)


class ProcessorOrchestrator:
    """Orchestrates all processors as async tasks."""
    
    def __init__(self):
        """Initialize orchestrator."""
        self.tasks = []
        self.running = False
    
    async def run_all_processors(
        self,
        num_threads: int = 3,
        trending_window_hours: int = 1,
        trending_top_k: int = 5,
        skip_ingestion: bool = False,
        skip_normalization: bool = False,
        skip_features: bool = False,
        skip_clustering: bool = False,
        skip_trending: bool = False,
    ):
        """Run all processors concurrently.
        
        Args:
            num_threads: Threads per processor
            trending_window_hours: Time window for trending (1, 4, or 24)
            trending_top_k: Top-K items to extract
            skip_*: Skip specific processors (for testing)
        """
        self.running = True
        
        logger.info("Starting Processor Pipeline...")
        logger.info(f"Config: {num_threads} threads, trending window: {trending_window_hours}h, top-{trending_top_k}")
        
        try:
            # Start processors as concurrent tasks
            if not skip_ingestion:
                self.tasks.append(
                    asyncio.create_task(run_ingestion_processor(num_threads=num_threads))
                )
                logger.info("✓ Ingestion processor started")
            
            if not skip_normalization:
                self.tasks.append(
                    asyncio.create_task(run_normalization_processor(num_threads=num_threads))
                )
                logger.info("✓ Normalization processor started")
            
            if not skip_features:
                self.tasks.append(
                    asyncio.create_task(run_features_processor(num_threads=num_threads))
                )
                logger.info("✓ Feature engineering processor started")
            
            if not skip_clustering:
                self.tasks.append(
                    asyncio.create_task(run_clustering_processor(num_threads=num_threads))
                )
                logger.info("✓ Clustering processor started")
            
            if not skip_trending:
                from backend.processors.processor_trending import run_trending_processor
                self.tasks.append(
                    asyncio.create_task(
                        run_trending_processor(
                            window_hours=trending_window_hours,
                            top_k=trending_top_k,
                            num_threads=num_threads
                        )
                    )
                )
                logger.info("✓ Trending processor started")
            
            logger.info(f"\nPipeline running with {len(self.tasks)} processors...")
            logger.info("Press Ctrl+C to stop")
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks)
        
        except asyncio.CancelledError:
            logger.info("Pipeline cancelled")
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            self.running = False
    
    def stop(self):
        """Stop all processors."""
        logger.info("Stopping processors...")
        
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        self.running = False


@click.group()
def cli():
    """Processor Pipeline CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.option('--threads', default=3, help='Processing threads per processor')
@click.option('--trending-window', default=1, type=int, help='Trending window hours (1/4/24)')
@click.option('--trending-top', default=5, type=int, help='Top-K trending items')
@click.option('--skip-ingestion', is_flag=True, help='Skip ingestion processor')
@click.option('--skip-normalization', is_flag=True, help='Skip normalization processor')
@click.option('--skip-features', is_flag=True, help='Skip feature processor')
@click.option('--skip-clustering', is_flag=True, help='Skip clustering processor')
@click.option('--skip-trending', is_flag=True, help='Skip trending processor')
def run_pipeline(threads, trending_window, trending_top, skip_ingestion, skip_normalization, 
                 skip_features, skip_clustering, skip_trending):
    """Run the complete processor pipeline."""
    
    orchestrator = ProcessorOrchestrator()
    
    def signal_handler(signum, frame):
        logger.info("\nShutdown signal received...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(
            orchestrator.run_all_processors(
                num_threads=threads,
                trending_window_hours=trending_window,
                trending_top_k=trending_top,
                skip_ingestion=skip_ingestion,
                skip_normalization=skip_normalization,
                skip_features=skip_features,
                skip_clustering=skip_clustering,
                skip_trending=skip_trending,
            )
        )
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user")


@cli.command()
@click.option('--csv', help='CSV file to load')
@click.option('--dir', help='Directory with CSV/JSONL files')
@click.option('--pattern', default='*.csv', help='File pattern for directory mode')
def backfill(csv, dir, pattern):
    """Load historical data from files or directory."""
    
    if csv:
        logger.info(f"Loading CSV: {csv}")
        stats = asyncio.run(backfill_historical(csv_path=csv))
    elif dir:
        logger.info(f"Loading from directory: {dir}")
        stats = asyncio.run(backfill_historical(directory=dir, pattern=pattern))
    else:
        logger.error("Must provide --csv or --dir")
        return
    
    logger.info(f"\nBackfill complete:")
    logger.info(f"  Records loaded: {stats['records_loaded']}")
    logger.info(f"  Published: {stats['records_published']}")
    logger.info(f"  Failed: {stats['records_failed']}")
    logger.info(f"  Success rate: {stats['success_rate']:.1f}%")


@cli.command()
@click.option('--processor', required=True, 
              type=click.Choice(['ingestion', 'normalization', 'features', 'clustering', 'trending']),
              help='Processor to run')
@click.option('--threads', default=3, help='Processing threads')
@click.option('--trending-window', default=1, type=int, help='Trending window (for trending processor)')
@click.option('--trending-top', default=5, type=int, help='Top-K items (for trending processor)')
def run_single(processor, threads, trending_window, trending_top):
    """Run a single processor."""
    
    logger.info(f"Starting {processor} processor with {threads} threads...")
    
    try:
        if processor == 'ingestion':
            asyncio.run(run_ingestion_processor(num_threads=threads))
        elif processor == 'normalization':
            asyncio.run(run_normalization_processor(num_threads=threads))
        elif processor == 'features':
            asyncio.run(run_features_processor(num_threads=threads))
        elif processor == 'clustering':
            asyncio.run(run_clustering_processor(num_threads=threads))
        elif processor == 'trending':
            from backend.processors.processor_trending import run_trending_processor
            asyncio.run(run_trending_processor(
                window_hours=trending_window,
                top_k=trending_top,
                num_threads=threads
            ))
    except KeyboardInterrupt:
        logger.info(f"{processor} processor stopped")


if __name__ == '__main__':
    cli()
