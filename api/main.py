import time
from fastapi import FastAPI, Depends, HTTPException, Query, Path, status, Body, Response
from fastapi.security import OAuth2PasswordRequestForm
from .auth import create_access_token, create_refresh_token, get_current_user
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any
from threading import Thread
from sqlalchemy import func
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta

from scripts.scrapping import save_to_csv, scrape_all_books_with_progress

from database.database import Base, engine
from models.models import Book as BookModel
from database.dependencies import get_db
from .users import users
from scripts.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM

from monitoring import (
    RequestMonitoringMiddleware,
    BusinessEventTracker,
    structured_logger,
    metrics,
    exporter,
)


import csv
import random
import pickle
import numpy as np

scraping_status = {
    "is_running": False,
    "current_page": 0,
    "books_found": 0,
    "start_time": None,
    "estimated_completion": None
}


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Webscraping Project",
    version="1.0.0",
    description="Projeto do Tech Challenge...",
)

books_result = []


class BookSchema(BaseModel):
    id: int
    title: str
    price: float
    rating: str
    availability: str
    category: str
    image_url: str
    target: int

    @field_validator("price")
    def format_price(cls, v):
        return round(v, 2)

    model_config = {"from_attributes": True}


rating_order = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

app.add_middleware(RequestMonitoringMiddleware)


@app.post("/api/v1/auth/login", tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    user = users.get(form_data.username)
    if not user or user != form_data.password:
        BusinessEventTracker.track_user_login(False, username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(data={"sub": username})

    BusinessEventTracker.track_user_login(True, username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/api/v1/auth/refresh", tags=["Authentication"])
async def refresh_token(refresh_token: str = Body(...)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return {"access_token": new_access_token, "token_type": "bearer"}


# ----------------------------------------------------------
# ---------------------- Scrape Books ----------------------
# ----------------------------------------------------------
@app.get("/api/v1/scrape", tags=["Completed"])
def scrape_books(
    db: Session = Depends(get_db), username: str = Depends(get_current_user)
):
    global scraping_status

    if scraping_status["is_running"]:
        return {"message": "Scraping already in progress", "status": scraping_status}
    
    def task():
        global scraping_status
        try:
            scraping_status = {
                "is_running": True,
                "current_page": 0,
                "books_found": 0,
                "start_time": time.time(),
                "total_pages": 50,
                "status_message": "Scraping in progress..."
            }
            
            # books = scrape_all_books()
            books = scrape_all_books_with_progress(update_status_callback)
            save_to_csv(books, "books.csv")

            # Clear table before inserting new records (optional)
            db.query(BookModel).delete()
            db.commit()

            scraping_status["status_message"] = "Saving to DB..."

            # Save to DB
            for i, book in enumerate(books):
                cleaned_price = "".join(
                    c for c in book["price"] if c.isdigit() or c == "."
                )
                rating_num = rating_order.get(book["rating"], 0)
                target = 1 if rating_num >= 4 and float(cleaned_price) < 40 else 0
                db_book = BookModel(
                    title=book["title"],
                    price=cleaned_price,
                    rating=book["rating"],
                    availability=book["availability"],
                    category=book["category"],
                    image_url=book["image_url"],
                    target=target,
                )
                db.add(db_book)
                if (i + 1) % 50 == 0:
                    scraping_status["status_message"] = f"Saving... {i+1}/{len(books)} books"
                    
            db.commit()

            print(f"Scraped and inserted {len(books)} books")

            scraping_status.update({
                "is_running": False,
                "last_completion": datetime.utcnow().isoformat(),
                "final_count": len(books),
                "status_message": "Successfully completed!",
                "duration_seconds": time.time() - scraping_status["start_time"]
            })
            
            BusinessEventTracker.track_book_scraping(len(books))

        except Exception as e:
            scraping_status.update({
                "is_running": False,
                "status_message": f"Erro: {str(e)}",
                "error": True
            })
            structured_logger.log_error(
                error=e, context={"operation": "book_scraping", "user": username}
            )

    Thread(target=task).start()
    return {"message": "Scraping started", "status": scraping_status}

def update_status_callback(page_number: int, page_books: int, total_books_so_far: int):
    """Callback chamado pelo scraping para atualizar status"""
    global scraping_status
    
    scraping_status.update({
        "current_page": page_number,
        "books_found": total_books_so_far,
        "status_message": f"Processing page {page_number}... ({total_books_so_far} books found)"
    })


# -------------------------------------------------------------------
# ---------------------- Lista todos os livros ----------------------
# -------------------------------------------------------------------
@app.get("/api/v1/books", response_model=List[BookSchema], tags=["Completed"])
def lista_todos_os_livros_disponiveis(db: Session = Depends(get_db)):
    start_time = time.time()
    
    books = db.query(BookModel).all()
    
    duration = time.time() - start_time
    structured_logger.log_database_query(
        query="SELECT * FROM books",
        duration=duration,
        table="books", 
        operation="SELECT",
        result_count=len(books)
    )
    return books


# ----------------------------------------------------------------------------
# ---------------------- Livros por titulo ou categoria ----------------------
# ----------------------------------------------------------------------------
@app.get("/api/v1/books/search", response_model=List[BookSchema], tags=["Completed"])
def busca_livros_por_titulo_ou_categoria(
    db: Session = Depends(get_db),
    title: str = Query(None, description="Title to search"),
    category: str = Query(None, description="Category to filter"),
):
    query = db.query(BookModel)
    if title:
        query = query.filter(BookModel.title.ilike(f"%{title}%"))
    if category:
        query = query.filter(BookModel.category.ilike(f"%{category}%"))

    result = query.all()

    structured_logger.log_business_event(
        event_name="book_search_performed",
        context={
            "search_title": title,
            "search_category": category,
            "results_count": len(result),
        },
    )

    if not result:
        raise HTTPException(
            status_code=404, detail="No books found matching the criteria"
        )
    return result


@app.get(
    "/api/v1/books/price-range", response_model=List[BookSchema], tags=["Statistics"]
)
def filtra_livros_em_uma_faixa_de_precos(
    min_price: float = 0.0, max_price: float = 1000.0, db: Session = Depends(get_db)
):
    query = db.query(BookModel)
    range_price = query.filter(
        BookModel.price >= min_price, BookModel.price <= max_price
    ).all()
    return range_price


# ------------------------------------------------------------------------
# ---------------------- Lista livros por avaliação ----------------------
# ------------------------------------------------------------------------
@app.get(
    "/api/v1/books/sorted_by_rating",
    response_model=List[BookSchema],
    tags=["Statistics"],
)
def books_sorted_by_rating(db: Session = Depends(get_db)):
    books = db.query(BookModel).all()

    # Sort books based on the rating_order mapping
    sorted_books = sorted(
        books,
        key=lambda x: rating_order.get(x.rating, 0),  # Default to 0 if rating missing
        reverse=True,
    )

    return sorted_books


# ----------------------------------------------------------------------
# ---------------------- Pesquisa o livro pelo ID ----------------------
# ----------------------------------------------------------------------
@app.get("/api/v1/books/{id}", response_model=BookSchema, tags=["Completed"])
def retorna_livro_pelo_id(
    id: int = Path(..., description="Book ID"), db: Session = Depends(get_db)
):
    book = db.query(BookModel).filter(BookModel.id == id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not Found")
    return book


# ------------------------------------------------------------------------------------
# ---------------------- Lista categoria dos livros disponíveis ----------------------
# ------------------------------------------------------------------------------------
@app.get("/api/v1/category", response_model=List[str], tags=["Completed"])
def lista_todas_as_categorias_de_livros_disponiveis(db: Session = Depends(get_db)):
    categories = db.query(BookModel.category).distinct().all()
    return [category[0] for category in categories]


# ------------------------------------------------------------------------------------
# ---------------------- Checar conectividade da API ----------------------
# ------------------------------------------------------------------------------------
@app.get("/api/v1/health", tags=["Completed"])
def checar_conectividade_da_api():
    return {"goal": "Check API status and conectivity with data"}


# ----------------------------------------------------------------------------------------------------
# ---------------------- Total de livros, preço médio e distribuição de ratings ----------------------
# ----------------------------------------------------------------------------------------------------
@app.get("/api/v1/stats/overview", tags=["Statistics"])
def estatisticas_gerais_da_colecao(
    db: Session = Depends(get_db), username: str = Depends(get_current_user)
):
    total_books = db.query(BookModel.title).count()
    avg_price = db.query(func.avg(BookModel.price)).scalar() or 0.0
    avg_price = round(avg_price, 2)

    rating_distribution = (
        db.query(BookModel.rating, func.count(BookModel.id))
        .group_by(BookModel.rating)
        .all()
    )
    distribution = {rating: count for rating, count in rating_distribution}

    structured_logger.log_business_event(
        event_name="stats_overview_accessed",
        user_id=username,
        context={
            "total_books": total_books,
            "avg_price": avg_price,
            "categories_count": len(distribution),
            "most_common_rating": max(distribution, key=distribution.get)
            if distribution
            else None,
        },
    )

    return {
        "Total of Books": total_books,
        "Average Price": avg_price,
        "Rating Distribution": distribution,
    }


# ----------------------------------------------------------------------------------------
# ---------------------- Quantidade de livros e preço por categoria ----------------------
# ----------------------------------------------------------------------------------------
@app.get("/api/v1/stats/categories", tags=["Statistics"])
def estatisticas_detalhadas_por_categoria(db: Session = Depends(get_db)):
    quantity = (
        db.query(BookModel.category, func.count(BookModel.id))
        .group_by(BookModel.category)
        .all()
    )
    quantity_category = {category: count for category, count in quantity}

    price = (
        db.query(BookModel.category, func.avg(BookModel.price))
        .group_by(BookModel.category)
        .all()
    )
    price_category = {category: round(avg_price, 2) for category, avg_price in price}
    return {
        "Quantity by Category": quantity_category,
        "Price by Category": price_category,
    }


#  {
#     "title": "A Light in the Attic",
#     "price": "Â£51.77",
#     "rating": "Three",
#     "availability": "In stock",
#     "category": "Poetry",
#     "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg"
#   },
#  {
#     "title": "Tipping the Velvet",
#     "price": "Â£53.74",
#     "rating": "One",
#     "availability": "In stock",
#     "category": "Historical Fiction",
#     "image_url": "https://books.toscrape.com/media/cache/26/0c/260c6ae16bce31c8f8c95daddd9f4a1c.jpg"
#   }

# ==============================================================================================
# ==============================  Not developed yet  ===========================================
# ==============================================================================================


# @app.get("/api/v1/books/price-range", tags=["Not developed yet"])
# def list_by_category_book():
#     return {"goal": "Filter book into a band specific price"}

# @app.post("api/v1/auth/login", tags=["Not developed yet"])
# def token():
#     return {"goal":"Obter token - JWT Authentication"}

# @app.post("api/v1/auth/refresh", tags=["Not developed yet"])
# def token():
#     return {"goal":"Renew token - JWWT Authentication"}

# ----------------------------------------------------------------------------------------
# ------------------------ Dados formatados para features --------------------------------
# ----------------------------------------------------------------------------------------
@app.get("/api/v1/ml/features", tags=["ML"])
def get_ml_features(db: Session = Depends(get_db)):
    books = db.query(BookModel).all()
    features = []
    for book in books:
        features.append(
            {
                "price": book.price,
                "rating": rating_order.get(book.rating, 0),
                "category": book.category,
                "availability": 1 if "In stock" in book.availability else 0,
                "target": book.target,
            }
        )
    # Gera arquivo CSV
    with open("ml_features.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["price", "rating", "category", "availability", "target"]
        )
        writer.writeheader()
        writer.writerows(features)
    return features


# ----------------------------------------------------------------------------------------
# ------------------------ Dataset para treinamento --------------------------------------
# ----------------------------------------------------------------------------------------
@app.get("/api/v1/ml/training-data", tags=["ML"])
def get_training_data(db: Session = Depends(get_db)):
    books = db.query(BookModel).all()
    data = []
    for book in books:
        data.append(
            {
                "price": book.price,
                "rating": rating_order.get(book.rating, 0),
                "category": book.category,
                "availability": 1 if "In stock" in book.availability else 0,
                "target": book.target,
            }
        )
    # Embaralha e divide em 70% para treinamento
    random.shuffle(data)
    split_idx = int(len(data) * 0.7)
    train_data = data[:split_idx]
    # Gera arquivo CSV
    with open("ml_training_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["price", "rating", "category", "availability", "target"]
        )
        writer.writeheader()
        writer.writerows(train_data)
    return train_data


# ----------------------------------------------------------------------------------------
# ------------------------ Endpoint para receber predições -------------------------------
# ----------------------------------------------------------------------------------------
class MLFeatures(BaseModel):
    price: float
    rating: int
    category: str
    availability: int


@app.post("/api/v1/ml/predictions", tags=["ML"])
def ml_predictions(features: MLFeatures, current_user: str = Depends(get_current_user)):
    try:
        # Carrega o modelo treinado
        with open("book_recommendation_model.pkl", "rb") as f:
            model = pickle.load(f)
        # Carrega o encoder de categoria
        with open("category_encoder.pkl", "rb") as f:
            category_encoder = pickle.load(f)
        # Transforma a categoria
        category_encoded = int(category_encoder.transform([features.category])[0])
        # Prepara os dados para o modelo
        input_data = np.array(
            [[features.price, features.rating, category_encoded, features.availability]]
        )
        # Predição
        pred = model.predict(input_data)
        recomendado = bool(pred[0]) if hasattr(pred[0], "__bool__") else pred[0] == 1
        BusinessEventTracker.track_ml_prediction(
            recommended=recomendado, user_id=current_user
        )
        return {"recomendado": recomendado}
    except Exception as e:
        structured_logger.log_error(
            error=e,
            context={
                "operation": "ml_prediction",
                "user": current_user,
                "features": features.dict(),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error making ML prediction",
        )


# ----------------------------------------------------------------------------------------
# ------------------------ Endpoint para Monitoramento -----------------------------------
# ----------------------------------------------------------------------------------------
@app.get("/api/v1/monitoring/metrics", tags=["Monitoring"])
def get_metrics():
    """Endpoint para métricas do Prometheus"""
    return Response(content=metrics.get_metrics(), media_type="text/plain")


# ----------------------------------------------------------------------------------------
# ------------------------ Endpoint para consumo na dashboard ----------------------------
# ----------------------------------------------------------------------------------------
@app.get("/api/v1/monitoring/dashboard", tags=["Monitoring"])
def get_dashboard_data():
    """Dados para dashboard de monitoramento"""
    return {
        "current_metrics": exporter.export_current_metrics(),
        "historical_data": exporter.export_historical_data(hours=24),
    }
