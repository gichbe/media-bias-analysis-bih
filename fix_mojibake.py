"""
Robustan fix mojibake-a koristeći ftfy biblioteku.

ftfy ('Fixes Text For You') rješava sve varijante mojibake-a:
  - jednostruki UTF-8 <-> Latin-1 swap
  - dvostruki/trostruki encoding
  - HTML entities, kontrolni karakteri, itd.

Instalacija:
    pip install ftfy

Pokretanje:
    python fix_mojibake.py "data/raw/*.json" "data/processed/*.json"
"""

import glob
import json
import sys
from pathlib import Path

try:
    import ftfy
except ImportError:
    print("Nedostaje ftfy biblioteka. Instaliraj sa:")
    print("    pip install ftfy")
    sys.exit(1)


def fix_recursive(obj):
    if isinstance(obj, str):
        return ftfy.fix_text(obj)
    if isinstance(obj, dict):
        return {k: fix_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fix_recursive(x) for x in obj]
    return obj


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python fix_mojibake.py 'data/raw/*.json' ...")
        sys.exit(1)

    files = []
    for arg in args:
        expanded = glob.glob(arg)
        if not expanded:
            print(f"Nema fajlova za: {arg}")
        files.extend(Path(f) for f in expanded)

    if not files:
        print("Nema JSON fajlova za obradu.")
        sys.exit(1)

    fixed_count = 0
    for path in files:
        if path.suffix != ".json" or not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  SKIP {path}: {e}")
            continue

        original = json.dumps(data, ensure_ascii=False, sort_keys=True)
        fixed = fix_recursive(data)
        new = json.dumps(fixed, ensure_ascii=False, sort_keys=True)

        if original != new:
            with path.open("w", encoding="utf-8") as f:
                json.dump(fixed, f, ensure_ascii=False, indent=2)
            print(f"  FIX  {path}")
            fixed_count += 1
        else:
            print(f"  OK   {path}")

    print(f"\nGotovo. Popravljeno {fixed_count} fajl(ova).")


if __name__ == "__main__":
    main()
