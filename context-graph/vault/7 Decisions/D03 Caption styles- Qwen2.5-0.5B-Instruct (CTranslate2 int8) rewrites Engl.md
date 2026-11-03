---
id: decision:D03
type: "decision"
why: "Speed test on 30 real lines (M4 Pro): 0.5B median 0.5 s Natural / 0.4 s Simple, never over 1.5 s; 1.5B was nicer but median 1.4 s with 12/30 Natural over 1.5 s. Qwen3-1.7B: fewest rejections but median 1.7 s, 23/30 Natural over 1.5 s. The small model sometimes changes the meaning, so strict checks fall back to word for word"
revisit_when: "a faster computer target, or the checks reject too often: try 1.5B (`tests/bench_meaning.py`)"
---
# Caption styles: Qwen2.5-0.5B-Instruct (CTranslate2 int8) rewrites English only, greedy, 1.5 s limit

**why:** Speed test on 30 real lines (M4 Pro): 0.5B median 0.5 s Natural / 0.4 s Simple, never over 1.5 s; 1.5B was nicer but median 1.4 s with 12/30 Natural over 1.5 s. Qwen3-1.7B: fewest rejections but median 1.7 s, 23/30 Natural over 1.5 s. The small model sometimes changes the meaning, so strict checks fall back to word for word

**revisit when:** a faster computer target, or the checks reject too often: try 1.5B (`tests/bench_meaning.py`)

## Links
- about [[Speech to text]] *(keyword match)*
- about [[Caption language]] *(keyword match)*
- about [[Caption style]] *(keyword match)*
