import re
import json
import requests
from transformers import MarianMTModel, MarianTokenizer
import torch
import nltk
from nltk.tokenize import sent_tokenize
import os

# Set NLTK data path to include our local directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
local_nltk_data = os.path.join(project_root, 'nltk_data')
if os.path.exists(local_nltk_data):
    nltk.data.path.append(local_nltk_data)

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt tokenizer data...")
    nltk.download('punkt', quiet=False)
    print("NLTK punkt tokenizer data downloaded successfully.")

# Create punkt_tab resource if it doesn't exist
try:
    nltk.data.find('tokenizers/punkt_tab/english')
    print("punkt_tab resource found.")
except LookupError:
    print("Creating punkt_tab resource...")
    # Create punkt_tab directory structure
    punkt_dir = os.path.join(nltk.data.find('tokenizers/punkt'))
    punkt_tab_dir = os.path.join(os.path.dirname(punkt_dir), 'punkt_tab', 'english')
    os.makedirs(punkt_tab_dir, exist_ok=True)
    
    # Copy punkt files to punkt_tab location
    import shutil
    for file in os.listdir(punkt_dir):
        if file.endswith('.pickle'):
            src = os.path.join(punkt_dir, file)
            dst = os.path.join(punkt_tab_dir, file)
            shutil.copy2(src, dst)
            print(f"Copied {src} to {dst}")
    print("Created punkt_tab resource successfully.")

# Create collocations.tab file if it doesn't exist
collocations_tab_path = os.path.join(nltk.data.path[0], 'tokenizers', 'punkt_tab', 'english', 'collocations.tab')
if not os.path.exists(collocations_tab_path):
    print(f"Creating collocations.tab file at: {collocations_tab_path}")
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(collocations_tab_path), exist_ok=True)
        
        # Create the collocations.tab file with common abbreviations
        with open(collocations_tab_path, 'w') as f:
            f.write("a.m.\na.m\np.m.\np.m\ne.g.\ni.e.\nU.S.\nU.S.A.\nMr.\nMrs.\nMs.\nDr.\nProf.\nJan.\nFeb.\nMar.\nApr.\nJun.\nJul.\nAug.\nSep.\nOct.\nNov.\nDec.\nSt.\nAve.\nBlvd.\n")
        print(f"Created collocations.tab file successfully.")
    except Exception as e:
        print(f"Error creating collocations.tab file: {str(e)}")

# Custom tokenize function to handle NLTK errors
def safe_sent_tokenize(text):
    """Safely tokenize text into sentences, with fallback methods if NLTK fails."""
    try:
        # Try using NLTK's sent_tokenize
        return sent_tokenize(text)
    except Exception as e:
        print(f"NLTK tokenization failed: {str(e)}")
        # Fallback method 1: Simple split by common sentence terminators
        try:
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) > 1:
                return sentences
        except Exception:
            pass
        
        # Fallback method 2: Just split by newlines and periods
        try:
            sentences = []
            for line in text.split('\n'):
                if line.strip():
                    for sent in line.split('. '):
                        if sent.strip():
                            sentences.append(sent.strip())
            if len(sentences) > 1:
                return sentences
        except Exception:
            pass
        
        # Last resort: return the whole text as one sentence
        return [text]

class ScriptGenerator:
    def __init__(self, model_name='Helsinki-NLP/opus-mt-en-es'):
        """Initialize the script generator with a translation model."""
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Loading translation model on {self.device}...")
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name).to(self.device)
        print("Translation model loaded.")

    def translate_text(self, text):
        """Translate text from English to Spanish."""
        try:
            # Split text into chunks to avoid exceeding max token length
            max_chunk_size = 512  # Maximum tokens for the model
            
            # Use our safe tokenization function
            sentences = safe_sent_tokenize(text)
            chunks = []
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                try:
                    tokens = self.tokenizer.tokenize(sentence)
                    token_length = len(tokens)
                except Exception as e:
                    print(f"Error tokenizing sentence: {str(e)}")
                    # Estimate token length as 1.5 times character length
                    token_length = int(len(sentence) * 1.5)
                    
                if current_length + token_length > max_chunk_size:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_length = token_length
                else:
                    current_chunk.append(sentence)
                    current_length += token_length
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Translate each chunk
            translated_chunks = []
            for chunk in chunks:
                try:
                    inputs = self.tokenizer(chunk, return_tensors="pt", padding=True).to(self.device)
                    with torch.no_grad():
                        outputs = self.model.generate(**inputs)
                    translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    translated_chunks.append(translated_text)
                except Exception as e:
                    print(f"Error translating chunk: {str(e)}")
                    # Fall back to a simple message
                    translated_chunks.append(f"[Error traduciendo: {str(e)}]")
            
            return ' '.join(translated_chunks)
        except Exception as e:
            print(f"Error in translate_text: {str(e)}")
            return f"Error en la traducción: {str(e)}"

    def structure_script(self, transcript, video_duration=None):
        """
        Structure the transcript into a proper script with sections while preserving the original flow.
        
        Sections:
        - Hook (0-15s)
        - Intro/Branding (15-30s)
        - Main Content
        - Call to Action
        - Outro (Optional)
        """
        try:
            # First, translate the entire transcript to preserve the original flow
            full_translated_transcript = self.translate_text(transcript)
            
            # Initialize variables
            hook = intro = main_content = call_to_action = outro = ""
            translated_hook = translated_intro = translated_main = translated_cta = translated_outro = ""
            
            # Divide the transcript into sections
            if video_duration:
                # Time-based sectioning (just use the full transcript for now)
                hook = intro = main_content = call_to_action = outro = transcript
                
                # Translate each section individually
                translated_hook = self.translate_text(transcript[:100])  # Just take first 100 chars for hook
                translated_intro = self.translate_text(transcript[100:300])  # Next 200 chars for intro
                translated_main = self.translate_text(transcript[300:-200])  # Middle part for main content
                translated_cta = self.translate_text(transcript[-200:-50])  # Last part for call to action
                translated_outro = self.translate_text(transcript[-50:])  # Very end for outro
            else:
                # Text-based sectioning
                sentences = safe_sent_tokenize(transcript)
                total_sentences = len(sentences)
                
                # Calculate section boundaries
                hook_end = max(1, int(total_sentences * 0.05))
                intro_end = max(2, int(total_sentences * 0.1))
                cta_start = max(hook_end + 1, int(total_sentences * 0.85))
                outro_start = max(cta_start + 1, int(total_sentences * 0.95))
                
                # Create sections from the original transcript
                hook = ' '.join(sentences[:hook_end])
                intro = ' '.join(sentences[hook_end:intro_end])
                main_content = ' '.join(sentences[intro_end:cta_start])
                call_to_action = ' '.join(sentences[cta_start:outro_start])
                outro = ' '.join(sentences[outro_start:]) if outro_start < total_sentences else ""
                
                # Try to use the full translated transcript to maintain flow
                translated_sentences = safe_sent_tokenize(full_translated_transcript)
                
                if len(translated_sentences) >= total_sentences:
                    # If we have enough translated sentences, match the original structure
                    translated_hook = ' '.join(translated_sentences[:hook_end])
                    translated_intro = ' '.join(translated_sentences[hook_end:intro_end])
                    translated_main = ' '.join(translated_sentences[intro_end:cta_start])
                    translated_cta = ' '.join(translated_sentences[cta_start:outro_start])
                    translated_outro = ' '.join(translated_sentences[outro_start:]) if outro_start < len(translated_sentences) else ""
                else:
                    # Fallback: translate each section individually
                    translated_hook = self.translate_text(hook)
                    translated_intro = self.translate_text(intro)
                    translated_main = self.translate_text(main_content)
                    translated_cta = self.translate_text(call_to_action)
                    translated_outro = self.translate_text(outro) if outro else ""
        except Exception as e:
            print(f"Error in structure_script: {str(e)}")
            # Create a simple error message as the script
            translated_hook = f"Error al estructurar el guión: {str(e)}"
            translated_intro = "Por favor, intente de nuevo."
            translated_main = "Si el error persiste, contacte al soporte técnico."
            translated_cta = "Gracias por su comprensión."
            translated_outro = ""
        
        # Format the script with ordered sections
        script = {
            "sections": [
                {
                    "id": "hook",
                    "title": "Gancho",
                    "description": "Captar la atención del espectador en los primeros 15 segundos",
                    "content": translated_hook
                },
                {
                    "id": "intro",
                    "title": "Introducción/Marca",
                    "description": "Presentar el tema y la marca (15-30 segundos)",
                    "content": translated_intro
                },
                {
                    "id": "main_content",
                    "title": "Contenido Principal",
                    "description": "El cuerpo principal del video",
                    "content": translated_main
                },
                {
                    "id": "call_to_action",
                    "title": "Llamada a la Acción",
                    "description": "Indicar al espectador qué hacer a continuación",
                    "content": translated_cta
                }
            ]
        }
        
        # Add outro if it exists
        if translated_outro:
            script["sections"].append({
                "id": "outro",
                "title": "Cierre",
                "description": "Conclusión del video (Opcional)",
                "content": translated_outro
            })
            
        return script

def generate_spanish_script(transcript, video_duration=None):
    """Generate a structured Spanish script from an English transcript."""
    generator = ScriptGenerator()
    script = generator.structure_script(transcript, video_duration)
    return script
