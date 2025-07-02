import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import re
import google.generativeai as genai
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache

# ---------------------- CONFIG ----------------------
genai.configure(api_key="AIzaSyBzOT2O03scMENbdWouWexYa10v4K4OVPE")

# Thread-local storage for WebDriver instances
thread_local = threading.local()

def get_driver():
    """Get a WebDriver instance for the current thread"""
    if not hasattr(thread_local, 'driver'):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-images')  # Speed up loading
        options.add_argument('--disable-javascript')  # Speed up loading
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        thread_local.driver = webdriver.Chrome(options=options)
        thread_local.driver.set_page_load_timeout(30)  # Reduced timeout
        thread_local.driver.implicitly_wait(5)  # Reduced wait
    
    return thread_local.driver

def cleanup_driver():
    """Clean up the WebDriver for the current thread"""
    if hasattr(thread_local, 'driver'):
        thread_local.driver.quit()
        del thread_local.driver

# ---------------------- URL Classification ----------------------
@lru_cache(maxsize=1000)  # Cache classification results
def classify_bnp_url(url):
    """Enhanced URL classification specifically for BNP Paribas Fortis"""
    url = url.lower()
    
    if any(term in url for term in [
        "product", "producten", "produits", "sparen", "saving", "epargne", 
        "lenen", "loan", "pret", "credit", "rekening", "account", "compte",
        "beleggen", "investment", "investir", "hypotheek", "mortgage", 
        "verzekering", "insurance", "assurance", "kaart", "card", "carte",
        "bankieren", "banking", "banque", "easy-banking", "business-banking"
    ]):
        return "Product"
    
    elif any(term in url for term in [
        "faq", "support", "help", "hulp", "ondersteuning", "aide", 
        "questions", "klantenservice", "clientservice", "assistance"
    ]):
        return "FAQ"
    
    elif any(term in url for term in [
        "legal", "juridisch", "juridique", "voorwaarden", "terms",
        "conditions", "privacy", "beleid", "policy", "cookie", "gdpr"
    ]):
        return "Legal"
    
    elif any(term in url for term in [
        "contact", "locatie", "location", "agences", "branches", 
        "kantoren", "afspraak", "appointment"
    ]):
        return "Contact"
    
    elif any(term in url for term in ["blog", "nieuws", "news", "actualites"]):
        return "Blog"
    
    else:
        return "Other"

# ---------------------- Text Extraction ----------------------
def extract_clean_text_bnp(url):
    """Optimized text extraction for BNP Paribas Fortis"""
    try:
        driver = get_driver()
        driver.get(url)
        
        # Reduced wait time
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        except:
            time.sleep(2)  # Reduced sleep
        
        # Quick cookie handling
        try:
            cookie_selectors = ['[data-testid*="accept"]', '[class*="accept"]']
            for selector in cookie_selectors:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons[:1]:  # Only try first button
                    if button.is_displayed():
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        break
                if buttons:
                    break
        except:
            pass
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            if tag:
                tag.decompose()
        
        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('.content')
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        
        if text and len(text.strip()) > 100:
            result = ' '.join(text.split())[:10000]
            return result
        else:
            return ""

    except Exception as e:
        return ""

def clean_bnp_text(raw_text):
    """
    Universal text cleaning function for Belgian banks (KBC, BNP Paribas, Belfius, ING)
    Handles multi-language content (NL/FR/EN) and bank-specific patterns
    """
    if not raw_text or len(raw_text.strip()) < 20:
        return ""
    
    # Universal navigation and header patterns
    navigation_patterns = [
        # Skip to content links
        r'Skip to .*?Log in',
        r'Retour au .*?Se connecter',
        r'Terug naar de inhoud',
        r'Overslaan en naar de inhoud gaan',
        r'Aller au contenu principal',
        r'Skip to main content',
        
        # Language switchers
        r'FR\s+NL\s+EN',
        r'Nederlands\s+Français\s+English',
        r'NL\s+FR\s+DE',
        r'\bFR\s+NL\b',
        r'\bFrançais\b\s*\bNederlands\b',
        
        # Main navigation menus
        r'Home.*?Contact.*?Login',
        r'Accueil.*?Contact.*?Connexion',
        r'Thuis.*?Contact.*?Inloggen',
        r'Menu\s+Sluiten',
        r'Menu\s+Fermer',
        r'Close\s+Menu',
        
        # Search functionality
        r'Zoeken \(Optioneel\).*?Contact',
        r'Rechercher \(En option\).*?Contact',
        r'Search \(Optional\).*?Contact',
        r'Zoeken.*?Zoek',
        r'Rechercher.*?Recherche',
        r'Search.*?Search',
        
        # Bank-specific navigation
        # KBC specific
        r'KBC.*?Inloggen',
        r'KBC.*?Se connecter',
        r'Online Banking.*?KBC',
        
        # BNP Paribas specific
        r'BNP Paribas Fortis.*?Inloggen',
        r'BNP Paribas Fortis.*?Se connecter',
        r'Word klant.*?Beobank Online',
        r'Devenir client.*?Beobank Online',
        
        # Belfius specific
        r'Belfius.*?Inloggen',
        r'Belfius.*?Se connecter',
        r'Belfius Direct Net',
        
        # ING specific
        r'ING.*?Inloggen',
        r'ING.*?Se connecter',
        r'Mijn ING.*?Inloggen',
    ]
    
    # Cookie and privacy notices (comprehensive)
    cookie_patterns = [
        # Cookie acceptance
        r'Accept all cookies.*?Manage cookies',
        r'Accepter tous les cookies.*?Gérer les cookies',
        r'Alle cookies accepteren.*?Cookies beheren',
        r'Deze website gebruikt cookies.*?Alles accepteren',
        r'Ce site utilise des cookies.*?Tout accepter',
        r'This website uses cookies.*?Accept all',
        
        # Cookie management sections
        r'Cookie settings.*?Save preferences',
        r'Paramètres des cookies.*?Sauvegarder',
        r'Cookie-instellingen.*?Voorkeuren opslaan',
        r'Mijn cookies beheren.*?Alles accepteren',
        r'Gérer mes cookies.*?Tout accepter',
        r'Manage my cookies.*?Accept all',
        
        # Cookie descriptions
        r'Functionele cookies.*?verbeteren\.',
        r'Les cookies fonctionnels.*?par des tiers\.',
        r'Functional cookies.*?third parties\.',
        r'Analytische cookies.*?voorkeuren zijn\.',
        r'Les cookies de mesure.*?leurs préférences\.',
        r'Analytics cookies.*?their preferences\.',
        r'Marketing cookies.*?te tonen\.',
        r'Les cookies publicitaires.*?pertinentes\.',
        r'Marketing cookies.*?relevant\.',
        
        # Privacy policy links
        r'Privacy policy.*?Terms',
        r'Politique de confidentialité.*?Conditions',
        r'Privacybeleid.*?Voorwaarden',
    ]
    
    # Technical and browser notices
    technical_patterns = [
        r'Voor een betere surfervaring.*?Chrome',
        r'Pour une meilleure expérience.*?Chrome\.',
        r'For a better browsing experience.*?Chrome',
        r'Adblock detection:.*?Sluiten',
        r'Adblock detection:.*?Fermer',
        r'Adblock detection:.*?Close',
        r'You have not yet given permission.*?Load video',
        r'JavaScript is disabled.*?Enable JavaScript',
        r'Loading\.\.\.',
        r'Laden\.\.\.',
        r'Chargement\.\.\.',
    ]
    
    # Footer and related content
    footer_patterns = [
        # Related articles
        r'Other articles that might interest you.*',
        r'Autres articles qui pourraient vous intéresser.*',
        r'Andere artikels die u kunnen interesseren.*',
        r'Gerelateerde concepten.*?Lees meer',
        r'Termes liés.*?Lire la suite',
        r'Related terms.*?Read more',
        
        # Newsletter and blog subscriptions
        r'Ontdek de.*?blog.*?Français',
        r'Découvrir le blog.*?Nederlands',
        r'Discover the.*?blog.*?Dutch',
        r'Schrijf u in op onze nieuwsbrief.*?Inschrijven',
        r'Inscrivez-vous à notre newsletter.*?S\'inscrire',
        r'Subscribe to our newsletter.*?Subscribe',
        
        # Legal and compliance
        r'Terms and conditions.*?Privacy',
        r'Termes et conditions.*?Confidentialité',
        r'Algemene voorwaarden.*?Privacy',
        r'Disclaimer.*?Copyright',
        r'Avertissement.*?Droits d\'auteur',
        r'Vrijwaring.*?Auteursrecht',
        
        # Copyright notices
        r'©.*?\d{4}.*?(KBC|BNP|Belfius|ING)',
        r'Alle rechten voorbehouden',
        r'Tous droits réservés',
        r'All rights reserved',
    ]
    
    # Banking-specific call-to-action patterns
    banking_cta_patterns = [
        # Appointment booking
        r'Maak een afspraak!.*?',
        r'Prenez rendez-vous.*?',
        r'Make an appointment.*?',
        r'Boek een gesprek.*?',
        r'Réservez un entretien.*?',
        
        # Investment advice
        r'Ontdek ons advies.*?',
        r'Laissez-vous conseiller.*?',
        r'Discover our advice.*?',
        r'Klaar om te beleggen\?.*?Maak een afspraak!',
        r'Prêt\(e\) à investir\?.*?Prenez rendez-vous',
        r'Ready to invest\?.*?Make an appointment',
        
        # Product promotions
        r'Ontdek onze.*?producten',
        r'Découvrez nos.*?produits',
        r'Discover our.*?products',
        r'Meer informatie.*?aanvragen',
        r'Plus d\'informations.*?demander',
        r'More information.*?request',
    ]
    
    # Social media and sharing
    social_patterns = [
        r'Share on.*?Facebook',
        r'Partager sur.*?Facebook',
        r'Delen op.*?Facebook',
        r'Tweet.*?Twitter',
        r'Tweeter.*?Twitter',
        r'LinkedIn.*?delen',
        r'LinkedIn.*?partager',
        r'LinkedIn.*?share',
        r'WhatsApp.*?delen',
        r'WhatsApp.*?partager',
        r'WhatsApp.*?share',
        r'E-mail.*?versturen',
        r'E-mail.*?envoyer',
        r'E-mail.*?send',
        r'Print this page',
        r'Imprimez cette page',
        r'Print deze pagina',
        r'Download PDF',
        r'Télécharger PDF',
        r'PDF downloaden',
    ]
    
    # Breadcrumb and metadata
    metadata_patterns = [
        r'Home\s*›.*?›',
        r'Accueil\s*›.*?›',
        r'Thuis\s*›.*?›',
        r'Last updated:.*?\d{4}',
        r'Dernière mise à jour:.*?\d{4}',
        r'Laatst bijgewerkt:.*?\d{4}',
        r'Posted on.*?\d{4}',
        r'Publié le.*?\d{4}',
        r'Geplaatst op.*?\d{4}',
        r'Tags:.*?(?=\n|\.|$)',
        r'Étiquettes:.*?(?=\n|\.|$)',
        r'Labels:.*?(?=\n|\.|$)',
        r'\d+\s+min read',
        r'\d+\s+min de lecture',
        r'\d+\s+min lezen',
    ]
    
    # Combine all patterns
    all_patterns = (navigation_patterns + cookie_patterns + technical_patterns + 
                   footer_patterns + banking_cta_patterns + social_patterns + metadata_patterns)
    
    # Apply cleaning
    cleaned = raw_text
    for pattern in all_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove repeated "Read more" links in all languages
    read_more_patterns = [
        r'Lees meer\s*',
        r'Lire la suite\s*',
        r'Read more\s*',
        r'Meer lezen\s*',
        r'En savoir plus\s*',
        r'Learn more\s*'
    ]
    
    for pattern in read_more_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove investment sidebar content
    cleaned = re.sub(r'Beleggen in \w+\s+[A-Z].*?\.{3}', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Investir dans \w+\s+[A-Z].*?\.{3}', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Investing in \w+\s+[A-Z].*?\.{3}', '', cleaned, flags=re.DOTALL)
    
    # Remove standalone navigation and form words
    standalone_words = [
        'Contact', 'Zoeken', 'Rechercher', 'Search',
        'Email adres', 'Adresse email', 'Email address',
        'Inschrijven', 'S\'inscrire', 'Subscribe',
        'Versturen', 'Envoyer', 'Send',
        'Annuleren', 'Annuler', 'Cancel',
        'Bevestigen', 'Confirmer', 'Confirm'
    ]
    
    for word in standalone_words:
        cleaned = re.sub(rf'\b{re.escape(word)}\b', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up formatting issues
    # Remove excessive punctuation
    cleaned = re.sub(r'[.]{2,}', '.', cleaned)
    cleaned = re.sub(r'[-]{3,}', '', cleaned)
    cleaned = re.sub(r'[_]{3,}', '', cleaned)
    cleaned = re.sub(r'(\b\w+\b)(\s+\1){2,}', r'\1', cleaned)  # Remove repeated words
    
    # Fix spacing around punctuation
    cleaned = re.sub(r'\s+([.,!?;:])', r'\1', cleaned)
    cleaned = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1 \2', cleaned)
    
    # Remove empty brackets and parentheses
    cleaned = re.sub(r'\(\s*\)', '', cleaned)
    cleaned = re.sub(r'\[\s*\]', '', cleaned)
    cleaned = re.sub(r'\{\s*\}', '', cleaned)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
    
    return cleaned.strip()

# ---------------------- Gemini Scoring ----------------------
def score_page_with_gemini(text, page_type):
    prompt = f"""
**Context:** This prompt is designed for the Gemini language model to evaluate the CEFR B2 level compliance of webpage content from retail banking websites for regulatory compliance. The evaluation focuses on vocabulary, grammar, clarity, and coherence to determine if the text is easily understandable for someone at a B2 level in English, French, or Dutch. The desired output includes the compliance level percentage and individual scores for vocabulary complexity, grammatical structures, overall clarity, and coherence, with a detailed rationale for each evaluated address presented in a single cell of an output file (e.g., CSV or Excel). The goal is to ensure the evaluation effectively differentiates between webpages with varying levels of B2 compliance, leading to a wider range of scores, and that the rationale is comprehensive yet concise enough to fit within a single cell per address. **It is important to consider that these are banking websites, and some technical or financial terms may be inherent to the content.**

**Task:** Assess the CEFR B2 compliance level of the provided webpage content, ensuring a variable range of scores and a detailed, single-cell rationale for each evaluated address, **while acknowledging the potential presence of necessary banking terminology.**

**Instructions:**

1. **Identify Language:** Determine if the input text is in English, French, or Dutch.

2. **Evaluate B2 Compliance with Granularity (Considering Banking Terms):** Analyze the text against the CEFR B2 criteria for the identified language, critically and precisely assessing the following aspects on a scale of 0 to 10. Avoid assigning only 0 or 10; use the full scale based on nuance and subtlety. “Do not hesitate to assign low (0–4) or high (8–10) scores when the text clearly deserves it. Avoid accumulating around 6–7 unless the text is truly average.” Remember the compliancy threshold is 70% (7/10) for B2 level. Therefore if a text is generally compliant it should receive a total score of higher than or equal to 70.

- **Vocabulary Complexity (0–10)**
  - 10 → very simple, common words, basic banking terms, no jargon
  - 7–9 → mostly common words, occasional technical terms explained
  - 4–6 → mix of general and technical terms, some unnecessarily complex or rare words
  - 1–3 → frequent use of complex, low-frequency words or jargon, often unexplained
  - 0 → highly complex, dense language with rare or unexplained terms everywhere

- **Grammatical Structures (0–10)**
  - 10 → simple sentences, clear structure, active voice, no complex clauses
  - 7–9 → mostly simple, some moderate clauses, minor passive use
  - 4–6 → mix of simple and complex sentences, occasional embedded or passive forms
  - 1–3 → mostly long, embedded, or passive structures, hard to follow
  - 0 → extremely complex grammar, frequent embedding, difficult to parse

- **Overall Clarity (0–10)**
  - 10 → very clear, easy to understand, minimal effort required
  - 7–9 → mostly clear, small moments of complexity
  - 4–6 → mixed clarity, occasional confusion or ambiguity
  - 1–3 → often unclear, requires effort to interpret
  - 0 → very unclear, confusing, hard to follow

- **Coherence (0–10)**
  - 10 → logical flow, clear organization, excellent connectors
  - 7–9 → mostly logical, some jumps, minor missing links
  - 4–6 → mixed coherence, weak transitions, partial disorganization
  - 1–3 → often disorganized, unclear connections
  - 0 → no logical order, chaotic, fragmented

3. **Provide Detailed Rationale (Single Cell):** Explain the reasoning behind each of the four scores within a single text string suitable for one Excel cell. Explicitly point out specific linguistic features (vocabulary, grammar, discourse markers) that contribute to the assigned level of complexity or simplicity for each criterion. When discussing vocabulary, specifically comment on the presence and handling of banking terminology. Justify why the text is or is not strictly at the B2 level for each aspect. Use clear separators (e.g., "; ") between the rationale for each criterion to ensure readability within the single cell.
```xml
<rationale>Vocabulary: [Explanation with examples, noting banking terms]; Grammar: [Explanation with examples]; Clarity: [Explanation with examples, considering banking terms]; Coherence: [Explanation with examples]</rationale>

**Output Format:**
Return the evaluation in the following XML format, ensuring all information for a single evaluated webpage address can be represented as a single row in an output file:
```xml
<vocabulary_complexity>Y</vocabulary_complexity>
<grammatical_structures>Z</grammatical_structures>
<overall_clarity>W</overall_clarity>
<coherence>V</coherence>
<rationale>Vocabulary: [Explanation with examples, noting banking terms], Grammar: [Explanation with examples], Clarity: [Explanation with examples, considering banking terms], Coherence: [Explanation with examples]</rationale>

Examples of B2 Compliant Texts and C1 Texts Which Are Not B2 Compliant
 To help you understand the evaluation criteria, here are some examples of texts rated at B2 and C1 levels:

English
B2 level text
 Source: LinguaPress Unsolved mysteries – a short story by Sarah Wollbach
 Megan’s acting career began one morning a couple of years ago, when a woman approached her in the parking lot of her neighborhood grocery store. “Excuse me,” she said, “but have you ever taken acting lessons?” — “No,” she answered hesitantly. 
 The woman reached into her pocket and handed Megan a card. “I’m a casting director for Unsolved Mysteries,” she said, shaking her hand. Megan had always been stage-struck. 
 For years she'd fantasized about being an actor, sure that deep within her lurked a brilliant chameleon like Meryl Streep or Julia Roberts. Maybe this was her big break. 
 “The show’s doing a feature about a woman who was kidnapped,” the lady continued, “and you look exactly like her. The resemblance is amazing. Would you be interested in auditioning?” 
 The episode aired the next week, with a couple of thousand dollars for two days’ work, plus travel, lodging, and food expenses.


C1 level text
 Source: LinguaPress The Enigma of the Missing Manuscript by John Doe
 The mystery of the missing manuscript has eluded generations of writers. It was said to contain the final, unpublished works and annotations of the author, whose sudden disappearance 
 had only added to the intrigue. The manuscript was believed to be hidden somewhere in the old mansion, a labyrinthine structure filled with secret passages and hidden rooms. 
 Many had tried to find it, but all had failed. The clues were cryptic, the dangers real, and the stakes high. For those who dared to search, it was a journey into the unknown, a test of wit and courage.



French
B2 level text
 Source: LinguaPress Mystères non résolus – une histoire courte par Sarah Wollbach
 La carrière d’actrice de Megan a commencé un matin il y a quelques années, lorsqu’une femme l’a abordée dans le parking de son épicerie de quartier. 
 “Excusez-moi,” dit-elle, “mais avez-vous déjà pris des cours de théâtre?” — “Non,” répondit-elle avec hésitation. La femme a fouillé dans sa poche et tendu une carte à Megan. 
 “Je suis directrice de casting de Mystères non résolus,” dit-elle en lui serrant la main. Megan avait toujours été fascinée par la scène. 
 Pendant des années, elle avait nourri en secret le rêve d’être actrice, convaincue qu’au fond d’elle-même se cachait un brillant caméléon comme Meryl Streep ou Julia Roberts. 
 Peut-être que c’était sa grande chance. “L’émission fait un reportage sur une femme qui a été kidnappée,” continua la dame, “et vous lui ressemblez exactement. 
 La ressemblance est incroyable. Seriez-vous intéressée par une audition?” Elle expliqua que le rôle valait quelques milliers de dollars pour deux jours de travail, plus les frais de voyage, de logement et de nourriture.


C1 level text
 Source: LinguaPress L’Enigme du Manuscrit Disparu par Jean Dupont
 Le mystère du manuscrit disparu que tout le monde tentait de percer depuis des décennies. On disait qu’il contenait les dernières œuvres finales, non publiées, d’un auteur renommé, 
 dont la disparition soudaine n’avait fait qu’ajouter à l’intrigue. On croyait que le manuscrit était caché quelque part dans le vieux manoir, une structure labyrinthique remplie de passages secrets et de pièces cachées. 
 Beaucoup avaient essayé de le trouver, mais tous avaient échoué. Les indices étaient cryptiques, les dangers réels, et les enjeux élevés. Pour ceux qui osaient chercher, c’était un voyage dans l’inconnu, un test d’esprit et de courage.



Dutch
B2 level text
 Source: LinguaPress Opgeloste mysteries – een kortverhaal door Sarah Wollbach
 Megan’s acteercarrière begon op een ochtend een paar jaar geleden, toen een vrouw haar benaderde op de parkeerplaats van haar buurtwinkel. “Excuseer me,” zei ze, “maar heb je ooit acteerlessen gevolgd?” — “Nee,” antwoordde ze aarzelend. 
 De vrouw stak haar hand in haar zak en gaf Megan een kaartje. “Ik ben een castingdirecteur voor Opgeloste mysteries,” zei ze, terwijl ze haar hand schudde. Megan was altijd al gefascineerd door het toneel. 
 Jarenlang had ze gefantaseerd over het zijn van een actrice, ervan overtuigd dat diep vanbinnen een briljante actrice zoals Meryl Streep of Julia Roberts schuilde. Misschien was dit haar grote doorbraak. 
 “De show doet een reportage over een vrouw die ontvoerd is,” vervolgde de dame, “en je lijkt precies op haar. De gelijkenis is verbazingwekkend. Zou je geïnteresseerd zijn in een auditie?” 
 Ze zette uit dat dit alles een paar duizend dollar waard was voor twee dagen werk, plus reis-, verblijf- en voedselkosten.


C1 level text
 Source: LinguaPress Het Raadsel van het Verdwenen Manuscript door Jan Jansen
 Het mysterie van het verdwenen manuscript dat generaties schrijvers decennialang verbijsterd. Er werd gezegd dat het de laatste, ongepubliceerde werken van een beroemde auteur bevatte, wiens plotselinge verdwijning alleen maar bijdroeg aan de intrige. 
 Het gerucht deed de ronde dat het manuscript ergens in het oude herenhuis verborgen was, een labyrintische structuur vol geheime gangen en verborgen kamers. Velen hadden geprobeerd het te vinden, maar allemaal waren ze mislukt. 
 De aanwijzingen waren cryptisch, de gevaren echt, en de inzet hoog. Voor degenen die durfden te zoeken, was het een reis in het onbekende, een test van verstand en moed.


Input Text content to check: \"\"\"{text}\"\"\" 
"""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt, generation_config={"temperature": 0.2})
        output = response.text.strip()

        if output.startswith("```"):
            output = output.strip("` \n").replace("xml", "").strip()

        scores = {
            "vocabulary_complexity": extract_xml_score(output, "vocabulary_complexity"),
            "grammatical_structures": extract_xml_score(output, "grammatical_structures"),
            "overall_clarity": extract_xml_score(output, "overall_clarity"),
            "coherence": extract_xml_score(output, "coherence"),
            "rationale": extract_xml_rationale(output),
        }
        return scores

    except Exception as e:
        return {
            "vocabulary_complexity": 0,
            "grammatical_structures": 0,
            "overall_clarity": 0,
            "coherence": 0,
            "rationale": f"Error: {str(e)}",
        }

def extract_xml_score(xml_text, tag):
    match = re.search(fr"<{tag}>(\d+)</{tag}>", xml_text)
    return int(match.group(1)) if match else 0

def extract_xml_rationale(xml_text):
    match = re.search(r"<rationale>(.*?)</rationale>", xml_text, re.DOTALL)
    return match.group(1).strip() if match else "No rationale found."

# ---------------------- Processing Function ----------------------
def process_single_url(url_data):
    """Process a single URL - designed for parallel execution"""
    url, page_type = url_data
    
    try:
        # Extract and clean text
        text = extract_clean_text_bnp(url)
        if not text.strip():
            return create_error_result(url, page_type, "No text extracted")
        
        cleaned_text = clean_bnp_text(text)
        
        # Score with Gemini
        result = score_page_with_gemini(cleaned_text, page_type)
        
        sub_scores = [
            result.get("vocabulary_complexity", 0),
            result.get("grammatical_structures", 0),
            result.get("overall_clarity", 0),
            result.get("coherence", 0),
        ]
        
        compliance_value = round(sum(sub_scores) / 4 * 10) if all(
            isinstance(score, int) and 0 <= score <= 10 for score in sub_scores
        ) else 0
        
        return {
            "URL": url,
            "Page Type": page_type,
            "Compliance Level": compliance_value,
            "Vocabulary Complexity": result.get("vocabulary_complexity"),
            "Grammatical Structures": result.get("grammatical_structures"),
            "Overall Clarity": result.get("overall_clarity"),
            "Coherence": result.get("coherence"),
            "Rationale": result.get("rationale"),
        }
        
    except Exception as e:
        return create_error_result(url, page_type, str(e))

def create_error_result(url, page_type, error_msg):
    """Create error result dictionary"""
    return {
        "URL": url,
        "Page Type": page_type,
        "Compliance Level": 0,
        "Vocabulary Complexity": 0,
        "Grammatical Structures": 0,
        "Overall Clarity": 0,
        "Coherence": 0,
        "Rationale": f"Error: {error_msg}",
    }

# ---------------------- Main Analysis ----------------------
def analyze_bnp_b2_compliance(excel_file_path, max_workers=4, batch_size=20):
    """Optimized main function with parallel processing"""
    
    print("🚀 BNP Paribas Fortis B2 Compliance Analysis (Optimized)")
    print("="*60)
    
    # Load URLs from Excel
    try:
        df_urls = pd.read_excel(excel_file_path)
        url_columns = ['Address', 'URL', 'url', 'address', 'link', 'Link']
        url_column = None
        for col in url_columns:
            if col in df_urls.columns:
                url_column = col
                break
        
        if url_column is None:
            url_column = df_urls.columns[0]
        
        urls = df_urls[url_column].dropna().tolist()
        print(f"✅ Loaded {len(urls)} URLs from {url_column} column")
        
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return
    
    # Create DataFrame and classify URLs
    df = pd.DataFrame({'Address': urls})
    df["Page Type"] = df["Address"].apply(classify_bnp_url)
    
    print(f"\n📊 URL Distribution:")
    print(df['Page Type'].value_counts())
    
    # Setup files
    checkpoint_file = "BNPPF/bnp_paribas_fortis_b2_checkpoint.csv"
    log_file = "BNPPF/bnp_paribas_fortis_b2_log.txt"
    
    # Resume from checkpoint
    processed_urls = set()
    scores = []
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            processed_urls = set(line.strip() for line in f.readlines())
    
    if os.path.exists(checkpoint_file):
        scores_df = pd.read_csv(checkpoint_file)
        scores = scores_df.to_dict(orient='records')
        print(f"📂 Resuming from checkpoint with {len(scores)} existing scores")
    
    # Filter unprocessed URLs
    unprocessed_data = [
        (url, page_type) for url, page_type in zip(df['Address'], df['Page Type'])
        if url not in processed_urls
    ]
    
    if not unprocessed_data:
        print("✅ All URLs already processed!")
        return pd.DataFrame(scores)
    
    print(f"🔄 Processing {len(unprocessed_data)} remaining URLs with {max_workers} workers")
    
    # Process in batches with parallel execution
    for i in range(0, len(unprocessed_data), batch_size):
        batch = unprocessed_data[i:i + batch_size]
        batch_results = []
        
        print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(unprocessed_data)-1)//batch_size + 1}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks in the batch
            future_to_url = {
                executor.submit(process_single_url, url_data): url_data[0] 
                for url_data in batch
            }
            
            # Collect results with progress bar
            for future in tqdm(as_completed(future_to_url), total=len(batch), desc="🤖 Scoring"):
                url = future_to_url[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout per URL
                    batch_results.append(result)
                    
                    # Log processed URL
                    with open(log_file, 'a') as f:
                        f.write(url + '\n')
                        
                except Exception as e:
                    print(f"❌ Failed to process {url}: {e}")
                    # Add error result
                    batch_results.append(create_error_result(url, "Unknown", str(e)))
        
        # Add batch results to main scores
        scores.extend(batch_results)
        
        # Save checkpoint after each batch
        pd.DataFrame(scores).to_csv(checkpoint_file, index=False)
        print(f"💾 Checkpoint saved: {len(scores)} total items processed")
        
        # Cleanup drivers for this batch
        for _ in range(max_workers):
            try:
                cleanup_driver()
            except:
                pass
        
        # Brief pause between batches
        time.sleep(2)
    
    # Final save and cleanup
    final_df = pd.DataFrame(scores)
    final_df.to_excel("BNPPF/bnp_paribas_fortis_b2_final_results.xlsx", index=False)
    
    # Summary
    if len(final_df) > 0:
        overall_score = final_df["Compliance Level"].mean()
        print(f"\n🌐 Overall CEFR B2 Accessibility Score: {overall_score:.2f}%")
        
        typology_avg = final_df.groupby("Page Type")["Compliance Level"].mean()
        for typ, score in typology_avg.items():
            status = "✅" if score >= 70 else "⚠️"
            print(f"{status} {typ} pages: {score:.2f}% average compliance")
    
    print(f"\n✅ Analysis complete! Results saved to: bnp_paribas_fortis_b2_final_results.xlsx")
    return final_df

# ---------------------- EXECUTION ----------------------
if __name__ == "__main__":
    excel_file_path = "BNPPF/bnppf_urls.xlsx"
    # Adjust parameters for your system:
    # max_workers: Number of parallel threads (4-8 recommended)
    # batch_size: URLs processed before checkpoint (20-50 recommended)
    analyze_bnp_b2_compliance(excel_file_path, max_workers=6, batch_size=30)
