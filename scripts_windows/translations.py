"""Traductions anglaises de l'interface, indexées par le texte français.

Les ``{noms}`` entre accolades sont remplacés par ``tr`` : ils doivent être les mêmes des deux côtés.
Les mots-clés du journal (terminé/finished, échec/failed, refusée/denied, fermée/closed…) servent
à colorer les lignes : voir ``core.classify``.

English translations of the interface, keyed by the French text.

The ``{names}`` in braces are replaced by ``tr``: they must be the same on both sides.
The log keywords (terminé/finished, échec/failed, refusée/denied, fermée/closed…) are used
to color the lines: see ``core.classify``.
"""

from __future__ import annotations

EN: dict[str, str] = {
    # -- navigation et sections / navigation and sections ----------------------------
    "Accueil": "Home",
    "Bureau": "Desktop",
    "Raccourcis et dossiers ajoutés au Bureau.": "Shortcuts and folders added to the desktop.",
    "Registre": "Registry",
    "Réglages système, toujours réversibles.": "System tweaks, always reversible.",
    "Système": "System",
    "Points de restauration et entretien de Windows.": "Restore points and Windows maintenance.",
    "En ligne": "Online",
    "Outils de la communauté, téléchargés au lancement.": "Community tools, downloaded when launched.",
    "Autres": "Other",
    "Divers, et les scripts ajoutés à scripts.json.": "Miscellaneous, and scripts added to scripts.json.",
    "Favoris": "Favorites",
    "Tes propres scripts .bat et .cmd, pris dans le dossier des scripts.": (
        "Your own .bat and .cmd scripts, taken from the scripts folder."
    ),
    "Journal": "Log",
    "Paramètres": "Settings",
    "Thème sombre": "Dark theme",
    "Thème clair": "Light theme",
    "Réduire ou agrandir le volet": "Collapse or expand the pane",
    # -- accueil / home --------------------------------------------------------------
    "Raccourcis, Registre et outils Windows, réunis au même endroit.": (
        "Shortcuts, Registry and Windows tools, all in one place."
    ),
    "{count} scripts": "{count} scripts",
    "{count} annulations": "{count} undo options",
    "Administrateur": "Administrator",
    "Utilisateur standard": "Standard user",
    "Tous les scripts, rangés par usage. Ctrl+F pour chercher.": (
        "All scripts, sorted by purpose. Press Ctrl+F to search."
    ),
    "Rechercher un script": "Search scripts",
    "Aucun script ne correspond à « {query} ».": "No script matches “{query}”.",
    "Aucun script dans cette catégorie.": "No scripts in this category.",
    # -- cartes / cards --------------------------------------------------------------
    "Lancer": "Run",
    "En cours…": "Running…",
    "Plus d’options": "More options",
    "Fichier introuvable": "File not found",
    "Ouvrir l’emplacement du fichier": "Open file location",
    "Copier le chemin": "Copy path",
    "Créer un point de restauration, puis lancer": "Create a restore point, then run",
    "Lancer en administrateur": "Run as administrator",
    "Modifier le script": "Edit script",
    "Retirer des favoris": "Remove from favorites",
    "Réversible": "Reversible",
    "Flèches des raccourcis": "Shortcut arrows",
    "flèches raccourcis": "shortcut arrows",
    "Masque la petite flèche des icônes de raccourcis, pour tous les utilisateurs. "
    "L’état d’origine est enregistré : désactiver l’interrupteur le restaure.": (
        "Hides the small arrow on shortcut icons, for all users. "
        "The original state is saved: turning the switch off restores it."
    ),
    "Masquées": "Hidden",
    "Visibles": "Visible",
    # -- favoris / favorites ---------------------------------------------------------
    "Ajouter un favori": "Add a favorite",
    "Ouvrir le dossier": "Open folder",
    "Aucun favori pour l’instant. Dépose tes scripts .bat ou .cmd dans le dossier des scripts, "
    "puis « Ajouter un favori » pour les retrouver ici.": (
        "No favorites yet. Put your .bat or .cmd scripts in the scripts folder, "
        "then use “Add a favorite” to find them here."
    ),
    "Aucun autre script .bat ou .cmd dans le dossier": "No other .bat or .cmd script in the folder",
    "Ouvrir le dossier des scripts": "Open the scripts folder",
    "Script personnel, ajouté depuis le dossier des scripts.": (
        "Personal script, added from the scripts folder."
    ),
    "Favori ajouté": "Favorite added",
    "{filename} est dans la section Favoris.": "{filename} is in the Favorites section.",
    "Favori retiré": "Favorite removed",
    "{filename} reste dans le dossier des scripts.": "{filename} stays in the scripts folder.",
    # -- journal / log ---------------------------------------------------------------
    "Lancements récents, d’après launcher.log.": "Recent runs, from launcher.log.",
    "Aucun lancement pour l’instant.": "Nothing has been run yet.",
    "Aujourd’hui": "Today",
    "Hier": "Yesterday",
    "%d/%m/%Y": "%Y-%m-%d",
    # Lignes de launcher.log (mots-clés de core.classify)
    # launcher.log lines (keywords of core.classify)
    "lancé": "started",
    "lancé en administrateur": "started as administrator",
    "terminé (code 0)": "finished (code 0)",
    "échec (code {code})": "failed (code {code})",
    "fenêtre fermée par l'utilisateur": "window closed by the user",
    "élévation refusée": "elevation denied",
    "lancement impossible ({error})": "launch failed ({error})",
    "Point de restauration": "Restore point",
    "créé": "created",
    "un point de moins de 24 h existe déjà, Windows n’en crée pas d’autre": (
        "a restore point less than 24 hours old already exists, so Windows won’t create another one"
    ),
    "protection du système désactivée": "system protection is disabled",
    "fenêtre fermée avant la fin": "window closed before the end",
    "création lancée ({target})": "creation started ({target})",
    "création impossible ({error})": "creation failed ({error})",
    "avant {filename}": "before {filename}",
    "point manuel": "manual point",
    # -- paramètres / settings -------------------------------------------------------
    "Apparence": "Appearance",
    "Thème de l’application": "App theme",
    "Clair, sombre ou comme Windows.": "Light, dark or the same as Windows.",
    "Clair": "Light",
    "Sombre": "Dark",
    "Utiliser le paramètre système": "Use system setting",
    "Langue": "Language",
    "Français, anglais ou comme Windows. Appliquée au prochain démarrage.": (
        "French, English or the same as Windows. Applied the next time the app starts."
    ),
    "Utiliser la langue du système": "Use system language",
    "Couleur d’accentuation": "Accent color",
    "Boutons, sélection et bandeau d’accueil.": "Buttons, selection and home banner.",
    "Effet Mica": "Mica effect",
    "Laisse transparaître le fond d’écran, comme les applis Windows 11. Appliqué au prochain démarrage.": (
        "Lets the wallpaper show through, like Windows 11 apps. Applied the next time the app starts."
    ),
    "Disponible sous Windows 11 uniquement.": "Only available on Windows 11.",
    "Le changement s’appliquera au prochain démarrage.": (
        "The change will apply the next time the app starts."
    ),
    "Transparence": "Transparency",
    "Rend le fond, le panneau et les cartes translucides ; le texte reste net. "
    "Windows floute ce qui se trouve derrière la fenêtre (ou montre Mica s’il est activé).": (
        "Makes the background, pane and cards translucent; text stays sharp. "
        "Windows blurs what is behind the window (or shows Mica if it is on)."
    ),
    "Rend toute la fenêtre transparente (le flou n’existe qu’à partir de Windows 11).": (
        "Makes the whole window transparent (blur is only available from Windows 11)."
    ),
    "{value} %": "{value}%",
    "Sécurité": "Safety",
    "Point de restauration automatique": "Automatic restore point",
    "Avant chaque script qui demande les droits administrateur ou modifie le Registre "
    "(flèches des raccourcis, WinUtil). Si la création échoue, le script n’est pas lancé.": (
        "Before each script that needs administrator rights or changes the Registry "
        "(shortcut arrows, WinUtil). If creation fails, the script is not run."
    ),
    "Points de restauration": "Restore points",
    "Crée un point maintenant, supprime les anciens pour libérer de la place (le plus "
    "récent est gardé), ou ouvre la Restauration du système pour revenir à un point.": (
        "Create a point now, delete old ones to free up space (the most recent is kept), "
        "or open System Restore to go back to a point."
    ),
    "Créer": "Create",
    "Création…": "Creating…",
    "Nettoyer…": "Clean up…",
    "Supprime tous les points sauf le plus récent, après confirmation": (
        "Deletes all points except the most recent, after confirmation"
    ),
    "Restaurer…": "Restore…",
    "Ouvre la Restauration du système de Windows": "Opens Windows System Restore",
    "Compte": "Account",
    "Droits administrateur": "Administrator rights",
    "Inutile en temps normal : chaque script demande lui-même l’élévation quand il en a besoin.": (
        "Not needed normally: each script asks for elevation itself when it needs it."
    ),
    "Administrateur : actif": "Administrator: active",
    "Relancer en administrateur": "Restart as administrator",
    "Dossiers": "Folders",
    "Dossier des scripts": "Scripts folder",
    "Réglages et journal": "Settings and log",
    "Ouvrir": "Open",
    "À propos": "About",
    "© 2026 Bulls64, licence MIT. Code source : github.com/Bulls64/Script-Manager. "
    "WinUtil et Super God Mode restent soumis à leurs propres licences.": (
        "© 2026 Bulls64, MIT License. Source code: github.com/Bulls64/Script-Manager. "
        "WinUtil and Super God Mode remain under their own licenses."
    ),
    # -- notifications / notifications -----------------------------------------------
    "Fermer": "Close",
    "Windows requis": "Windows required",
    "Les scripts ne peuvent être lancés que sous Windows.": "Scripts can only be run on Windows.",
    "Dossier des scripts introuvable": "Scripts folder not found",
    "Les scripts doivent être dans {folder}.": "Scripts must be in {folder}.",
    "Script introuvable": "Script not found",
    "{path} est absent. Garde les scripts dans le dossier « {folder} ».": (
        "{path} is missing. Keep the scripts in the “{folder}” folder."
    ),
    "{filename} est absent du dossier des scripts.": "{filename} is missing from the scripts folder.",
    "Demande administrateur annulée": "Administrator request canceled",
    "{title} n’a pas été lancé.": "{title} was not run.",
    "{title} est lancé.": "{title} is running.",
    "Impossible de lancer le script": "Couldn’t run the script",
    "Point de restauration en cours": "Restore point in progress",
    "Attends la fin de la création en cours.": "Wait for the current creation to finish.",
    "Point de restauration…": "Restore point…",
    "Point de restauration annulé": "Restore point canceled",
    "Élévation refusée.": "Elevation denied.",
    "Point de restauration impossible": "Couldn’t create a restore point",
    "Point de restauration créé": "Restore point created",
    "Point de restauration non créé": "Restore point not created",
    "Échec du point de restauration": "Restore point failed",
    "Point de restauration : {text}.": "Restore point: {text}.",
    "Script non lancé": "Script not run",
    "Point récent conservé": "Recent point kept",
    "Flèches masquées": "Arrows hidden",
    "Flèches visibles": "Arrows visible",
    "Flèches des raccourcis inchangées": "Shortcut arrows unchanged",
    "Terminé": "Finished",
    "Fenêtre fermée": "Window closed",
    "Échec": "Failed",
    "{name} : {text}.": "{name}: {text}.",
    "Scripts en cours": "Scripts running",
    "Attends la fin des scripts en cours avant de relancer l’application.": (
        "Wait for the running scripts to finish before restarting the app."
    ),
    "L’application reste en utilisateur standard.": "The app stays a standard user.",
    "Élévation impossible": "Couldn’t elevate",
    # Messages internes de launcher.log
    # Internal launcher.log messages
    "Réglages non enregistrés dans %s": "Settings not saved to %s",
    "Application relancée en administrateur": "App restarted as administrator",
    "Fermeture avec %d script(s) encore en cours": "Closing with %d script(s) still running",
    # -- erreurs de scripts.json / scripts.json errors -------------------------------
    "Impossible de charger {path} :\n{error}": "Couldn’t load {path}:\n{error}",
    "lecture impossible ({error}).": "can’t be read ({error}).",
    "JSON invalide, ligne {line} colonne {column}.": "invalid JSON, line {line} column {column}.",
    "le fichier doit contenir un objet avec une liste « scripts ».": (
        "the file must contain an object with a “scripts” list."
    ),
    "la liste « scripts » est vide.": "the “scripts” list is empty.",
    "script n° {number}": "script no. {number}",
    "{where} : un objet est attendu.": "{where}: an object is expected.",
    "{where} : champ inconnu {names}.": "{where}: unknown field {names}.",
    "{where} : « {key} » doit être un texte non vide.": "{where}: “{key}” must be non-empty text.",
    "{where} : « {key} » doit valoir true ou false.": "{where}: “{key}” must be true or false.",
    "{where} : « {key} » doit valoir {values}.": "{where}: “{key}” must be one of {values}.",
    "{where} : « {filename} » doit être un nom de fichier, sans dossier.": (
        "{where}: “{filename}” must be a file name, without a folder."
    ),
    "{where} : « {filename} » doit être un fichier .bat ou .cmd.": (
        "{where}: “{filename}” must be a .bat or .cmd file."
    ),
    "{where} : « {filename} » apparaît deux fois.": "{where}: “{filename}” appears twice.",
    "il est dans Téléchargements": "it is in Downloads",
    "il est sur un lecteur amovible": "it is on a removable drive",
    "il est sur un lecteur réseau": "it is on a network drive",
    "Dossier des scripts exposé": "Scripts folder exposed",
    "Les scripts administrateur sont lancés depuis {folder}, mais {reason} : d’autres "
    "programmes peuvent les modifier. Range Script Manager dans un dossier à toi, "
    "sur un disque interne.": "Administrator scripts are run from {folder}, but {reason}: other programs "
    "can change them. Move Script Manager to a folder of your own, on an internal drive.",
    "Version {version} disponible : télécharge-la depuis la page de la release.": (
        "Version {version} is available: download it from the release page."
    ),
    "Dossier protégé": "Protected folder",
    "Installer": "Install",
    "Échec de la mise à jour": "Update failed",
    "Mises à jour": "Updates",
    "Archive trop volumineuse.": "Archive too large.",
    "Impossible de joindre GitHub ({error}).": "Cannot reach GitHub ({error}).",
    "Vérification impossible : {error}": "Check failed: {error}",
    "Mise à jour reportée": "Update postponed",
    "Mise à jour disponible": "Update available",
    "Vérification impossible": "Check failed",
    "Archive incomplète : {name} ou {manifest} manque.": (
        "Incomplete archive: {name} or {manifest} is missing."
    ),
    "Échec de la mise à jour : {error}": "Update failed: {error}",
    "Téléchargement de la version {version}…": "Downloading version {version}…",
    "Aucune mise à jour": "No update",
    "Téléchargement impossible ({error}).": "Download failed ({error}).",
    "Script Manager {version} est disponible : Paramètres › Mises à jour.": (
        "Script Manager {version} is available: Settings › Updates."
    ),
    "Version {version}": "Version {version}",
    "Version {version} disponible.": "Version {version} is available.",
    "Attends la fin des scripts en cours, puis relance l’installation.": (
        "Wait for the running scripts to finish, then start the installation again."
    ),
    "Script Manager est à jour (dernière version : {version}).": (
        "Script Manager is up to date (latest version: {version})."
    ),
    "Rechercher": "Check now",
    "Réponse de GitHub inattendue.": "Unexpected answer from GitHub.",
    "mise à jour vers la version {version}": "updating to version {version}",
    "Pas encore vérifié.": "Not checked yet.",
    "Vérification des mises à jour impossible : %s": "Update check failed: %s",
    "Interroge les releases GitHub du projet à chaque lancement, sans rien installer.": (
        "Checks the project’s GitHub releases at every start, without installing anything."
    ),
    "mise à jour impossible ({error})": "update failed ({error})",
    "Adresse de téléchargement refusée : {url}": "Download address refused: {url}",
    "Voir la release": "Open the release",
    "Installer la mise à jour": "Install the update",
    "Tâche de fond en échec": "Background task failed",
    "Empreinte SHA-256 incorrecte : l’archive n’est pas installée.": (
        "Wrong SHA-256 hash: the archive is not installed."
    ),
    "Script Manager ne peut pas écrire dans {folder}. Télécharge la mise à jour depuis la "
    "page de la release.": (
        "Script Manager cannot write to {folder}. Download the update from the release page."
    ),
    "Rechercher les mises à jour au démarrage": "Check for updates at startup",
    "Cette release ne contient pas d’archive à installer.": "This release has no archive to install.",
    "Script Manager va télécharger la version {version}, se fermer, installer les nouveaux "
    "fichiers puis redémarrer. Tes favoris et tes réglages sont conservés.": (
        "Script Manager will download version {version}, close, install the new files and start "
        "again. Your favorites and settings are kept."
    ),
    "Recherche d’une nouvelle version…": "Looking for a new version…",
    "Archive refusée : chemin invalide ({name}).": "Archive refused: invalid path ({name}).",
    "Tu as déjà la dernière version.": "You already have the latest version.",
    "Nouveautés": "What's new",
    "Nouveautés de la v{version}": "What's new in v{version}",
    "Ce qui a changé dans cette version de Script Manager.": (
        "What changed in this version of Script Manager."
    ),
    "Aucune nouveauté listée pour cette version.": "No changes listed for this version.",
    "Historique complet : CHANGELOG.md sur GitHub.": "Full history: CHANGELOG.md on GitHub.",
    "Afficher les nouveautés après une mise à jour": "Show what's new after an update",
    (
        "Ouvre la liste des nouveautés au premier lancement d’une nouvelle version. "
        "« Nouveautés » la rouvre à tout moment."
    ): (
        "Opens the list of changes the first time a new version starts. "
        '"What\'s new" opens it again at any time.'
    ),
    (
        "Fenêtre « Nouveautés » : elle s’affiche au premier lancement d’une nouvelle version "
        "et liste ce qui a changé."
    ): '"What\'s new" window: it opens the first time a new version starts and lists what changed.',
    "Elle peut être rouverte à tout moment depuis Paramètres › Mises à jour › Nouveautés.": (
        "It can be opened again at any time from Settings › Updates › What's new."
    ),
    (
        "Son affichage automatique se désactive dans Paramètres › Mises à jour, avec "
        "« Afficher les nouveautés après une mise à jour »."
    ): (
        "Its automatic display can be turned off in Settings › Updates, with "
        '"Show what\'s new after an update".'
    ),
    (
        "Mises à jour depuis les releases GitHub : recherche automatique au démarrage "
        "(désactivable) et bouton « Rechercher » dans Paramètres › Mises à jour."
    ): (
        "Updates from GitHub releases: automatic check at startup (can be turned off) "
        'and a "Check now" button in Settings › Updates.'
    ),
    (
        "« Installer » télécharge l’archive, vérifie son empreinte SHA-256, puis ferme l’appli, "
        "copie les nouveaux fichiers et la relance."
    ): (
        '"Install" downloads the archive, checks its SHA-256 hash, then closes the app, '
        "copies the new files and starts it again."
    ),
    "Réglages, favoris et scripts ajoutés à scripts.json sont conservés.": (
        "Settings, favorites and scripts added to scripts.json are kept."
    ),
    (
        "Version ARM64 pour les PC ARM (Snapdragon, PC Copilot+) : chaque release propose "
        "aussi une archive « -arm64 », native, à côté de l’archive x64."
    ): (
        "ARM64 version for ARM PCs (Snapdragon, Copilot+ PCs): each release also has a native "
        '"-arm64" archive next to the x64 one.'
    ),
    (
        "Les mises à jour téléchargent l’archive du processeur : sur un PC ARM, la version x64 "
        "émulée est remplacée par la version ARM64 native."
    ): (
        "Updates download the archive for the processor: on an ARM PC, the emulated x64 version "
        "is replaced by the native ARM64 version."
    ),
    "Paramètres › Mises à jour affiche l’architecture à côté du numéro de version.": (
        "Settings › Updates shows the architecture next to the version number."
    ),
}
