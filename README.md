# Mobthreat
<img width="1536" height="464" alt="mobthreatlogo" src="https://github.com/user-attachments/assets/c4db43ad-73aa-46d4-b49e-247e8b38f920" />

## Mobile App Impersonation & Threat Intelligence Scanner

mobthreat is an automated mobile threat intelligence tool that continuously scans both Google Play and Apple App Store for impersonating, copycat, or fraudulent apps targeting specific brands or organizations
It helps security teams and digital brand protection units detect potential brand abuse, malware distribution, and phishing through fake apps

## Features

- Queries both Play Store and App Store APIs
- Compares app names, developers, packages, and keywords in descriptions
- Fine-tune sensitivity (fuzzy name match, overall score, description bonus, etc.)
- Remembers previously seen apps, only reports new suspicious results
- Slack and Discord webhook integration (stdout fallback by default)
- Extendable to icon similarity via perceptual hashing (pHash)
- Add multiple targets, keywords, and known legitimate apps

## Installation
```
git clone https://github.com/shamo0/mobthreat.git
cd mobthreat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

All configuration is handled through config.yml

```
poll_interval_minutes: 60

thresholds:
  name_fuzzy: 55
  package_exact: true
  icon_phash_distance: 8
  overall_score: 50
  description_weight: 15  
  description_bonus: 20 

targets:
  - id: <ID>
    company_name: "<Name>"
    keywords:
      - "Keyword 1"
      - "Keyword 2"
    known_apps:
      - name: "Known App Name"
        platform: android
        package: "<Android Package>"
      - name: "iOS App name"
        platform: ios
        bundle: "<App ID>"

notifications:
  slack_webhook: null
  discord_webhook: null

logging:
  level: INFO
```

## Usage 

### One-time scan:

```
python -m src.mobthreat.main --config config.yml --once
```

### Continuous Monitoring

```
python -m src.mobthreat.main --config config.yml
```

## Contributing
Contributions are welcome :) 
