import os
import nltk

def create_collocations_tab():
    """Create the missing collocations.tab file for NLTK punkt_tab."""
    print("Creating collocations.tab file...")
    
    # Get the nltk data path
    nltk_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nltk_data')
    
    # Create the punkt_tab directory if it doesn't exist
    punkt_tab_dir = os.path.join(nltk_data_dir, 'tokenizers', 'punkt_tab', 'english')
    os.makedirs(punkt_tab_dir, exist_ok=True)
    
    # Create an empty collocations.tab file
    collocations_tab_path = os.path.join(punkt_tab_dir, 'collocations.tab')
    with open(collocations_tab_path, 'w') as f:
        # Write some basic English collocations
        f.write("a.m.\na.m\np.m.\np.m\ne.g.\ni.e.\nU.S.\nU.S.A.\nMr.\nMrs.\nMs.\nDr.\nProf.\nJan.\nFeb.\nMar.\nApr.\nJun.\nJul.\nAug.\nSep.\nOct.\nNov.\nDec.\nSt.\nAve.\nBlvd.\n")
    
    print(f"Created collocations.tab file at: {collocations_tab_path}")

if __name__ == "__main__":
    create_collocations_tab()
