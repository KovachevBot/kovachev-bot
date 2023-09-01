import json

out_words = set()
with open("kaikki_dot_org-dictionary-Bulgarian-inflected.json") as f:
    for line in f:
        entry = json.loads(line)
        word = entry["word"]
        for sense in entry["senses"]:
            if "objective" in sense["tags"] or "subjective" in sense["tags"]:
                out_words.add(word)

with open("words-to-edit.txt", mode="w") as f:
    f.write("\n".join(out_words))