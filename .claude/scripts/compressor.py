ldef ultra_compress(text):
    replacements = {
        " and ": " & ",
        " to ": " → ",
        " at ": " @ ",
        " add ": " + ",
        " remove ": " - ",
        "configuration": "cfg",
        "function": "fn",
        "implementation": "impl",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


if __name__ == "__main__":
    print(ultra_compress("test and configuration"))  # Testable
