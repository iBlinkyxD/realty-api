from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    resend_api_key: str = ""
    email_from: str = "noreply@ilovedrrealty.com"
    landing_url: str = "http://localhost:3000"
    logo_url: str = ""  # override with CDN URL; falls back to landing_url/iLoveDRRealty_Dark.png
    allowed_origins: str = "http://localhost:3000,http://localhost:5174"
    environment: str = "development"
    cookie_domain: str = ""  # set to ".ilovedrrealty.com" in production
    port: int = 8000
    supabase_url: str = ""
    supabase_service_key: str = ""
    storage_bucket: str = "listing-images"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
