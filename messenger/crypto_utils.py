from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# symmetric key (32 bytes for AES-256)
AES_KEY = b'Kx9#mP2$vL8@nQ5!wR7&tY4^uI6*oE3%'

def encrypt_data(plaintext: str) -> str:
    """
    Encrypts plaintext using AES-256-CBC and returns base64-encoded ciphertext.
    """
    cipher = AES.new(AES_KEY, AES.MODE_CBC)
    iv = cipher.iv
    
    # Pad and encrypt
    padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    
    # Combine IV and ciphertext, then base64 encode
    encrypted = iv + ciphertext
    return base64.b64encode(encrypted).decode('ascii')

def decrypt_data(encrypted_b64: str) -> str:
    """
    Decrypts base64-encoded ciphertext using AES-256-CBC and returns plaintext.
    """
    try:
        # Decode from base64
        encrypted = base64.b64decode(encrypted_b64.encode('ascii'))
        
        # Extract IV and ciphertext
        iv = encrypted[:AES.block_size]
        ciphertext = encrypted[AES.block_size:]
        
        # Decrypt and unpad
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)
        plaintext = unpad(padded_plaintext, AES.block_size)
        
        return plaintext.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Decryption error: {e}")
