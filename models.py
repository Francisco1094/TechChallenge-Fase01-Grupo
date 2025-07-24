from sqlalchemy import Column, Integer, String, Float
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String, index=True)
    price= Column(Float)
    rating= Column(String, index=True)
    availability= Column(String, index=True)
    image_url= Column(String, index=True)