import os
import sys

# Must be set before app.db.mongo is imported anywhere.
os.environ["MONGO_URI"] = "memory"
os.environ["MONGO_DB"] = "solsight_test"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
