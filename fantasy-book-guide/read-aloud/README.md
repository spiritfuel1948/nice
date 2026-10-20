# Read-Aloud Page

Builds the "Wizards & Knights Read-Aloud" page, which reads the guide's lessons
out loud with the device's built-in voice (the browser's Web Speech API).
It's published at https://claude.ai/artifact/G2tu6adFXPzH7A5gN8CJdt

To rebuild after editing the guide (or adding story chapters):

```sh
pip install markdown==3.7
python build_reader.py .. reader_template.html read-aloud.html
```

Then republish `read-aloud.html` to the same artifact URL.
