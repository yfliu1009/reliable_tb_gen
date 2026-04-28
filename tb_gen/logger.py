import logging
from pathlib import Path


def setup_output_log_dir(log_id: str = None, output_dir: str = "./result") -> str:
    # unique log id
    if not log_id:
        from datetime import datetime

        log_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    # create ./result/ exists
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # create ./result/[log_dir]
    log_dir = base_dir / log_id
    log_dir.mkdir()

    # setup logger
    logger = logging.getLogger("main")
    logger.setLevel(logging.INFO)
    log_file = log_dir / "output.log"
    file_handler = logging.FileHandler(str(log_file))
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return str(log_dir)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("main")

    return logger
