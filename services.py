import re
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from nltk.sentiment import SentimentIntensityAnalyzer

import models
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()


but_words = [" but ", " however ", " although ", " though "]


# =========================
# PREPROCESS TEXT
# =========================

def preprocess_text(text: str) -> str:
    text = str(text).lower().strip()
    for bw in but_words:
        if bw in text:
            text = text.split(bw)[-1]
            break
    return text


# =========================
# HYBRID PROBABILITY
# =========================

def hybrid_probability(text: str, vectorizer, log_model, svm_model) -> float:
    processed = preprocess_text(text)
    vec = vectorizer.transform([processed])

    log_prob = log_model.predict_proba(vec)[0][1]
    svm_pred = svm_model.predict(vec)[0]

    final_prob = (log_prob * 0.7) + (svm_pred * 0.3)
    return float(max(0, min(1, final_prob)))


# =========================
# REVIEW SELECTOR
# =========================

def hybrid_review_selector(reviews: list, vectorizer, log_model, svm_model):
    negation_words = ["no", "not", "never", "without"]
    negative_terms = ["issue", "issues", "problem", "problems", "complaint", "complaints"]

    filtered = [r for r in reviews if 8 <= len(str(r).split()) <= 80]
    if len(filtered) < 6:
        filtered = reviews

    unique_reviews = list(dict.fromkeys(filtered))
    scored = []

    for review in unique_reviews:
        prob = hybrid_probability(review, vectorizer, log_model, svm_model)
        words = review.lower().split()

        for i, word in enumerate(words):
            if word in negation_words:
                window = words[i:i + 4]
                if any(term in window for term in negative_terms):
                    prob *= 0.2
                    break

        prob = max(0, min(1, prob))
        scored.append((review, prob))

    negatives_sorted = sorted(scored, key=lambda x: x[1], reverse=True)
    positives_sorted = sorted(scored, key=lambda x: x[1])

    negatives, positives = [], []

    for review, score in negatives_sorted:
        sentiment = sia.polarity_scores(review)["compound"]
        if score >= 0.6 and sentiment < 0.2 and len(negatives) < 3:
            negatives.append(review)
        if len(negatives) == 3:
            break

    for review, score in positives_sorted:
        sentiment = sia.polarity_scores(review)["compound"]
        if score <= 0.4 and sentiment > 0 and review not in negatives and len(positives) < 3:
            positives.append(review)
        if len(positives) == 3:
            break

    return negatives, positives


# =========================
# ASIN EXTRACTION
# =========================

def extract_asin(input_text: str):
    if not input_text:
        return None

    text = input_text.strip()

    asin_match = re.search(r"\b([A-Z0-9]{10})\b", text)
    if asin_match:
        return asin_match.group(1).upper()

    dp_match = re.search(r"/dp/([A-Z0-9]{10})", text)
    if dp_match:
        return dp_match.group(1).upper()

    gp_match = re.search(r"/gp/product/([A-Z0-9]{10})", text)
    if gp_match:
        return gp_match.group(1).upper()

    try:
        if "amzn." in text:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(text, headers=headers, allow_redirects=True, timeout=7)
            final_url = response.url

            dp_match = re.search(r"/dp/([A-Z0-9]{10})", final_url)
            if dp_match:
                return dp_match.group(1).upper()

            gp_match = re.search(r"/gp/product/([A-Z0-9]{10})", final_url)
            if gp_match:
                return gp_match.group(1).upper()
    except Exception:
        pass

    return None


# =========================
# ANALYZE REVIEWS
# =========================

def analyze_reviews(reviews: list, vectorizer, log_model, svm_model):
    probs = np.array([
        hybrid_probability(r, vectorizer, log_model, svm_model)
        for r in reviews
    ])

    regret_percent = float(round(probs.mean() * 100, 2))

    if regret_percent < 30:
        recommendation = "Proceed with Purchase"
        risk_level = "Low"
        color = "green"
    elif regret_percent < 60:
        recommendation = "Consider Carefully"
        risk_level = "Medium"
        color = "orange"
    else:
        recommendation = "We Suggest Reconsidering"
        risk_level = "High"
        color = "red"

    purchase_confidence = round(100 - regret_percent, 2)

    return regret_percent, recommendation, risk_level, color, purchase_confidence, probs


# =========================
# SAVE ANALYSIS TO DB
# =========================

def save_analysis_to_db(
    db: Session,
    asin: str,
    product_name: str,
    main_image,
    regret: float,
    rec: str,
    reviews_count: int
):
    # Upsert Product
    existing_product = db.query(models.Product).filter(
        models.Product.asin == asin
    ).first()

    if not existing_product:
        db.add(models.Product(
            asin=asin,
            product_name=product_name,
            regret_percentage=regret,
            reviews_count=reviews_count
        ))
    else:
        existing_product.regret_percentage = regret
        existing_product.reviews_count = reviews_count

    # Upsert AnalysisHistory
    existing_history = db.query(models.AnalysisHistory).filter(
        models.AnalysisHistory.asin == asin
    ).all()

    if len(existing_history) == 0:
        db.add(models.AnalysisHistory(
            asin=asin,
            product_name=product_name,
            product_image=main_image,
            regret_percentage=regret,
            recommendation=rec,
            analyzed_at=datetime.utcnow()
        ))
    else:
        record = existing_history[0]
        record.regret_percentage = regret
        record.recommendation = rec
        record.product_image = main_image
        record.analyzed_at = datetime.utcnow()

        for extra in existing_history[1:]:
            db.delete(extra)

    db.commit()


# =========================
# GET HISTORY FROM DB
# =========================

def get_history_records(db: Session):
    return db.query(models.AnalysisHistory).order_by(
        models.AnalysisHistory.analyzed_at.desc()
    ).all()
