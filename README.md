# IP-Sentinel AI

Built for the SerpApi India Hackathon 2026.

## The problem

Apple AirPods are one of the most counterfeited electronics products in the world. US Customs seized over $62 million worth of fake AirPods and headphones in a single nine-month period, including one shipment of 50,000 fake units found in Houston. Brands usually catch these listings by searching marketplaces by hand, one site at a time, which takes weeks while fakes keep selling.

IP-Sentinel AI automates that search.

## What it does

You give it a genuine product: its name, its official price, and a link to the official product photo. It runs three SerpApi searches in parallel against that baseline:

- Google Shopping, to find who's selling it and at what price
- Google Reverse Image, to find where the official photo is being reused
- Google Search, to find reseller sites mentioning the product

Every listing gets scored 0 to 100 based on how far below the official price it's listed, how trustworthy the seller looks, how closely it matches the official photo, and how new the seller's domain is (checked with a live WHOIS lookup). Each flagged listing shows exactly which of those factors triggered and by how much, so nothing is a black box.

One click on a flagged listing drafts a cease-and-desist notice. It's clearly labeled as an AI-generated draft for a brand's legal team to review, not legal advice, and the tool never sends anything on its own.

Every scan is also saved as a watch. A background job re-runs it automatically (every 6 hours by default) and only surfaces what's new, so the brand isn't checking manually every time.

## Why SerpApi specifically

All three engines feed the score directly. There's no price factor without Google Shopping, no visual factor without Reverse Image, no reseller-domain factor without Google Search. This isn't a price comparison tool with SerpApi added on top; the scoring is built around having three live results to compare against the baseline.

## Scoring, briefly

```
risk_score = price_points (max 40) + seller_points (max 20) + visual_points (max 20) + domain_points (max 20)
```

A listing at or under half the official price gets the full 40 price points. A seller rated below 3.0 gets the full 20 (unrated sellers get 10, as a moderate default). Visual match blends reverse-image and title similarity. A reseller domain registered in the last 6 months gets the full 20 domain points. A score above 20, or a very sharp price cut, or a very new domain on its own, is enough to flag a listing.

## Currency and region

Switching the currency field between USD and INR doesn't just change the symbol, it re-routes the SerpApi search through Google India (gl=in) for INR, so results and prices are actually India-specific.

## Running it locally

You'll need a free SerpApi key and, optionally, a free Groq key.

Backend:
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```
cd fronted/cybersecurity-dashboard-development
npm install
npm run dev
```

Open localhost:3000. API docs are at localhost:8000/docs.

## Limitations

Google Shopping's matching isn't perfect for smaller or regional brands, so a niche product can occasionally pull in unrelated results sharing a brand word. A low price alone doesn't prove a fake, some of it is legitimate resale. This is built to tell a human where to look first, not to replace that judgment.

## Tech stack

Backend: Python, FastAPI, SQLite, APScheduler for the recurring re-scans.
Frontend: Next.js, React, Tailwind.
Data: SerpApi (Google Shopping, Google Reverse Image, Google Search), python-whois.
AI: Groq (Llama 3) for fraud reasoning and legal notice drafting.

## Disclaimer

The cease-and-desist drafts are AI-generated templates for a brand's legal team to review. They are not legal advice, and the tool does not send or file anything automatically.
