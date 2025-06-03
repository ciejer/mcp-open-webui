import os
from dotenv import load_dotenv

# Always reload from .env file, overriding existing environment variables
load_dotenv(override=True)

# Print environment variables for debugging
print("Config: Loaded environment variables:")
for key in ["OPENWEBUI_URL", "OPENWEBUI_API_KEY", "AGENT_WHITELIST", "AGENT_BLACKLIST", "LOG_LEVEL"]:
    print(f"  {key}={os.getenv(key, 'Not set')}")

class Settings:
    OPENWEBUI_URL: str = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
    OPENWEBUI_API_KEY: str = os.getenv("OPENWEBUI_API_KEY", "")
    
    # Better handling of whitelist/blacklist
    _whitelist = os.getenv("AGENT_WHITELIST", "")
    AGENT_WHITELIST: list[str] | None = _whitelist.split(',') if _whitelist and _whitelist.strip() else None
    
    _blacklist = os.getenv("AGENT_BLACKLIST", "")
    AGENT_BLACKLIST: list[str] | None = _blacklist.split(',') if _blacklist and _blacklist.strip() else None
    
    CACHE_DURATION_SECONDS: int = int(os.getenv("CACHE_DURATION_SECONDS", "600"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    def validate(self):
        """Validate required settings and log warnings."""
        if not self.OPENWEBUI_API_KEY:
            print("WARNING: OPENWEBUI_API_KEY is not set. API calls will likely fail.")
        
        # Print actual values being used
        print(f"Using OPENWEBUI_URL: {self.OPENWEBUI_URL}")
        print(f"Using AGENT_WHITELIST: {self.AGENT_WHITELIST}")
        print(f"Using AGENT_BLACKLIST: {self.AGENT_BLACKLIST}")
        print(f"Using LOG_LEVEL: {self.LOG_LEVEL}")

settings = Settings()
settings.validate()