import os

path = "plugins/rbg/hooks/evaluator.py"
with open(path, "r") as f:
    content = f.read()

content = content.replace(
    'messages.load(hooks_dir, "classifier-prompt")',
    'load_message_pair(hooks_dir, "classifier-prompt")[0]',
)

with open(path, "w") as f:
    f.write(content)
