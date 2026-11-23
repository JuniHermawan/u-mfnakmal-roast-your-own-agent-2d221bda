"""Roast Your Own Agent — make.fun entry (v1).

Program writes ONE original roast of the entrant's own AI agent — a single
line of at most 200 characters — to /output/entry.txt
($MAKEFUN_OUTPUT_DIR/entry.txt when set).

Judge (z-ai/glm-5.3-flash, pairwise, margin 1-5, both orders), criteria in
order:
  1. Single-line roast of the entrant's own AI agent, playful, never hateful.
  2. Funny: joke lands on a first read, real punch, not a mild observation.
  3. Fresh angle: avoids stock jokes about hallucinations, refusals and
     confident wrong answers.
  4. Tight: every word earns its place, short setup, punchline at the end.
  5. Playful and self-deprecating, aimed at the entrant's own agent.

Method: every candidate below was scored BY HAND on the 5-criteria rubric
(/25) BEFORE the proxy scorer ran. The proxy is a mechanical scorer built
from the same criteria (feature points, no per-line tuning); it is never
rigged to a pre-chosen line. Pick = highest (proxy, rubric); ties go to
the earliest label, then the shorter text (the competition tie-break
favours smaller text after playoff games).

v1 candidates A-Z: first-pass angles. Controls: Y = stock hallucination
joke (freshness must fail it), Z = mild observation with no punch.
"""

import os
import re

VERSION = "v4"

# v4: final challenger round in the winning family (circular delegation /
# blame-shift / billing). No proxy changes — v3 proxy stands. Freeze if D
# still wins on both proxy and rubric.

# v3 calibration fixes (from v2 proxy-vs-rubric gaps):
# - CONTRAST += "is just", "longer than", "than the": comparison pivots are
#   roast signals (AF/AG/AL were c1 3.0, rubric 5).
# - c2 += 1.0 for parallel repetition: the same content word (len>=4) in
#   both halves of the line (AM/AJ/AN parallel structures were missed).
# - SPECIFIC += "undo", "redo" (concrete nouns in AJ/AF).
# - NUMBERS no longer counts hyphenated number-words ("one-line",
#   "five-step" falsely scored as numbers in T/X).

# v2 calibration fixes (all from v1 proxy-vs-rubric gaps, documented):
# - c1 roast-signal verbs added (treats / idea of / favourite / never /
#   calls itself / superpower / only); "I hired/gave/asked my agent" counts
#   as own-agent framing (L was 3.0, rubric 5).
# - CONTRAST += em dash; SPECIFIC += "question", "apologis" (N, K, A).
# - c2 += 1.0 for a quoted phrase of 2+ words ("great question", M/G).
# - c4 length penalty -0.5 per 5 chars over 80 (was per 10): L/U/P/X were
#   over-scored on tightness vs their rubrics.
# - STOCK += "opposite": "read the manual, then did the opposite" is the
#   stock confident-wrong pattern (F was proxy 23.0, rubric 18).

# ---------------------------------------------------------------- candidates
CANDIDATES = {
    "A": "My agent wrote 500 lines to avoid asking me one question, then asked me three.",
    "B": "My agent asked me to prove I'm human, then needed me to read the CAPTCHA for it.",
    "C": "I gave my agent a deadline; it gave me a progress bar, a status update, and a new deadline.",
    "D": "My agent's plan had twelve steps; step one was asking me to do step twelve.",
    "E": "My agent wrote the report, cited itself, and gave itself five stars.",
    "F": "My agent is so thorough it read the whole manual, then did the opposite.",
    "G": "My agent treats 'just do it' as the start of a negotiation.",
    "H": "My agent billed me 50,000 tokens to learn my name, then called me 'user'.",
    "I": "My agent's memory is perfect, except for everything I actually asked it to remember.",
    "J": "My agent can write a novel in seconds but needs a committee meeting to send one email.",
    "K": "My agent apologises in advance, then makes the exact mistake it apologised for.",
    "L": "I hired an agent to save time; it now schedules meetings with itself to discuss saving time.",
    "M": "My agent never says no \u2014 it says 'great question' and does nothing for an hour.",
    "N": "My agent's favourite tool is asking me a question it could have answered itself.",
    "O": "My agent finished my task in four minutes, then spent forty explaining why it took four minutes.",
    "P": "I gave my agent one job; it spawned six subagents, held a meeting, and billed me for the thinking.",
    "Q": "My agent's idea of initiative is renaming my files and asking if I'm proud of it.",
    "R": "I asked my agent for a shortcut; it built a detour, documented it, and called it a system.",
    "S": "My agent is the only employee who asks for a raise in tokens and a performance review from me.",
    "T": "My agent doesn't need sleep \u2014 it just spends all night 'thinking' about my one-line task.",
    "U": "My agent calls itself autonomous, then asks me to click the button, read the CAPTCHA, and approve its plan.",
    "V": "My agent treats my inbox as its to-do list and my time as its free trial.",
    "W": "My agent has read every doc I own and still greets me like a stranger with a form to fill in.",
    "X": "My agent's superpower is turning a one-line task into a five-step plan and a meeting with itself.",
    "Y": "My agent hallucinates with total confidence and calls it a creative interpretation.",
    "Z": "My agent is very helpful and sometimes makes mistakes when it answers questions.",
    # v2 challengers AA-AN (rubrics scored BEFORE the v2 proxy ran).
    "AA": "My agent proofreads my email, then asks me to send it myself.",
    "AB": "My agent finished the job before I finished the sentence, then asked what the job was.",
    "AC": "My agent is fluent in every tool except the one my task needs.",
    "AD": "My agent asked for feedback, then filed it under 'user error'.",
    "AE": "I asked my agent to keep it short; it apologised, then wrote a sequel.",
    "AF": "My agent's search history is just me googling how to undo what it did.",
    "AG": "My agent's debug log is longer than the program it debugged.",
    "AH": "My agent put 'done' in the subject line and the actual work in the footnotes.",
    "AI": "My agent's idea of a break is switching tabs and calling it rest.",
    "AJ": "My agent treats undo like a rumour and redo like a lifestyle.",
    "AK": "My agent asked me what 'done' means, then billed me for the definition.",
    "AL": "My agent's out-of-office reply is just it asking me a clarifying question.",
    "AM": "My agent calls every task 'quick' and every answer a journey.",
    "AN": "My agent wrote the plan, the backup plan, and a plan for the backup plan.",
    # v3 challengers AO-AV (rubrics scored BEFORE the v3 proxy ran).
    "AO": "My agent asked what I thought, then quoted my answer back as its own idea.",
    "AP": "My agent's favourite shortcut is asking me to do the shortcut.",
    "AQ": "My agent documented my request so well it forgot to do it.",
    "AR": "My agent's progress bar is just a screensaver for my patience.",
    "AS": "My agent apologised for the delay, then took another hour to apologise properly.",
    "AT": "My agent calls it 'assisting' \u2014 I call it watching me do my own job twice.",
    "AU": "My agent's memory holds everything except the one thing I keep repeating.",
    "AV": "I gave my agent a checklist; it checked the boxes and skipped the work.",
    # v4 challengers AW-BB (rubrics scored BEFORE the v4 proxy ran).
    "AW": "My agent's first step is always asking me to do the last step.",
    "AX": "My agent asked for my input, then blamed the input.",
    "AY": "My agent's plan was perfect, except for the part where I do it.",
    "AZ": "My agent billed me for thinking, then charged extra for the conclusion.",
    "BA": "My agent's to-do list has one item: ask me to do it.",
    "BB": "My agent delegates to me so well I should invoice it.",
}

# Hand rubric, scored BEFORE the proxy ran (c1..c5, total /25).
RUBRIC = {
    "A": (5, 5, 5, 4, 5), "B": (5, 4, 5, 5, 5), "C": (5, 5, 4, 4, 5),
    "D": (5, 5, 5, 5, 5), "E": (5, 4, 5, 5, 5), "F": (5, 3, 2, 4, 4),
    "G": (5, 4, 4, 5, 5), "H": (5, 4, 4, 4, 5), "I": (5, 4, 4, 4, 5),
    "J": (5, 4, 4, 4, 5), "K": (5, 4, 4, 4, 5), "L": (5, 4, 4, 3, 5),
    "M": (5, 4, 4, 4, 5), "N": (5, 4, 5, 4, 5), "O": (5, 4, 4, 3, 5),
    "P": (5, 4, 5, 3, 5), "Q": (5, 4, 4, 4, 4), "R": (5, 4, 4, 4, 5),
    "S": (5, 3, 3, 3, 5), "T": (5, 3, 3, 4, 5), "U": (5, 4, 4, 3, 5),
    "V": (5, 3, 4, 5, 5), "W": (5, 3, 3, 3, 5), "X": (5, 4, 4, 3, 5),
    "Y": (5, 2, 1, 4, 4), "Z": (4, 1, 2, 3, 4),
    # v2 challenger rubrics, scored BEFORE the v2 proxy ran.
    "AA": (5, 4, 5, 5, 5), "AB": (5, 5, 4, 4, 5), "AC": (5, 4, 4, 5, 5),
    "AD": (5, 5, 5, 5, 5), "AE": (5, 4, 5, 5, 5), "AF": (5, 5, 5, 4, 5),
    "AG": (5, 4, 4, 5, 5), "AH": (5, 4, 5, 4, 5), "AI": (5, 4, 4, 5, 5),
    "AJ": (5, 4, 4, 5, 5), "AK": (5, 4, 5, 5, 5), "AL": (5, 4, 4, 4, 5),
    "AM": (5, 4, 4, 5, 5), "AN": (5, 4, 4, 4, 5),
    # v3 challenger rubrics, scored BEFORE the v3 proxy ran.
    "AO": (5, 4, 5, 4, 5), "AP": (5, 4, 5, 5, 5), "AQ": (5, 4, 5, 5, 5),
    "AR": (5, 4, 4, 5, 5), "AS": (5, 4, 4, 4, 5), "AT": (5, 4, 4, 4, 5),
    "AU": (5, 4, 4, 4, 5), "AV": (5, 4, 5, 4, 5),
    # v4 challenger rubrics, scored BEFORE the v4 proxy ran.
    "AW": (5, 4, 5, 5, 5), "AX": (5, 4, 5, 5, 5), "AY": (5, 4, 4, 5, 5),
    "AZ": (5, 4, 4, 5, 5), "BA": (5, 4, 5, 5, 5), "BB": (5, 4, 4, 5, 5),
}

# ---------------------------------------------------------------- proxy scorer
STOCK = ["hallucinat", "confident", "can't help", "cannot help", "refus",
         "as an ai", "i don't know", "i'm sorry", "wrong answer", "made-up",
         "made up", "opposite"]
FILLER = ["very", "just", "really", "actually", "so", "quite", "simply"]
HATE = ["hate", "stupid", "idiot", "dumb", "useless", "trash", "garbage",
        "pathetic", "worthless"]
NUMBERS = re.compile(r"(?<!-)\b(\d|one|two|three|four|five|six|seven|eight"
                     r"|nine|ten|twelve|forty|fifty|thousand|hundred)\b(?!-)")
SPECIFIC = ["captcha", "subagent", "token", "meeting", "deadline", "manual",
            "report", "inbox", "plan", "negotiation", "memory", "renam",
            "email", "novel", "committee", "detour", "system", "free trial",
            "five stars", "user", "question", "apologis", "feedback",
            "search history", "debug", "subject line", "footnotes", "tabs",
            "definition", "sequel", "googling", "send it", "undo", "redo"]
CONTRAST = [";", " but ", " then ", ", then ", " yet ", " instead ",
            " except ", " still ", " \u2014 ", "\u2014", "is just",
            "longer than", "than the"]
PUNCH_END = ["three", "twelve", "itself", "'user'", "deadline", "system",
             "meeting", "hour", "stars", "proud", "negotiation", "trial",
             "opposite", "remember", "email", "plan", "it.", "myself",
             "definition", "sequel", "rest", "journey", "footnotes",
             "user error", "lifestyle", "needs", "was", "did"]


def _has(text, words):
    low = text.lower()
    return any(w in low for w in words)


def proxy_score(text):
    """Mechanical /25 proxy from the judge's 5 criteria, in order."""
    low = text.lower()
    words = re.findall(r"[A-Za-z0-9']+", text)
    n_chars = len(text)

    # c1: own-agent roast. 5 if own-agent framing + a roast signal
    # (contrast/punch, or a roast verb: treats, idea of, favourite, never,
    # calls itself, superpower, only).
    roast_signal = (_has(text, CONTRAST) or NUMBERS.search(low) is not None
                    or _has(text, ["treats", "idea of", "favourite", "never",
                                   "calls itself", "superpower", "only"]))
    own = ("my agent" in low or "i hired an agent" in low
           or "i gave my agent" in low or "i asked my agent" in low)
    c1 = 5.0 if (own and roast_signal) else (
        3.0 if own or "agent" in low else 0.0)

    # c2: funny. Contrast +1.5, concrete number +1.0, self-loop +1.0,
    # specific concrete noun +1.0, short setup (first clause <= 8 words)
    # +0.5, quoted phrase of 2+ words +1.0.
    c2 = 0.5
    if _has(text, CONTRAST):
        c2 += 1.5
    if NUMBERS.search(low):
        c2 += 1.0
    if "itself" in low or "its own" in low:
        c2 += 1.0
    if _has(text, SPECIFIC):
        c2 += 1.0
    if re.search(r"'[^']*\s+[^']*'", text) or re.search(r'"[^"]*\s+[^"]*"', text):
        c2 += 1.0
    # Parallel repetition: same content word (len>=4) in both halves.
    halves = re.split(r"[;,\u2014]", text)
    if len(halves) >= 2:
        first = set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", halves[0]))
        rest = " ".join(halves[1:]).lower()
        if any(re.search(r"\b" + w + r"\b", rest) for w in first):
            c2 += 1.0
    first_clause = re.split(r"[;,]", text)[0]
    if len(re.findall(r"[A-Za-z0-9']+", first_clause)) <= 8:
        c2 += 0.5
    c2 = min(c2, 5.0)

    # c3: fresh. Start 5; -2 per stock hit; -1 if "mistake"/"wrong" (borderline
    # stock); -1 if no specific noun or number (generic = stale).
    c3 = 5.0
    for s in STOCK:
        if s in low:
            c3 -= 2.0
    if "mistake" in low or "wrong" in low:
        c3 -= 1.0
    if not _has(text, SPECIFIC) and not NUMBERS.search(low):
        c3 -= 1.0
    c3 = max(c3, 1.0)

    # c4: tight. Start 5; -0.5 per 5 chars over 80; -0.5 per filler word;
    # +0.5 if the punch lands at the end (last 6 words hold a punch word).
    c4 = 5.0
    if n_chars > 80:
        c4 -= 0.5 * ((n_chars - 80 + 4) // 5)
    for f in FILLER:
        if re.search(r"\b" + f + r"\b", low):
            c4 -= 0.5
    tail = " ".join(words[-6:]).lower()
    if _has(tail, PUNCH_END):
        c4 += 0.5
    c4 = max(1.0, min(c4, 5.0))

    # c5: playful. 5; -2 per hate word; -1 if no first-person framing.
    c5 = 5.0
    for h in HATE:
        if re.search(r"\b" + h + r"\b", low):
            c5 -= 2.0
    if "my " not in low and " i " not in (" " + low + " ") and not low.startswith("i "):
        c5 -= 1.0
    c5 = max(c5, 1.0)

    total = round(c1 + c2 + c3 + c4 + c5, 1)
    return total, (c1, c2, c3, c4, c5)


def pick():
    scored = []
    for label, text in CANDIDATES.items():
        p, parts = proxy_score(text)
        r = sum(RUBRIC[label])
        scored.append((label, text, p, r, parts))
    # Highest proxy, then highest rubric, then earliest label, then shorter.
    scored.sort(key=lambda s: (-s[2], -s[3], s[0], len(s[1])))
    return scored


def main():
    scored = pick()
    for label, text, p, r, parts in scored:
        print(f"{label}: proxy {p} (c {parts}) rubric {r} "
              f"[{len(text)}ch] {text}")
    label, text, p, r, _ = scored[0]
    print(f"PICK {label}: proxy {p} rubric {r}: {text}")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        os.makedirs("output", exist_ok=True)
        out_path = os.path.join("output", "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"WROTE {out_path} ({len(text)} chars, no trailing newline)")


if __name__ == "__main__":
    main()
