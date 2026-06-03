from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
import pandas as pd
import joblib
import nltk
import numpy as np
from sqlalchemy.orm import Session

from database import engine, get_db
import models
import services
import schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

models.Base.metadata.create_all(bind=engine)

nltk.download("punkt", quiet=True)
nltk.download("vader_lexicon", quiet=True)

# =========================
# LOAD MODELS & DATA
# =========================

vectorizer = joblib.load("tfidf_vectorizer_v9.pkl")
log_model  = joblib.load("regret_logistic_v9.pkl")
svm_model  = joblib.load("regret_svm_v9.pkl")

df          = pd.read_csv("dataset.csv").drop_duplicates()
products_df = pd.read_csv("products.csv").drop_duplicates()


# =========================
# ROUTES
# =========================

@app.get("/analyze")
def analyze(url: str, db: Session = Depends(get_db)):

    if not url or len(url.strip()) < 10:
        return {"error": "Please enter a valid Amazon product link."}

    asin = services.extract_asin(url)
    if not asin:
        return {"error": "Invalid product link or ASIN"}

    product = df[df["asin"] == asin]

    # Product not in dataset — log the request
    if product.empty:
        existing_request = db.query(models.RequestedProduct).filter(
            models.RequestedProduct.asin == asin
        ).first()

        if existing_request:
            existing_request.request_count += 1
        else:
            db.add(models.RequestedProduct(asin=asin))

        db.commit()

        return schemas.PendingResponse(
            status="pending",
            asin=asin,
            message="Product not in dataset yet."
        )

    reviews = product["clean_review"].dropna().astype(str).tolist()
    if not reviews:
        return {"error": "No reviews available"}

    # Run analysis
    regret, rec, risk_level, color, purchase_confidence, probs = services.analyze_reviews(
        reviews, vectorizer, log_model, svm_model
    )

    total = len(probs)
    distribution = {
        "low":    round(float(np.sum(probs < 0.3))                       / total * 100, 2),
        "medium": round(float(np.sum((probs >= 0.3) & (probs < 0.6)))    / total * 100, 2),
        "high":   round(float(np.sum(probs >= 0.6))                      / total * 100, 2),
    }
    variance = float(round(np.var(probs), 4))

    product_name = str(product["product_title"].iloc[0])

    product_info = products_df[products_df["asin"] == asin]
    if not product_info.empty:
        main_image        = str(product_info["main_image"].iloc[0])
        rating            = float(product_info["rating"].iloc[0])            if pd.notna(product_info["rating"].iloc[0])            else None
        number_of_ratings = int(product_info["number_of_ratings"].iloc[0])   if pd.notna(product_info["number_of_ratings"].iloc[0])   else None
    else:
        main_image        = None
        rating            = None
        number_of_ratings = None

    negative_reviews, positive_reviews = services.hybrid_review_selector(
        reviews, vectorizer, log_model, svm_model
    )

    # Persist to DB
    services.save_analysis_to_db(
        db, asin, product_name, main_image, regret, rec, len(reviews)
    )

    return {
        "product": {
            "asin":              asin,
            "name":              product_name,
            "image":             main_image,
            "rating":            rating,
            "number_of_ratings": number_of_ratings,
        },
        "regret": {
            "score":      regret,
            "risk_level": risk_level,
            "color":      color,
        },
        "decision_intelligence": {
            "purchase_confidence": purchase_confidence,
        },
        "advanced_insights": {
            "distribution": distribution,
            "variance":     variance,
        },
        "recommendation": rec,
        "evidence": {
            "top_negative": negative_reviews,
            "top_positive": positive_reviews,
        },
    }


@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    records = services.get_history_records(db)
    return [
        {
            "asin":               r.asin,
            "product_name":       r.product_name,
            "product_image":      r.product_image,
            "regret_percentage":  r.regret_percentage,
            "recommendation":     r.recommendation,
            "analyzed_at":        r.analyzed_at,
        }
        for r in records
    ]
@app.delete("/history/clear")
def clear_history(db: Session = Depends(get_db)):

    db.query(models.AnalysisHistory).delete()
    db.commit()

    return {"message": "History cleared successfully"}

@app.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()

    if not products:
        return {
            "total_products":    0,
            "average_regret":    0.0,
            "high_risk_products": 0
        }

    total     = len(products)
    avg       = round(sum(p.regret_percentage for p in products) / total, 2)
    high_risk = sum(1 for p in products if p.regret_percentage >= 60)

    return {
        "total_products":    total,
        "average_regret":    avg,
        "high_risk_products": high_risk
    }
