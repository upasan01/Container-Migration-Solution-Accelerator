import logging
import sys

def setup_logging(
    debug: bool = False
) -> None:
    """
    Configure logging for RAI testing framework
    
    Args:
        debug: Enable debug logging if True, otherwise use WARNING level
    """
    
    level = logging.DEBUG if debug else logging.INFO
    format_string = '%(levelname)s: %(message)s'
        
    # Configure basic logging
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True  # Override any existing configuration
    )
    
    logging.getLogger('azure').setLevel(logging.ERROR)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
    logging.getLogger('azure.storage').setLevel(logging.ERROR)
    logging.getLogger('azure.cosmos').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)
    logging.getLogger('sas.cosmosdb.sql.repository').setLevel(logging.WARNING)
    logging.getLogger('rich').setLevel(logging.WARNING)


