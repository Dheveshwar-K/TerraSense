import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from project root or backend directory if present (never override explicit env vars)
for env_candidate in (BASE_DIR.parent / ".env", BASE_DIR / ".env"):
    if env_candidate.exists():
        load_dotenv(dotenv_path=env_candidate, override=False)

INSECURE_SECRET_PLACEHOLDERS = {
    "",
    "FOUNDRY-QUALITY-4.0-PS010-SUPER-SECURE-KEY-2026",
    "REPLACE_WITH_64_CHAR_RANDOM_HEX_SECRET",
    "changeme",
    "secret",
    "dev-secret",
    "test-secret",
}

INSECURE_DB_PASSWORDS = {
    "foundry_pass",
    "REPLACE_WITH_STRONG_DB_PASSWORD",
    "postgres",
    "password",
    "admin",
}


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _parse_origins(raw: str | None) -> list[str]:
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    origins = [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
    return origins or ["http://localhost:5173"]


# Process-local fallback secret for non-production environments when SECRET_KEY is unset
_EPHEMERAL_DEV_SECRET = secrets.token_urlsafe(48)


class Settings:
    PROJECT_NAME: str = os.getenv(
        "PROJECT_NAME",
        "PS-010: Digital Sand Quality Management & Rejection Analytics",
    )
    VERSION: str = os.getenv("VERSION", "1.1.0")
    API_V1_STR: str = "/api"

    @property
    def ENVIRONMENT(self) -> str:
        env = os.getenv("ENVIRONMENT", "development").strip().lower()
        if env not in {"development", "demo", "testing", "production"}:
            return "development"
        return env

    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'foundry_quality.db'}")

    @property
    def SECRET_KEY(self) -> str:
        raw = os.getenv("SECRET_KEY", "").strip()
        if not raw:
            if self.ENVIRONMENT == "production":
                return ""
            return _EPHEMERAL_DEV_SECRET
        return raw

    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    @property
    def REFRESH_TOKEN_EXPIRE_MINUTES(self) -> int:
        return int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return _parse_origins(os.getenv("ALLOWED_ORIGINS"))

    @property
    def DEMO_MODE(self) -> bool:
        env = self.ENVIRONMENT
        if env == "production":
            return _parse_bool(os.getenv("DEMO_MODE"), default=False)
        if env in ("demo", "development"):
            return _parse_bool(os.getenv("DEMO_MODE"), default=True)
        return _parse_bool(os.getenv("DEMO_MODE"), default=False)

    @property
    def MAX_REQUEST_BYTES(self) -> int:
        return int(os.getenv("MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))

    @property
    def LOGIN_RATE_LIMIT_MAX_ATTEMPTS(self) -> int:
        return int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "10"))

    @property
    def LOGIN_RATE_LIMIT_WINDOW_SECONDS(self) -> int:
        return int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))

    def is_demo_enabled(self) -> bool:
        return self.ENVIRONMENT != "production" and self.DEMO_MODE

    def validate_runtime_settings(self) -> None:
        """
        Enforces strict security invariants at startup.
        Production refuses insecure secrets, SQLite, placeholder DB credentials, or DEMO_MODE=true.
        """
        env = self.ENVIRONMENT
        secret = self.SECRET_KEY

        if env == "production":
            if secret in INSECURE_SECRET_PLACEHOLDERS or len(secret) < 32:
                raise RuntimeError(
                    "SECURITY BLOCK: Production requires a strong SECRET_KEY (>= 32 chars) and rejects placeholder secrets."
                )
            if self.DEMO_MODE:
                raise RuntimeError(
                    "SECURITY BLOCK: DEMO_MODE=true is strictly forbidden when ENVIRONMENT=production."
                )
            db_url = self.DATABASE_URL
            if db_url.startswith("sqlite"):
                raise RuntimeError(
                    "CONFIGURATION BLOCK: Production requires PostgreSQL; SQLite is not permitted in ENVIRONMENT=production."
                )
            for bad_pw in INSECURE_DB_PASSWORDS:
                if f":{bad_pw}@" in db_url:
                    raise RuntimeError(
                        "SECURITY BLOCK: Production DATABASE_URL contains a known placeholder database password."
                    )
            if "*" in self.ALLOWED_ORIGINS:
                raise RuntimeError(
                    "SECURITY BLOCK: Wildcard CORS origin is not allowed in production."
                )
        else:
            # Even in non-production, reject known leaked placeholder in SECRET_KEY if explicitly set in env
            explicit_secret = os.getenv("SECRET_KEY", "").strip()
            if explicit_secret and explicit_secret in INSECURE_SECRET_PLACEHOLDERS:
                raise RuntimeError(
                    "SECURITY BLOCK: Known placeholder SECRET_KEY configured. Provide a unique secret or unset it for ephemeral dev key."
                )


settings = Settings()
