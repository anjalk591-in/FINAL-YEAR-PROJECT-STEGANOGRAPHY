import time
import numpy as np
from PIL import Image
from app.detection.statistical import StatisticalAnalyzer
from app.detection.extraction import DataExtractor
from app.utils.visualization import generate_visualizations

class DetectionCoordinator:
    """Coordinate all detection modules"""
    
    def __init__(self, image_path, scan_type='standard'):
        """
        Initialize coordinator
        
        Args:
            image_path: Path to image file
            scan_type: 'quick', 'standard', or 'deep'
        """
        self.image_path = image_path
        self.scan_type = scan_type
        self.img = None
        self.img_array = None
        self.results = {
            'statistical': {},
            'visual': {},
            'frequency': {},
            'format': {},
            'extraction': {}
        }
    
    def run_analysis(self, analysis_id=None):
        """Run complete analysis"""
        start_time = time.time()
        
        # Load image
        self._load_image()
        
        # Run detection modules based on scan type
        if self.scan_type == 'quick':
            self._run_quick_scan()
        elif self.scan_type == 'deep':
            self._run_deep_scan()
        else:  # standard
            self._run_standard_scan()
        
        # Generate visualizations (if analysis_id provided)
        visualizations = {}
        if analysis_id:
            try:
                visualizations = generate_visualizations(self.img_array, analysis_id)
            except Exception as e:
                print(f"Error generating visualizations: {e}")
        
        # Calculate final score and verdict
        processing_time = time.time() - start_time
        final_score, statistical_confidence = self._calculate_final_score()
        confidence = self._calculate_confidence(final_score, statistical_confidence)
        verdict = self._determine_verdict(confidence)  # Verdict based on confidence only
        
        return {
            'results': self.results,
            'score': final_score,
            'verdict': verdict,
            'confidence': confidence,
            'processing_time': processing_time,
            'visualizations': visualizations
        }
    
    def _load_image(self):
        """Load and prepare image"""
        self.img = Image.open(self.image_path).convert('RGB')
        self.img_array = np.array(self.img)
    
    def _run_quick_scan(self):
        """Quick scan - essential tests only"""
        # Statistical: LSB, Chi-square, Entropy
        stat_analyzer = StatisticalAnalyzer(self.img_array)
        self.results['statistical']['lsb_distribution'] = stat_analyzer.lsb_distribution()
        self.results['statistical']['chi_square'] = stat_analyzer.chi_square_test()
        self.results['statistical']['entropy'] = stat_analyzer.entropy_analysis()
        
        # Quick extraction attempt
        extractor = DataExtractor(self.img_array)
        self.results['extraction'] = extractor.extract_all(image_path=self.image_path, limit=1000)
    
    def _run_standard_scan(self):
        """Standard scan - most tests"""
        # All statistical tests
        stat_analyzer = StatisticalAnalyzer(self.img_array)
        self.results['statistical'] = stat_analyzer.analyze_all()
        
        # DCT analysis for JPEG files
        if self.image_path.lower().endswith(('.jpg', '.jpeg')):
            self.results['statistical']['dct_analysis'] = stat_analyzer.dct_coefficient_analysis(self.image_path)
        
        # Extraction with image path for steghide and DCT methods
        extractor = DataExtractor(self.img_array)
        self.results['extraction'] = extractor.extract_all(image_path=self.image_path, limit=2000)
        
        # Visual analysis (basic)
        self.results['visual'] = self._basic_visual_analysis()
        
        # Format analysis (basic)
        self.results['format'] = self._basic_format_analysis()
    
    def _run_deep_scan(self):
        """Deep scan - all tests"""
        # Run standard scan first
        self._run_standard_scan()
        
        # Additional deep tests
        extractor = DataExtractor(self.img_array)
        self.results['extraction']['multi_bit_2'] = extractor.extract_multi_bit(bits=2, limit=1000)
        self.results['extraction']['multi_bit_3'] = extractor.extract_multi_bit(bits=3, limit=500)
        
        # More detailed visual/frequency analysis would go here
        # For now, we'll keep it simplified
    
    def _basic_visual_analysis(self):
        """Basic visual analysis"""
        # Bit plane analysis
        lsb_plane = self.img_array & 1
        lsb_variance = np.var(lsb_plane)
        
        # Check if LSB plane looks random
        # Random should have variance close to 0.25 (for binary values)
        expected_var = 0.25
        var_diff = abs(lsb_variance - expected_var)
        
        # IMPROVED: Very close to 0.25 suggests artificial randomness
        very_suspicious = var_diff < 0.02
        somewhat_suspicious = var_diff < 0.05
        
        suspicious = very_suspicious
        
        return {
            'lsb_variance': float(lsb_variance),
            'expected_variance': expected_var,
            'variance_difference': float(var_diff),
            'suspicious': suspicious,
            'score': 2 if very_suspicious else (1 if somewhat_suspicious else 0),
            'confidence': 0.7 if very_suspicious else (0.4 if somewhat_suspicious else 0.2)
        }
    
    def _basic_format_analysis(self):
        """Basic format analysis"""
        # Check image format
        img_format = self.img.format
        
        # Get file size
        import os
        filesize = os.path.getsize(self.image_path)
        
        # Calculate expected size (rough estimate)
        width, height = self.img.size
        expected_size = width * height * 3  # RGB
        
        # For PNG, add compression estimate
        if img_format == 'PNG':
            expected_size = expected_size * 0.7  # Rough compression ratio
        elif img_format == 'JPEG':
            expected_size = expected_size * 0.1  # Heavy compression
        
        size_ratio = filesize / expected_size if expected_size > 0 else 1
        
        # IMPROVED: More nuanced file size analysis
        very_large = size_ratio > 1.5
        somewhat_large = size_ratio > 1.3
        
        suspicious = very_large
        
        return {
            'format': img_format,
            'filesize': filesize,
            'expected_size': int(expected_size),
            'size_ratio': float(size_ratio),
            'suspicious': suspicious,
            'score': 2 if very_large else (1 if somewhat_large else 0),
            'confidence': 0.5 if very_large else (0.3 if somewhat_large else 0.1)
        }
    
    def _calculate_final_score(self):
        """Calculate final detection score and confidence"""
        total_score = 0
        weighted_confidence = 0
        total_weight = 0
        
        # Statistical scores with weights
        statistical_tests = {
            'lsb_distribution': 1.0,
            'chi_square': 1.5,
            'entropy': 1.0,
            'histogram': 1.5,
            'rs_analysis': 2.5,  # RS is very reliable
            'spa': 2.5,  # SPA is very reliable
            'dct_analysis': 2.0  # DCT analysis for JPEG steganography
        }
        
        for test_name, weight in statistical_tests.items():
            test_result = self.results['statistical'].get(test_name, {})
            if isinstance(test_result, dict) and 'score' in test_result:
                total_score += test_result['score']
                
                # Weighted confidence
                if 'confidence' in test_result:
                    weighted_confidence += test_result['confidence'] * weight
                    total_weight += weight
        
        # Visual scores
        if 'score' in self.results.get('visual', {}):
            total_score += self.results['visual']['score']
            if 'confidence' in self.results['visual']:
                weighted_confidence += self.results['visual']['confidence'] * 1.0
                total_weight += 1.0
        
        # Format scores (lower weight)
        if 'score' in self.results.get('format', {}):
            total_score += self.results['format']['score']
            if 'confidence' in self.results['format']:
                weighted_confidence += self.results['format']['confidence'] * 0.5
                total_weight += 0.5
        
        # Calculate average confidence from statistical tests
        statistical_confidence = (weighted_confidence / total_weight) if total_weight > 0 else 0
        
        # IMPROVED: Extraction only adds to score if BOTH found AND high readability
        extraction_data = self.results.get('extraction', {})
        if extraction_data.get('found', False) and extraction_data.get('readability', 0) > 0.75:
            total_score += 2  # Moderate boost, not overwhelming
        
        return total_score, statistical_confidence
    
    def _determine_verdict(self, confidence):
        """Determine verdict based on CONFIDENCE ONLY"""
        # Verdict determined SOLELY by confidence percentage
        if confidence >= 85:
            return 'CRITICAL'
        elif confidence >= 70:
            return 'HIGH'
        elif confidence >= 50:
            return 'MEDIUM'
        elif confidence >= 30:
            return 'LOW'
        else:
            return 'CLEAN'
    
    def _calculate_confidence(self, score, statistical_confidence):
        """Calculate overall confidence percentage"""
        # Start with statistical confidence as base (0-100%)
        base_confidence = statistical_confidence * 100
        
        # Adjust based on score
        # Higher scores increase confidence
        score_factor = min(score / 10.0, 1.0)  # Normalize score to 0-1
        score_contribution = score_factor * 30  # Max 30% from score
        
        confidence = base_confidence + score_contribution
        
        # IMPROVED: Extraction is SUPPORTING evidence only
        extraction_data = self.results.get('extraction', {})
        if extraction_data.get('found', False):
            readability = extraction_data.get('readability', 0)
            
            # Only boost if readability is genuinely high AND statistical tests agree
            if readability > 0.8 and statistical_confidence > 0.5:
                confidence += 10  # Modest boost
            elif readability > 0.7 and statistical_confidence > 0.6:
                confidence += 5  # Small boost
        
        # Cap confidence
        confidence = min(confidence, 98)  # Never 100% certain
        
        # Floor confidence based on evidence
        if score < 2 and statistical_confidence < 0.3 and not extraction_data.get('found', False):
            confidence = min(confidence, 20)  # Very low confidence for clean images
        
        # Multiple strong indicators increase confidence
        strong_indicators = self._count_strong_indicators()
        
        if strong_indicators >= 3:
            confidence = max(confidence, 70)
        elif strong_indicators >= 2:
            confidence = max(confidence, 50)
        elif strong_indicators == 0 and score < 2:
            confidence = min(confidence, 25)
        
        return round(confidence, 2)
    
    def _count_strong_indicators(self):
        """Count number of strong indicators"""
        count = 0
        
        # RS Analysis
        rs_data = self.results.get('statistical', {}).get('rs_analysis', {})
        if rs_data.get('suspicious', False) and rs_data.get('confidence', 0) > 0.7:
            count += 1
        
        # SPA
        spa_data = self.results.get('statistical', {}).get('spa', {})
        if spa_data.get('suspicious', False) and spa_data.get('confidence', 0) > 0.7:
            count += 1
        
        # Chi-square
        chi_data = self.results.get('statistical', {}).get('chi_square', {})
        if chi_data.get('suspicious', False) and chi_data.get('confidence', 0) > 0.7:
            count += 1
        
        # Histogram
        hist_data = self.results.get('statistical', {}).get('histogram', {})
        if hist_data.get('suspicious', False) and hist_data.get('confidence', 0) > 0.6:
            count += 1
        
        # DCT Analysis (for JPEG)
        dct_data = self.results.get('statistical', {}).get('dct_analysis', {})
        if dct_data.get('suspicious', False) and dct_data.get('confidence', 0) > 0.6:
            count += 1
        
        # Extraction (only if VERY strong)
        extraction_data = self.results.get('extraction', {})
        if extraction_data.get('found', False) and extraction_data.get('readability', 0) > 0.85:
            count += 1
        
        return count