from sqlmodel import Session, select
from database.db import engine
from database.models import UserFact, UserDocument

class SQLRepository:
    def save_fact(self, chat_id: int, fact: str):
        with Session(engine) as session:
            new_fact = UserFact(chat_id=chat_id, fact=fact)

            session.add(new_fact)
            session.commit()

    def get_facts(self, chat_id: int) -> list[str]:
        with Session(engine) as session:
            statement = select(UserFact).where(UserFact.chat_id == chat_id)
            result = session.exec(statement).all()

            return [f.fact for f in result]

    def save_document(self, chat_id: int, file_name: str, local_path: str):
        with Session(engine) as session:
            doc = UserDocument(chat_id=chat_id, file_name=file_name, local_path=local_path)
            session.add(doc)
            session.commit()

    def get_documents(self, chat_id: int) -> list[UserDocument]:
        with Session(engine) as session:
            statement = select(UserDocument).where(UserDocument.chat_id == chat_id)

            return session.exec(statement).all()

    def get_document_by_name(self, chat_id: int, file_name: str) -> UserDocument | None:
        with Session(engine) as session:
            statement = select(UserDocument).where(
                UserDocument.chat_id == chat_id,
                UserDocument.file_name == file_name
            )

            return session.exec(statement).first()

