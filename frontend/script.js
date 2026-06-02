// ===============================
// ANALYZE FROM HOME PAGE
// ===============================

async function analyzeProduct() {

    const input = document.getElementById("productInput").value;

    if (!input) {
        alert("Paste Amazon link or ASIN first");
        return;
    }

    try {

        const response = await fetch(`/analyze?url=${encodeURIComponent(input)}`);
        const data = await response.json();

        // Cold start
        if (data.status === "pending") {
            alert("This product is not in dataset yet. It will be analyzed soon.");
            return;
        }

        // Error
        if (data.error) {
            alert(data.error);
            return;
        }

        // Save result
        localStorage.setItem("analysisResult", JSON.stringify(data));

        // Redirect to result page
        window.location.href = "/app/result.html";

    } catch (err) {
        console.log(err);
        alert("Backend not running or server error.");
    }
}



// ===============================
// LOAD RESULT PAGE
// ===============================

function loadResultPage() {

    const result = JSON.parse(localStorage.getItem("analysisResult"));

    if (!result) {
        window.location.href = "/app/home.html";
        return;
    }

    // PRODUCT INFO
    document.getElementById("productName").innerText = result.product.name;

    document.getElementById("productImage").src =
        result.product.image || "https://via.placeholder.com/220";

    if (result.product.rating) {
        document.getElementById("ratingText").innerText =
            "Rating: " + result.product.rating +
            " (" + result.product.number_of_ratings + " reviews)";
    }

    // RISK SCORE
    document.getElementById("riskScore").innerText =
        result.regret.score + "%";

    const circle = document.getElementById("riskCircle");

    if (result.regret.color === "green") {
        circle.style.background = "#22c55e";
    } else if (result.regret.color === "orange") {
        circle.style.background = "#f59e0b";
    } else {
        circle.style.background = "#ef4444";
    }

    // PURCHASE CONFIDENCE
    if (result.decision_intelligence) {
        document.getElementById("confidence").innerText =
            result.decision_intelligence.purchase_confidence + "%";
    }

    // DISTRIBUTION
    if (result.advanced_insights) {
        document.getElementById("lowPercent").innerText =
            result.advanced_insights.distribution.low + "%";
        document.getElementById("mediumPercent").innerText =
            result.advanced_insights.distribution.medium + "%";
        document.getElementById("highPercent").innerText =
            result.advanced_insights.distribution.high + "%";
    } else {
        const distSection = document.getElementById("lowPercent");
        if (distSection) distSection.closest("section, .card, div").style.display = "none";
    }

    // RECOMMENDATION
    document.getElementById("recommendationText").innerText =
        result.recommendation;


    // ===============================
    // REAL CUSTOMER EXPERIENCES (FIXED)
    // ===============================

    if (result.evidence) {

        const negativeContainer = document.getElementById("negativeReviews");
        const positiveContainer = document.getElementById("positiveReviews");

        if (negativeContainer && !result.evidence.top_negative.length) {
            negativeContainer.innerHTML = "<p style='opacity:0.5'>Not available for history view.</p>";
        }
        if (positiveContainer && !result.evidence.top_positive.length) {
            positiveContainer.innerHTML = "<p style='opacity:0.5'>Not available for history view.</p>";
        }

        if (negativeContainer && positiveContainer) {

            negativeContainer.innerHTML = "";
            positiveContainer.innerHTML = "";

            result.evidence.top_negative.forEach(review => {
                const item = document.createElement("p");

                const shortText = review.length > 260
                    ? review.substring(0, 260)
                    : review;

                item.innerHTML = shortText +
                    (review.length > 260
                        ? '... <span class="read-more">Read more</span>'
                        : '');

                if (review.length > 260) {
                    item.querySelector(".read-more").onclick = () => {
                        item.innerText = review;
                    };
                }

                negativeContainer.appendChild(item);
            });

            result.evidence.top_positive.forEach(review => {
                const item = document.createElement("p");

                const shortText = review.length > 260
                    ? review.substring(0, 260)
                    : review;

                item.innerHTML = shortText +
                    (review.length > 260
                        ? '... <span class="read-more">Read more</span>'
                        : '');

                if (review.length > 260) {
                    item.querySelector(".read-more").onclick = () => {
                        item.innerText = review;
                    };
                }

                positiveContainer.appendChild(item);
            });
        }
    }
}



// ===============================
// LOAD DASHBOARD
// ===============================

async function loadDashboard() {

    try {

        const response = await fetch("/dashboard");
        const data = await response.json();

        document.getElementById("totalProducts").innerText = data.total_products;
        document.getElementById("averageRegret").innerText = data.average_regret + "%";
        document.getElementById("highRiskProducts").innerText = data.high_risk_products;

    } catch {
        console.log("Dashboard load error");
    }
}



// ===============================
// LOAD HISTORY
// ===============================

async function loadHistory() {

    try {

        const response = await fetch("/history");
        const data = await response.json();

        const tableBody = document.querySelector("#historyTable tbody");

        if (!tableBody) return;

        tableBody.innerHTML = "";

        data.forEach(item => {

            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${item.product_name}</td>
                <td>${item.regret_percentage}%</td>
                <td>${item.recommendation}</td>
                <td>${new Date(item.analyzed_at).toLocaleDateString()}</td>
            `;

            row.onclick = () => {

                const score = item.regret_percentage;
                const riskLevel = score < 30 ? "Low"   : score < 60 ? "Medium" : "High";
                const color     = score < 30 ? "green" : score < 60 ? "orange" : "red";

                localStorage.setItem("analysisResult", JSON.stringify({
                    product: {
                        name:              item.product_name,
                        image:             item.product_image || null,
                        rating:            null,
                        number_of_ratings: null
                    },
                    regret: {
                        score:      score,
                        risk_level: riskLevel,
                        color:      color
                    },
                    decision_intelligence: {
                        purchase_confidence: Math.round((100 - score) * 100) / 100
                    },
                    advanced_insights: null,
                    recommendation: item.recommendation,
                    evidence: null
                }));

                window.location.href = "/app/result.html";
            };

            tableBody.appendChild(row);
        });

    } catch {
        console.log("History load error");
    }
}



// ===============================
// AUTO LOAD PER PAGE
// ===============================

window.onload = () => {

    // home page
    if (document.getElementById("productInput")) return;

    // result page
    if (document.getElementById("riskScore")) {
        loadResultPage();
        return;
    }

    // dashboard page
    if (document.getElementById("totalProducts")) {
        loadDashboard();
        return;
    }

    // history page
    if (document.getElementById("historyTable")) {
        loadHistory();
        return;
    }
};