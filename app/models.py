from sqlalchemy import Column, DateTime, Integer, String, func

from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan = Column(String, nullable=False, default="free")
    ai_calls_used = Column(Integer, nullable=False, default=0)
    ai_call_limit = Column(Integer, nullable=False, default=50)
    created_at = Column(DateTime, server_default=func.now())