# ClearedDirect Content Feed

Live JSON content served via GitHub Pages for the ClearedDirect iOS app.

## Structure

```
v1/
├── hiring_status.json    # Airline hiring board data
├── deadlines.json        # Scholarship/program deadlines
└── news_feed.json        # Industry news items
```

## How it works

The ClearedDirect app fetches these files on launch and caches them locally. Updates here go live to all users on their next app open.

## Updating content

1. Edit the JSON files in `v1/`
2. Commit and push to `main`
3. GitHub Pages deploys automatically — changes are live within minutes

## Base URL

```
https://gray1223.github.io/skypath-content/v1/
```
