from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class Settings:
    mode: str = 'production'
    data_dir: Path = field(default_factory=lambda: ROOT / 'data' / 'production')
    cors_origins: tuple = ('http://localhost:3000', 'http://127.0.0.1:3000')
    max_upload_mb: int = 20
    session_hours: int = 24
    ai_provider: str = ''
    file_provider: str = ''
    learning_provider: str = ''

    def __post_init__(self):
        self.data_dir = Path(self.data_dir).resolve()
        if self.mode not in ('production', 'demo'):
            raise ValueError('APP_MODE must be production or demo')
        if not 1 <= self.max_upload_mb <= 100 or not 1 <= self.session_hours <= 168:
            raise ValueError('Invalid upload/session limits')

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / '.env')
        mode = os.getenv('APP_MODE', 'production')
        raw_dir = Path(os.getenv('DATA_DIR', str(ROOT / 'data' / mode)))
        if not raw_dir.is_absolute():
            raw_dir = ROOT / raw_dir
        return cls(mode=mode, data_dir=raw_dir,
                   cors_origins=tuple(x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if x.strip()),
                   max_upload_mb=int(os.getenv('MAX_UPLOAD_MB', '20')),
                   session_hours=int(os.getenv('SESSION_HOURS', '24')),
                   ai_provider=os.getenv('AI_PROVIDER', ''),
                   file_provider=os.getenv('FILE_PROVIDER', ''),
                   learning_provider=os.getenv('LEARNING_PROVIDER', ''))
