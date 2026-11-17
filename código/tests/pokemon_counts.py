import re
from collections import Counter


# First match wins. For example, Pikachu-Gmax counts as Gigantamax
# and Ogerpon-Wellspring-Tera counts as Terastal.
FORM_PATTERNS = {
    "mega_evolutions": r"^Mega |-Mega(?:-|$)",
    "gigantamax_forms": r"-Gmax$",
    "arceus_forms": r"^Arceus-",
    "totem_forms": r"-Totem$",
    "regional_forms": (
        r"^(?:Alolan|Galarian|Hisuian|Paldean) |^(?!Pikachu-).*-(?:Alola|Galar|"
        r"Hisui|Paldea)(?:$|-(?:Aqua|Blaze|Combat)$)"
    ),
    "silvally_forms": r"^Silvally-",
    "event_and_partner_forms": (
        r"^Pikachu-|^(?:Eevee-Starter|Pichu-Spiky-eared|Floette-Eternal|"
        r"Greninja-Bond|Zarude-Dada)$"
    ),
    "deoxys_forms": r"^Deoxys-",
    "rotom_appliances": r"^Rotom-",
    "genesect_drives": r"^Genesect-",
    "gender_forms": r"^(?:Meowstic|Indeedee|Basculegion|Oinkologne)-F$",
    "size_forms": r"^(?:Pumpkaboo|Gourgeist)-(?:Large|Small|Super)$",
    "primal_forms": r"^Primal |-Primal$",
    "origin_forms": r"-Origin$",
    "therian_forms": r"-Therian$",
    "fusion_forms": (
        r"^(?:Calyrex-(?:Ice|Shadow)(?:-Rider)?|Kyurem-(?:Black|White)|"
        r"Necrozma-(?:Dawn-Wings|Dusk-Mane))$"
    ),
    "weather_forms": r"^Castform-|^Cherrim-Sunshine$",
    "battle_forms": (
        r"^(?:Darmanitan-(?:Galar-)?Zen|Meloetta-Pirouette|Greninja-Ash|"
        r"Aegislash-Blade|Zygarde-Complete|Wishiwashi-School|Minior-Meteor|"
        r"Mimikyu-Busted|Necrozma-Ultra|Cramorant-(?:Gorging|Gulping)|"
        r"Eiscue-Noice|Morpeko-Hangry|Zacian-Crowned|Zamazenta-Crowned|"
        r"Eternatus-Eternamax|Palafin-Hero|Xerneas-Neutral)$"
    ),
    "terastal_forms": r"-Tera$|^Terapagos-(?:Stellar|Terastal)$",
    "ogerpon_masks": r"^Ogerpon-",
    "burmy_cloaks": r"^(?:Burmy|Wormadam)-(?:Sandy|Trash)$",
    "minior_cores": r"^Minior-",
    "authenticity_forms": (
        r"^(?:Sinistea-Antique|Polteageist-Antique|"
        r"Poltchageist-Artisan|Sinistcha-Masterpiece)$"
    ),
    "lycanroc_forms": r"^Lycanroc-(?:Dusk|Midnight)$",
    "basculin_forms": r"^Basculin-",
    "tatsugiri_forms": r"^Tatsugiri-",
    "color_and_pattern_forms": (
        r"^(?:Alcremie|Deerling|Vivillon|Shellos|Gastrodon|Squawkabilly|Magearna)-"
    ),
}


def assert_pokemon_counts(
    test, names, expected_counts, additional_forms, representatives=()
):
    test.assertEqual(len(names), sum(expected_counts.values()))
    test.assertEqual(len(names), len(set(names)), "Duplicate Pokémon names")

    counts = Counter()
    matched_additional_forms = set()
    for name in names:
        if name in representatives:
            category = "unique_species"
        elif name in additional_forms:
            category = "additional_forms"
            matched_additional_forms.add(name)
        else:
            category = next(
                (key for key, pattern in FORM_PATTERNS.items() if re.search(pattern, name)),
                "unique_species",
            )
        counts[category] += 1

    test.assertEqual(matched_additional_forms, additional_forms)
    for category in sorted(counts.keys() | expected_counts.keys()):
        with test.subTest(category=category):
            test.assertEqual(counts[category], expected_counts.get(category, 0))
