import json
import os

class ConfigManager:
    def __init__(self):
        # Look for secrets.json in the root directory (parent of 'src')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.secrets_file = os.path.join(base_dir, "secrets.json")
        self.secrets = {}
        self.load_secrets()

    def load_secrets(self):
        if os.path.exists(self.secrets_file):
            try:
                with open(self.secrets_file, 'r') as f:
                    self.secrets = json.load(f)
            except Exception as e:
                print(f"Error loading secrets: {e}")
                self.secrets = {}
        else:
            print(f"Secrets file {self.secrets_file} not found.")

    def get_api_key(self, name):
        return self.secrets.get("api_keys", {}).get(name)

# Global instance
config = ConfigManager()
