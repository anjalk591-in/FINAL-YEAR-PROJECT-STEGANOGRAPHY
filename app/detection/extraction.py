import numpy as np
import string
import base64
import binascii
import subprocess
import os
import tempfile
import re

class DataExtractor:
    """Extract hidden data from images"""
    
    def __init__(self, img_array):
        """
        Initialize with image array
        
        Args:
            img_array: numpy array of image (H, W, 3)
        """
        self.img = img_array
        self.results = {}
    
    def extract_all(self, image_path=None, limit=3000):
        """Try all extraction methods"""
        methods = {
            'red_lsb': self.extract_red_channel,
            'green_lsb': self.extract_green_channel,
            'blue_lsb': self.extract_blue_channel,
            'rgb_sequential': self.extract_rgb_sequential,
            'grayscale_lsb': self.extract_grayscale,
            'lsb_2bit': lambda l: self.extract_multi_bit(2, l),
            'reverse_order': self.extract_reverse_order,
            'lsbsteg_method': self.extract_lsbsteg_method,
            'green_channel_header': self.extract_green_channel_with_header,
            'pvd': lambda l: self.extract_pvd(image_path, l),
            'dct_coefficients': lambda l: self.extract_dct_coefficients(image_path, l),
            'dct_zigzag': lambda l: self.extract_dct_zigzag(image_path, l),
            'dct_ac_only': lambda l: self.extract_dct_ac_only(image_path, l),
        }
        
        # Try DCT extraction methods if image_path is provided (for JPEG)
        if image_path and image_path.lower().endswith(('.jpg', '.jpeg')):
            methods['dct_coefficients'] = lambda l: self.extract_dct_coefficients(image_path, l)
            methods['dct_zigzag'] = lambda l: self.extract_dct_zigzag(image_path, l)
            methods['dct_ac_only'] = lambda l: self.extract_dct_ac_only(image_path, l)
            methods['steghide'] = lambda l: self.extract_steghide(image_path)
        elif image_path:
            # For non-JPEG files, still try steghide
            methods['steghide'] = lambda l: self.extract_steghide(image_path)
        
        best_result = None
        best_score = 0
        all_results = []
        
        for method_name, method_func in methods.items():
            try:
                result = method_func(limit)
                result['method'] = method_name
                all_results.append(result)
                
                if result['readability'] > best_score:
                    best_score = result['readability']
                    best_result = result
            except Exception as e:
                print(f"Error in {method_name}: {e}")
                continue
        
        if best_result:
            # Try to decode as base64 if readability is low but data exists
            if best_score < 0.6 and best_result.get('text'):
                base64_result = self._try_base64_decode(best_result['text'])
                if base64_result and base64_result['readability'] > best_score:
                    best_result = base64_result
                    best_score = base64_result['readability']
            
            # IMPROVED: Only consider it "found" if readability is high enough
            # AND the text has reasonable characteristics
            is_valid = (
                best_score >= 0.65 and  # Increased threshold
                len(best_result.get('text', '')) >= 20 and  # Minimum length
                self._has_word_like_patterns(best_result.get('text', ''))  # Check for words
            )
            
            self.results = {
                **best_result,
                'found': is_valid,
                'all_methods': all_results
            }
        else:
            self.results = {
                'method': 'none',
                'readability': 0,
                'preview': '',
                'text': '',
                'found': False
            }
        
        self.results['score'] = 2 if self.results['found'] else 0
        
        return self.results
    
    def extract_red_channel(self, limit=3000):
        """Extract from red channel LSB"""
        bits = [str(p[0] & 1) for p in self.img.reshape(-1, 3)]
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_green_channel(self, limit=3000):
        """Extract from green channel LSB"""
        bits = [str(p[1] & 1) for p in self.img.reshape(-1, 3)]
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_blue_channel(self, limit=3000):
        """Extract from blue channel LSB"""
        bits = [str(p[2] & 1) for p in self.img.reshape(-1, 3)]
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_rgb_sequential(self, limit=3000):
        """Extract from RGB channels sequentially"""
        bits = []
        for pixel in self.img.reshape(-1, 3):
            for channel_value in pixel:
                bits.append(str(channel_value & 1))
        
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_grayscale(self, limit=3000):
        """Extract from grayscale conversion"""
        gray = np.mean(self.img, axis=2).astype(np.uint8)
        bits = [str(p & 1) for p in gray.flatten()]
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_reverse_order(self, limit=3000):
        """Extract from RGB in reverse order (BGR)"""
        bits = []
        for pixel in self.img.reshape(-1, 3):
            # Reverse: Blue, Green, Red
            for channel_value in [pixel[2], pixel[1], pixel[0]]:
                bits.append(str(channel_value & 1))
        
        text = self._bits_to_text(bits, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
        }
    
    def extract_pvd(self, image_path=None, limit=3000):
        print(">>> PVD EXTRACT FUNCTION CALLED <<<")
        import cv2

        if image_path is None:
            return {'text': '', 'preview': '', 'readability': 0}

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {'text': '', 'preview': '', 'readability': 0}

        # SAME ranges used in embedding
        PVD_RANGES = [
            (0, 7, 3),
            (8, 15, 3),
            (16, 31, 4),
            (32, 63, 5),
            (64, 127, 6)
        ]

        def get_range(diff):
            for low, high, bits in PVD_RANGES:
                if low <= diff <= high:
                    return low, bits
            return None, None

        bits = ""
        h, w = img.shape

        for i in range(h):
            for j in range(0, w - 1, 2):
                p1, p2 = int(img[i, j]), int(img[i, j + 1])
                diff = abs(p1 - p2)

                lower, n = get_range(diff)
                if n is None:
                    continue

                secret = diff - lower
                bits += format(secret, f'0{n}b')

        # Convert bits → text
        message = ""
        for k in range(0, len(bits), 8):
            byte = bits[k:k+8]
            if byte == "00000000":
             break
        message += chr(int(byte, 2))

        readability = 1.0

        return {
            'text': message,
            'preview': message[:200],
            'readability': 1.0
        }

    def extract_green_channel_with_header(self, limit=3000):
        """Extract from green channel LSB with 32-bit length header (dct_steg.py compatible)"""
        import struct
        
        bits = []
        for pixel in self.img.reshape(-1, 3):
            bits.append(pixel[1] & 1)
            
            # Check if we have header
            if len(bits) == 32:
                try:
                    header_bytes = []
                    for k in range(0, 32, 8):
                        byte_val = 0
                        for bit in bits[k:k+8]:
                            byte_val = (byte_val << 1) | bit
                        header_bytes.append(byte_val)
                    msg_len = struct.unpack('>I', bytes(header_bytes))[0]
                    if msg_len <= 0 or msg_len > 100000:
                        continue
                except:
                    continue
            
            # Check if we have complete message
            if len(bits) >= 32:
                try:
                    header_bytes = []
                    for k in range(0, 32, 8):
                        byte_val = 0
                        for bit in bits[k:k+8]:
                            byte_val = (byte_val << 1) | bit
                        header_bytes.append(byte_val)
                    msg_len = struct.unpack('>I', bytes(header_bytes))[0]
                    
                    if 0 < msg_len < 100000:
                        needed = 32 + (msg_len * 8)
                        if len(bits) >= needed:
                            # Extract message
                            msg_bits = bits[32:needed]
                            msg_bytes = []
                            for k in range(0, len(msg_bits), 8):
                                if k + 8 <= len(msg_bits):
                                    byte_val = 0
                                    for bit in msg_bits[k:k+8]:
                                        byte_val = (byte_val << 1) | bit
                                    msg_bytes.append(byte_val)
                            
                            try:
                                text = bytes(msg_bytes).decode('utf-8')
                                readability = self._calculate_readability(text)
                                return {
                                    'text': text,
                                    'preview': text[:200] if text else '',
                                    'readability': readability,
                                }
                            except:
                                pass
                except:
                    pass
        
        # Fallback: no valid header found
        return {
            'text': '',
            'preview': '',
            'readability': 0,
        }
    
    def _bits_to_text(self, bits, limit=3000):
        """Convert bit array to text with improved validation"""
        text = ""
        consecutive_invalid = 0
        max_consecutive_invalid = 5  # Stop after 5 consecutive invalid chars
        
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            
            if len(byte) < 8:
                break
            
            try:
                char_value = int(''.join(byte), 2)
                
                # Only printable ASCII and common whitespace
                if 32 <= char_value <= 126:
                    text += chr(char_value)
                    consecutive_invalid = 0
                elif char_value in [10, 13]:  # newline, carriage return
                    text += '\n'
                    consecutive_invalid = 0
                elif char_value == 9:  # tab
                    text += '\t'
                    consecutive_invalid = 0
                else:
                    # Invalid character
                    consecutive_invalid += 1
                    if consecutive_invalid >= max_consecutive_invalid:
                        break
                
                if len(text) >= limit:
                    break
            except:
                break
        
        return text.strip()
    
    def _calculate_readability(self, text):
        """Calculate readability score (0-1) with stricter requirements"""
        if not text or len(text) < 20:
            return 0.0
        
        # Count different types of characters
        alphanumeric = sum(c.isalnum() for c in text)
        spaces = sum(c == ' ' for c in text)
        punctuation = sum(c in '.,!?;:\n-_()[]{}"\'' for c in text)
        total = len(text)
        
        alpha_ratio = alphanumeric / total
        space_ratio = spaces / total
        punct_ratio = punctuation / total
        
        # Calculate score with stricter requirements
        score = 0.0
        
        # Alphanumeric should be dominant (60-90%)
        if 0.6 <= alpha_ratio <= 0.9:
            score += 0.5
        elif alpha_ratio > 0.5:
            score += 0.2
        
        # Spaces should exist in reasonable amounts (5-25%)
        if 0.08 < space_ratio < 0.25:
            score += 0.3
        elif 0.05 < space_ratio < 0.3:
            score += 0.15
        
        # Some punctuation is good (but not too much)
        if 0.01 < punct_ratio < 0.15:
            score += 0.2
        elif punct_ratio > 0:
            score += 0.05
        
        # Penalize if text is too repetitive
        if self._is_too_repetitive(text):
            score *= 0.5
        
        return min(score, 1.0)
    
    def _is_too_repetitive(self, text):
        """Check if text has too many repeated characters/patterns"""
        if len(text) < 20:
            return False
        
        # Check for excessive character repetition
        for i in range(len(text) - 3):
            substring = text[i:i+3]
            if text.count(substring) > len(text) / 10:  # If a 3-char pattern repeats too much
                return True
        
        # Check for single character repetition
        max_char_ratio = max(text.count(c) / len(text) for c in set(text))
        if max_char_ratio > 0.3:  # If any single char is >30% of text
            return True
        
        return False
    
    def _has_word_like_patterns(self, text):
        """Check if text contains word-like patterns"""
        if not text or len(text) < 10:
            return False
        
        # Look for sequences of letters that resemble words
        words = re.findall(r'[a-zA-Z]{3,}', text)
        
        # Should have at least a few word-like sequences
        if len(words) < 3:
            return False
        
        # Check if we have reasonable word lengths (3-15 chars)
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        if not (3 <= avg_word_len <= 15):
            return False
        
        return True
    
    def extract_multi_bit(self, bits=2, limit=1000):
        """Extract using multiple LSBs"""
        pixels = self.img.reshape(-1, 3)
        bit_array = []
        
        for pixel in pixels:
            for channel_value in pixel:
                # Extract N LSBs
                for bit_pos in range(bits):
                    bit_array.append(str((channel_value >> bit_pos) & 1))
        
        text = self._bits_to_text(bit_array, limit)
        readability = self._calculate_readability(text)
        
        return {
            'text': text,
            'preview': text[:200] if text else '',
            'readability': readability,
            'bits_used': bits
        }
    
    def extract_lsbsteg_method(self, limit=3000):
        """Extract using LSBSteg algorithm (length-prefixed binary)"""
        try:
            # Read 16-bit length prefix
            bits = []
            for pixel in self.img.reshape(-1, 3):
                for channel_value in pixel:
                    bits.append(str(channel_value & 1))
                    if len(bits) >= 16:
                        break
                if len(bits) >= 16:
                    break
            
            if len(bits) < 16:
                return {'text': '', 'preview': '', 'readability': 0}
            
            # Get text length
            length_bits = ''.join(bits[:16])
            text_length = int(length_bits, 2)
            
            # Sanity check
            if text_length > 65536 or text_length == 0:
                return {'text': '', 'preview': '', 'readability': 0}
            
            # Extract the text
            bits = []
            bit_count = 0
            for pixel in self.img.reshape(-1, 3):
                for channel_value in pixel:
                    bits.append(str(channel_value & 1))
                    bit_count += 1
                    if bit_count >= 16 + (text_length * 8):
                        break
                if bit_count >= 16 + (text_length * 8):
                    break
            
            # Skip the 16-bit length prefix
            text_bits = bits[16:16 + (text_length * 8)]
            
            # Convert to text
            text = ""
            for i in range(0, len(text_bits), 8):
                byte = text_bits[i:i+8]
                if len(byte) == 8:
                    char_value = int(''.join(byte), 2)
                    if 32 <= char_value <= 126:
                        text += chr(char_value)
                    elif char_value in [10, 13, 9]:
                        text += chr(char_value)
            
            readability = self._calculate_readability(text)
            
            return {
                'text': text,
                'preview': text[:200] if text else '',
                'readability': readability,
            }
        except Exception as e:
            print(f"LSBSteg extraction error: {e}")
            return {'text': '', 'preview': '', 'readability': 0}
    
    def extract_steghide(self, image_path):
        """Extract using steghide tool (common passwords)"""
        common_passwords = [
            '', # No password
            'password', 'secret', '123456', 'steghide', 
            'hidden', 'admin', 'test', '12345', 'pass'
        ]
        
        try:
            # Check if steghide is installed
            result = subprocess.run(['steghide', '--version'], 
                                  capture_output=True, 
                                  timeout=2)
            
            if result.returncode != 0:
                return {
                    'text': '[steghide not installed]',
                    'preview': 'Install steghide to use this method',
                    'readability': 0
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {
                'text': '[steghide not available]',
                'preview': 'Steghide tool not found on system',
                'readability': 0
            }
        
        # Try each password
        for password in common_passwords:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
                    tmp_output = tmp.name
                
                cmd = ['steghide', 'extract', '-sf', image_path, 
                       '-xf', tmp_output, '-f']
                
                if password:
                    cmd.extend(['-p', password])
                else:
                    cmd.extend(['-p', ''])
                
                result = subprocess.run(cmd, 
                                      capture_output=True, 
                                      timeout=10,
                                      text=True)
                
                if result.returncode == 0 and os.path.exists(tmp_output):
                    # Read extracted data
                    with open(tmp_output, 'rb') as f:
                        data = f.read()
                    
                    # Try to decode as text
                    try:
                        text = data.decode('utf-8', errors='ignore')
                        readability = self._calculate_readability(text)
                        
                        # Clean up
                        os.unlink(tmp_output)
                        
                        if readability > 0.3:
                            return {
                                'text': text,
                                'preview': text[:200],
                                'readability': readability,
                                'password': password or '[none]'
                            }
                    except:
                        pass
                    
                    # Clean up
                    if os.path.exists(tmp_output):
                        os.unlink(tmp_output)
            
            except (subprocess.TimeoutExpired, Exception) as e:
                if 'tmp_output' in locals() and os.path.exists(tmp_output):
                    os.unlink(tmp_output)
                continue
        
        return {
            'text': '',
            'preview': 'No data extracted with common passwords',
            'readability': 0
        }
    
    def _try_base64_decode(self, text):
        """Try to decode text as base64"""
        try:
            # Remove whitespace
            clean_text = ''.join(text.split())
            
            # Try to decode
            decoded = base64.b64decode(clean_text, validate=True)
            decoded_text = decoded.decode('utf-8', errors='ignore')
            
            readability = self._calculate_readability(decoded_text)
            
            if readability > 0.6:  # Higher threshold
                return {
                    'text': decoded_text,
                    'preview': decoded_text[:200],
                    'readability': readability,
                    'method': 'base64_decoded'
                }
        except:
            pass
        
        return None
    
    def _get_zigzag_order(self):
        """Get zigzag order for 8x8 DCT blocks (JPEG standard)"""
        return [
            (0,0), (0,1), (1,0), (2,0), (1,1), (0,2), (0,3), (1,2),
            (2,1), (3,0), (4,0), (3,1), (2,2), (1,3), (0,4), (0,5),
            (1,4), (2,3), (3,2), (4,1), (5,0), (6,0), (5,1), (4,2),
            (3,3), (2,4), (1,5), (0,6), (0,7), (1,6), (2,5), (3,4),
            (4,3), (5,2), (6,1), (7,0), (7,1), (6,2), (5,3), (4,4),
            (3,5), (2,6), (1,7), (2,7), (3,6), (4,5), (5,4), (6,3),
            (7,2), (7,3), (6,4), (5,5), (4,6), (3,7), (4,7), (5,6),
            (6,5), (7,4), (7,5), (6,6), (5,7), (6,7), (7,6), (7,7)
        ]
    
    def extract_dct_coefficients(self, image_path, limit=3000):
        """Extract from DCT coefficients (for JPEG steganography like JSteg, F5, OutGuess) - handles dct_stego.py format"""
        try:
            import cv2
            import struct
            
            # Check if it's a JPEG file
            if not image_path.lower().endswith(('.jpg', '.jpeg')):
                return {
                    'text': '', 
                    'preview': 'Not a JPEG file', 
                    'readability': 0
                }
            
            # Read image with OpenCV
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return {
                    'text': '', 
                    'preview': 'Could not read image', 
                    'readability': 0
                }
            
            # Divide into 8x8 blocks and apply DCT
            h, w = img.shape
            h = (h // 8) * 8
            w = (w // 8) * 8
            img = img[:h, :w]
            
            bits = []
            
            # Process each 8x8 block
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    block = img[i:i+8, j:j+8].astype(np.float32)
                    
                    # Apply DCT
                    dct_block = cv2.dct(block)
                    
                    # Extract LSB from non-zero AC coefficients
                    # Skip DC coefficient (0,0) and focus on AC coefficients
                    for x in range(8):
                        for y in range(8):
                            if x == 0 and y == 0:  # Skip DC coefficient
                                continue
                            
                            coeff = int(round(dct_block[x, y]))
                            
                            # Only use non-zero coefficients with abs > 1
                            if abs(coeff) > 1:
                                # Extract LSB
                                bits.append(abs(coeff) & 1)
                            
                            if len(bits) >= 32 + (limit * 8):
                                break
                        if len(bits) >= 32 + (limit * 8):
                            break
                    if len(bits) >= 32 + (limit * 8):
                        break
                if len(bits) >= 32 + (limit * 8):
                    break
            
            # Try to extract with length prefix (dct_stego.py format)
            if len(bits) >= 32:
                # Extract 32-bit length header
                length_bytes = []
                for i in range(0, 32, 8):
                    byte_val = 0
                    for bit in bits[i:i+8]:
                        byte_val = (byte_val << 1) | bit
                    length_bytes.append(byte_val)
                
                try:
                    message_length = struct.unpack('>I', bytes(length_bytes))[0]
                    
                    # Sanity check
                    if 0 < message_length < 100000 and len(bits) >= 32 + (message_length * 8):
                        # Extract message
                        message_bits = bits[32:32 + (message_length * 8)]
                        message_bytes = []
                        for i in range(0, len(message_bits), 8):
                            if i + 8 <= len(message_bits):
                                byte_val = 0
                                for bit in message_bits[i:i+8]:
                                    byte_val = (byte_val << 1) | bit
                                message_bytes.append(byte_val)
                        
                        text = bytes(message_bytes).decode('utf-8', errors='ignore')
                        readability = self._calculate_readability(text)
                        
                        if readability > 0.5:  # Good extraction
                            return {
                                'text': text,
                                'preview': text[:200] if text else '',
                                'readability': readability,
                                'method_details': 'DCT coefficients (dct_stego.py compatible)'
                            }
                except:
                    pass
            
            # Fallback to standard extraction
            text = self._bits_to_text([str(b) for b in bits], limit)
            readability = self._calculate_readability(text)
            
            return {
                'text': text,
                'preview': text[:200] if text else '',
                'readability': readability,
                'method_details': 'DCT coefficient extraction'
            }
            
        except ImportError:
            return {
                'text': '',
                'preview': 'OpenCV required for DCT extraction',
                'readability': 0
            }
        except Exception as e:
            print(f"DCT extraction error: {e}")
            return {
                'text': '', 
                'preview': '', 
                'readability': 0
            }
    
    def extract_dct_zigzag(self, image_path, limit=3000):
        """Extract using zigzag order (better for JSteg detection) - handles dct_stego.py format"""
        try:
            import cv2
            import struct
            
            if not image_path.lower().endswith(('.jpg', '.jpeg')):
                return {
                    'text': '', 
                    'preview': 'Not a JPEG file', 
                    'readability': 0
                }
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return {
                    'text': '', 
                    'preview': 'Could not read image', 
                    'readability': 0
                }
            
            h, w = img.shape
            h = (h // 8) * 8
            w = (w // 8) * 8
            img = img[:h, :w]
            
            zigzag_order = self._get_zigzag_order()
            bits = []
            
            # Process each 8x8 block in zigzag order
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    block = img[i:i+8, j:j+8].astype(np.float32)
                    dct_block = cv2.dct(block)
                    
                    # Extract in zigzag order (skip DC coefficient)
                    for idx, (x, y) in enumerate(zigzag_order):
                        if idx < 1:  # Skip DC
                            continue
                        
                        coeff = int(round(dct_block[x, y]))
                        
                        # JSteg: only non-zero, non-one coefficients
                        if abs(coeff) > 1:
                            bits.append(abs(coeff) & 1)
                        
                        # Get enough bits to check for length header
                        if len(bits) >= 32 + (limit * 8):
                            break
                    
                    if len(bits) >= 32 + (limit * 8):
                        break
                if len(bits) >= 32 + (limit * 8):
                    break
            
            # Try to extract with length prefix (dct_stego.py format)
            if len(bits) >= 32:
                # Extract 32-bit length header
                length_bytes = []
                for i in range(0, 32, 8):
                    byte_val = 0
                    for bit in bits[i:i+8]:
                        byte_val = (byte_val << 1) | bit
                    length_bytes.append(byte_val)
                
                try:
                    message_length = struct.unpack('>I', bytes(length_bytes))[0]
                    
                    # Sanity check
                    if 0 < message_length < 100000 and len(bits) >= 32 + (message_length * 8):
                        # Extract message
                        message_bits = bits[32:32 + (message_length * 8)]
                        message_bytes = []
                        for i in range(0, len(message_bits), 8):
                            if i + 8 <= len(message_bits):
                                byte_val = 0
                                for bit in message_bits[i:i+8]:
                                    byte_val = (byte_val << 1) | bit
                                message_bytes.append(byte_val)
                        
                        text = bytes(message_bytes).decode('utf-8', errors='ignore')
                        readability = self._calculate_readability(text)
                        
                        if readability > 0.5:  # Good extraction
                            return {
                                'text': text,
                                'preview': text[:200] if text else '',
                                'readability': readability,
                                'method_details': 'DCT Zigzag (dct_stego.py compatible)'
                            }
                except:
                    pass
            
            # Fallback to standard extraction (no length prefix)
            text = self._bits_to_text([str(b) for b in bits], limit)
            readability = self._calculate_readability(text)
            
            return {
                'text': text,
                'preview': text[:200] if text else '',
                'readability': readability,
                'method_details': 'DCT Zigzag (JSteg-compatible)'
            }
            
        except Exception as e:
            print(f"DCT zigzag extraction error: {e}")
            return {
                'text': '', 
                'preview': '', 
                'readability': 0
            }
    
    def extract_dct_ac_only(self, image_path, limit=3000):
        """Extract from AC coefficients only (F5 compatible) - handles dct_stego.py format"""
        try:
            import cv2
            import struct
            
            if not image_path.lower().endswith(('.jpg', '.jpeg')):
                return {
                    'text': '', 
                    'preview': 'Not a JPEG file', 
                    'readability': 0
                }
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return {
                    'text': '', 
                    'preview': 'Could not read image', 
                    'readability': 0
                }
            
            h, w = img.shape
            h = (h // 8) * 8
            w = (w // 8) * 8
            img = img[:h, :w]
            
            bits = []
            
            # Process each 8x8 block
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    block = img[i:i+8, j:j+8].astype(np.float32)
                    dct_block = cv2.dct(block)
                    
                    # Extract from AC coefficients (skip DC at 0,0)
                    for x in range(8):
                        for y in range(8):
                            if x == 0 and y == 0:
                                continue
                            
                            coeff = int(round(dct_block[x, y]))
                            
                            # F5 uses all non-zero AC coefficients
                            if coeff != 0:
                                bits.append(abs(coeff) & 1)
                            
                            if len(bits) >= 32 + (limit * 8):
                                break
                        if len(bits) >= 32 + (limit * 8):
                            break
                    if len(bits) >= 32 + (limit * 8):
                        break
                if len(bits) >= 32 + (limit * 8):
                    break
            
            # Try to extract with length prefix (dct_stego.py format)
            if len(bits) >= 32:
                # Extract 32-bit length header
                length_bytes = []
                for i in range(0, 32, 8):
                    byte_val = 0
                    for bit in bits[i:i+8]:
                        byte_val = (byte_val << 1) | bit
                    length_bytes.append(byte_val)
                
                try:
                    message_length = struct.unpack('>I', bytes(length_bytes))[0]
                    
                    # Sanity check
                    if 0 < message_length < 100000 and len(bits) >= 32 + (message_length * 8):
                        # Extract message
                        message_bits = bits[32:32 + (message_length * 8)]
                        message_bytes = []
                        for i in range(0, len(message_bits), 8):
                            if i + 8 <= len(message_bits):
                                byte_val = 0
                                for bit in message_bits[i:i+8]:
                                    byte_val = (byte_val << 1) | bit
                                message_bytes.append(byte_val)
                        
                        text = bytes(message_bytes).decode('utf-8', errors='ignore')
                        readability = self._calculate_readability(text)
                        
                        if readability > 0.5:  # Good extraction
                            return {
                                'text': text,
                                'preview': text[:200] if text else '',
                                'readability': readability,
                                'method_details': 'DCT AC Only (dct_stego.py F5 compatible)'
                            }
                except:
                    pass
            
            # Fallback to standard extraction
            text = self._bits_to_text([str(b) for b in bits], limit)
            readability = self._calculate_readability(text)
            
            return {
                'text': text,
                'preview': text[:200] if text else '',
                'readability': readability,
                'method_details': 'DCT AC coefficients (F5-compatible)'
            }
            
        except Exception as e:
            print(f"DCT AC extraction error: {e}")
            return {
                'text': '', 
                'preview': '', 
                'readability': 0
            }
    import cv2
import numpy as np
import struct


def embed_dct_message(input_image, output_image, message):

    img = cv2.imread(input_image, cv2.IMREAD_GRAYSCALE).astype(np.float32)

    h, w = img.shape
    h = (h // 8) * 8
    w = (w // 8) * 8
    img = img[:h, :w]

    # Prepare payload
    msg_bytes = message.encode("utf-8")
    payload = struct.pack(">I", len(msg_bytes)) + msg_bytes

    bits = []
    for b in payload:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    bit_index = 0

    for i in range(0, h, 8):
        for j in range(0, w, 8):

            if bit_index >= len(bits):
                break

            block = img[i:i+8, j:j+8]

            for x in range(8):
                for y in range(8):

                    if x == 0 and y == 0:
                        continue

                    if bit_index >= len(bits):
                        break

                    target_bit = bits[bit_index]

                    success = False

                    # Try small pixel perturbations
                    for attempt in range(50):

                        test_block = block.copy()

                        px = np.random.randint(0,8)
                        py = np.random.randint(0,8)

                        change = np.random.choice([-1,1])

                        test_block[px,py] = np.clip(test_block[px,py] + change, 0, 255)

                        dct = cv2.dct(test_block)

                        coeff = int(round(dct[x,y]))

                        if abs(coeff) > 1 and (abs(coeff) & 1) == target_bit:

                            block[:] = test_block
                            success = True
                            break

                    if success:
                        bit_index += 1

                if bit_index >= len(bits):
                    break

        if bit_index >= len(bits):
            break

    stego = np.clip(img, 0, 255).astype(np.uint8)

    cv2.imwrite(output_image, stego)

    print("Embedded bits:", bit_index)
    print("Output saved to:", output_image)