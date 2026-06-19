# conftest.py — adds the project root to sys.path so pytest can import tools, agent, etc.
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
