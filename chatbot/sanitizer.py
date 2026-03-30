import re
import bleach

# Longueur maximale d'un message utilisateur
MAX_LENGTH = 500

# Patterns de prompt injection connus
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(your\s+)?(previous\s+)?instructions?",
    r"you\s+are\s+now",
    r"act\s+as\s+(a\s+)?(?!blackvue)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(your\s+)?(instructions?|rules?|guidelines?)",
    r"new\s+instructions?",
    r"system\s*:",
    r"<\s*system\s*>",
    r"\[system\]",
    r"assistant\s*:",
    r"<\s*assistant\s*>",
    r"reveal\s+your\s+(prompt|instructions?|system)",
    r"what\s+are\s+your\s+instructions?",
    r"repeat\s+(everything|all)\s+(above|before)",
    r"print\s+(your\s+)?(system\s+)?prompt",
]

# Patterns de tentative d'exécution de code
CODE_EXECUTION_PATTERNS = [
    r"(import|require|include)\s+\w+",
    r"(exec|eval|system|os\.)\s*\(",
    r"subprocess",
    r"__import__",
    r"\$\{.*\}",         # template injection
    r"`[^`]+`",          # backtick execution
    r"<script.*?>",
    r"javascript\s*:",
    r"on\w+\s*=",        # HTML event handlers
]

# Patterns SQL
SQL_INJECTION_PATTERNS = [
    r"(--|#|\/\*)",                          # commentaires SQL
    r"\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b",
    r"'\s*(OR|AND)\s*'?\d",                 # OR/AND classiques
    r"1\s*=\s*1",
    r";\s*(DROP|DELETE|INSERT|UPDATE)",
]


class SanitizationError(Exception):
    """Levée quand l'entrée est considérée dangereuse."""
    pass


def sanitize(text: str) -> str:
    """
    Nettoie et valide un message utilisateur.
    Lève SanitizationError si une menace est détectée.
    Retourne le texte nettoyé si tout est bon.
    """
    if not isinstance(text, str):
        raise SanitizationError("Entrée invalide.")

    # 1. Longueur
    if len(text) > MAX_LENGTH:
        raise SanitizationError(f"Message trop long (max {MAX_LENGTH} caractères).")

    # 2. Suppression des caractères de contrôle (sauf espaces normaux)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 3. Nettoyage HTML (supprime toutes les balises)
    text = bleach.clean(text, tags=[], strip=True)

    # 4. Détection prompt injection
    lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            raise SanitizationError("Message refusé : tentative d'injection de prompt détectée.")

    # 5. Détection injection de code
    for pattern in CODE_EXECUTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise SanitizationError("Message refusé : contenu potentiellement dangereux détecté.")

    # 6. Détection injection SQL
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise SanitizationError("Message refusé : tentative d'injection SQL détectée.")

    return text.strip()
