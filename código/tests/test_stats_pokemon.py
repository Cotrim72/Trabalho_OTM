import csv
import unittest
from pathlib import Path

from pokemon_counts import assert_pokemon_counts


UNIQUE_SPECIES_COUNT = 1025
MEGA_EVOLUTION_COUNT = 97
GIGANTAMAX_FORM_COUNT = 34
ARCEUS_FORM_COUNT = 17

# Additional forms in this CSV:
# Dudunsparce-Three-Segment, Gimmighoul-Roaming, Hoopa-Unbound,
# Keldeo-Resolute, Maushold-Four, Oricorio-Pa'u, Oricorio-Pom-Pom,
# Oricorio-Sensu, Rockruff-Dusk, Shaymin-Sky, Toxtricity-Low-Key,
# Ursaluna-Bloodmoon, Urshifu-Rapid-Strike, Zygarde-10%.
ADDITIONAL_FORM_COUNT = 14
ADDITIONAL_FORMS = {
    "Dudunsparce-Three-Segment",
    "Gimmighoul-Roaming",
    "Hoopa-Unbound",
    "Keldeo-Resolute",
    "Maushold-Four",
    "Oricorio-Pa'u",
    "Oricorio-Pom-Pom",
    "Oricorio-Sensu",
    "Rockruff-Dusk",
    "Shaymin-Sky",
    "Toxtricity-Low-Key",
    "Ursaluna-Bloodmoon",
    "Urshifu-Rapid-Strike",
    "Zygarde-10%",
}

EXPECTED_COUNTS = {
    "unique_species": UNIQUE_SPECIES_COUNT,
    "mega_evolutions": MEGA_EVOLUTION_COUNT,
    "gigantamax_forms": GIGANTAMAX_FORM_COUNT,
    "arceus_forms": ARCEUS_FORM_COUNT,
    "totem_forms": 12,
    "regional_forms": 57,
    "silvally_forms": 17,
    "event_and_partner_forms": 20,
    "deoxys_forms": 3,
    "rotom_appliances": 5,
    "genesect_drives": 4,
    "gender_forms": 4,
    "size_forms": 6,
    "primal_forms": 2,
    "origin_forms": 3,
    "therian_forms": 4,
    "fusion_forms": 6,
    "weather_forms": 4,
    "battle_forms": 19,
    "terastal_forms": 6,
    "ogerpon_masks": 3,
    "burmy_cloaks": 4,
    "minior_cores": 6,
    "authenticity_forms": 4,
    "lycanroc_forms": 2,
    "basculin_forms": 2,
    "tatsugiri_forms": 2,
    "color_and_pattern_forms": 35,
    "additional_forms": ADDITIONAL_FORM_COUNT,
}


class TestStatsPokemon(unittest.TestCase):
    def test_total_pokemon_count(self):
        csv_path = Path(__file__).resolve().parents[1] / "stats_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        self.assertFalse(any(row["Tier"].startswith("CAP") for row in rows))
        names = [row["Pokemon"] for row in rows]
        self.assertFalse(
            any(name == "MissingNo." or name.startswith("Pokestar ") for name in names)
        )
        assert_pokemon_counts(self, names, EXPECTED_COUNTS, ADDITIONAL_FORMS)


if __name__ == "__main__":
    unittest.main()
