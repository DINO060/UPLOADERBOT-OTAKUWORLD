import re
from models.types import ParsedFilename


def parse_filename(filename: str) -> ParsedFilename:
    """
    Parse un nom de fichier anime/manga en extrayant:
    - Titre
    - Numéro d'épisode (EP10, S01E03, 10)
    - Saison
    - Langue (VF, VOSTFR, VO, VOSTA)
    - @username Telegram

    Exemples:
        "Let's Play EP10 VF @djd208.mp4" → title="Let's Play", ep=10, lang="VF"
        "One Piece S01E003 VOSTFR.mkv"   → title="One Piece", s=1, ep=3, lang="VOSTFR"
        "Naruto 145 VF.mp4"              → title="Naruto", ep=145, lang="VF"
    """
    result = ParsedFilename(title="", raw=filename)

    # Supprimer l'extension
    name = re.sub(r'\.\w{2,4}$', '', filename)

    # 1. Extraire @username (toujours du bruit)
    match = re.search(r'\s*@(\w+)', name)
    if match:
        result.username = match.group(1)
        name = name[:match.start()] + name[match.end():]

    # 2. Extraire la langue
    match = re.search(r'\b(VOSTFR|VOSTA|VOST|VF|VO)\b', name, re.IGNORECASE)
    if match:
        result.language = match.group(1).upper()
        name = name[:match.start()] + name[match.end():]

    # 3. Extraire S01E03 ou S1E3
    match = re.search(r'\bS(\d{1,2})\s*[Ee](\d{1,4})\b', name)
    if match:
        result.season = int(match.group(1))
        result.episode = int(match.group(2))
        name = name[:match.start()] + name[match.end():]
    else:
        # 4. Extraire EP10 ou Episode 10
        match = re.search(r'\b(?:EP|Episode)\s*(\d{1,4})\b', name, re.IGNORECASE)
        if match:
            result.episode = int(match.group(1))
            name = name[:match.start()] + name[match.end():]
        else:
            # 5. Numéro isolé en fin de chaîne ex: "Naruto 145"
            match = re.search(r'\s+(\d{1,4})\s*$', name)
            if match:
                result.episode = int(match.group(1))
                name = name[:match.start()]

    # 6. Nettoyer le titre restant
    name = re.sub(r'[\[\(][^\]\)]*[\]\)]', '', name)  # supprimer [720p] (HD) etc.
    name = re.sub(r'\s+', ' ', name).strip(' -_.')
    result.title = name

    return result
