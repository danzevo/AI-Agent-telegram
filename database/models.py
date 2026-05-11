from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class UserFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int= Field(index=True)
    fact: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(index=True)
    file_name: str
    local_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
