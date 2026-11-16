"""
db/seed_insights.py
Seeds: market_insights, sentiment_themes  (REAL data, not typed in)

Runs backend/controllers/insights_controller.py once, the same code the backend's scheduler runs: market
insights are the real headlines the sentiment engines read, and themes are named from them by the LLM
(needs GROQ_API_KEY). It used to insert six made-up stories and five made-up themes; those, and anything
else not written by the controller, are deleted.

The crypto headlines come from the crypto sentiment engine's stored readings, so run this after the backend
has been up for a few minutes (or just let the backend's scheduler do it).

Run: python db/seed_insights.py
"""
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))


def seed():
    from controllers.insights_controller import refresh_insights, refresh_themes
    print(f"[market_insights] {refresh_insights()}")
    try:
        print(f"[sentiment_themes] {refresh_themes()}")
    except Exception as exc:          # no engine dependencies or no Groq here: the backend will do it
        print(f"[sentiment_themes] skipped: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
