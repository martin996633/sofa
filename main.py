name: SofaScraper LIVE

on:
  schedule:
    - cron: '*/10 * * * *' # Každých 10 minut
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scrape_and_commit:
    runs-on: ubuntu-latest

    steps:
      - name: Stáhnout kód
        uses: actions/checkout@v3

      - name: Nastavit Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Instalace knihoven
        run: pip install -r requirements.txt

      - name: Spustit skript
        run: python main.py

      - name: Commit a Push
        run: |
          git config --global user.name "SofaBot"
          git config --global user.email "sofabot@users.noreply.github.com"
          
          # Hledáme live_results.csv
          if [ -f live_results.csv ]; then
            git add live_results.csv
            git commit -m "Live update: $(date)" || echo "Žádné změny"
            git push
            echo "✅ Live data odeslána."
          else
            echo "⚠️ Soubor live_results.csv nevznikl."
          fi
