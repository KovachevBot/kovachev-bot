def process(line: str) -> str:
    return line[line.rfind(" ")+1:].replace("-", "")

with open("words.txt") as f:
    contents = f.readlines()

for i, line in enumerate(contents):
    contents[i] = process(line)

with open("modified.txt", mode="w") as f:
    f.writelines(contents)
