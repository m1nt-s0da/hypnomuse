from dotenv import load_dotenv
from logging import basicConfig, WARNING
import os

load_dotenv()
basicConfig(
    level=os.environ.get("LOG_LEVEL", WARNING),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


del load_dotenv, basicConfig, WARNING, os

from .scan import *
