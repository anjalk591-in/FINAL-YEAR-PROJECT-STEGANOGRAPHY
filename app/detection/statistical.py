import numpy as np
from scipy.stats import chisquare
import math

class StatisticalAnalyzer:
    """Statistical steganography detection methods"""
    
    def __init__(self, img_array):
        """
        Initialize with image array
        
        Args:
            img_array: numpy array of image (H, W, 3)
        """
        self.img = img_array
        self.results = {}
    
    def analyze_all(self):
        """Run all statistical tests"""
        self.lsb_distribution()
        self.chi_square_test()
        self.entropy_analysis()
        self.histogram_attack()
        self.rs_analysis()
        self.sample_pair_analysis()
        
        return self.results
    
    def lsb_distribution(self):
        """Analyze LSB bit distribution"""
        lsb = self.img & 1
        zeros = np.sum(lsb == 0)
        ones = np.sum(lsb == 1)
        total = zeros + ones
        ratio = ones / total if total > 0 else 0.5
        
        # Deviation from expected 0.5
        deviation = abs(ratio - 0.5)
        
        # IMPROVED: Too perfect is suspicious, but so is too unbalanced
        # Natural images typically have slight imbalance (0.48-0.52)
        # Perfect balance (0.495-0.505) suggests LSB embedding
        # Very unbalanced suggests no embedding
        
        is_too_perfect = 0.495 < ratio < 0.505
        is_reasonably_balanced = 0.48 < ratio < 0.52
        
        # Suspicious if TOO perfect (indicates artificial randomness from stego)
        suspicious = is_too_perfect
        
        self.results['lsb_distribution'] = {
            'zeros': int(zeros),
            'ones': int(ones),
            'ratio': float(ratio),
            'deviation': float(deviation),
            'suspicious': suspicious,
            'score': 1 if suspicious else 0,
            'confidence': 0.7 if is_too_perfect else 0.3  # Add confidence metric
        }
        
        return self.results['lsb_distribution']
    
    def chi_square_test(self):
        """Chi-square test for PoV (Pairs of Values)"""
        # Convert to grayscale
        gray = np.mean(self.img, axis=2).astype(np.uint8)
        pixels = gray.flatten()
        
        # Count even and odd values
        even = np.sum(pixels % 2 == 0)
        odd = np.sum(pixels % 2 == 1)
        
        observed = [even, odd]
        expected = [(even + odd) / 2, (even + odd) / 2]
        
        chi, p = chisquare(observed, expected)
        
        # IMPROVED: Very low p-value indicates non-random (suspicious)
        # But we should be more nuanced
        very_suspicious = p < 0.01
        somewhat_suspicious = p < 0.05
        
        suspicious = very_suspicious
        
        self.results['chi_square'] = {
            'chi_statistic': float(chi),
            'p_value': float(p),
            'even_pixels': int(even),
            'odd_pixels': int(odd),
            'suspicious': suspicious,
            'score': 2 if very_suspicious else (1 if somewhat_suspicious else 0),
            'confidence': 0.8 if very_suspicious else (0.5 if somewhat_suspicious else 0.2)
        }
        
        return self.results['chi_square']
    
    def entropy_analysis(self):
        """Calculate Shannon entropy"""
        entropies = []
        
        for channel in range(3):
            channel_data = self.img[:, :, channel].flatten()
            hist = np.histogram(channel_data, bins=256, range=(0, 256))[0]
            hist = hist / np.sum(hist)
            
            # Shannon entropy
            ent = -np.sum([p * math.log2(p) for p in hist if p != 0])
            entropies.append(ent)
        
        avg_entropy = np.mean(entropies)
        
        # IMPROVED: High entropy can indicate stego, but natural photos also have high entropy
        # Very high entropy (>7.8) is more suspicious
        # Moderate-high entropy (7.5-7.8) is somewhat suspicious
        very_high = avg_entropy > 7.8
        moderately_high = avg_entropy > 7.5
        
        suspicious = very_high
        
        self.results['entropy'] = {
            'red_entropy': float(entropies[0]),
            'green_entropy': float(entropies[1]),
            'blue_entropy': float(entropies[2]),
            'average_entropy': float(avg_entropy),
            'suspicious': suspicious,
            'score': 2 if very_high else (1 if moderately_high else 0),
            'confidence': 0.6 if very_high else (0.4 if moderately_high else 0.2)
        }
        
        return self.results['entropy']
    
    def histogram_attack(self):
        """Histogram analysis for LSB embedding detection"""
        # Analyze histogram pairs (values differing by 1)
        correlations = []
        
        for channel in range(3):
            channel_data = self.img[:, :, channel].flatten()
            hist = np.histogram(channel_data, bins=256, range=(0, 256))[0]
            
            # Check correlation between adjacent histogram bins
            pair_correlations = []
            for i in range(0, 255, 2):
                if hist[i] + hist[i+1] > 0:
                    correlation = abs(hist[i] - hist[i+1]) / (hist[i] + hist[i+1])
                    pair_correlations.append(correlation)
            
            if pair_correlations:
                correlations.append(np.mean(pair_correlations))
        
        avg_correlation = np.mean(correlations) if correlations else 0
        
        # IMPROVED: Very low correlation indicates potential LSB embedding
        very_low = avg_correlation < 0.2
        somewhat_low = avg_correlation < 0.35
        
        suspicious = very_low
        
        self.results['histogram'] = {
            'average_pair_correlation': float(avg_correlation),
            'suspicious': suspicious,
            'score': 2 if very_low else (1 if somewhat_low else 0),
            'confidence': 0.7 if very_low else (0.4 if somewhat_low else 0.2)
        }
        
        return self.results['histogram']
    
    def rs_analysis(self):
        """RS (Regular-Singular) Analysis - simplified version"""
        # Simplified RS analysis on grayscale
        gray = np.mean(self.img, axis=2).astype(np.uint8)
        h, w = gray.shape
        
        # Use 3x3 blocks
        block_size = 3
        blocks_h = h // block_size
        blocks_w = w // block_size
        
        regular_m = 0
        singular_m = 0
        regular_neg_m = 0
        singular_neg_m = 0
        
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = gray[i*block_size:(i+1)*block_size, 
                           j*block_size:(j+1)*block_size]
                
                # Discrimination function
                d = self._discrimination_function(block)
                
                # Positive flipping
                block_flipped = block.copy()
                block_flipped = (block_flipped & 0xFE) | (~block_flipped & 0x01)
                d_flipped = self._discrimination_function(block_flipped)
                
                if d > d_flipped:
                    regular_m += 1
                else:
                    singular_m += 1
                
                # Negative flipping
                block_neg = block.copy()
                block_neg = (block_neg & 0xFE) | ((~block_neg & 0x01) ^ 0x01)
                d_neg = self._discrimination_function(block_neg)
                
                if d > d_neg:
                    regular_neg_m += 1
                else:
                    singular_neg_m += 1
        
        total = blocks_h * blocks_w
        if total > 0:
            rm = regular_m / total
            sm = singular_m / total
            r_neg_m = regular_neg_m / total
            s_neg_m = singular_neg_m / total
            
            # RS difference
            rs_diff = abs(rm - r_neg_m) + abs(sm - s_neg_m)
            
            # IMPROVED: Higher thresholds for different confidence levels
            very_suspicious = rs_diff > 0.08
            somewhat_suspicious = rs_diff > 0.05
            
            suspicious = very_suspicious
        else:
            rm = sm = r_neg_m = s_neg_m = rs_diff = 0
            very_suspicious = somewhat_suspicious = suspicious = False
        
        self.results['rs_analysis'] = {
            'regular_ratio': float(rm),
            'singular_ratio': float(sm),
            'rs_difference': float(rs_diff),
            'suspicious': suspicious,
            'score': 3 if very_suspicious else (2 if somewhat_suspicious else 0),  # RS is strong indicator
            'confidence': 0.85 if very_suspicious else (0.6 if somewhat_suspicious else 0.2)
        }
        
        return self.results['rs_analysis']
    
    def _discrimination_function(self, block):
        """Calculate discrimination function for RS analysis"""
        # Sum of absolute differences between adjacent pixels
        diff_sum = 0
        h, w = block.shape
        
        for i in range(h):
            for j in range(w-1):
                diff_sum += abs(int(block[i, j]) - int(block[i, j+1]))
        
        for i in range(h-1):
            for j in range(w):
                diff_sum += abs(int(block[i, j]) - int(block[i+1, j]))
        
        return diff_sum
    
    def sample_pair_analysis(self):
        """Sample Pair Analysis (SPA) - simplified"""
        gray = np.mean(self.img, axis=2).astype(np.uint8)
        pixels = gray.flatten()
        
        # Count sample pairs
        pairs = []
        for i in range(0, len(pixels)-1, 2):
            pairs.append((pixels[i], pixels[i+1]))
        
        # Analyze LSB of pairs
        u = 0  # Both LSBs are 0
        v = 0  # LSBs differ
        w = 0  # Both LSBs are 1
        
        for p1, p2 in pairs:
            lsb1 = p1 & 1
            lsb2 = p2 & 1
            
            if lsb1 == 0 and lsb2 == 0:
                u += 1
            elif lsb1 != lsb2:
                v += 1
            else:  # both 1
                w += 1
        
        total = len(pairs)
        if total > 0:
            # Estimate embedding rate
            if v > 0:
                embedding_rate = abs(2 * (u - w) / v) if v != 0 else 0
            else:
                embedding_rate = 0
            
            # IMPROVED: Different thresholds for confidence
            very_high_rate = embedding_rate > 0.15
            high_rate = embedding_rate > 0.1
            moderate_rate = embedding_rate > 0.05
            
            suspicious = very_high_rate or high_rate
        else:
            embedding_rate = 0
            very_high_rate = high_rate = moderate_rate = suspicious = False
        
        self.results['spa'] = {
            'u_count': int(u),
            'v_count': int(v),
            'w_count': int(w),
            'estimated_embedding_rate': float(min(embedding_rate, 1.0)),
            'suspicious': suspicious,
            'score': 3 if very_high_rate else (2 if high_rate else (1 if moderate_rate else 0)),
            'confidence': 0.9 if very_high_rate else (0.7 if high_rate else (0.4 if moderate_rate else 0.2))
        }
        
        return self.results['spa']    
    def dct_coefficient_analysis(self, image_path=None):
        """
        Analyze DCT coefficients for JPEG steganography detection
        Works for JSteg, F5, OutGuess, and similar techniques
        """
        if image_path is None:
            # Can't analyze DCT without the actual JPEG file
            self.results['dct_analysis'] = {
                'error': 'JPEG file path required for DCT analysis',
                'suspicious': False,
                'score': 0,
                'confidence': 0
            }
            return self.results['dct_analysis']
        
        if not image_path.lower().endswith(('.jpg', '.jpeg')):
            self.results['dct_analysis'] = {
                'error': 'Not a JPEG file',
                'suspicious': False,
                'score': 0,
                'confidence': 0
            }
            return self.results['dct_analysis']
        
        try:
            import cv2
            
            # Read grayscale image
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise ValueError("Could not read image")
            
            h, w = img.shape
            h = (h // 8) * 8
            w = (w // 8) * 8
            img = img[:h, :w]
            
            # Collect DCT coefficients
            all_coeffs = []
            zero_coeffs = 0
            one_coeffs = 0
            total_coeffs = 0
            
            # Process 8x8 blocks
            for i in range(0, h, 8):
                for j in range(0, w, 8):
                    block = img[i:i+8, j:j+8].astype(np.float32)
                    dct_block = cv2.dct(block)
                    
                    # Analyze AC coefficients (skip DC at 0,0)
                    for x in range(8):
                        for y in range(8):
                            if x == 0 and y == 0:
                                continue
                            
                            coeff = int(round(dct_block[x, y]))
                            all_coeffs.append(abs(coeff))
                            total_coeffs += 1
                            
                            if coeff == 0:
                                zero_coeffs += 1
                            elif abs(coeff) == 1:
                                one_coeffs += 1
            
            # Statistical analysis
            all_coeffs = np.array(all_coeffs)
            
            # 1. Check coefficient histogram (JSteg detection)
            hist_analysis = self._analyze_dct_histogram(all_coeffs)
            
            # 2. Check LSB distribution in DCT coefficients
            lsb_analysis = self._analyze_dct_lsb(all_coeffs)
            
            # 3. Blockiness analysis (F5 detection)
            blockiness = self._analyze_blockiness(img)
            
            # Determine if suspicious
            suspicious_indicators = 0
            if hist_analysis['suspicious']:
                suspicious_indicators += 1
            if lsb_analysis['suspicious']:
                suspicious_indicators += 1
            if blockiness['suspicious']:
                suspicious_indicators += 1
            
            suspicious = suspicious_indicators >= 2
            very_suspicious = suspicious_indicators >= 3
            
            # Calculate confidence
            confidence = 0
            if very_suspicious:
                confidence = 0.85
            elif suspicious:
                confidence = 0.65
            else:
                confidence = 0.3
            
            self.results['dct_analysis'] = {
                'total_coefficients': total_coeffs,
                'zero_coefficients': zero_coeffs,
                'one_coefficients': one_coeffs,
                'zero_ratio': float(zero_coeffs / total_coeffs) if total_coeffs > 0 else 0,
                'histogram_analysis': hist_analysis,
                'lsb_analysis': lsb_analysis,
                'blockiness_analysis': blockiness,
                'suspicious_indicators': suspicious_indicators,
                'suspicious': suspicious,
                'score': 3 if very_suspicious else (2 if suspicious else 0),
                'confidence': confidence
            }
            
            return self.results['dct_analysis']
            
        except ImportError:
            self.results['dct_analysis'] = {
                'error': 'OpenCV required for DCT analysis',
                'suspicious': False,
                'score': 0,
                'confidence': 0
            }
            return self.results['dct_analysis']
        except Exception as e:
            self.results['dct_analysis'] = {
                'error': str(e),
                'suspicious': False,
                'score': 0,
                'confidence': 0
            }
            return self.results['dct_analysis']
    
    def _analyze_dct_histogram(self, coeffs):
        """Analyze DCT coefficient histogram for anomalies"""
        if len(coeffs) == 0:
            return {'suspicious': False, 'score': 0}
        
        # Create histogram for low-value coefficients (-10 to 10)
        hist_range = range(-10, 11)
        hist_counts = {}
        for val in hist_range:
            hist_counts[val] = np.sum(coeffs == abs(val))
        
        # Check for suspicious pairs (values differing by 1)
        pair_anomalies = 0
        for val in range(-9, 10):
            if hist_counts[val] > 0 and hist_counts[val + 1] > 0:
                ratio = min(hist_counts[val], hist_counts[val + 1]) / max(hist_counts[val], hist_counts[val + 1])
                # Suspiciously similar frequencies
                if ratio > 0.95:
                    pair_anomalies += 1
        
        suspicious = pair_anomalies > 5
        
        return {
            'pair_anomalies': pair_anomalies,
            'suspicious': suspicious,
            'score': 2 if suspicious else 0
        }
    
    def _analyze_dct_lsb(self, coeffs):
        """Analyze LSB distribution in DCT coefficients"""
        # Non-zero coefficients
        non_zero = coeffs[coeffs != 0]
        
        if len(non_zero) == 0:
            return {'suspicious': False, 'score': 0}
        
        # Check LSB distribution
        lsb_ones = np.sum(non_zero & 1)
        lsb_zeros = len(non_zero) - lsb_ones
        total = len(non_zero)
        
        lsb_ratio = lsb_ones / total if total > 0 else 0.5
        
        # Natural JPEG should have slight imbalance
        # Perfect balance (0.495-0.505) suggests embedding
        too_perfect = 0.495 < lsb_ratio < 0.505
        
        return {
            'lsb_ratio': float(lsb_ratio),
            'suspicious': too_perfect,
            'score': 2 if too_perfect else 0
        }
    
    def _analyze_blockiness(self, img):
        """Analyze blockiness artifact (F5 detection)"""
        # F5 can reduce blocking artifacts
        h, w = img.shape
        boundary_diffs = []
        internal_diffs = []
        
        # Sample some blocks
        for i in range(0, min(h - 16, 200), 8):
            for j in range(0, min(w - 16, 200), 8):
                # Boundary difference (across 8-pixel boundary)
                if i + 16 < h:
                    boundary_diff = abs(int(img[i + 7, j]) - int(img[i + 8, j]))
                    boundary_diffs.append(boundary_diff)
                
                # Internal difference (within block)
                if i + 8 < h and j + 8 < w:
                    internal_diff = abs(int(img[i + 3, j]) - int(img[i + 4, j]))
                    internal_diffs.append(internal_diff)
        
        if len(boundary_diffs) > 0 and len(internal_diffs) > 0:
            avg_boundary = np.mean(boundary_diffs)
            avg_internal = np.mean(internal_diffs)
            
            # Normally, boundary differences should be higher
            blockiness_ratio = avg_boundary / avg_internal if avg_internal > 0 else 1.0
            
            # Suspiciously low blockiness
            suspicious = blockiness_ratio < 1.1
        else:
            blockiness_ratio = 1.0
            suspicious = False
        
        return {
            'blockiness_ratio': float(blockiness_ratio),
            'suspicious': suspicious,
            'score': 1 if suspicious else 0
        }