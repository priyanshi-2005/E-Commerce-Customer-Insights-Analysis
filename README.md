# E-commerce Insights Analysis

SQL analysis of the public Olist e-commerce dataset: about 100,000 orders from a Brazilian online marketplace.

**Aaditya Rathi** • **Priyanshi Agarwal**

The app is for product, finance, and analyst questions. There are 6 topics and 90 questions. Each answer is a short dashboard — a few numbers, a chart, and a table — with the SQL query shown underneath.

## Topics

| Topic | What it covers |
| --- | --- |
| Revenue & Growth | Sales over time, and orders that never get delivered |
| Product & Categories | Which product types sell, get reordered, or fail to arrive |
| Customer Analytics | Best customers, repeat buyers, and customers going quiet |
| Payments & Checkout | How people pay, and where checkout stops |
| Logistics & Reviews | Where orders get stuck, and how delays affect reviews |
| Sellers & Marketplace | Which sellers drive sales, and which ones fail to deliver |

Customer questions use `customer_unique_id`. In this dataset, `customer_id` is a new id on every order, so it cannot be used to tell whether someone bought again.

## Dataset

The order files are not in this repository. Download [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) from Kaggle and unzip the CSVs into `data/raw/`.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/load_olist.py
streamlit run app/streamlit_app.py
```

## Layout

```text
app/           Streamlit app, question list, and dashboard
quests/        One SQL file per question, grouped by topic
schema/        Table definitions
views/         Shared SQL views
scripts/       Loader that builds the SQLite database from the CSVs
```
