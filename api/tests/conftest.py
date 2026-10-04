import os
import tempfile

# Tests run against a throwaway SQLite file and key file, never the dev database or keys.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GLOSA_KEY_FILE"] = f"{_tmp}/secret.key"
os.environ.pop("GLOSA_SECRET_KEY", None)
