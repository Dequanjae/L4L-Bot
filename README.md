# L4L-Bot — Free Instagram Engagement Credit Farmer

Docker containers that auto-earn credits on Like4Like + AddMeFast 24/7. $0/month.

## What It Does

3 Docker containers run Selenium bots that:
1. Log into Like4Like + AddMeFast (not Instagram directly)
2. Auto-click like/follow/view tasks on the exchange dashboards
3. Earn credits 24/7
4. You spend credits to get real likes/follows on your Instagram posts

## Why This Approach

- **$0/month** — no paid SMM panels, no paid proxies
- **Safer** — bots interact with exchange websites, not Instagram
- **Real engagement** — real exchange users like your content (not fake bot accounts)
- **Free proxies** — rotates from public GitHub proxy lists

## Quick Start

```bash
# 1. Create free accounts:
#    - Like4Like.org (create 3 accounts, different emails)
#    - AddMeFast.com (create 3 accounts, different emails)

# 2. Clone this repo
git clone https://github.com/Dequanjae/L4L-Bot.git
cd L4L-Bot

# 3. Edit docker-compose.yml — fill in your account credentials

# 4. Build and deploy
docker compose up -d --build

# 5. Monitor
docker compose logs -f farmer1
```

## Files

```
L4L-Bot/
├── docker-compose.yml      ← 3 farmer containers
├── farmer/
│   ├── Dockerfile          ← Chrome + Selenium + Python
│   ├── requirements.txt    ← Python deps
│   ├── farmer.py           ← Main credit farming bot
│   ├── proxy_rotator.py    ← Free proxy rotation (GitHub lists)
│   └── comments.py         ← Comment pool (for direct bot mode)
├── logs/                   ← Per-farmer logs
└── shared/
    └── credits_state.json  ← Tracks earned credits
```

## Expected Output ($0)

| Metric | Daily |
|--------|-------|
| Credits farmed | ~6,000 |
| Likes on your posts | 50-100 |
| New followers | 10-25 |
| Cost | $0 |

## Adding More Farmers

Edit `docker-compose.yml`, copy a farmer service block, change the credentials and container name. Each farmer = one exchange account pair (1 Like4Like + 1 AddMeFast).

## Safety

- Exchange accounts use burner emails, not your main
- Bots interact with Like4Like/AddMeFast, NOT Instagram directly
- Free proxies rotate from 3 public sources (Proxifly, ProxyScrape, stormsia)
- Human-like delays between all actions (2-10 min)
- Farmers sleep at night (configurable)

## License

MIT — do whatever you want with this.
