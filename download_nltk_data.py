import nltk
import os

def download_nltk_data():
    """Download required NLTK data packages."""
    print("Downloading NLTK data packages...")
    
    # Create nltk_data directory in the project root
    nltk_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    # Set NLTK data path
    nltk.data.path.append(nltk_data_dir)
    
    # Download required packages
    packages = ['punkt']
    for package in packages:
        print(f"Downloading {package}...")
        nltk.download(package, download_dir=nltk_data_dir, quiet=False)
        
    # Create punkt_tab directory structure and files
    print("Creating punkt_tab resources...")
    punkt_dir = os.path.join(nltk_data_dir, 'tokenizers', 'punkt')
    punkt_tab_dir = os.path.join(nltk_data_dir, 'tokenizers', 'punkt_tab', 'english')
    os.makedirs(punkt_tab_dir, exist_ok=True)
    
    # Copy punkt files to punkt_tab location
    import shutil
    for file in os.listdir(punkt_dir):
        if file.endswith('.pickle'):
            src = os.path.join(punkt_dir, file)
            dst = os.path.join(punkt_tab_dir, file)
            shutil.copy2(src, dst)
            print(f"Copied {src} to {dst}")
    
    print("Created punkt_tab resources successfully.")
    
    print("NLTK data packages downloaded successfully.")
    print(f"Data stored in: {nltk_data_dir}")
    print(f"NLTK data path: {nltk.data.path}")

if __name__ == "__main__":
    download_nltk_data()
