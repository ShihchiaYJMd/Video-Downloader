# 🎥 Institutional Media Archiver

A specialized, headless video downloader for **a specific university's** media platform.

> **⚠️ Privacy Protocol:**
> To prevent automated indexing, the target institution's name is **encrypted**. You must possess the correct key to unlock the tool.

## 🔐 The Challenge

Which university is this for? The target configuration is locked behind an **AES-128** cipher, protected by a custom **31-bit Perfect Hash** mechanism.

To reveal the target (and use the script), you need to figure out the **Magic Passphrase** and run the decoder below.

### 🧩 The Hint

The passphrase is a 6-character string constructed as follows:

1.  **Part 1**: The standard 3-letter prefix meaning "three" (e.g., triangle).
2.  **Part 2**: The letter representing the vertical coordinate axis (Capitalized).
3.  **Part 3**: The same letter as Part 2, repeated twice, but in lowercase.

*(Combine them to get the passphrase)*

### 🔓 The Decoder Script

Copy the code below. Run it locally. Enter your guess based on the hint above.

**Prerequisites:**
```bash
pip install cryptography
