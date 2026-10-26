"""test_cards.py - check the card cutter on one or more PDFs, and time it.

Usage:  python test_cards.py report1.pdf [report2.pdf ...] [--max-pages 300] [--embed]
Several PDFs with --max-pages 300 imitate the biggest case the rules allow.
--embed also times the meaning-matcher (bge-base) turning every card into a vector.
"""

import os
import sys
import time

import pypdfium2 as pdfium

from chunker import make_cards

MODEL_PATH = os.path.expanduser("~/work/models/BAAI/bge-base-en-v1.5/a5beb1e3e68b9ab74eb54cfd186867f64f240e1a")


def read_pages(path: str) -> list[str]:
    pdf = pdfium.PdfDocument(path)
    pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    pdf.close()
    return pages


args = sys.argv[1:]
embed = "--embed" in args
args = [a for a in args if a != "--embed"]
max_pages = 10**9
if "--max-pages" in args:
    k = args.index("--max-pages")
    max_pages = int(args[k + 1])
    args = args[:k] + args[k + 2:]

t0 = time.perf_counter()
all_cards, total_pages, skipped = [], 0, {}
for n, path in enumerate(args, start=1):
    pages = read_pages(path)[: max(0, max_pages - total_pages)]
    total_pages += len(pages)
    cards, kinds = make_cards(pages, document_id=f"D{n:03d}")
    all_cards += cards
    for page, kind in kinds.items():
        if kind != "normal":
            skipped.setdefault(kind, []).append(f"D{n:03d}:{page}")
t1 = time.perf_counter()

words = [len(c["text"].split()) for c in all_cards]
print(f"pages read:  {total_pages}")
print(f"cards made:  {len(all_cards)}  (words per card: avg {sum(words)/len(words):.0f}, max {max(words)})")
for kind, where in skipped.items():
    print(f"skipped {kind:10s} {len(where)} pages: {', '.join(where[:12])}{' ...' if len(where) > 12 else ''}")
print(f"time:        {t1 - t0:.2f} s (reading + cutting)")

if embed:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(4)                          # the event machine has 4 cores
    t2 = time.perf_counter()
    model = SentenceTransformer(MODEL_PATH, device="cpu", local_files_only=True)
    t3 = time.perf_counter()
    model.encode([c["text"] for c in all_cards], batch_size=32, normalize_embeddings=True)
    t4 = time.perf_counter()
    print(f"model load:  {t3 - t2:.1f} s")
    print(f"embedding:   {t4 - t3:.1f} s for {len(all_cards)} cards ({len(all_cards) / (t4 - t3):.0f} cards per second)")
    print(f"total:       {t4 - t0:.1f} s")
else:
    print()
    for c in all_cards[5:8]:
        print(f"--- {c['document_id']} page {c['page']}, {len(c['sentences'])} sentences")
        for s in c["sentences"]:
            print("  •", s[:160])