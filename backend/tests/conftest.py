"""Keep all test databases inside a chosen scratch directory.

Explicit directory permissions avoid restricted Windows sandbox temp ACLs.
"""
import os
from pathlib import Path
import shutil
from uuid import uuid4
import pytest

@pytest.fixture
def tmp_path():
    root=Path(os.getenv('STUDY_TEST_ROOT',str(Path(__file__).parent/'_scratch'))).resolve()
    root.mkdir(parents=True,exist_ok=True)
    target=root/str(uuid4())
    target.mkdir(mode=0o755)
    try:
        yield target
    finally:
        if target.resolve().parent!=root:
            raise RuntimeError('Refusing to clean up outside test scratch directory')
        shutil.rmtree(target)
