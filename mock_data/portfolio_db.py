"""
Mock Multi-Tenant MFD Portfolio Database
Simulates 650+ client portfolios across all major mutual fund categories.
Used by Module 2 (Book Auditor) to identify impacted clients.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

random.seed(42)

FUND_UNIVERSE: Dict[str, List[Dict]] = {
    "Small Cap": [
        {"isin": "INF090I01239", "name": "Nippon India Small Cap Fund - Direct Growth", "ter": 0.68},
        {"isin": "INF200K01LF2", "name": "SBI Small Cap Fund - Direct Growth", "ter": 0.62},
        {"isin": "INF846K01DP8", "name": "Axis Small Cap Fund - Direct Growth", "ter": 0.54},
        {"isin": "INF769K01EA7", "name": "HDFC Small Cap Fund - Direct Growth", "ter": 0.60},
    ],
    "Mid Cap": [
        {"isin": "INF179K01CE9", "name": "HDFC Mid Cap Opportunities - Direct Growth", "ter": 0.75},
        {"isin": "INF174K01LS2", "name": "Kotak Emerging Equity - Direct Growth", "ter": 0.44},
        {"isin": "INF740K01LQ5", "name": "DSP Midcap Fund - Direct Growth", "ter": 0.74},
    ],
    "Large Cap": [
        {"isin": "INF769K01DM5", "name": "Mirae Asset Large Cap - Direct Growth", "ter": 0.55},
        {"isin": "INF846K01CI0", "name": "Axis Bluechip Fund - Direct Growth", "ter": 0.44},
        {"isin": "INF109K01Z28", "name": "ICICI Pru Bluechip Fund - Direct Growth", "ter": 0.92},
    ],
    "ELSS": [
        {"isin": "INF846K01BN4", "name": "Axis Long Term Equity - Direct Growth", "ter": 0.63},
        {"isin": "INF769K01DK9", "name": "Mirae Asset Tax Saver - Direct Growth", "ter": 0.53},
        {"isin": "INF204K01BG5", "name": "ICICI Pru Long Term Equity - Direct Growth", "ter": 1.05},
    ],
    "Liquid": [
        {"isin": "INF179K01DA6", "name": "HDFC Liquid Fund - Direct Growth", "ter": 0.20},
        {"isin": "INF200K01RX9", "name": "SBI Liquid Fund - Direct Growth", "ter": 0.20},
        {"isin": "INF846K01BS3", "name": "Axis Liquid Fund - Direct Growth", "ter": 0.14},
    ],
    "Short Duration Debt": [
        {"isin": "INF179K01FS8", "name": "HDFC Short Duration Fund - Direct Growth", "ter": 0.36},
        {"isin": "INF204K01056", "name": "ICICI Pru Short Term Fund - Direct Growth", "ter": 0.48},
    ],
    "Corporate Bond": [
        {"isin": "INF179K01FT6", "name": "HDFC Corporate Bond Fund - Direct Growth", "ter": 0.25},
        {"isin": "INF200K01PA2", "name": "SBI Corporate Bond Fund - Direct Growth", "ter": 0.30},
    ],
    "Flexi Cap": [
        {"isin": "INF769K01EK6", "name": "Parag Parikh Flexi Cap - Direct Growth", "ter": 0.63},
        {"isin": "INF109K01Z46", "name": "ICICI Pru Flexicap Fund - Direct Growth", "ter": 0.77},
    ],
    "Multi Cap": [
        {"isin": "INF740K01LS1", "name": "DSP Multicap Fund - Direct Growth", "ter": 0.80},
        {"isin": "INF200K01OM5", "name": "Nippon India Multi Cap - Direct Growth", "ter": 0.78},
    ],
    "Index Fund": [
        {"isin": "INF769K01EI0", "name": "Mirae Asset Nifty 50 ETF", "ter": 0.05},
        {"isin": "INF200K01990", "name": "SBI Nifty Index Fund - Direct Growth", "ter": 0.07},
        {"isin": "INF846K01LV2", "name": "Axis Nifty 100 Index Fund - Direct Growth", "ter": 0.21},
    ],
    "International Fund": [
        {"isin": "INF769K01EL4", "name": "Parag Parikh Flexi Cap (Intl Allocation)", "ter": 1.04},
        {"isin": "INF204K01DO9", "name": "ICICI Pru US Bluechip Equity - Direct Growth", "ter": 1.10},
    ],
    "Gold Fund": [
        {"isin": "INF179K01FK3", "name": "HDFC Gold Fund - Direct Growth", "ter": 0.56},
        {"isin": "INF200K01QS5", "name": "SBI Gold Fund - Direct Growth", "ter": 0.56},
    ],
}

_FIRST_NAMES = [
    "Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Anita", "Deepak", "Meena",
    "Suresh", "Kavita", "Rohit", "Pooja", "Arun", "Geeta", "Manoj", "Rekha",
    "Sanjay", "Usha", "Rakesh", "Lalita", "Dinesh", "Seema", "Harish", "Nisha",
    "Prakash", "Asha", "Ramesh", "Shobha", "Vinod", "Kamla", "Ajay", "Ritu",
    "Sunil", "Vandana", "Mohan", "Savita", "Naresh", "Poonam", "Ashok", "Saroj",
]

_LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Verma", "Gupta", "Kumar", "Joshi", "Mehta",
    "Agarwal", "Mishra", "Tiwari", "Yadav", "Pandey", "Chauhan", "Shukla",
    "Srivastava", "Dubey", "Rao", "Nair", "Iyer", "Pillai", "Reddy", "Choudhary",
    "Kapoor", "Malhotra", "Bose", "Das", "Chatterjee", "Banerjee", "Mukherjee",
]

_INVESTMENT_BUCKETS = [10_000, 25_000, 50_000, 1_00_000, 2_00_000, 5_00_000, 10_00_000, 25_00_000, 50_00_000]


def _generate_pan() -> str:
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        f"{random.choice(alpha)}{random.choice(alpha)}{random.choice(alpha)}"
        f"P"  # P = Person
        f"{random.choice(alpha)}"
        f"{random.randint(1000, 9999)}"
        f"{random.choice(alpha)}"
    )


def _generate_client(client_id: int) -> Dict:
    first = random.choice(_FIRST_NAMES)
    last = random.choice(_LAST_NAMES)

    num_holdings = random.randint(1, 6)
    categories = random.sample(list(FUND_UNIVERSE.keys()), min(num_holdings, len(FUND_UNIVERSE)))

    holdings = []
    for category in categories:
        fund = random.choice(FUND_UNIVERSE[category])
        days_ago = random.randint(90, 2190)  # 3 months to 6 years
        purchase_date = datetime.now() - timedelta(days=days_ago)
        invested_amount = random.choice(_INVESTMENT_BUCKETS)
        growth_factor = random.uniform(0.65, 2.8)
        current_value = round(invested_amount * growth_factor, 2)
        nav = random.uniform(30, 800)
        units = round(invested_amount / nav, 3)

        holdings.append({
            "isin": fund["isin"],
            "fund_name": fund["name"],
            "category": category,
            "units": units,
            "invested_amount": invested_amount,
            "current_value": current_value,
            "purchase_date": purchase_date.strftime("%Y-%m-%d"),
            "holding_period_days": days_ago,
            "is_ltcg_eligible": days_ago > 365,
            "unrealized_gain": round(current_value - invested_amount, 2),
            "ter": fund["ter"],
            "folio_number": f"FOL{client_id:04d}{random.randint(100, 999)}",
        })

    total_value = sum(h["current_value"] for h in holdings)

    return {
        "client_id": f"CLT{client_id:04d}",
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}{client_id}@example.com",
        "phone": f"+91-{random.randint(7000000000, 9999999999)}",
        "pan": _generate_pan(),
        "kyc_status": random.choices(["VERIFIED", "PENDING"], weights=[85, 15])[0],
        "risk_profile": random.choices(
            ["Conservative", "Moderate", "Aggressive"],
            weights=[25, 50, 25]
        )[0],
        "tax_bracket_pct": random.choices([5, 20, 30], weights=[20, 30, 50])[0],
        "holdings": holdings,
        "total_portfolio_value": round(total_value, 2),
        "nomination_linked": random.choices([True, False], weights=[70, 30])[0],
        "sip_active": random.choices([True, False], weights=[60, 40])[0],
    }


class MockPortfolioDatabase:
    """
    Simulates an MFD's complete book of business.
    Supports filtering by fund category, nomination status, KYC status, etc.
    """

    def __init__(self, num_clients: int = 650):
        self._clients = [_generate_client(i + 1) for i in range(num_clients)]
        self._by_id: Dict[str, Dict] = {c["client_id"]: c for c in self._clients}
        self._category_index: Dict[str, List[str]] = {}
        for client in self._clients:
            for holding in client["holdings"]:
                cat = holding["category"]
                self._category_index.setdefault(cat, []).append(client["client_id"])

    def get_all_clients(self) -> List[Dict]:
        return self._clients

    def get_client(self, client_id: str) -> Optional[Dict]:
        return self._by_id.get(client_id)

    def get_clients_by_category(self, category: str) -> List[Dict]:
        ids = set(self._category_index.get(category, []))
        return [self._by_id[cid] for cid in ids]

    def get_clients_without_nomination(self) -> List[Dict]:
        return [c for c in self._clients if not c["nomination_linked"]]

    def get_clients_with_pending_kyc(self) -> List[Dict]:
        return [c for c in self._clients if c["kyc_status"] == "PENDING"]

    def get_clients_by_categories(self, categories: List[str]) -> List[Dict]:
        ids: set = set()
        for cat in categories:
            ids.update(self._category_index.get(cat, []))
        return [self._by_id[cid] for cid in ids]

    def get_summary_stats(self) -> Dict:
        total_aum = sum(c["total_portfolio_value"] for c in self._clients)
        return {
            "total_clients": len(self._clients),
            "total_aum_inr": round(total_aum, 2),
            "categories": list(self._category_index.keys()),
            "clients_per_category": {
                cat: len(set(ids)) for cat, ids in self._category_index.items()
            },
        }


# Module-level singleton — shared across all nodes
db = MockPortfolioDatabase(num_clients=650)
