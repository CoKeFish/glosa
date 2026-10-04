import os
import tempfile

# Tests run against a throwaway SQLite file, never the dev database.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
