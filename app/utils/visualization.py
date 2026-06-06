import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from flask import current_app
import uuid

def generate_visualizations(img_array, analysis_id):
    """
    Generate all visualizations for an analysis
    
    Args:
        img_array: numpy array of image (H, W, 3)
        analysis_id: ID of the analysis record
    
    Returns:
        dict: Dictionary of visualization filepaths
    """
    visualizations = {}
    viz_folder = current_app.config['VISUALIZATIONS_FOLDER']
    os.makedirs(viz_folder, exist_ok=True)
    
    # Generate each visualization
    visualizations['heatmap'] = generate_heatmap(img_array, analysis_id, viz_folder)
    visualizations['bitplanes'] = generate_bitplanes(img_array, analysis_id, viz_folder)
    visualizations['histograms'] = generate_histograms(img_array, analysis_id, viz_folder)
    visualizations['lsb_plane'] = generate_lsb_plane(img_array, analysis_id, viz_folder)
    
    return visualizations


def generate_heatmap(img_array, analysis_id, viz_folder):
    """Generate heat map showing suspicious regions"""
    try:
        h, w, _ = img_array.shape
        
        # Create suspicion score map based on LSB variance in blocks
        block_size = 16
        heatmap = np.zeros((h // block_size, w // block_size))
        
        for i in range(0, h - block_size, block_size):
            for j in range(0, w - block_size, block_size):
                block = img_array[i:i+block_size, j:j+block_size]
                
                # Extract LSB
                lsb = block & 1
                
                # Calculate variance (high variance = more suspicious)
                variance = np.var(lsb)
                
                # Calculate LSB ratio
                ones = np.sum(lsb == 1)
                zeros = np.sum(lsb == 0)
                total = ones + zeros
                ratio = ones / total if total > 0 else 0.5
                
                # Suspicion score (closer to 0.5 ratio = more suspicious)
                ratio_score = 1 - abs(ratio - 0.5) * 2  # 0 to 1
                variance_score = min(variance / 0.25, 1)  # Normalize
                
                # Combined score
                suspicion = (ratio_score + variance_score) / 2
                heatmap[i // block_size, j // block_size] = suspicion
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot heatmap
        im = ax.imshow(heatmap, cmap='hot', interpolation='nearest', aspect='auto')
        ax.set_title('Suspicious Regions Heat Map\n(Red = High Suspicion, Dark = Low Suspicion)', 
                     fontsize=14, fontweight='bold')
        ax.set_xlabel('Image Width (blocks)', fontsize=10)
        ax.set_ylabel('Image Height (blocks)', fontsize=10)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Suspicion Score', rotation=270, labelpad=20)
        
        # Save
        filename = f'heatmap_{analysis_id}_{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(viz_folder, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename
    except Exception as e:
        print(f"Error generating heatmap: {e}")
        return None


def generate_bitplanes(img_array, analysis_id, viz_folder):
    """Generate bit plane decomposition visualization"""
    try:
        # Create figure with 8 subplots (one for each bit plane)
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        fig.suptitle('Bit Plane Decomposition (LSB = Bit 0)', fontsize=16, fontweight='bold')
        
        # Convert to grayscale for simplicity
        gray = np.mean(img_array, axis=2).astype(np.uint8)
        
        for bit in range(8):
            row = bit // 4
            col = bit % 4
            
            # Extract bit plane
            bit_plane = (gray >> bit) & 1
            
            # Plot
            axes[row, col].imshow(bit_plane * 255, cmap='gray', vmin=0, vmax=255)
            axes[row, col].set_title(f'Bit {bit} {"(LSB)" if bit == 0 else "(MSB)" if bit == 7 else ""}',
                                    fontweight='bold' if bit == 0 else 'normal')
            axes[row, col].axis('off')
        
        plt.tight_layout()
        
        # Save
        filename = f'bitplanes_{analysis_id}_{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(viz_folder, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename
    except Exception as e:
        print(f"Error generating bit planes: {e}")
        return None


def generate_histograms(img_array, analysis_id, viz_folder):
    """Generate RGB histograms"""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Color Histograms', fontsize=16, fontweight='bold')
        
        colors = ['red', 'green', 'blue']
        channel_names = ['Red', 'Green', 'Blue']
        
        # Individual channel histograms
        for i, (color, name) in enumerate(zip(colors, channel_names)):
            row = i // 2
            col = i % 2
            
            channel_data = img_array[:, :, i].flatten()
            axes[row, col].hist(channel_data, bins=256, range=(0, 256), 
                               color=color, alpha=0.7, edgecolor='black')
            axes[row, col].set_title(f'{name} Channel Histogram', fontweight='bold')
            axes[row, col].set_xlabel('Pixel Value')
            axes[row, col].set_ylabel('Frequency')
            axes[row, col].grid(True, alpha=0.3)
        
        # Combined histogram
        axes[1, 1].hist(img_array[:, :, 0].flatten(), bins=256, range=(0, 256), 
                       color='red', alpha=0.5, label='Red')
        axes[1, 1].hist(img_array[:, :, 1].flatten(), bins=256, range=(0, 256), 
                       color='green', alpha=0.5, label='Green')
        axes[1, 1].hist(img_array[:, :, 2].flatten(), bins=256, range=(0, 256), 
                       color='blue', alpha=0.5, label='Blue')
        axes[1, 1].set_title('Combined RGB Histogram', fontweight='bold')
        axes[1, 1].set_xlabel('Pixel Value')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save
        filename = f'histograms_{analysis_id}_{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(viz_folder, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename
    except Exception as e:
        print(f"Error generating histograms: {e}")
        return None


def generate_lsb_plane(img_array, analysis_id, viz_folder):
    """Generate LSB plane visualization for all channels"""
    try:
        fig, axes = plt.subplots(1, 4, figsize=(16, 4))
        fig.suptitle('Least Significant Bit (LSB) Planes', fontsize=16, fontweight='bold')
        
        channel_names = ['Red LSB', 'Green LSB', 'Blue LSB', 'Combined LSB']
        
        # Individual channel LSB
        for i in range(3):
            lsb = (img_array[:, :, i] & 1) * 255
            axes[i].imshow(lsb, cmap='gray', vmin=0, vmax=255)
            axes[i].set_title(channel_names[i], fontweight='bold')
            axes[i].axis('off')
        
        # Combined LSB (average of all channels)
        lsb_combined = np.mean(img_array & 1, axis=2) * 255
        axes[3].imshow(lsb_combined, cmap='gray', vmin=0, vmax=255)
        axes[3].set_title(channel_names[3], fontweight='bold')
        axes[3].axis('off')
        
        # Add note
        fig.text(0.5, 0.02, 'Note: Random noise pattern is expected. Structured patterns may indicate steganography.',
                ha='center', fontsize=10, style='italic')
        
        plt.tight_layout()
        
        # Save
        filename = f'lsb_plane_{analysis_id}_{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(viz_folder, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename
    except Exception as e:
        print(f"Error generating LSB plane: {e}")
        return None


def generate_edge_detection(img_array, analysis_id, viz_folder):
    """Generate edge detection visualization"""
    try:
        from scipy import ndimage
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        fig.suptitle('Edge Detection Analysis', fontsize=16, fontweight='bold')
        
        # Convert to grayscale
        gray = np.mean(img_array, axis=2).astype(np.uint8)
        
        # Original
        axes[0].imshow(gray, cmap='gray')
        axes[0].set_title('Original (Grayscale)', fontweight='bold')
        axes[0].axis('off')
        
        # Laplacian edge detection
        laplacian = ndimage.laplace(gray)
        axes[1].imshow(np.abs(laplacian), cmap='hot')
        axes[1].set_title('Laplacian Edge Detection', fontweight='bold')
        axes[1].axis('off')
        
        plt.tight_layout()
        
        # Save
        filename = f'edges_{analysis_id}_{uuid.uuid4().hex[:8]}.png'
        filepath = os.path.join(viz_folder, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename
    except Exception as e:
        print(f"Error generating edge detection: {e}")
        return None