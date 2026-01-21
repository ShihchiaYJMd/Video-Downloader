import hashlib, base64, struct, getpass
from cryptography.fernet import Fernet

# The Encrypted Secret (Do not modify)
CIPHERTEXT = b'gAAAAABpcEMbSxOJC8T5DWIln04durjghWrYr8Ztu0ZwixNN0-2GG8865pfex15gFkIqLxAXgQ2QXBR00gHLbvUy2HMO_tYiow=='

def solve():
    print("--- 🔐 Secure Archiver Config Decoder ---")
    # You must guess the key based on the hint in README
    guess = input("Enter the Magic Passphrase: ").strip()
    
    # 1. Logic: 31-bit Perfect Hash (Java/CS Style)
    h = 0
    for c in guess:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    h = h & 0x7FFFFFFF # Mask to 31-bit positive integer
    
    # 2. Logic: Key Derivation (Hash -> SHA256 -> AES Key)
    # If your guess is wrong, this key will be wrong.
    key_bytes = hashlib.sha256(struct.pack(">I", h)).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    
    # 3. Attempt Decryption
    try:
        f = Fernet(fernet_key)
        # If decryption fails (wrong padding/signature), it throws an error
        secret = f.decrypt(CIPHERTEXT).decode()
        
        print("\n" + "="*40)
        print(f"✅ ACCESS GRANTED!")
        print(f"Target Institution: [{secret}]")
        print("="*40 + "\n")
        print("You may now use the downloader script.")
        
    except Exception:
        print("\n❌ ACCESS DENIED.")
        print("Wrong passphrase. The hash signature does not match.")

if __name__ == "__main__":
    solve()
