from fastapi import Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.services.usage_service import UsageService

def get_usage_service(db: Session = Depends(get_db)):
    return UsageService(db)

