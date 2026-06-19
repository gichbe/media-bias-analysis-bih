"""
Konzervativan fix mojibake-a koristeci samo ftfy biblioteku.

Vazno: koristi SAMO ftfy. Nema agresivnih strategija koje mogu uniStiti tekst.
Ako ftfy ne moze popraviti, ostavlja tekst kakav jeste.

Instalacija: pip install ftfy
Pokretanje:  python fix_mojibake.py "data/raw/*.json" "data/processed/*.json"
"""

import glob
import json
import sys
from pathlib import Path

try:
    import ftfy
except ImportError:
    print("Instaliraj: pip install ftfy")
    sys.exit(1)


MOJIBAKE_CHARS = ["Ä", "Å", "Â", "Ã", "â\x80"]


def mojibake_score(text):
    if not isinstance(text, str):
        return 0
    return sum(text.count(c) for c in MOJIBAKE_CHARS)


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
        files.extend(Path(f) for f in glob.glob(arg))

    total_fixed = 0
    for path in files:
        if path.suffix != ".json" or not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  SKIP {path}: {e}")
            continue

        original_score = mojibake_score(json.dumps(data, ensure_ascii=False))
        fixed = fix_recursive(data)
        new_score = mojibake_score(json.dumps(fixed, ensure_ascii=False))

        if new_score < original_score:
            with path.open("w", encoding="utf-8") as f:
                json.dump(fixed, f, ensure_ascii=False, indent=2)
            print(f"  FIX  {path}  ({original_score} -> {new_score})")
            total_fixed += 1
        elif original_score > 0:
            print(f"  ??   {path}  (mojibake i dalje: {original_score} - ftfy nije uspio)")
        else:
            print(f"  OK   {path}")

    print(f"\nGotovo. Popravljeno {total_fixed} fajl(ova).")


if __name__ == "__main__":
    main()
