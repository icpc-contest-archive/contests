#!/usr/bin/env python3
"""Build the location tree (locations.yaml) and the per-contest `sites:` lists.

One-shot, resumable migration (phase C, second half of the 2026-11-02 redesign;
DEFINITIONS.md, Locations). Re-running is a no-op: nodes already in locations.yaml keep
their ids (matched by ISO code, admin code, geonameid or name key), new ones are added,
and every contest's `sites:` is recomputed deterministically from the same inputs.

Inputs
  data/cms-sites.json          CMS site records per CMS contest id (name, free-text location,
                               sometimes city/state/country, type, delivery)
  series/*.yaml                contests (cms_ids, free-text location, series region)
  geonamescache (offline)      GeoNames cities >= 1000 inhabitants, countries, US states
  KNOWN_INSTITUTIONS (below)   hand table: institutions whose city is not in their name

Resolution, per site: country (CMS country > a country name in the text > a city lookup
constrained to the series' region's countries > the CMS geographic area), city (CMS city >
the text > the city read off the institution's name: "University of X", "X University",
"Campus X", "ACRONYM City"), institution (a label with an institution word or an acronym).
Administrative CMS sites become {type: administrative}; online delivery becomes
{type: online}. Everything uncertain goes to the review file, never silently merged.

Outputs
  locations.yaml               the tree: country > region > city > institution
  series/*.yaml                each contest gets `sites: [{location, name?, date?, type?}]`
  data/locations-review-<date>.md   what needs a human (unresolved, ambiguous, inferred, dups)

Usage: python3 tools/migrate_locations.py [--dry-run] [--review PATH]
  --dry-run writes only the review file. To rebuild from scratch, delete locations.yaml first
  (ids of nodes still referenced by series/*.yaml then come back identical, since the id
  scheme is a function of the data).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODAY = datetime.date.today().isoformat()
LOC_PATH = ROOT / "locations.yaml"
TOOL = "migrate_locations.py (sites, 2026-11-02)"

# --------------------------------------------------------------------------------------
# Country sets per ICPC super-region (used only to disambiguate; not a membership rule)
# --------------------------------------------------------------------------------------
ARAB_ASIA = {"SA", "AE", "QA", "KW", "BH", "OM", "YE", "IQ", "SY", "LB", "JO", "PS"}
NE_CORE = {"RU", "BY", "KZ", "KG", "UZ", "AM", "AZ", "GE", "TJ", "TM", "UA"}
ASIA_WEST = {"IN", "PK", "BD", "IR", "AF", "LK", "NP", "BT", "MV"}
ASIA_PACIFIC = {"JP", "KR", "TW", "SG", "MY", "ID", "TH", "VN", "PH", "MM", "AU", "NZ", "MN",
                "KH", "LA", "BN", "FJ", "PG", "TL", "WS", "TO", "VU", "SB", "NC", "PF", "GU"}
ASIA_EAST = {"CN", "HK", "MO", "KP"}
NORTH_AMERICA = {"US", "CA"}

# region + state codes we keep as `region` nodes
US_CA_AU_REGIONS = {
    "CA": {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
           "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
           "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
           "SK": "Saskatchewan", "YT": "Yukon"},
    "AU": {"ACT": "Australian Capital Territory", "NSW": "New South Wales", "NT": "Northern Territory",
           "QLD": "Queensland", "SA": "South Australia", "TAS": "Tasmania", "VIC": "Victoria",
           "WA": "Western Australia"},
}
# geonames admin1 codes for CA / AU (numeric in geonames) -> our code
GEONAMES_ADMIN = {
    "CA": {"01": "AB", "02": "BC", "03": "MB", "04": "NB", "05": "NL", "07": "NS", "08": "ON",
           "09": "PE", "10": "QC", "11": "SK", "12": "YT", "13": "NT", "14": "NU"},
    "AU": {"01": "ACT", "02": "NSW", "03": "NT", "04": "QLD", "05": "SA", "06": "TAS", "07": "VIC",
           "08": "WA"},
}
REGION_NAME_ALIASES = {
    "CA": {"Québec": "QC", "Newfoundland": "NL", "Labrador": "NL", "PEI": "PE"},
    "AU": {"A.C.T.": "ACT"},
    "US": {"Washington DC": "DC", "Washington D.C.": "DC", "D.C.": "DC", "Washington, DC": "DC"},
}

COUNTRY_ALIASES = {
    "usa": "US", "u.s.a.": "US", "u.s.a": "US", "u.s.": "US", "us": "US", "united states": "US",
    "united states of america": "US", "estados unidos": "US",
    "russia": "RU", "russian federation": "RU", "south korea": "KR", "korea": "KR",
    "republic of korea": "KR", "s. korea": "KR", "korea, republic of": "KR", "north korea": "KP",
    "taiwan": "TW", "taiwan, roc": "TW", "iran": "IR", "syria": "SY", "vietnam": "VN", "viet nam": "VN",
    "czech republic": "CZ", "czechia": "CZ", "uk": "GB", "u.k.": "GB", "united kingdom": "GB",
    "england": "GB", "scotland": "GB", "wales": "GB", "northern ireland": "GB", "great britain": "GB",
    "hong kong": "HK", "hongkong": "HK", "macau": "MO", "macao": "MO", "bolivia": "BO",
    "venezuela": "VE", "tanzania": "TZ", "laos": "LA", "brunei": "BN", "moldova": "MD",
    "macedonia": "MK", "north macedonia": "MK", "palestine": "PS", "palestinian territory": "PS",
    "ivory coast": "CI", "cote d'ivoire": "CI", "côte d'ivoire": "CI", "mexico": "MX", "méxico": "MX",
    "peru": "PE", "perú": "PE", "brasil": "BR", "brazil": "BR", "argentina": "AR", "chile": "CL",
    "colombia": "CO", "guatemala": "GT", "el salvador": "SV", "costa rica": "CR", "panama": "PA",
    "panamá": "PA", "nicaragua": "NI", "honduras": "HN", "cuba": "CU", "dominican republic": "DO",
    "república dominicana": "DO", "republica dominicana": "DO", "ecuador": "EC", "uruguay": "UY",
    "paraguay": "PY", "puerto rico": "PR", "trinidad and tobago": "TT",
    "jamaica": "JM", "bangladesh": "BD", "india": "IN", "pakistan": "PK", "sri lanka": "LK",
    "nepal": "NP", "indonesia": "ID", "malaysia": "MY", "singapore": "SG", "thailand": "TH",
    "philippines": "PH", "myanmar": "MM", "burma": "MM", "australia": "AU", "new zealand": "NZ",
    "mongolia": "MN", "japan": "JP", "china": "CN", "p.r. china": "CN", "pr china": "CN",
    "people's republic of china": "CN", "egypt": "EG", "morocco": "MA", "algeria": "DZ", "tunisia": "TN",
    "jordan": "JO", "kuwait": "KW", "lebanon": "LB", "oman": "OM", "qatar": "QA", "bahrain": "BH",
    "saudi arabia": "SA", "ksa": "SA", "uae": "AE", "united arab emirates": "AE", "iraq": "IQ",
    "yemen": "YE", "sudan": "SD", "libya": "LY", "south africa": "ZA", "nigeria": "NG", "kenya": "KE",
    "ghana": "GH", "senegal": "SN", "togo": "TG", "benin": "BJ", "cameroon": "CM", "ethiopia": "ET",
    "uganda": "UG", "rwanda": "RW", "mauritius": "MU", "madagascar": "MG", "zimbabwe": "ZW",
    "botswana": "BW", "namibia": "NA", "mozambique": "MZ", "angola": "AO", "zambia": "ZM",
    "malawi": "MW", "congo": "CG", "dr congo": "CD", "democratic republic of the congo": "CD",
    "burkina faso": "BF", "mali": "ML", "niger": "NE", "chad": "TD", "mauritania": "MR", "somalia": "SO",
    "djibouti": "DJ", "eritrea": "ER", "gabon": "GA", "guinea": "GN", "liberia": "LR",
    "sierra leone": "SL", "gambia": "GM", "cape verde": "CV", "lesotho": "LS", "eswatini": "SZ",
    "swaziland": "SZ", "burundi": "BI", "ukraine": "UA", "belarus": "BY", "kazakhstan": "KZ",
    "kyrgyzstan": "KG", "uzbekistan": "UZ", "tajikistan": "TJ", "turkmenistan": "TM", "armenia": "AM",
    "azerbaijan": "AZ", "georgia": None,  # ambiguous with the US state: handled by region
    "turkey": "TR", "türkiye": "TR", "turkiye": "TR", "israel": "IL", "cyprus": "CY", "greece": "GR",
    "bulgaria": "BG", "romania": "RO", "serbia": "RS", "croatia": "HR", "slovenia": "SI",
    "bosnia and herzegovina": "BA", "bosnia": "BA", "montenegro": "ME", "albania": "AL",
    "kosovo": "XK", "hungary": "HU", "slovakia": "SK", "slovak republic": "SK", "poland": "PL",
    "germany": "DE", "deutschland": "DE", "austria": "AT", "switzerland": "CH", "france": "FR",
    "italy": "IT", "italia": "IT", "spain": "ES", "españa": "ES", "portugal": "PT", "netherlands": "NL",
    "the netherlands": "NL", "holland": "NL", "belgium": "BE", "luxembourg": "LU", "luxemburg": "LU",
    "denmark": "DK", "sweden": "SE", "norway": "NO", "finland": "FI", "iceland": "IS", "estonia": "EE",
    "latvia": "LV", "lithuania": "LT", "ireland": "IE", "malta": "MT", "afghanistan": "AF",
    "cambodia": "KH", "fiji": "FJ", "papua new guinea": "PG", "canada": "CA", "chinese taipei": "TW",
}

# text that means "no physical site"
ONLINE_WORDS = {"internet", "online", "www", "virtual reality", "ether", "us online", "virtual",
                "remote", "the internet", "online site", "web"}
ADMIN_WORDS = {"administrative site location", "administration", "administrative", "admin"}
JUNK_WORDS = {"", "xxxx", "xxxxx", "x", "unofficial", "tbd", "tba", "n/a", "na", "-", "?", "none",
              "test", "unknown", "site", "ltd", "n.a."}
REGION_WORDS = {  # free-text that names a region, not a place: resolves to nothing, not an error
    "north america", "africa and arab", "africa & arab", "asia", "europe", "latin america",
    "south america", "central america", "worldwide", "caribbean", "south pacific",
    "the nordic countries", "benelux", "the benelux", "central europe", "northwest europe",
    "eastern europe", "southeastern europe", "southwestern europe", "northern eurasia",
    "asia pacific", "asia west", "asia east", "middle east", "north africa", "arab",
}

INSTITUTION_RE = re.compile(
    r"\b(univ(ersit(y|ies|ät|aet|é|e|à|a|as|ad|ade|at|eit|et|as|atea)|\.)?|u\.|college|colleges|institut[eo]?|"
    r"instituto|institution|polytechnic|politecnic[oa]|politehnica|politécnic[oa]|polytechnique|"
    r"school|schools|uni|escuela|escola|école|ecole|faculty|facultad|faculdade|academy|academia|akademi[ae]?|"
    r"hochschule|fachhochschule|technion|tecnológico|tecnologico|tecnológica|tecnologica|centro universitário|"
    r"centro universitario|iit|nit|iiit|bits|campus|high school|universitas|universiti|universite|"
    r"universidade|universidad|universität|universiteit|università|universitat|universitetet|"
    r"universitet|universiteti|universytet|technikon|conservatory|laboratory|lab|museum|center|centre|"
    r"state u|tech|ieee|sede|unidad|fundação|fundacion|fundación|ucb|uc)\b",
    re.I,
)
ACRONYM_RE = re.compile(r"^[A-Z][A-Z&\.\-]{1,9}$")


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def slug(s: str) -> str:
    s = strip_accents(s).lower()
    s = s.replace("&", " and ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "x"


def norm(s: str) -> str:
    """Match key for place/institution names."""
    s = strip_accents(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\buniv\.?\b", "university", s)
    s = re.sub(r"\binst\.?\b", "institute", s)
    s = re.sub(r"\btech\.\b", "technology", s)
    s = re.sub(r"\bst\.?\b", "saint", s)
    s = re.sub(r"\bu\.\s*(of|de)\b", "university \\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\b(the|of|at|de|del|la|el|los|las|da|do|di|du|des|der|den|and|y|e|in)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_full(s: str) -> str:
    """Like norm() but keeps articles/prepositions (country names: El Salvador, Costa Rica)."""
    s = strip_accents(s).lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def clean_text(s: str) -> str:
    s = re.sub(r"<br\s*/?>", ", ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip(" .;,")
    return s


# --------------------------------------------------------------------------------------
# gazetteer
# --------------------------------------------------------------------------------------
class Gazetteer:
    def __init__(self):
        import geonamescache
        gc = geonamescache.GeonamesCache(min_city_population=1000)
        self.countries = gc.get_countries()  # iso -> record
        self.country_by_name = {}
        for iso, rec in self.countries.items():
            self.country_by_name[norm_full(rec["name"])] = iso
        for k, v in COUNTRY_ALIASES.items():
            if v:
                self.country_by_name[norm_full(k)] = v
        self.continent = {iso: rec["continentcode"] for iso, rec in self.countries.items()}
        self.us_states = gc.get_us_states()  # code -> {name}
        self.state_codes = {"US": {c: r["name"] for c, r in self.us_states.items()}}
        self.state_codes.update(US_CA_AU_REGIONS)
        self.state_by_name = {}
        for cc, m in self.state_codes.items():
            for code, name in m.items():
                self.state_by_name[(cc, norm(name))] = code
                self.state_by_name[(cc, code.lower())] = code
            for name, code in REGION_NAME_ALIASES.get(cc, {}).items():
                self.state_by_name[(cc, norm(name))] = code
        self.state_names = {norm(n) for m in self.state_codes.values() for n in m.values()} | {
            norm(x) for x in ("Missouri", "Oregon", "Delaware", "Washington", "Georgia", "Virginia", "Indiana",
                              "Nevada", "Texas", "Florida", "Alabama", "Mississippi", "Kentucky", "Tennessee",
                              "Oriente", "Occidente", "Norte", "Sur", "Jalisco", "Veracruz", "Puebla state",
                              "Michoacán", "Nuevo León", "Sinaloa", "Sonora", "Chiapas", "Guerrero",
                              "Yucatán", "Quintana Roo", "Baja California", "Tabasco", "Hidalgo", "Morelos",
                              "Nayarit", "Coahuila", "Tamaulipas",
                              "Paraná", "Bahia", "Ceará", "Goiás", "Pará", "Pernambuco", "Sergipe",
                              "Maranhão", "Piauí", "Tocantins", "Amazonas", "Rondônia", "Alagoas", "Paraíba",
                              "Kerala", "Punjab", "Gujarat", "Assam", "Bihar", "Odisha", "Sindh", "Hubei",
                              "Hunan", "Henan", "Hebei", "Shandong", "Shanxi", "Shaanxi", "Jiangsu", "Zhejiang",
                              "Fujian", "Guangdong", "Guangxi", "Hainan", "Sichuan", "Yunnan", "Guizhou",
                              "Anhui", "Jiangxi", "Liaoning", "Jilin", "Heilongjiang", "Gansu", "Qinghai",
                              "Xinjiang", "Tibet", "Selangor", "Perak", "Penang", "Johor", "Sabah", "Sarawak",
                              "Normal")}
        self.cities = gc.get_cities()
        self.index: dict[str, list] = defaultdict(list)
        for gid, c in self.cities.items():
            self.index[norm(c["name"])].append(c)
            for a in c.get("alternatenames") or []:
                if a.isascii() or any(ord(ch) < 0x250 for ch in a):
                    k = norm(a)
                    if k and k != norm(c["name"]):
                        self.index[k].append(c)
        for lst in self.index.values():
            lst.sort(key=lambda c: -c["population"])

    def region_set(self, region: str | None) -> set[str] | None:
        if not region:
            return None
        eu = {iso for iso, cc in self.continent.items() if cc == "EU"} | {"TR", "CY", "IL"}
        eu -= {"RU", "BY"}
        if region == "North America":
            return NORTH_AMERICA
        if region == "Latin America":
            return {iso for iso, cc in self.continent.items() if cc in ("SA", "NA")} - {"US", "CA", "GL", "BM", "PM"}
        if region == "Europe":
            return eu
        if region == "Northern Eurasia":
            return NE_CORE
        if region == "Africa & Arab":
            return {iso for iso, cc in self.continent.items() if cc == "AF"} | ARAB_ASIA
        if region == "Asia West":
            return ASIA_WEST
        if region == "Asia Pacific":
            return ASIA_PACIFIC
        if region == "Asia East":
            return ASIA_EAST
        return None

    def country_from_text(self, s: str) -> str | None:
        return self.country_by_name.get(norm_full(s))

    def state_from_text(self, s: str, cc: str | None):
        """(cc, code) when `s` names a US state / CA province / AU state."""
        k = norm(s)
        for c in ([cc] if cc else ["US", "CA", "AU"]):
            code = self.state_by_name.get((c, k))
            if code:
                return c, code
        return None

    def admin_code(self, city: dict) -> str | None:
        cc = city["countrycode"]
        if cc == "US":
            return city["admin1code"] if city["admin1code"] in self.us_states else None
        if cc in GEONAMES_ADMIN:
            return GEONAMES_ADMIN[cc].get(city["admin1code"])
        return None

    def lookup(self, name: str, cc: str | None = None, admin: str | None = None,
               allowed: set[str] | None = None) -> list[dict]:
        k = norm(name)
        cands = self.index.get(k, [])
        if cc:
            cands = [c for c in cands if c["countrycode"] == cc]
        elif allowed:
            cands = [c for c in cands if c["countrycode"] in allowed]
        if admin:
            cands = [c for c in cands if self.admin_code(c) == admin]
        # a match on the primary name beats an alternate-name match, unless the primary match is a
        # hamlet and the alternate-name match a real city (Querétaro village vs Santiago de Querétaro)
        big = max((c["population"] for c in cands), default=0)

        def key(c):
            primary = norm(c["name"]) == k
            if primary and c["population"] < 5000 and big >= 20 * max(c["population"], 1):
                primary = False
            return (0 if primary else 1, -c["population"])
        return sorted(cands, key=key)


# --------------------------------------------------------------------------------------
# the tree
# --------------------------------------------------------------------------------------
class Tree:
    def __init__(self, gaz: Gazetteer, existing: dict | None):
        self.gaz = gaz
        self.nodes: dict[str, dict] = {}
        self.by_country: dict[str, str] = {}
        self.by_region: dict[tuple, str] = {}
        self.by_geoname: dict[int, str] = {}
        self.by_city_key: dict[tuple, str] = {}        # (cc, region_id|None, norm name) -> id
        self.by_inst_key: dict[tuple, str] = {}        # (city_id, norm name) -> id
        self.by_merge_key: dict[tuple, str] = {}       # (city_id, significant words) -> id
        self.added: list[str] = []
        for n in (existing or {}).get("locations") or []:
            self._register(n)

    def _register(self, n: dict) -> None:
        self.nodes[n["id"]] = n
        t = n["type"]
        if t == "country":
            self.by_country[n["iso"]] = n["id"]
        elif t == "region":
            self.by_region[(n["parent"], n.get("code"))] = n["id"]
        elif t == "city":
            if n.get("geonameid"):
                self.by_geoname[n["geonameid"]] = n["id"]
            for nm in [n["name"]] + list(n.get("aliases") or []):
                self.by_city_key[(self.country_of(n["parent"]), norm(nm))] = n["id"]
        elif t == "institution":
            for nm in [n["name"]] + list(n.get("aliases") or []):
                self.by_inst_key[(n["parent"], norm(nm))] = n["id"]
            mk = merge_key(n["name"], self.nodes[n["parent"]]["name"])
            if mk:
                self.by_merge_key.setdefault((n["parent"], mk), n["id"])

    def country_of(self, nid: str) -> str:
        n = self.nodes[nid]
        while n["type"] != "country":
            n = self.nodes[n["parent"]]
        return n["iso"]

    def _add(self, n: dict) -> str:
        assert n["id"] not in self.nodes, n["id"]
        self._register(n)
        self.added.append(n["id"])
        return n["id"]

    def add_alias(self, nid: str, name: str) -> None:
        n = self.nodes[nid]
        have = {n["name"].casefold()} | {a.casefold() for a in n.get("aliases") or []}
        if name.casefold() in have:
            return
        if name != n["name"] and name not in (n.get("aliases") or []):
            n.setdefault("aliases", []).append(name)
            n["aliases"].sort()
            self._register(n)

    def country(self, iso: str) -> str:
        if iso in self.by_country:
            return self.by_country[iso]
        rec = self.gaz.countries.get(iso)
        name = rec["name"] if rec else {"XK": "Kosovo"}.get(iso, iso)
        return self._add({"id": iso.lower(), "name": name, "type": "country", "iso": iso})

    def region(self, iso: str, code: str) -> str:
        cid = self.country(iso)
        if (cid, code) in self.by_region:
            return self.by_region[(cid, code)]
        name = self.gaz.state_codes[iso][code]
        return self._add({"id": f"{cid}-{code.lower()}", "name": name, "type": "region",
                          "parent": cid, "code": code})

    def city(self, rec: dict | None, iso: str, name: str, admin: str | None = None,
             alias: str | None = None) -> str:
        """City node for a gazetteer record (preferred) or a bare name in a country."""
        if rec is not None:
            iso = rec["countrycode"]
            admin = self.gaz.admin_code(rec) or admin
            name = rec["name"]
            if rec["geonameid"] in self.by_geoname:
                nid = self.by_geoname[rec["geonameid"]]
                if alias:
                    self.add_alias(nid, alias)
                return nid
        if admin and admin not in self.gaz.state_codes.get(iso, {}):
            admin = None
        parent = self.region(iso, admin) if admin else self.country(iso)
        key = (iso, norm(name))
        if key in self.by_city_key:
            nid = self.by_city_key[key]
            n = self.nodes[nid]
            if rec is not None and not n.get("geonameid"):
                n["geonameid"] = rec["geonameid"]
                self.by_geoname[rec["geonameid"]] = nid
            if alias:
                self.add_alias(nid, alias)
            return nid
        base = f"{iso.lower()}-{slug(name)}"
        nid = base
        if nid in self.nodes:
            nid = f"{base}-{admin.lower()}" if admin else base
            k = 2
            while nid in self.nodes:
                nid = f"{base}-{k}"
                k += 1
        node = {"id": nid, "name": name, "type": "city", "parent": parent}
        if rec is not None:
            node["geonameid"] = rec["geonameid"]
        if alias and alias != name:
            node["aliases"] = [alias]
        return self._add(node)

    def institution(self, city_id: str, name: str, aliases: list[str] = ()) -> str:
        key = (city_id, norm(name))
        if key in self.by_inst_key:
            nid = self.by_inst_key[key]
            for a in aliases:
                self.add_alias(nid, a)
            return nid
        for a in aliases:
            if (city_id, norm(a)) in self.by_inst_key:
                nid = self.by_inst_key[(city_id, norm(a))]
                self.add_alias(nid, name)
                return nid
        # "Aarhus University" = "University of Aarhus" = "Uni Aarhus": same significant words, same city
        mk = merge_key(name, self.nodes[city_id]["name"])
        if mk and (city_id, mk) in self.by_merge_key:
            nid = self.by_merge_key[(city_id, mk)]
            self.add_alias(nid, name)
            for a in aliases:
                self.add_alias(nid, a)
            return nid
        acr = sorted((a for a in aliases if is_acronym(a) and 3 <= len(a) <= 8 and a.isalpha()), key=lambda a: (-len(a), a))
        cn = self.nodes[city_id]
        short = slug(acr[0]) if acr and not is_acronym(name) else short_slug(name, [cn["name"]] + list(cn.get("aliases") or []))
        nid = f"{city_id}-{short}"
        if nid in self.nodes:
            nid = f"{city_id}-{slug(name)}"
            k = 2
            while nid in self.nodes:
                nid = f"{city_id}-{slug(name)}-{k}"
                k += 1
        node = {"id": nid, "name": name, "type": "institution", "parent": city_id}
        als, seen_cf = [], {name.casefold()}
        for a in sorted(set(aliases)):
            if a.casefold() not in seen_cf:
                seen_cf.add(a.casefold())
                als.append(a)
        if als:
            node["aliases"] = als
        return self._add(node)

    def dump(self) -> dict:
        order = {"country": 0, "region": 1, "city": 2, "institution": 3}

        def path(nid):
            n = self.nodes[nid]
            return (path(n["parent"]) if n.get("parent") else ()) + (n["id"],)

        nodes = sorted(self.nodes.values(), key=lambda n: (path(n["id"]), order[n["type"]]))
        out = []
        for n in nodes:
            d = {k: n[k] for k in ("id", "name", "type", "parent", "iso", "code", "geonameid",
                                   "aliases", "notes") if k in n}
            out.append(d)
        return {"locations": out}


SHORT_DROP = {"university", "univ", "universidad", "universidade", "universita", "universitat",
              "universitaet", "universite", "universiteit", "universitas", "universiti", "college",
              "institute", "instituto", "institut", "technology", "tecnologia", "tecnologico",
              "of", "the", "de", "del", "la", "el", "los", "las", "da", "do", "di", "du", "des",
              "and", "y", "e", "at", "in", "campus", "state", "national", "nacional", "autonoma",
              "autonomous", "federal", "polytechnic", "politecnico", "politecnica", "school",
              "escuela", "faculty", "facultad", "academy", "sciences", "science"}


MERGE_DROP = {"university", "univ", "universidad", "universidade", "universita", "universitat", "universitaet",
              "universite", "universiteit", "universitas", "universiti", "uni", "of", "the", "de", "del", "la", "el",
              "los", "las", "da", "do", "di", "du", "des", "and", "y", "e", "at", "in", "zu", "van"}


def merge_key(name: str, city: str) -> str | None:
    """Significant words of an institution name (generic words and the city dropped), or None when
    nothing significant is left or the name is an acronym."""
    if is_acronym(name):
        return None
    toks = [t for t in norm(name).split() if t not in MERGE_DROP]
    ctoks = set(norm(city).split())
    sig = [t for t in toks if t not in ctoks]
    had_city = len(sig) < len(toks)
    if not sig and not had_city:
        return None
    return " ".join(sig) + ("|city" if had_city else "")


def short_slug(name: str, city="") -> str:
    """Short id tail for an institution: generic words and the city's own name(s) dropped."""
    full = slug(name)
    s = full
    for c in ([city] if isinstance(city, str) else city):
        cs = slug(c) if c else ""
        if cs:
            s = re.sub(rf"(^|-){re.escape(cs)}(-|$)", "-", s)
    s_nocity = s
    toks = [t for t in s.split("-") if t and t not in SHORT_DROP]
    s = "-".join(toks)
    if not s or len(s) < 3:
        stop = {"of", "the", "de", "del", "la", "el", "los", "las", "da", "do", "di", "du", "des", "and", "y", "e", "at", "in"}
        s = "-".join(t for t in s_nocity.split("-") if t and t not in stop)
        if not s or len(s) < 3:
            s = "-".join(t for t in full.split("-") if t not in stop) or full
    return s[:48].strip("-")


# --------------------------------------------------------------------------------------
# text parsing
# --------------------------------------------------------------------------------------
BR_STATES = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
             "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
# words that are never a city on their own (state/province/adjective/generic) — skipped as candidates
NOT_A_CITY = {
    "new south wales", "western australia", "south australia", "northern territory", "new mexico",
    "new england", "west virginia", "north carolina", "south carolina", "north dakota", "south dakota",
    "rhode island", "new hampshire", "new jersey", "yucatan", "jalisco", "michoacan", "tamaulipas", "coahuila", "hidalgo", "nuevo leon", "guerrero",
    "sinaloa", "sonora", "tabasco", "chiapas", "morelos", "quintana roo", "nayarit", "baja california",
    "estado de mexico", "baja california sur",
    "minas gerais", "sao paulo state", "rio grande do sul", "rio grande do norte", "santa catarina",
    "mato grosso", "mato grosso do sul", "espirito santo", "pernambuco", "ceara", "bahia", "goias",
    "maranhao", "piaui", "para", "tocantins", "amazonas", "kerala", "tamil nadu", "karnataka",
    "maharashtra", "gujarat", "punjab", "bengal", "west bengal", "uttar pradesh", "andhra pradesh",
    "telangana", "rajasthan", "madhya pradesh", "bihar", "odisha", "hubei", "guangdong", "zhejiang",
    "jiangsu", "shandong", "sichuan", "hunan", "hebei", "henan", "anhui", "fujian", "shaanxi", "shanxi",
    "liaoning", "jilin", "heilongjiang", "yunnan", "guizhou", "guangxi", "hainan", "qinghai", "gansu",
    "xinjiang", "tibet", "inner mongolia", "perak", "selangor", "penang", "johor", "sabah", "sarawak",
    "java", "sumatra", "bali", "luzon", "mindanao", "siberia", "ural", "urals", "crimea", "caucasus",
    "state", "national", "technical", "technology", "open", "free", "american", "international",
    "catholic", "christian", "baptist", "methodist", "polytechnic", "metropolitan", "federal", "central",
    "eastern", "western", "northern", "southern", "north", "south", "east", "west", "new", "upper", "lower",
    "united", "royal", "imperial", "city", "ciudad", "campus", "sede", "unidad", "division", "site",
    "teams", "team", "schools", "school", "college", "university", "universidad", "universidade",
    "institute", "instituto", "tecnologico", "tecnológico", "superior", "nacional", "autonoma", "autónoma",
    "estudios", "superiores", "politecnico", "politécnico", "engineering", "science", "sciences",
    "computer", "department", "faculty", "hall", "building", "room", "online", "virtual", "area", "region",
    "regional", "contest", "asia", "europe", "africa", "america", "pacific", "atlantic", "grand",
    "great", "mid", "middle", "trinity", "temple", "columbia", "georgetown", "marshall", "webster",
    "mercer", "samford", "indiana", "rice", "brown", "liberty", "union", "valley",
    "coast", "gulf", "nile", "maghreb", "oriente", "occidente", "estado", "normal", "centro", "qro", "west division", "east division", "lehigh", "western subregion", "central subregion", "far eastern subregion",
}
ORG_ACRONYMS = {"icpc", "acm", "ibm", "clics", "hq", "wf", "nac", "napc", "tba", "tbd", "ieee", "upe", "jetbrains",
                "huawei", "baylor", "nwerc", "swerc", "cerc", "seerc", "neerc", "nerc", "ncpc", "bapc", "ukiepc",
                "gcpc", "scpc", "ecpc", "acpc", "lcpc", "kcpc", "tcpc", "alcpc", "jcpc", "ocpc", "qcpc", "bcpc",
                "saudicpc", "mcpc", "nac", "naq", "naq2", "icpcnac", "aucpc", "grcpc", "sysops", "ccs"}
GENERIC_OF = {"technology", "science", "sciences", "engineering", "applied sciences", "economics", "business",
              "science technology", "engineering technology", "information technology", "computer science",
              "arts", "medicine", "management", "mining technology", "petroleum", "agriculture", "education",
              "technology economics", "electronic science technology", "posts telecommunications",
              "aeronautics astronautics", "chemical technology", "finance economics", "technology sydney",
              "science technology beijing", "business technology", "engineering technology vnu", "informatics",
              "information technologies", "applied science", "the arts", "life environmental sciences ukraine"}
NA_PREFIX_SKIP = {"columbia", "washington", "lincoln", "austin", "oakland", "lafayette", "jackson", "columbus",
                  "salem", "springfield", "georgetown", "temple", "marshall", "trinity", "wheaton", "hope", "union",
                  "concordia", "wake forest", "notre dame", "mercer", "samford", "webster", "stanford", "princeton",
                  "indiana", "york", "carleton", "lehigh", "villanova", "fordham", "bradley", "butler", "drake",
                  "elon", "furman", "hamilton", "hofstra", "howard", "lamar", "loyola", "marist", "northern",
                  "southern", "eastern", "western", "central", "pacific", "american", "national", "united",
                  "liberty", "cornell", "rice", "brown", "duke", "yale", "harvard", "tufts", "emory", "clemson",
                  "auburn", "baylor", "purdue", "rutgers", "vanderbilt", "mcgill", "queens", "ryerson", "brock",
                  "laval", "simon fraser", "mount", "saint", "st", "west", "east", "north", "south", "new", "cal",
                  "texas", "florida", "california", "michigan", "ohio", "virginia", "georgia", "arizona", "oregon",
                  "nevada", "colorado", "utah", "kansas", "iowa", "idaho", "montana", "alabama", "mississippi",
                  "missouri", "kentucky", "tennessee", "louisiana", "oklahoma", "arkansas", "nebraska", "wisconsin",
                  "minnesota", "illinois", "wyoming", "maine", "vermont", "delaware", "maryland", "connecticut",
                  "pennsylvania", "alaska", "hawaii", "ontario", "quebec", "alberta", "manitoba", "saskatchewan",
                  "dalhousie", "acadia", "memorial", "wilfrid laurier", "waterloo", "trent", "lakehead", "guelph"}
DIRECTION_WORDS = {"inner", "outer", "new", "north", "south", "east", "west", "northern", "southern", "eastern", "western",
                   "central", "upper", "lower", "greater", "nueva", "nuevo", "nova", "novo", "neu"}

DECOR_RES = [
    re.compile(r"\((?:[^()]*\b(?:only|teams?|students?|register|hidden|all sites|non-advancing)\b[^()]*)\)", re.I),
    re.compile(r"\b(?:Division|Div\.?)\s*(?:1|2|3|I{1,3}|One|Two)\b", re.I),
    re.compile(r"\bD[123]\b"),
    re.compile(r"\b(?:On-?\s?Site|Onsite|Site\s*\d*|Test-?site|Virtual Site)\b", re.I),
    re.compile(r"^\s*(?:SWERC|NWERC|CERC|SEERC|NEERC|NERC|ICPC|ACM)\s+Site\s*[­\-–—]*\s*", re.I),
    re.compile(r"^\s*(?:SWERC|NWERC|CERC|SEERC|NEERC|NERC|NCPC|BAPC|UKIEPC|GCPC|CTU Open|ICPC|ACM|NAC|NAQ)(?:\s+\d{4}(?:[-–/]\d{2,4})?)?\s*[-–—:@]\s*(?=.*[A-Za-z]{3})"),
    re.compile(r"\b(?:Regional Contest|Regional|Contest|Programming Contest)\b", re.I),
    re.compile(r"\s*[­\-–—]+\s*$"),
    re.compile(r"^\s*[­\-–—]+\s*"),
]

INST_OF_RE = re.compile(
    r"\b(?:university|universit[eé]|universidad|universidade|universit[àa]|universitat|universiteit|"
    r"institute|instituto|institut|college|politecnico|politécnico|polit[eé]cnica|politehnica|"
    r"escola|escuela|école|ecole|faculdade|facultad|hochschule|tecnol[oó]gico(?:\s+superior)?|"
    r"centro universit[aá]rio|academy|académie|conservatoire|ensa|ensias)\s+"
    r"(?:of\s+technology\s+|of\s+science\s+and\s+technology\s+|of\s+applied\s+sciences\s+|"
    r"(?:nacional|federal|estadual|aut[oó]noma|polit[eé]cnica|t[eé]cnica|cat[oó]lica|pontif[ií]cia|"
    r"nacional\s+aut[oó]noma)\s+)*"
    r"(?:of|de|di|da|du|d'|degli|della|van|von|zu|in|at|em|en|à|a)\s+(?:la\s+|el\s+|los\s+|las\s+|the\s+)?(.+)$",
    re.I,
)
INST_PREFIX_RE = re.compile(
    r"^((?:[A-ZÀ-ɏ][\wÀ-ɏ'’\.\-]*\s+){1,3})"
    r"(?:University|Universit[äa]e?t|Universit[eé]|Universidad|Universidade|Universiteit|Universitas|Universiti|"
    r"Uni|Institute|Instituto|Institut|College|Polytechnic|Politecnico|Politehnica|Tech|State University|"
    r"Technical University|Technological University|School|Schools|Academy)\b",
)
INST_SUFFIX_RE = re.compile(
    r"\b(?:University|Universität|Universitaet|Universidad|Universidade|Universitat|Institute|College|Hochschule|Tech)\s+"
    r"(?:of\s+Technology\s+|(?:Tec[A-Za-z]*|Anáhuac|Anahuac|Panamericana|Iberoamericana|Marista|Politécnica|Politecnica|Tecnológica|Tecnologica)\s+)?"
    r"((?:[A-ZÀ-ɏ][\wÀ-ɏ'’\.\-]*\s*){1,2})$"
)
MARKER_RE = re.compile(r"\b(?:campus|sede|unidad|c\.)\s+(?:de\s+|del\s+|la\s+)?(.+)$", re.I)
ASIA_SITE_RE = re.compile(r"^Asia\s+(.+?)(?:\s+(?:On-?\s?Site|Site|Regional|Contest|Online|Programming|Preliminary).*)?$", re.I)
ACR_RE = re.compile(r"^[^\sa-z]{2,10}$")


def is_acronym(tok: str) -> bool:
    t = tok.strip(" .,")
    return bool(ACR_RE.match(t)) and sum(ch.isalpha() for ch in t) >= 2


def is_institution_name(name: str) -> bool:
    n = clean_text(name)
    if not n:
        return False
    if INSTITUTION_RE.search(n):
        return True
    head = re.split(r"[,@\-–/(]", n)[0].strip()
    return is_acronym(head.split()[0]) if head.split() else False


def strip_decor(s: str) -> tuple[str, list[str]]:
    """Remove division/site decorations; return (clean string, parenthesised extras)."""
    s = clean_text(s)
    extras = []
    for m in re.finditer(r"\(([^()]*)\)", s):
        inner = m.group(1).strip()
        if inner and not re.search(r"\b(?:only|teams?|students?|register|hidden)\b", inner, re.I):
            extras.append(inner)
    s = re.sub(r"\([^()]*\)", " ", s)
    for rx in DECOR_RES:
        s = rx.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-–—")
    return s, extras


def split_parts(s: str) -> list[str]:
    parts = re.split(r"\s*(?::|,|;|@|/|\s[-–—]\s|\s[-–—](?=[A-Z])|(?<=[a-z])[-–—]\s)\s*", s)
    return [p.strip(" .") for p in parts if p and p.strip(" .")]


def city_candidates(phrase: str, last_word: bool = True) -> list[str]:
    """Candidate city strings to try, in order, from a phrase that should name a place."""
    phrase = phrase.strip(" .,-")
    if not phrase:
        return []
    out = [phrase]
    toks = phrase.split()
    # drop trailing acronyms / roman numerals / numbers: "Guadalajara CUCEI", "Milpa Alta II"
    t2 = list(toks)
    while len(t2) > 1 and (is_acronym(t2[-1]) or re.fullmatch(r"[IVX]+|\d+", t2[-1])):
        t2.pop()
    if t2 != toks:
        out.append(" ".join(t2))
    # drop leading generic words: "Ciudad de X" keeps, "Campus X" drops
    t3 = list(t2)
    while len(t3) > 1 and norm(t3[0]) in {"campus", "sede", "unidad", "multidisciplinaria", "regional",
                                          "sitio", "site", "greater", "metropolitan", "area", "uni", "college",
                                          "university", "institute", "school", "hochschule", "universidad",
                                          "universidade", "instituto", "faculty", "facultad", "faculdade"}:
        t3.pop(0)
    if t3 != t2:
        out.append(" ".join(t3))
    # last word alone, when the phrase is several words
    if last_word and len(t3) >= 2 and t3[-1][:1].isupper() and norm(t3[-1]) not in NOT_A_CITY:
        out.append(t3[-1])
    seen = set()
    res = []
    for o in out:
        k = norm(o)
        if k and k not in seen and k not in NOT_A_CITY and k not in JUNK_WORDS:
            seen.add(k)
            res.append(o)
    return res


class Resolver:
    """Turns site records / free text into tree nodes, recording what needs a human."""

    def __init__(self, gaz: Gazetteer, tree: Tree, known: dict):
        self.gaz, self.tree = gaz, tree
        self.known = known  # norm(name) -> {name, city, country, admin?, aliases}
        self.review = defaultdict(list)   # section -> lines
        self.ambiguous = {}               # key -> (pick, alternatives)
        self.inferred = {}                # institution name -> city node (inferred from its name)
        self.counts = Counter()

    # -- gazetteer picks --
    def pick_city(self, name: str, cc: str | None, admin: str | None, allowed: set[str] | None,
                  ctx: str, min_pop: int = 0, derived: bool = False) -> dict | None:
        k = norm(name)
        if k in NOT_A_CITY or k in JUNK_WORDS or len(k) < 3:
            return None
        if k in self.gaz.state_names and (derived or not any(norm(c["name"]) == k for c in self.gaz.index.get(k, []))) \
                and not (admin and cc and self.gaz.lookup(name, cc, admin)):
            return None   # "University of Washington", "Paraíba": a state, not a city ("New York, NY" is fine)
        cands = []
        if cc:
            cands = self.gaz.lookup(name, cc, admin, None)
        else:
            for al in (getattr(self, "allowed_chain", None) or [allowed]):
                cands = self.gaz.lookup(name, None, admin, al)
                if cands:
                    if len({c["countrycode"] for c in cands}) == 1:
                        min_pop = min(min_pop, 5000)
                    break
            if not cands and not derived:
                world = [c for c in self.gaz.lookup(name) if norm(c["name"]) == k]
                if len({c["countrycode"] for c in world}) == 1 and world[0]["population"] >= 100000:
                    cands = world
        if derived or is_acronym(name):
            # read off a name / an acronym: trust an alternate-name match only for a big city
            cands = [c for c in cands if norm(c["name"]) == k or c["population"] >= 100000]
        cands = [c for c in cands if c["population"] >= min_pop]
        if not cands:
            return None
        # a regional's geographic area names its states: prefer a candidate in one of them
        states = getattr(self, "area_states", set())
        if states and not admin and len(cands) > 1:
            prim = [c for c in cands if norm(c["name"]) == k]
            pool = prim or cands   # never let the area override a match on the city's own name
            pref = [c for c in pool if (c["countrycode"], self.gaz.admin_code(c)) in states]
            if pref:
                cands = pref + [c for c in cands if c not in pref]
        top = cands[0]
        others = [c for c in cands[1:] if c["countrycode"] != top["countrycode"]
                  or self.gaz.admin_code(c) != self.gaz.admin_code(top)]
        others = [c for c in others if c["population"] * 3 >= top["population"] or c["population"] >= 100000]
        if others:
            key = (norm(name), cc, admin, frozenset(allowed or ()))
            if key not in self.ambiguous:
                self.ambiguous[key] = (name, top, others[:4], ctx)
        return top

    # -- country / state scanning --
    def scan_country(self, s: str, allowed: set[str] | None) -> tuple[str | None, str]:
        """Find a country name inside `s` (longest n-gram first). Returns (iso, s without it)."""
        toks = s.replace(",", " , ").split()
        words = [t for t in toks]
        for n in (4, 3, 2, 1):
            for i in range(0, len(words) - n + 1):
                gram = " ".join(words[i:i + n]).strip(" ,.")
                if not gram or "," in gram:
                    continue
                iso = self.gaz.country_by_name.get(norm_full(gram))
                if not iso:
                    continue
                if i > 0 and norm(words[i - 1]) in DIRECTION_WORDS:
                    continue
                if iso == "GE" and (allowed is None or "US" in allowed or "GE" not in allowed):
                    continue  # Georgia the US state
                if iso == "JO" and i > 0 and words[i - 1][:1].isupper() and n == 1 and norm(gram) == "jordan" and \
                        norm(words[i - 1]) not in {"of", "de"}:
                    continue  # "South Jordan", "Michael Jordan Hall"
                rest = " ".join(words[:i] + words[i + n:]).replace(" , ", ", ").strip(" ,.")
                return iso, rest
        return None, s

    def scan_state(self, parts: list[str], cc: str | None, allowed: set[str] | None):
        """A trailing US/CA/AU state or BR state code among the parts. Returns ((cc, code)|None, parts)."""
        # a full state/province name anywhere wins ("Alberta, CA" is Canada, not California)
        for i in range(len(parts) - 1, -1, -1):
            k = norm(parts[i].strip(" ."))
            for c in ([cc] if cc else ["US", "CA", "AU"]):
                if c not in self.gaz.state_codes or (allowed is not None and cc is None and c not in allowed):
                    continue
                code = self.gaz.state_by_name.get((c, k))
                if code and len(k) > 2:
                    rest = parts[:i] + parts[i + 1:]
                    rest = [r for r in rest if r.strip(" .").upper() not in {"US", "USA", "CA", "AU", c}]
                    return (c, code), rest
        for i in range(len(parts) - 1, -1, -1):
            p = parts[i].strip(" .")
            if re.fullmatch(r"[A-Z]\.[A-Z]\.?", p):
                p = p.replace(".", "")
            k = norm(p)
            if cc in (None, "BR") and (allowed is None or "BR" in allowed) and p.upper() in BR_STATES and len(p) == 2 \
                    and (cc == "BR" or not (allowed and ("US" in allowed or "CA" in allowed))):
                return ("BR", None), parts[:i] + parts[i + 1:]
            if p.upper() == "CA" and cc is None and i > 0:
                # "Winnipeg, CA": Canada when the town is Canadian and not Californian
                other = parts[i - 1]
                ca_hit = [c for c in self.gaz.lookup(other, "CA") if norm(c["name"]) == norm(other) and c["population"] >= 20000]
                us_hit = self.gaz.lookup(other, "US", "CA")
                if ca_hit and not us_hit:
                    return ("CA", self.gaz.admin_code(ca_hit[0])), parts[:i] + parts[i + 1:]
            for c in ([cc] if cc else ["US", "CA", "AU"]):
                if c not in self.gaz.state_codes:
                    continue
                if allowed is not None and c not in allowed and cc is None:
                    continue
                code = self.gaz.state_by_name.get((c, k))
                if code and (len(p) > 2 or (i > 0 and p.isupper())):
                    return (c, code), parts[:i] + parts[i + 1:]
        return None, parts

    def known_institution(self, s: str, cc: str | None = None):
        """Hand-table hit. A bare acronym ("UCI", "ASU") counts only inside its own region/country."""
        k = norm(s)
        ents = self.known.get(k)
        if not ents:
            return None
        chain = getattr(self, "allowed_chain", None) or []
        if cc:
            fit = [e for e in ents if e["country"] == cc]
        else:
            fit = [e for e in ents if not chain or any(e["country"] in al for al in chain)]
        if len(ents) > 1 or (len(s.strip()) <= 6 and " " not in s.strip()):
            # an acronym, or a shared label: only a region/country fit counts
            return fit[0] if fit else None
        return fit[0] if fit else ents[0]

    # -- analysis of one string --
    def analyse(self, s: str, cc: str | None, allowed: set[str] | None, region: str | None) -> dict:
        """{inst: str|None, cities: [str], cc, admin, known}"""
        res = {"inst": None, "cities": [], "cc": cc, "admin": None, "known": None, "text_city": None, "known_label": None}
        s0, extras = strip_decor(s)
        if not s0 and not extras:
            return res
        ki = self.known_institution(s0, cc) or self.known_institution(s, cc)
        if ki is None:
            for e in extras:
                ki = self.known_institution(e, cc)
                if ki:
                    break
        if ki:
            res["known"] = ki
            res["inst"] = ki["name"]
            res["cc"] = cc or ki["country"]
            res["admin"] = ki.get("admin")
            res["cities"] = [ki["city"]]
            return res
        m = ASIA_SITE_RE.match(s0)
        if m and region in ("Asia East", "Asia West", "Asia Pacific", None):
            res["cities"] = city_candidates(m.group(1))
            return res
        parts = [p.title() if p.isupper() and " " in p else p for p in split_parts(s0)] + [e for e in extras]
        st, parts = self.scan_state(parts, res["cc"], allowed)
        if st:
            res["cc"] = res["cc"] or st[0]
            res["admin"] = st[1]
            if st == ("US", "DC") and not parts:
                parts = ["Washington"]
            plain = [p for p in parts if not is_institution_name(p) and norm(p) not in NOT_A_CITY
                     and norm(p) not in JUNK_WORDS and not re.search(r"\d", p)]
            if len(plain) == 1 and len(plain[0].split()) <= 3 and re.fullmatch(r"[^,;/@\-–]+,\s*[^,;/@\-–]+", s0) \
                    and s0.strip().startswith(plain[0]):
                res["text_city"] = plain[0]   # "Elsah, IL": a town even when the gazetteer lacks it
        # country anywhere (the original wording is kept for the institution's name)
        new_parts = []
        orig: dict[str, str] = {}
        for p in parts:
            p = re.sub(r"^(?:Ciudad|Cidade|City) (?:de |of )?(Guatemala|M[eé]xico|Panam[aá])$",
                       lambda m: {"guatemala": "Guatemala City", "mexico": "Mexico City", "panama": "Panama City"}[strip_accents(m.group(1)).lower()], p)
            iso, rest = self.scan_country(p, allowed)
            if iso and (res["cc"] is None or (iso in ("HK", "MO", "SG") and res["cc"] in ("CN", None))):
                res["cc"] = iso
            if iso in ("HK", "MO", "SG") and res["cc"] == iso:
                new_parts.append({"HK": "Hong Kong", "MO": "Macau", "SG": "Singapore"}[iso])
            if iso and rest:
                new_parts.append(rest)
                orig[rest] = p
            elif not iso:
                new_parts.append(p)
        parts = new_parts
        parts = [p for p in parts if norm(p) not in REGION_WORDS and norm(p) not in JUNK_WORDS
                 and norm(p) not in ONLINE_WORDS and norm(p) not in ADMIN_WORDS]
        inst = None
        cities: list[str] = []
        derived: set[str] = set()   # norm keys of candidates read off an institution's own name

        def add_derived(lst):
            for c in lst:
                derived.add(norm(c))
                cities.append(c)

        if not st:
            for i, p in enumerate(parts):
                toks = p.split()
                if 2 <= len(toks) <= 4 and not is_institution_name(p):
                    for n in (2, 1):
                        if len(toks) > n:
                            tail = " ".join(toks[-n:])
                            st2 = self.gaz.state_from_text(tail, res["cc"]) if len(tail) > 2 else None
                            if st2 and (allowed is None or st2[0] in allowed or res["cc"] == st2[0]):
                                res["cc"] = res["cc"] or st2[0]
                                res["admin"] = st2[1]
                                parts[i] = " ".join(toks[:-n])
                                break
        for p in parts:
            # a known institution as one part ("SWERC 2022 @ Politecnico di Milano", "Royal Institute of Technology, Sweden")
            kp = self.known_institution(p, res["cc"])
            if kp and res["known"] is None:
                # "University of Missouri - Kansas City": another part names a different town -> not the known one
                conflict = False
                for q in parts:
                    if q is p or is_institution_name(q):
                        continue
                    hit = [c for c in self.gaz.lookup(q, res["cc"] or kp["country"]) if norm(c["name"]) == norm(q) and c["population"] >= 5000]
                    if hit and norm(q) != norm(kp["city"]) and norm(hit[0]["name"]) != norm(kp["city"]):
                        conflict = True
                if conflict:
                    inst = s0
                    continue
                res["known"] = kp
                res["inst"] = kp["name"]
                res["cc"] = res["cc"] or kp["country"]
                res["admin"] = res["admin"] or kp.get("admin")
                res["cities"] = [kp["city"]] + res["cities"]
                res["known_label"] = p
                return res
            if is_acronym(p) and norm(p) in ORG_ACRONYMS:
                continue   # ICPC, IBM, ACM...: organisers, not places or institutions
            # an all-caps token that is itself a sizeable city ("HANGZHOU", "RABAT") is a place, not an acronym
            if is_acronym(p) and not INSTITUTION_RE.search(p):
                hit = self.gaz.lookup(p, res["cc"], None, None if res["cc"] else allowed)
                if hit and hit[0]["population"] >= 50000 and norm(p) == norm(hit[0]["name"]):
                    cities += city_candidates(p)
                    continue
            # a part that is itself a town ("College Station", "University Park") is a place first
            if INSTITUTION_RE.search(p) and " " in p:
                hit = self.gaz.lookup(p, res["cc"], res["admin"], None if res["cc"] else allowed)
                if hit and hit[0]["population"] >= 5000 and norm(p) == norm(hit[0]["name"]):
                    cities += city_candidates(p, last_word=False)
                    continue
            if is_institution_name(p):
                if inst is None:
                    o = orig.get(p, p)
                    # original wording, unless the country was a trailing tag ("Kateb University Kabul Afghanistan")
                    removed = [w for w in o.replace(",", " ").split() if w not in p.replace(",", " ").split()]
                    tag = " ".join(removed)
                    inst = p if (tag and o.rstrip(" ,.").endswith(tag)) else o
                    if re.search(r"\b(de|of|di|du|da|in|at|del|la|the)$", inst, re.I):
                        inst = o   # "Universidad de Santiago de" lost its tail: keep the whole label
                else:
                    add_derived(city_candidates(p))  # a second institution-like part
                # "UFMG-Belo Horizonte", "PUC-Campinas": acronym, hyphen, city
                hm = re.match(r"^([^\sa-z]{2,10})\s*[-–]\s*(.+)$", p)
                if hm and is_acronym(hm.group(1)) and not INSTITUTION_RE.search(hm.group(2)):
                    add_derived(city_candidates(hm.group(2)))
                    continue
                # city embedded in the institution name
                pm = MARKER_RE.search(p)
                if pm:
                    add_derived(city_candidates(pm.group(1)))
                    p_wo = MARKER_RE.sub("", p).strip()
                else:
                    p_wo = p
                om = INST_OF_RE.search(p_wo)
                if om and norm(om.group(1)) in GENERIC_OF:
                    om = None   # "University of Technology": not a place
                if om:
                    add_derived(city_candidates(om.group(1)))
                am = re.match(r"^([^\sa-z]{2,10})\s+(.+)$", p_wo)  # "ACRONYM City" / "ITESM Campus X"
                if am and is_acronym(am.group(1)) and not INSTITUTION_RE.search(am.group(2)):
                    add_derived(city_candidates(am.group(2)))
                sm = INST_SUFFIX_RE.search(p_wo)
                if sm and not om:
                    add_derived(city_candidates(sm.group(1), last_word=False))
                pr = INST_PREFIX_RE.match(p_wo)
                na = region == "North America" or (cc in NORTH_AMERICA)
                if pr and not om and not na:
                    pre = pr.group(1).strip()
                    toks = pre.split()
                    for n in range(len(toks), 0, -1):
                        add_derived(city_candidates(" ".join(toks[:n]), last_word=False))
                elif pr and not om and na:
                    # US/CA institutions are often named after people: only a big city, by its own name
                    pre = pr.group(1).strip()
                    if norm(pre) not in NA_PREFIX_SKIP:
                        hit = self.gaz.lookup(pre, res["cc"], None, None if res["cc"] else (allowed or NORTH_AMERICA))
                        if hit and norm(hit[0]["name"]) == norm(pre) and hit[0]["population"] >= 100000:
                            add_derived([pre])
            else:
                cities += city_candidates(p)
        res["inst"] = inst
        seen = set()
        res["cities"] = [c for c in cities if not (norm(c) in seen or seen.add(norm(c)))]
        res["derived"] = derived
        return res

    # -- main entry --
    def resolve_text(self, text: str, region: str | None, ctx: str, country_hint: str | None = None,
                     site_name: str | None = None, state_hint: str | None = None,
                     city_hint: str | None = None, area: str | None = None) -> dict:
        """Returns {location?: node id, name?: str, level: country|region|city|institution|none,
        status: ok|unresolved|online|administrative, type?: online|administrative}"""
        region_allowed = self.gaz.region_set(region)
        area_ccs = set()
        if area:
            a = area
            for _ in range(12):
                iso, a2 = self.scan_country(a, None)
                if not iso:
                    break
                area_ccs.add(iso)
                a = a2
        cc_fb = next(iter(area_ccs)) if len(area_ccs) == 1 else None
        self.area_states = set()
        if area and (region in ("North America", None)):
            for tok in re.split(r"[,;()]|\band\b|\bthe\b", area):
                tok = re.sub(r"\b(eastern|western|northern|southern|upstate|portions? of|areas? of|all of|north|south|east|west|"
                             r"metropolitan area|greater|including|area)\b",
                             " ", tok, flags=re.I).strip(" .")
                for c_ in ("US", "CA"):
                    code = self.gaz.state_by_name.get((c_, norm(tok)))
                    if code:
                        self.area_states.add((c_, code))
        # lookups try the area's countries first, then the series' region
        self.allowed_chain = [x for x in (area_ccs or None, region_allowed) if x]
        allowed = self.allowed_chain[0] if self.allowed_chain else None
        text = clean_text(text)
        name = clean_text(site_name or "")
        kind = {}
        for label, v in (("text", text), ("name", name)):
            k = norm(v)
            v2, _ = strip_decor(v) if v else ("", [])
            if not k or k in JUNK_WORDS or norm(v2) in JUNK_WORDS:
                kind[label] = "junk"
            elif k in ADMIN_WORDS or ADMIN_RE.search(v) or norm(v2) in ADMIN_WORDS or ADMIN_RE.search(v2):
                kind[label] = "admin"
            elif k in ONLINE_WORDS or ONLINE_RE.search(v) or norm(v2) in ONLINE_WORDS:
                kind[label] = "online"
            else:
                kind[label] = "place"
        out: dict = {}
        if "admin" in kind.values():
            out["type"] = "administrative"
        if "online" in kind.values():
            out["type"] = "online"
        if kind["text"] != "place" and kind["name"] != "place":
            if out.get("type") == "administrative" and kind["name"] in ("admin", "junk") and kind["text"] in ("admin", "junk"):
                keep = name if kind["name"] == "admin" and norm(name) not in ADMIN_WORDS else ""
                r = {"status": "administrative", "type": "administrative"}
                if keep:
                    r["name"] = keep
                return r
            r = {"status": "online" if out.get("type") == "online" else "unresolved", "level": "none"}
            if out.get("type"):
                r["type"] = out["type"]
            if name and kind["name"] != "junk":
                r["name"] = name
            return r

        cc = country_hint
        admin = None
        a_text = self.analyse(text, cc, allowed, region) if kind["text"] == "place" else None
        a_name = self.analyse(name, cc, allowed, region) if kind["name"] == "place" else None
        analyses = [a for a in (a_text, a_name) if a]
        for a in analyses:
            cc = cc or a["cc"]
            if a["cc"] in ("HK", "MO") and cc == "CN":
                cc = a["cc"]
        for a in analyses:
            if a["cc"] == cc and a["admin"]:
                admin = admin or a["admin"]
        if state_hint and cc in self.gaz.state_codes:
            st = self.gaz.state_from_text(state_hint, cc)
            admin = admin or (st[1] if st else None)
        if admin and cc and admin not in self.gaz.state_codes.get(cc, {}):
            admin = None
        known = next((a["known"] for a in analyses if a["known"]), None)
        inst_name = known["name"] if known else next((a["inst"] for a in analyses if a["inst"]), None)
        inst_aliases = list(known.get("aliases") or []) if known else []
        if known:
            for a in analyses:
                if a["known"] is known:
                    pass
            for s_ in (text, name):
                s_clean, _ = strip_decor(s_)
                if s_clean and norm(s_clean) != norm(known["name"]) and self.known_institution(s_clean, cc) is known:
                    inst_aliases.append(s_clean)

        # city: structured hint > known institution's city > text candidates > name candidates
        cands: list[tuple[str, str]] = []
        if known:
            cands.append((known["city"], "known institution"))
        if city_hint:
            cands.append((clean_text(city_hint), "cms city"))
        derived_keys = set()
        for a, src in ((a_text, "text"), (a_name, "name")):
            if a:
                cands += [(c, src) for c in a["cities"]]
                derived_keys |= a.get("derived", set())
        city_rec = None
        city_name = None
        inferred_from_inst = False
        for cand, src in cands:
            der = norm(cand) in derived_keys
            rec = self.pick_city(cand, cc or cc_fb, admin, allowed, ctx,
                                 min_pop=0 if (cc or cc_fb or known or src == "cms city") else 20000,
                                 derived=der)
            if rec:
                city_rec, city_name = rec, cand
                cc = rec["countrycode"]
                inferred_from_inst = der
                break
            if src == "known institution":
                break   # the hand table's city is authoritative even when the gazetteer lacks it
        text_city = next((a["text_city"] for a in analyses if a.get("text_city") and a["cc"] == cc), None)
        if city_rec is None and known:
            city_name = known["city"]
            cc = known["country"]
            admin = known.get("admin") or admin
        elif city_rec is None and city_hint and cc:
            city_name = clean_text(city_hint)
        elif city_rec is None and text_city and cc and admin:
            city_name = text_city
        else:
            city_name = city_name if city_rec else None

        # build nodes
        if city_rec is None and city_name and cc:
            nid = self.tree.city(None, cc, city_name, admin if cc in self.gaz.state_codes else None)
            out["location"], out["level"] = nid, "city"
            self.review["City not in gazetteer (node made from text)"].append(
                f"`{nid}` from {text!r} / {name!r} ({ctx})")
        elif city_rec is not None:
            alias = None
            if city_name and norm(city_name) != norm(city_rec["name"]) and not inferred_from_inst \
                    and len(norm(city_name)) >= 4 and norm(city_name) not in self.gaz.state_names:
                alias = city_name
            nid = self.tree.city(city_rec, cc, city_rec["name"], admin if cc in self.gaz.state_codes else None,
                                 alias=alias)
            out["location"], out["level"] = nid, "city"
        elif cc and admin and admin in self.gaz.state_codes.get(cc, {}):
            out["location"], out["level"] = self.tree.region(cc, admin), "region"
        elif cc or cc_fb:
            out["location"], out["level"] = self.tree.country(cc or cc_fb), "country"
            if not cc:
                self.review["Country taken from the CMS geographic area only"].append(
                    f"{ctx}: {name!r} / {text!r} -> `{out['location']}` (area {area!r})")
        else:
            out["level"] = "none"

        if inst_name and out.get("level") == "city":
            iid = self.tree.institution(out["location"], inst_name, inst_aliases)
            out["location"], out["level"] = iid, "institution"
            if inferred_from_inst:
                self.inferred.setdefault(iid, (inst_name, self.tree.nodes[self.tree.nodes[iid]["parent"]]["name"], ctx))
            n_clean, _ = strip_decor(name) if name else ("", [])
            if name and norm(n_clean) != norm(inst_name) and norm(n_clean) not in {norm(a) for a in inst_aliases} \
                    and norm(name) != norm(inst_name):
                out["name"] = name
        elif name:
            n_clean, _ = strip_decor(name)
            city_words = set()
            if out.get("level") == "city":
                cn = self.tree.nodes[out["location"]]
                city_words = {norm(cn["name"])} | {norm(a) for a in cn.get("aliases") or []} | {norm(city_name or "")}
            if norm(n_clean) in REGION_WORDS or norm(n_clean) in city_words or norm(name) in city_words:
                pass   # "Europe" (a World Finals team group), "Copenhagen" for Copenhagen: nothing to keep
            else:
                out["name"] = name
            if inst_name and out.get("level") in ("country", "region"):
                self.review["Institution without a city (placed at country/region level)"].append(
                    f"{ctx}: {name!r} / {text!r} -> `{out['location']}`")
        out["status"] = "ok" if out.get("location") else ("online" if out.get("type") == "online" else "unresolved")
        return out


ADMIN_RE = re.compile(
    r"^(?:administration|administrative(?: site)?|any site|hidden teams?|canceled teams?.*|cancelled teams?.*|"
    r"division (?:i{1,3}|[123]) all|every division.*|all sites|purgatory|test[- ]?site|no location|"
    r"certificates only|tba|tbd|icpc (?:sysops|events|services|contest control system.*)|"
    r"nac teams|alumni.*|.*volunteers|administration \(.*\)|.*- administration|administrative.*|"
    r"icpc ineligible site|ineligible.*|guests|.*\bfinals\b.*|cancelled|canceled|certificates.*|administration\d+|"
    r".*\bstaff\b.*|.*headquarters.*|.*symposium.*|host site|.*\bjudges\b.*|.*\bcoaches\b.*|clics\+live|"
    r"icpc.*|.*world finals.*|.*\bteams\b.*|unofficial.*|.*\bunofficial\b.*|.*\(unofficial\).*|.*unoffcial.*|"
    r"hidden|please ignore.*|admin:.*|.*\(dummy-site\)|satellite|microsite.*|test|dummy.*|.*host guests|w ?- ?africa|"
    r"northern eurasia|transcaucasian (?:group|area)|levant|nile|maghreb|gulf|central africa|north|south|east|west|"
    r"north site|south site|east site|west site)$", re.I)
ONLINE_RE = re.compile(r"^(?:on-?line(?: site)?|internet|www|virtual(?: reality| site)?|remote|ether|us online|"
                       r"magyar verseny|online.*|.*\bonline\b.*)$", re.I)


# --------------------------------------------------------------------------------------
# known institutions: name key -> canonical node. Conservative: frequent CMS labels whose
# city is not in the text. Aliases are other spellings seen in the CMS.
# --------------------------------------------------------------------------------------
def load_known() -> dict:
    """norm(name or alias) -> [entry, ...] (several institutions may share an acronym)."""
    raw = KNOWN_INSTITUTIONS
    out: dict[str, list] = defaultdict(list)
    for name, (city, cc, *rest) in raw.items():
        admin = None
        aliases = []
        for r in rest:
            if isinstance(r, str) and len(r) <= 3 and r.isupper():
                admin = r
            elif isinstance(r, (list, tuple)):
                aliases = list(r)
        ent = {"name": name, "city": city, "country": cc, "admin": admin, "aliases": aliases}
        out[norm(name)].append(ent)
        for a in aliases:
            if ent not in out[norm(a)]:
                out[norm(a)].append(ent)
    return dict(out)


KNOWN_INSTITUTIONS: dict[str, tuple] = {
    # Asia Pacific / South Pacific
    "University of Western Australia": ("Perth", "AU", "WA", ["UWA"]),
    "Australian National University": ("Canberra", "AU", "ACT", ["ANU"]),
    "Queensland University of Technology": ("Brisbane", "AU", "QLD", ["QUT"]),
    "University of Queensland": ("Brisbane", "AU", "QLD", ["UQ"]),
    "University of Otago": ("Dunedin", "NZ"),
    "University of Canterbury": ("Christchurch", "NZ"),
    "Southland Institute of Technology": ("Invercargill", "NZ", ["Southern Institute of Technology", "SIT"]),
    "University of the South Pacific": ("Suva", "FJ", ["University of the South Pacific, Fiji", "USP"]),
    "University of Sydney": ("Sydney", "AU", "NSW", ["Univerity of Sydney"]),
    "University of New South Wales": ("Sydney", "AU", "NSW", ["UNSW"]),
    "RMIT University": ("Melbourne", "AU", "VIC", ["RMIT"]),
    "University of Melbourne": ("Melbourne", "AU", "VIC"),
    "Flinders University": ("Adelaide", "AU", "SA"),
    "University of South Australia": ("Adelaide", "AU", "SA", ["UniSA"]),
    "University of Adelaide": ("Adelaide", "AU", "SA"),
    "Victoria University of Wellington": ("Wellington", "NZ", ["VUW"]),
    "AUT University": ("Auckland", "NZ", ["Auckland University of Technology", "AUT"]),
    "University of Auckland": ("Auckland", "NZ"),
    "University of Waikato": ("Hamilton", "NZ"),
    "Massey University": ("Palmerston North", "NZ"),
    "University of Newcastle": ("Newcastle", "AU", "NSW"),
    "Griffith University": ("Brisbane", "AU", "QLD"),
    "University of Wollongong": ("Wollongong", "AU", "NSW"),
    "Curtin University": ("Perth", "AU", "WA"),
    "Murdoch University": ("Perth", "AU", "WA"),
    "James Cook University": ("Townsville", "AU", "QLD"),
    "University of Aizu": ("Aizuwakamatsu", "JP"),
    "University of Tokyo": ("Tokyo", "JP"),
    "Universiti Teknologi PETRONAS": ("Seri Iskandar", "MY", ["UTP"]),
    "National Taiwan University": ("Taipei", "TW", ["NTU"]),
    "National Chiao Tung University": ("Hsinchu", "TW", ["NCTU"]),
    "National Tsing Hua University": ("Hsinchu", "TW", ["NTHU"]),
    "Binus University": ("Jakarta", "ID", ["Bina Nusantara University", "BINUS"]),
    "Jakarta site": ("Jakarta", "ID"),
    # Nordic / Europe
    "KTH Royal Institute of Technology": ("Stockholm", "SE", ["KTH - Royal Institute of Technology", "KTH", "Royal Institute of Technology"]),
    "Chalmers University of Technology": ("Gothenburg", "SE", ["Chalmers"]),
    "NTNU": ("Trondheim", "NO", ["Norwegian University of Science and Technology"]),
    "University of Oslo": ("Oslo", "NO", ["UiO"]),
    "University of Bergen": ("Bergen", "NO", ["UiB"]),
    "University of Helsinki": ("Helsinki", "FI"),
    "Aalto University": ("Espoo", "FI", ["Helsinki University of Technology", "TKK"]),
    "Aarhus University": ("Aarhus", "DK"),
    "Aalborg University": ("Aalborg", "DK"),
    "University of Copenhagen": ("Copenhagen", "DK", ["DIKU"]),
    "Technical University of Denmark": ("Lyngby", "DK", ["DTU"]),
    "Reykjavik University": ("Reykjavik", "IS"),
    "University of Iceland": ("Reykjavik", "IS"),
    "Linköping University": ("Linköping", "SE", ["LiU"]),
    "Lund University": ("Lund", "SE"),
    "Umeå University": ("Umeå", "SE"),
    "Uppsala University": ("Uppsala", "SE"),
    "Karlstad University": ("Karlstad", "SE"),
    "Luleå University of Technology": ("Luleå", "SE"),
    "Molde University College": ("Molde", "NO"),
    "Tampere University": ("Tampere", "FI", ["Tampere University of Technology", "TUT"]),
    "University of Turku": ("Turku", "FI"),
    "Delft University of Technology": ("Delft", "NL", ["TU Delft"]),
    "Eindhoven University of Technology": ("Eindhoven", "NL", ["TU Eindhoven", "TU/e", "TUE"]),
    "Leiden University": ("Leiden", "NL"),
    "Utrecht University": ("Utrecht", "NL"),
    "University of Twente": ("Enschede", "NL"),
    "Vrije Universiteit Amsterdam": ("Amsterdam", "NL", ["VU Amsterdam", "VU"]),
    "Radboud University": ("Nijmegen", "NL"),
    "KU Leuven": ("Leuven", "BE", ["Katholieke Universiteit Leuven"]),
    "University of Antwerp": ("Antwerp", "BE"),
    "University of Luxembourg": ("Luxembourg", "LU"),
    "VSB - Technical University of Ostrava": ("Ostrava", "CZ", ["VSB Ostrava", "VSB", "VŠB"]),
    "Masaryk University": ("Brno", "CZ", ["MUNI Brno", "MUNI"]),
    "University of Žilina": ("Žilina", "SK", ["UNIZA Žilina", "UNIZA"]),
    "Czech Technical University in Prague": ("Prague", "CZ", ["CTU Prague", "CTU", "Prague, CTU"]),
    "Charles University": ("Prague", "CZ", ["Charles University in Prague"]),
    "Slovak University of Technology in Bratislava": ("Bratislava", "SK", ["STUBA Bratislava", "STUBA", "STU Bratislava"]),
    "Comenius University": ("Bratislava", "SK"),
    "Technical University of Košice": ("Košice", "SK", ["TUKE"]),
    "Matej Bel University": ("Banská Bystrica", "SK", ["Banska Bystrica"]),
    "University of West Bohemia": ("Pilsen", "CZ", ["ZCU", "UWB"]),
    "Technical University of Munich": ("Munich", "DE", ["TU München", "TUM"]),
    "Friedrich-Alexander-Universität Erlangen-Nürnberg": ("Erlangen", "DE", ["FAU", "FAU Erlangen"]),
    "Karlsruhe Institute of Technology": ("Karlsruhe", "DE", ["KIT", "Universität Karlsruhe"]),
    "University of Lübeck": ("Lübeck", "DE", ["Universität zu Lübeck"]),
    "Saarland University": ("Saarbrücken", "DE", ["Universität des Saarlandes"]),
    "Ulm University": ("Ulm", "DE", ["Universität Ulm"]),
    "University of Bonn": ("Bonn", "DE", ["Universität Bonn"]),
    "University of Rostock": ("Rostock", "DE", ["Universität Rostock"]),
    "RWTH Aachen University": ("Aachen", "DE", ["RWTH Aachen", "RWTH"]),
    "ETH Zurich": ("Zurich", "CH", ["ETH Zürich", "ETH", "ETHZ"]),
    "EPFL": ("Lausanne", "CH", ["École Polytechnique Fédérale de Lausanne"]),
    "University of Vienna": ("Vienna", "AT", ["Universität Wien"]),
    "Jagiellonian University": ("Kraków", "PL"),
    "University of Warsaw": ("Warsaw", "PL", ["Uniwersytet Warszawski"]),
    "University of Wrocław": ("Wrocław", "PL"),
    "University Politehnica of Bucharest": ("Bucharest", "RO", ["University Politehnica of Bucharest, Romania", "Politehnica University of Bucharest", "UPB"]),
    "University of Bucharest": ("Bucharest", "RO"),
    "University of Zagreb": ("Zagreb", "HR", ["FER Zagreb", "FER"]),
    "University of Ljubljana": ("Ljubljana", "SI"),
    "Taurida National University": ("Simferopol", "UA", ["Taurida NU", "Taurida National V.I. Vernadsky University"]),
    "Ivan Franko National University of Lviv": ("Lviv", "UA", ["Ivan Franko National University of Lviv, Ukraine", "Lviv National University"]),
    "University of Macedonia": ("Thessaloniki", "GR", ["University of Macedonia, Greece"]),
    "Imperial College London": ("London", "GB", ["Imperial College"]),
    "University of Bath": ("Bath", "GB"),
    "University of Cambridge": ("Cambridge", "GB"),
    "Instituto Superior Técnico": ("Lisbon", "PT", ["Tecnico, University of Lisbon, Portugal", "IST", "Técnico Lisboa"]),
    "University of Porto": ("Porto", "PT", ["FC Universidade do Porto", "FCUP", "Universidade do Porto"]),
    "Universidad Complutense de Madrid": ("Madrid", "ES", ["UCM"]),
    "Universitat Politècnica de Catalunya": ("Barcelona", "ES", ["UPC"]),
    "Universidad Politécnica de Madrid": ("Madrid", "ES", ["UPM"]),
    "Universidad de Valladolid": ("Valladolid", "ES", ["UVa"]),
    "Politecnico di Milano": ("Milan", "IT"),
    "Sapienza University of Rome": ("Rome", "IT", ["Università di Roma - La Sapienza", "La Sapienza", "Sapienza"]),
    "University of Pisa": ("Pisa", "IT", ["University of Pisa, Italy", "Università di Pisa"]),
    "INSA Lyon": ("Lyon", "FR"),
    "Epitech Lyon": ("Lyon", "FR", ["Epitech, Lyon"]),
    "Sorbonne University": ("Paris", "FR", ["Sorbonne Université", "UPMC", "Université Pierre et Marie Curie"]),
    "Polytech Nice Sophia": ("Nice", "FR"),
    "Université de Rennes 1": ("Rennes", "FR"),
    "École Normale Supérieure": ("Paris", "FR", ["ENS Paris", "ENS"]),
    "École Polytechnique": ("Palaiseau", "FR"),
    "Université Paris-Saclay": ("Orsay", "FR"),
    "Technion": ("Haifa", "IL", ["Technion - Israel Institute of Technology"]),
    "Tel Aviv University": ("Tel Aviv", "IL"),
    "Bilkent University": ("Ankara", "TR"),
    "Middle East Technical University": ("Ankara", "TR", ["METU"]),
    # North America
    "University of Colorado Boulder": ("Boulder", "US", "CO", ["University of Colorado at Boulder", "CU Boulder", "Univ. of Colorado, Boulder", "University of Colorado, Boulder", "CU-Boulder"]),
    "Colorado School of Mines": ("Golden", "US", "CO"),
    "Johns Hopkins University": ("Baltimore", "US", "MD", ["JHU"]),
    "University of Cincinnati": ("Cincinnati", "US", "OH"),
    "Youngstown State University": ("Youngstown", "US", "OH", ["YSU"]),
    "Duke University": ("Durham", "US", "NC"),
    "University of North Carolina at Chapel Hill": ("Chapel Hill", "US", "NC", ["University of North Carolina (Chapel Hill)", "UNC Chapel Hill", "UNC"]),
    "Louisiana State University": ("Baton Rouge", "US", "LA", ["LSU @ Baton Rouge, Louisiana", "LSU"]),
    "Riverside City College": ("Riverside", "US", "CA", ["RCC"]),
    "University of California, Riverside": ("Riverside", "US", "CA", ["UC Riverside", "UCR"]),
    "University of California, Irvine": ("Irvine", "US", "CA", ["UCI", "UC Irvine"]),
    "University of California, San Diego": ("San Diego", "US", "CA", ["UCSD", "UC San Diego"]),
    "University of California, Berkeley": ("Berkeley", "US", "CA", ["UC Berkeley"]),
    "University of California, Los Angeles": ("Los Angeles", "US", "CA", ["UCLA"]),
    "University of Southern California": ("Los Angeles", "US", "CA", ["USC"]),
    "California Institute of Technology": ("Pasadena", "US", "CA", ["Caltech"]),
    "San Diego State University": ("San Diego", "US", "CA", ["SDSU"]),
    "Rochester Institute of Technology": ("Rochester", "US", "NY", ["RIT"]),
    "SUNY Oswego": ("Oswego", "US", "NY", ["State University of New York at Oswego"]),
    "Grand Valley State University": ("Allendale", "US", "MI", ["GVSU"]),
    "University of Windsor": ("Windsor", "CA", "ON"),
    "University of Arizona": ("Tucson", "US", "AZ"),
    "Arizona State University": ("Tempe", "US", "AZ", ["ASU"]),
    "Ashland University": ("Ashland", "US", "OH"),
    "Christopher Newport University": ("Newport News", "US", "VA", ["Christopher Newport", "CNU"]),
    "Shippensburg University": ("Shippensburg", "US", "PA"),
    "Wilkes University": ("Wilkes-Barre", "US", "PA", ["Wilkes"]),
    "Howard University": ("Washington", "US", "DC"),
    "Washington College": ("Chestertown", "US", "MD"),
    "Radford University": ("Radford", "US", "VA"),
    "Virginia Tech": ("Blacksburg", "US", "VA", ["Virginia Polytechnic Institute and State University"]),
    "Penn State Harrisburg": ("Middletown", "US", "PA", ["PSU Harrisburg"]),
    "New Jersey Institute of Technology": ("Newark", "US", "NJ", ["NJIT"]),
    "Dalhousie University": ("Halifax", "CA", "NS"),
    "Rensselaer Polytechnic Institute": ("Troy", "US", "NY", ["RPI"]),
    "Northeastern University": ("Boston", "US", "MA"),
    "Université de Moncton": ("Moncton", "CA", "NB", ["University of Moncton"]),
    "McGill University": ("Montreal", "CA", "QC"),
    "Wellesley College": ("Wellesley", "US", "MA"),
    "Memorial University of Newfoundland": ("St. John's", "CA", "NL", ["Memorial University"]),
    "Harvard University": ("Cambridge", "US", "MA"),
    "Massachusetts Institute of Technology": ("Cambridge", "US", "MA", ["MIT"]),
    "Boston University": ("Boston", "US", "MA"),
    "Utah Valley University": ("Orem", "US", "UT", ["Utah Valley State College", "UVU"]),
    "Brigham Young University": ("Provo", "US", "UT", ["BYU"]),
    "University of Utah": ("Salt Lake City", "US", "UT"),
    "University of Saskatchewan": ("Saskatoon", "CA", "SK"),
    "University of Alberta": ("Edmonton", "CA", "AB"),
    "University of Calgary": ("Calgary", "CA", "AB"),
    "University of Lethbridge": ("Lethbridge", "CA", "AB"),
    "Montana State University": ("Bozeman", "US", "MT"),
    "Montana Tech": ("Butte", "US", "MT", ["Montana Tech of the University of Montana"]),
    "Colorado Mesa University": ("Grand Junction", "US", "CO", ["Mesa State College", "Mesa State"]),
    "New Mexico Tech": ("Socorro", "US", "NM", ["New Mexico Institute of Mining and Technology"]),
    "Eastern Washington University": ("Cheney", "US", "WA", ["EWU, Cheney, WA", "EWU"]),
    "Simon Fraser University": ("Burnaby", "CA", "BC", ["Simon Fraser - Burnaby", "SFU"]),
    "University of British Columbia": ("Vancouver", "CA", "BC", ["UBC"]),
    "George Fox University": ("Newberg", "US", "OR"),
    "LeTourneau University": ("Longview", "US", "TX", ["LETU"]),
    "East Central University": ("Ada", "US", "OK", ["ECU"]),
    "Baylor University": ("Waco", "US", "TX"),
    "DeVry University - Seattle": ("Seattle", "US", "WA"),
    "DeVry University - Fremont": ("Fremont", "US", "CA"),
    "Metropolitan State University of Denver": ("Denver", "US", "CO", ["Metro State Denver", "Metropolitan State College of Denver"]),
    "University of Colorado Colorado Springs": ("Colorado Springs", "US", "CO", ["UC-Colorado Springs", "UCCS"]),
    "Weber State University": ("Ogden", "US", "UT", ["Weber"]),
    "Southwest Baptist University": ("Bolivar", "US", "MO", ["SBU"]),
    "Murray State University": ("Murray", "US", "KY"),
    "Tennessee Tech University": ("Cookeville", "US", "TN", ["Tennessee Technological University"]),
    "University of Wisconsin-Platteville": ("Platteville", "US", "WI"),
    "University of Wisconsin-La Crosse": ("La Crosse", "US", "WI"),
    "University of Northern Iowa": ("Cedar Falls", "US", "IA", ["UNI"]),
    "South Dakota School of Mines and Technology": ("Rapid City", "US", "SD", ["SDSM&T"]),
    "North Dakota State University": ("Fargo", "US", "ND", ["NDSU"]),
    "University of Central Missouri": ("Warrensburg", "US", "MO", ["Central Missouri State University", "UCM"]),
    "Missouri State University": ("Springfield", "US", "MO", ["Southwest Missouri State University", "SMSU"]),
    "University of Illinois Springfield": ("Springfield", "US", "IL", ["UIS"]),
    "University of Chicago": ("Chicago", "US", "IL"),
    "University of Louisville": ("Louisville", "US", "KY"),
    "Georgia Institute of Technology": ("Atlanta", "US", "GA", ["Georgia Tech"]),
    "University of Minnesota": ("Minneapolis", "US", "MN"),
    "University of Manitoba": ("Winnipeg", "CA", "MB"),
    "Northwestern College": ("Orange City", "US", "IA"),
    "Michigan Technological University": ("Houghton", "US", "MI", ["Michigan Tech"]),
    "Northern Michigan University": ("Marquette", "US", "MI"),
    "Simpson College": ("Indianola", "US", "IA"),
    "Augustana University": ("Sioux Falls", "US", "SD", ["Augustana College"]),
    "Iowa State University": ("Ames", "US", "IA"),
    "College of Saint Benedict and Saint John's University": ("St. Joseph", "US", "MN", ["St. John's University"]),
    "Luther College": ("Decorah", "US", "IA"),
    "University of Nebraska-Lincoln": ("Lincoln", "US", "NE", ["UNL"]),
    "Park University": ("Parkville", "US", "MO"),
    "Adelphi University": ("Garden City", "US", "NY"),
    "University of Hawaii at Manoa": ("Honolulu", "US", "HI", ["University of Hawaii"]),
    "Edgewood College": ("Madison", "US", "WI"),
    # Latin America
    "ITESO": ("Guadalajara", "MX", ["ITESO University", "Instituto Tecnológico y de Estudios Superiores de Occidente"]),
    "Universidad de Guadalajara": ("Guadalajara", "MX", ["UdeG"]),
    "Universidad Centroamericana José Simeón Cañas": ("San Salvador", "SV", ['Universidad Centroamericana "José Simeón Cañas"', "UCA El Salvador"]),
    "Sede Interuniversitaria Alajuela": ("Alajuela", "CR"),
    "Universidad Nacional Siglo XX": ("Llallagua", "BO"),
    "Universidad Autónoma Juan Misael Saracho": ("Tarija", "BO", ["Universidad Autonoma Juan Misael Saracho"]),
    "Universidad Autónoma Juan Misael Saracho - Yacuiba": ("Yacuiba", "BO", ["Universidad Autonoma Juan Misael Saracho - Yacuiba"]),
    "Universidad Autónoma del Beni": ("Trinidad", "BO", ["Universidad Autonoma del Beni", "UAB"]),
    "Universidad Autónoma Tomás Frías": ("Potosí", "BO", ["UATF, Potosi", "UATF"]),
    "Universidade Federal de Goiás": ("Goiânia", "BR", ["UFG"]),
    "Universidade Federal de Mato Grosso": ("Cuiabá", "BR", ["UFMT"]),
    "Universidade Federal de Sergipe": ("São Cristóvão", "BR", ["UFS"]),
    "Universidade Vila Velha": ("Vila Velha", "BR", ["UVV, Vila Velha - ES", "UVV"]),
    "Universidade de São Paulo": ("São Paulo", "BR", ["USP"]),
    "Universidade Estadual de Campinas": ("Campinas", "BR", ["UNICAMP", "Unicamp"]),
    "Universidade Federal do Rio Grande do Sul": ("Porto Alegre", "BR", ["UFRGS"]),
    "Universidade Federal de Minas Gerais": ("Belo Horizonte", "BR", ["UFMG"]),
    "Universidade Federal do Rio de Janeiro": ("Rio de Janeiro", "BR", ["UFRJ"]),
    "Pontifícia Universidade Católica do Rio de Janeiro": ("Rio de Janeiro", "BR", ["PUC-Rio"]),
    "Universidade Federal do Ceará": ("Fortaleza", "BR", ["UFC"]),
    "Universidade Federal do Paraná": ("Curitiba", "BR", ["UFPR"]),
    "Universidade Federal de Santa Catarina": ("Florianópolis", "BR", ["UFSC"]),
    "Universidade de Brasília": ("Brasília", "BR", ["UnB"]),
    "Universidad de Buenos Aires": ("Buenos Aires", "AR", ["UBA"]),
    "Universidad Nacional de Córdoba": ("Córdoba", "AR"),
    "Universidad Nacional de La Plata": ("La Plata", "AR"),
    "Universidad Nacional de Río Cuarto": ("Río Cuarto", "AR", ["Rio Cuarto"]),
    "Universidad de Chile": ("Santiago", "CL"),
    "Pontificia Universidad Católica de Chile": ("Santiago", "CL", ["PUC Chile"]),
    "Universidad de los Andes": ("Bogotá", "CO"),
    "Universidad Nacional de Colombia": ("Bogotá", "CO"),
    "Universidad de Antioquia": ("Medellín", "CO"),
    "Universidad del Valle": ("Cali", "CO"),
    "Universidad Nacional de Ingeniería": ("Lima", "PE", ["UNI Lima"]),
    "Pontificia Universidad Católica del Perú": ("Lima", "PE", ["PUCP"]),
    "Universidad Simón Bolívar": ("Caracas", "VE", ["USB"]),
    "Universidad de La Habana": ("Havana", "CU", ["University of Havana"]),
    "Universidad de Puerto Rico": ("Mayagüez", "PR", ["UPRM", "University of Puerto Rico at Mayagüez"]),
    "Universidad de Costa Rica": ("San José", "CR", ["UCR"]),
    "Instituto Tecnológico de Costa Rica": ("Cartago", "CR", ["TEC"]),
    "Tecnológico de Monterrey": ("Monterrey", "MX", ["ITESM"]),
    "Universidad Nacional Autónoma de México": ("Mexico City", "MX", ["UNAM"]),
    "Instituto Politécnico Nacional": ("Mexico City", "MX", ["IPN"]),
    "Universidad Nacional Autónoma de Honduras": ("Tegucigalpa", "HN", ["UNAH"]),
    "Universidad Tecnológica de Panamá": ("Panama City", "PA", ["UTP Panamá"]),
    # Africa & Arab
    "Al Akhawayn University": ("Ifrane", "MA", ["Al Akhawayn University in Ifrane", "AUI"]),
    "Rhodes University": ("Grahamstown", "ZA"),
    "University of Pretoria": ("Pretoria", "ZA"),
    "University of Cape Town": ("Cape Town", "ZA", ["UCT"]),
    "University of KwaZulu-Natal": ("Pietermaritzburg", "ZA", ["UKZN"]),
    "University of the Witwatersrand": ("Johannesburg", "ZA", ["Wits"]),
    "Stellenbosch University": ("Stellenbosch", "ZA"),
    "Arab Academy for Science, Technology and Maritime Transport": ("Alexandria", "EG", ["AAST", "Arab Academy for Science and Technology"]),
    "Cairo University": ("Cairo", "EG"),
    "German University in Cairo": ("Cairo", "EG", ["GUC"]),
    "American University in Cairo": ("Cairo", "EG", ["AUC"]),
    "Ain Shams University": ("Cairo", "EG"),
    "Alexandria University": ("Alexandria", "EG"),
    "Lebanese American University": ("Beirut", "LB", ["LAU"]),
    "American University of Beirut": ("Beirut", "LB", ["AUB"]),
    "Kuwait University": ("Kuwait City", "KW"),
    "Princess Sumaya University for Technology": ("Amman", "JO", ["PSUT"]),
    "Jordan University of Science and Technology": ("Irbid", "JO", ["JUST"]),
    "University of Jordan": ("Amman", "JO"),
    "Sultan Qaboos University": ("Muscat", "OM", ["SQU"]),
    "Qatar University": ("Doha", "QA"),
    "Carnegie Mellon University in Qatar": ("Doha", "QA", ["CMU Qatar", "CMU-Q"]),
    "Damascus University": ("Damascus", "SY"),
    "Birzeit University": ("Birzeit", "PS"),
    "An-Najah National University": ("Nablus", "PS"),
    "Islamic University of Gaza": ("Gaza", "PS", ["IUG"]),
    "King Fahd University of Petroleum and Minerals": ("Dhahran", "SA", ["KFUPM"]),
    "King Saud University": ("Riyadh", "SA", ["KSU"]),
    "University of Khartoum": ("Khartoum", "SD"),
    "Université Cadi Ayyad": ("Marrakesh", "MA", ["Cadi Ayyad University", "UCA Marrakech"]),
    "Hassan II University": ("Casablanca", "MA"),
    "Mohammed V University": ("Rabat", "MA"),
    "ENSA Khouribga": ("Khouribga", "MA", ["École Nationale des Sciences Appliquées de Khouribga"]),
    "University of Nairobi": ("Nairobi", "KE"),
    "Makerere University": ("Kampala", "UG"),
    "Ashesi University": ("Berekuso", "GH"),
    "University of Lagos": ("Lagos", "NG", ["UNILAG"]),
    "University of Ibadan": ("Ibadan", "NG"),
    "Covenant University": ("Ota", "NG"),
    "Université de Lomé": ("Lomé", "TG"),
    "Université d'Abomey-Calavi": ("Cotonou", "BJ", ["UAC"]),
    # Northern Eurasia
    "Saint Petersburg State University": ("Saint Petersburg", "RU", ["SPbSU", "St. Petersburg State University"]),
    "Moscow State University": ("Moscow", "RU", ["Lomonosov Moscow State University", "MSU"]),
    "Moscow Institute of Physics and Technology": ("Dolgoprudny", "RU", ["MIPT"]),
    "Ural Federal University": ("Yekaterinburg", "RU", ["UrFU", "Ural State University"]),
    "Novosibirsk State University": ("Novosibirsk", "RU", ["NSU"]),
    "Saratov State University": ("Saratov", "RU", ["SSU"]),
    "Siberian Federal University": ("Krasnoyarsk", "RU", ["SibFU", "SFU Krasnoyarsk"]),
    "Altai State Technical University": ("Barnaul", "RU", ["AltSTU"]),
    "Kazakh-British Technical University": ("Almaty", "KZ", ["KBTU"]),
    "Tbilisi State University": ("Tbilisi", "GE", ["Ivane Javakhishvili Tbilisi State University", "TSU"]),
    "Free University of Tbilisi": ("Tbilisi", "GE"),
    "Yerevan State University": ("Yerevan", "AM", ["YSU"]),
    "Baku Engineering University": ("Baku", "AZ"),
    "Baku State University": ("Baku", "AZ", ["BSU Baku"]),
    "ADA University": ("Baku", "AZ"),
    "National University of Uzbekistan": ("Tashkent", "UZ"),
    "Tashkent University of Information Technologies": ("Tashkent", "UZ", ["TUIT"]),
    "Kyrgyz State Technical University": ("Bishkek", "KG"),
    "American University of Central Asia": ("Bishkek", "KG", ["AUCA"]),
    "Tajik Technical University": ("Dushanbe", "TJ"),
    "Vinnytsia National Technical University": ("Vinnytsia", "UA", ["VNTU"]),
    "Kharkiv National University of Radio Electronics": ("Kharkiv", "UA", ["KNURE"]),
    # Asia West / East
    "Amrita Vishwa Vidyapeetham": ("Amritapuri", "IN", ["Amrita University", "Amritapuri, Kerala, India", "Amrita School of Engineering, Amritapuri"]),
    "Indian Institute of Technology Kanpur": ("Kanpur", "IN", ["IIT Kanpur", "IITK"]),
    "Indian Institute of Technology Kharagpur": ("Kharagpur", "IN", ["IIT Kharagpur"]),
    "Indian Institute of Technology Madras": ("Chennai", "IN", ["IIT Madras"]),
    "Indian Institute of Technology Gandhinagar": ("Gandhinagar", "IN", ["IIT Gandhinagar"]),
    "Indian Institute of Information Technology Kolkata": ("Kolkata", "IN"),
    "PSG College of Technology": ("Coimbatore", "IN"),
    "Amrita School of Engineering, Coimbatore": ("Coimbatore", "IN"),
    "East West University": ("Dhaka", "BD", ["EWU Dhaka"]),
    "University of Dhaka": ("Dhaka", "BD", ["DU"]),
    "Bangladesh University of Engineering and Technology": ("Dhaka", "BD", ["BUET"]),
    "North South University": ("Dhaka", "BD", ["NSU"]),
    "BRAC University": ("Dhaka", "BD"),
    "Daffodil International University": ("Dhaka", "BD", ["DIU"]),
    "Bangladesh University of Business and Technology": ("Dhaka", "BD", ["BUBT"]),
    "Green University of Bangladesh": ("Dhaka", "BD"),
    "IUBAT": ("Dhaka", "BD", ["International University of Business Agriculture and Technology"]),
    "Independent University, Bangladesh": ("Dhaka", "BD", ["IUB"]),
    "American International University-Bangladesh": ("Dhaka", "BD", ["AIUB"]),
    "Shahjalal University of Science and Technology": ("Sylhet", "BD", ["SUST"]),
    "Sharif University of Technology": ("Tehran", "IR", ["Sharif"]),
    "University of Tehran": ("Tehran", "IR"),
    "Amirkabir University of Technology": ("Tehran", "IR"),
    "University of Peradeniya": ("Peradeniya", "LK"),
    "University of Moratuwa": ("Moratuwa", "LK"),
    "University of Colombo": ("Colombo", "LK", ["UCSC"]),
    "Tsinghua University": ("Beijing", "CN"),
    "Peking University": ("Beijing", "CN"),
    "Shanghai Jiao Tong University": ("Shanghai", "CN", ["SJTU", "Shanghai Univ. (SJTU+SHU HMs at WF'97)"]),
    "Fudan University": ("Shanghai", "CN"),
    "Zhejiang University": ("Hangzhou", "CN"),
    "Harbin Institute of Technology": ("Harbin", "CN", ["HIT"]),
    "Heilongjiang University": ("Harbin", "CN"),
    "Northeast Normal University": ("Changchun", "CN"),
    "Dalian University of Technology": ("Dalian", "CN", ["DUT"]),
    "Inner Mongolia University of Technology": ("Hohhot", "CN"),
    "Sun Yat-sen University": ("Guangzhou", "CN"),
    "Nanjing University": ("Nanjing", "CN"),
    "Chinese University of Hong Kong": ("Hong Kong", "HK", ["CUHK", "The Chinese University of Hong Kong"]),
    "Hong Kong University of Science and Technology": ("Hong Kong", "HK", ["HKUST"]),
    "University of Hong Kong": ("Hong Kong", "HK", ["HKU"]),
    "University of Macau": ("Macau", "MO"),
    "Kim Koo Museum": ("Seoul", "KR", ["Kim Koo Museum -Seoul"]),
    "National Olympics Memorial Youth Center": ("Tokyo", "JP", ["National Olympics Memorial Center"]),
    "Tsukuba International Congress Center": ("Tsukuba", "JP", ["Tsukuba Capio"]),
    "Seoul National University": ("Seoul", "KR", ["SNU"]),
    "KAIST": ("Daejeon", "KR", ["Korea Advanced Institute of Science and Technology"]),
    "National University of Mongolia": ("Ulaanbaatar", "MN", ["NUM"]),
    "Mongolian University of Science and Technology": ("Ulaanbaatar", "MN", ["MUST"]),
    "Nanyang Technological University": ("Singapore", "SG", ["NTU Singapore"]),
    "National University of Singapore": ("Singapore", "SG", ["NUS"]),
    "Chulalongkorn University": ("Bangkok", "TH"),
    "Ateneo de Manila University": ("Quezon City", "PH"),
    "University of the Philippines Diliman": ("Quezon City", "PH", ["UP Diliman"]),
    "Vietnam National University, Hanoi": ("Hanoi", "VN", ["VNU Hanoi"]),
    "Ho Chi Minh City University of Technology": ("Ho Chi Minh City", "VN", ["HCMUT"]),
    "University of Information Technology, Yangon": ("Yangon", "MM", ["UIT Yangon"]),
    "Universiti Malaya": ("Kuala Lumpur", "MY", ["University of Malaya", "UM"]),
    # Southeast USA / misc North America (division labels in the CMS)
    "Florida International University": ("Miami", "US", "FL", ["FIU"]),
    "University of West Florida": ("Pensacola", "US", "FL", ["UWF"]),
    "Mercer University": ("Macon", "US", "GA"),
    "Samford University": ("Birmingham", "US", "AL"),
    "Florida State University": ("Tallahassee", "US", "FL", ["FSU"]),
    "Middle Georgia State University": ("Macon", "US", "GA", ["MGSU", "Middle Georgia State Unversity"]),
    "University of North Georgia": ("Dahlonega", "US", "GA", ["UNG"]),
    "College of Charleston": ("Charleston", "US", "SC", ["CofC"]),
    "Augusta University": ("Augusta", "US", "GA"),
    "Webster University": ("Webster Groves", "US", "MO"),
    "Purdue University": ("West Lafayette", "US", "IN", ["Purdue"]),
    "Purdue University Northwest": ("Hammond", "US", "IN"),
    "Clarkson University": ("Potsdam", "US", "NY"),
    "University of Texas at San Antonio": ("San Antonio", "US", "TX", ["UTSA"]),
    "University of Texas at Dallas": ("Richardson", "US", "TX", ["UTD"]),
    "University of Houston": ("Houston", "US", "TX", ["UH"]),
    "University of Oklahoma": ("Norman", "US", "OK", ["OU", "Oklahoma University"]),
    "University of Tulsa": ("Tulsa", "US", "OK", ["Tulsa"]),
    "Columbia University": ("New York", "US", "NY"),
    "Harvard": ("Cambridge", "US", "MA"),
    "Boston College": ("Boston", "US", "MA"),
    "Acadia University": ("Wolfville", "CA", "NS"),
    "College of the Holy Cross": ("Worcester", "US", "MA"),
    "Sheridan College": ("Oakville", "CA", "ON", ["Sheridan Inst. of Tech", "Sheridan Institute of Technology"]),
    "University of Virginia": ("Charlottesville", "US", "VA", ["UVA"]),
    "North Carolina State University": ("Raleigh", "US", "NC", ["NCSU"]),
    "Western New England College": ("Springfield", "US", "MA", ["Western New England University"]),
    "University of Illinois Urbana-Champaign": ("Urbana", "US", "IL", ["University of Illinois at Urbana/Champaign", "UIUC", "University of Illinois at Urbana-Champaign"]),
    "Stanford University": ("Stanford", "US", "CA"),
    "Princeton University": ("Princeton", "US", "NJ"),
    "Yale University": ("New Haven", "US", "CT", ["Yale"]),
    "Auburn University": ("Auburn", "US", "AL"),
    "HSGS Tran Phu": ("Haiphong", "VN", ["Tran Phu High School for the Gifted"]),
    "Avans Hogeschool": ("'s-Hertogenbosch", "NL", ["Hogeschool 's-Hertogenbosch"]),
    "Technische Universität Darmstadt": ("Darmstadt", "DE", ["Darmstadt University of Technology", "TU Darmstadt", "TUDa"]),
    "James Madison University": ("Harrisonburg", "US", "VA", ["JMU", "King Hall", "ICAT/CS Bldg"]),
    "Liberty University": ("Lynchburg", "US", "VA"),
    "University of Kentucky": ("Lexington", "US", "KY", ["UK Lexington"]),
    "Lake Superior State University": ("Sault Ste. Marie", "US", "MI", ["LSSU"]),
    "Westfield State University": ("Westfield", "US", "MA", ["Westfield State College", "WSU Westfield"]),
    "Southeastern Louisiana University": ("Hammond", "US", "LA", ["SELU"]),
    "McMaster University": ("Hamilton", "CA", "ON", ["McMaster Site", "McMaster"]),
    "Touro University": ("New York", "US", "NY", ["Touro College"]),
    "Portland State University": ("Portland", "US", "OR", ["PSU Portland"]),
    "Western Washington University": ("Bellingham", "US", "WA", ["Western Washington Univ", "WWU"]),
    "Tufts University": ("Medford", "US", "MA", ["Tufts"]),
    "University of Technology, Jamaica": ("Kingston", "JM", ["UTECH", "UTech Jamaica"]),
    "University of Southampton": ("Southampton", "GB", ["Uni of Southampton", "Soton", "ECS"]),
    "University of Edinburgh": ("Edinburgh", "GB", ["Department of Informatics"]),
    "University of Sussex": ("Brighton", "GB"),
    "South Ural State University": ("Chelyabinsk", "RU", ["SouthUral State University", "SUSU"]),
    "Ghent University": ("Ghent", "BE", ["UGent", "Ugent's preliminaries ICPC", "Therminal"]),
    "Binghamton University": ("Binghamton", "US", "NY", ["SUNY Binghamton"]),
    "Rockhurst University": ("Kansas City", "US", "MO", ["Rockhurst College"]),
    "Arkansas State University": ("Jonesboro", "US", "AR"),
    "University of Missouri - Rolla": ("Rolla", "US", "MO", ["Missouri University of Science and Technology", "Missouri S&T", "UMR"]),
    "University of Illinois Chicago": ("Chicago", "US", "IL", ["University of Illinois - Chicago", "UIC", "University of Illinois at Chicago"]),
    "Colorado State University": ("Fort Collins", "US", "CO", ["CSU", "Colorado State Univeristy"]),
    "Neumont College of Computer Science": ("South Jordan", "US", "UT", ["Neumont University", "Neumont"]),
    "Florida Institute of Technology": ("Melbourne", "US", "FL", ["Florida Tech"]),
    "Beijing University of Chemical Technology": ("Beijing", "CN", ["BUCT", "Beijing Univ. of Chemical Technology"]),
    "Beijing University of Posts and Telecommunications": ("Beijing", "CN", ["BUPT", "Beijing Univ of Posts&Telecommunications"]),
    "Nanjing University of Aeronautics and Astronautics": ("Nanjing", "CN", ["NUAA", "Nanjing Univ. of A & A", "Nanjing Univ. of Aeronautics&Astronautics", "Nanjing Univ. of Aeronautics&Astronautics Programmig", "Nanjing Univ. of Aronautics&Astronautics Programming Contest_1"]),
    "Jilin University": ("Changchun", "CN", ["JiLin University", "JLU"]),
    "Heilongjiang Institute of Technology": ("Harbin", "CN", ["HLJIT"]),
    "Harbin Engineering University": ("Harbin", "CN", ["HRBEU", "HEU"]),
    "Inner Mongolia University": ("Hohhot", "CN", ["IMU"]),
    "Inner Mongolia Normal University": ("Hohhot", "CN", ["Inner Mongolia Normal Univ"]),
    "Cornell University": ("Ithaca", "US", "NY"),
    "Carnegie Mellon University": ("Pittsburgh", "US", "PA", ["CMU"]),
    "University of Waterloo": ("Waterloo", "CA", "ON"),
    "University of Toronto": ("Toronto", "CA", "ON"),
    "York University": ("Toronto", "CA", "ON"),
    "Georgetown University": ("Washington", "US", "DC"),
    "Temple University": ("Philadelphia", "US", "PA"),
    "Marshall University": ("Huntington", "US", "WV"),
    "Indiana University": ("Bloomington", "US", "IN", ["Indiana University Bloomington"]),
    "Rice University": ("Houston", "US", "TX"),
    "Brown University": ("Providence", "US", "RI"),
    "Trinity University": ("San Antonio", "US", "TX"),
    "Lincoln University": ("Jefferson City", "US", "MO"),
    # Europe additions
    "Université catholique de Louvain": ("Ottignies-Louvain-la-Neuve", "BE", ["UCLouvain", "UCL"]),
    "Université de Mons": ("Mons", "BE", ["UMONS", "BAPC Preliminaries at UMONS", "Plaine de Nimy"]),
    "University of Manchester": ("Manchester", "GB", ["Manchester Uni"]),
    "Dublin City University": ("Dublin", "IE", ["DCU", "Eng/Computing, DCU"]),
    "University College Dublin": ("Dublin", "IE", ["UCD", "Computer Science & Informatics"]),
    "Trinity College Dublin": ("Dublin", "IE", ["TCD"]),
    "Queen's University Belfast": ("Belfast", "GB", ["Queens University Belfast", "QUB"]),
    "Aberystwyth University": ("Aberystwyth", "GB"),
    "University of Oxford": ("Oxford", "GB"),
    "Ostfalia University of Applied Sciences": ("Wolfenbüttel", "DE", ["Wolfenbuettel (Ostfalia)", "Ostfalia", "Fakultaet Informatik"]),
    "Johannes Gutenberg University Mainz": ("Mainz", "DE", ["Universitaet Mainz", "Universität Mainz"]),
    "Pavol Jozef Šafárik University in Košice": ("Košice", "SK", ["UPJŠ Košice", "UPJŠ", "UPJS Kosice"]),
    "University of Amsterdam": ("Amsterdam", "NL", ["UvA", "Universiteit van Amsterdam", "Amsterdam Programming Contest (Universiteit van Amsterdam)"]),
    "Télécom Paris": ("Palaiseau", "FR", ["Telecom Paris", "Télécom ParisTech"]),
    "Universidad de Murcia": ("Murcia", "ES"),
    "Universidade da Coruña": ("A Coruña", "ES", ["UDC"]),
    "Lappeenranta University of Technology": ("Lappeenranta", "FI", ["LUT"]),
    "UiT The Arctic University of Norway, Narvik": ("Narvik", "NO", ["UiT - Narvik", "UiT Narvik", "Narvik University College"]),
    "NTNU Gjøvik": ("Gjøvik", "NO", ["Gjøvik University College"]),
    "UiT The Arctic University of Norway": ("Tromsø", "NO", ["UiT - Tromsø", "UiT Tromsø", "UiT", "University of Tromsø"]),
    # Northern Eurasia additions
    "Far Eastern Federal University": ("Vladivostok", "RU", ["FEFU", "Far Eastern SU", "Far Eastern State University", "FESU"]),
    "Rybinsk State Aviation Technical University": ("Rybinsk", "RU", ["RSATU", "Rybinsk SAAT"]),
    "Belarusian State University": ("Minsk", "BY", ["BSU", "Belarus State University"]),
    "ITMO University": ("Saint Petersburg", "RU", ["ITMO", "St. Petersburg IFMO", "SPb IFMO", "St. Petersburg State University of IT, Mechanics and Optics", "SPbSU ITMO", "SPb ITMO"]),
    "National Aerospace University KhAI": ("Kharkiv", "UA", ["National Aerospace University “KhAI”", "KhAI"]),
    "National University of Life and Environmental Sciences of Ukraine": ("Kyiv", "UA", ["NULES"]),
    "Ternopil Volodymyr Hnatiuk National Pedagogical University": ("Ternopil", "UA", ["Ternopil V. Hnatiuk National Pedagogical University"]),
    # Latin America additions
    "Universidad Nacional Chorotega": ("Nicoya", "CR", ["Universidad Nacional Chorotega - Nicoya", "Universidad Nacional Sede Regional Chorotega"]),
    "Universidad Privada Franz Tamayo": ("El Alto", "BO", ["UNIFRANZ", "UNIFRANZ - El Alto"]),
    "Universidad San Francisco Xavier de Chuquisaca": ("Sucre", "BO", ["USFX", "Chuquisaca"]),
    "Universidad Amazónica de Pando": ("Cobija", "BO"),
    "Instituto Tecnológico de Santo Domingo": ("Santo Domingo", "DO", ["INTEC"]),
    "Pontificia Universidad Católica Madre y Maestra": ("Santiago de los Caballeros", "DO", ["PUCMM"]),
    "Universidad de San Carlos de Guatemala": ("Guatemala City", "GT", ["USAC", "Universidad de San Carlos"]),
    "Universidad Veracruzana": ("Xalapa", "MX"),
    "Universidad Autónoma de Yucatán": ("Mérida", "MX", ["Universidad Autonoma de Yucatan", "Autonoma de Yucatan", "UADY"]),
    "Universidad Autónoma de Sinaloa": ("Culiacán", "MX", ["UAS"]),
    "Universidad Autónoma de Tamaulipas": ("Ciudad Victoria", "MX", ["UAT"]),
    "Universidad Autónoma del Estado de Hidalgo": ("Pachuca", "MX", ["UAEH"]),
    "Universidad del Valle de Atemajac": ("Zapopan", "MX", ["UNIVA"]),
    "Universidad Panamericana Campus Bonaterra": ("Aguascalientes", "MX", ["Panamericana Bonaterra", "Universidad Panamericana Bonaterra"]),
    "Centro de Investigación en Matemáticas": ("Guanajuato", "MX", ["CIMAT", "Centro de Investigacion en Matematicas"]),
    "Universidad Anáhuac Oaxaca": ("Oaxaca", "MX", ["Anahuac Oaxaca", "Universidad Anahuac Oaxaca"]),
    "Universidad Michoacana de San Nicolás de Hidalgo": ("Morelia", "MX", ["UMSNH"]),
    "Universidad Popular Autónoma del Estado de Puebla": ("Puebla", "MX", ["UPAEP"]),
    "Instituto Tecnológico de la Laguna": ("Torreón", "MX", ["ITLag"]),
    "Instituto Tecnológico Superior del Sur de Guanajuato": ("Uriangato", "MX", ["ITSUR", "Tecnologico Superior del Sur de Guanajuato", "Instituto Tecnologico Superior del Sur de Guanajuato"]),
    "Instituto Tecnológico Superior de Guanajuato": ("Puentecillas", "MX", ["ITESG", "Instituto Tecnologico Superior de Guanajuato", "Tecnologico Superior de Guanajuato"]),
    "Universidade Federal de Pernambuco": ("Recife", "BR", ["UFPE"]),
    "Universidade Federal do Amazonas": ("Manaus", "BR", ["UFAM"]),
    "Universidade de Fortaleza": ("Fortaleza", "BR", ["UNIFOR", "UNIFOR - Universidade de Fortaleza"]),
    "Universidade Federal do Maranhão": ("São Luís", "BR", ["UFMA"]),
    "Universidade Federal do Espírito Santo": ("Vitória", "BR", ["UFES"]),
    "Universidade Federal do Tocantins": ("Palmas", "BR", ["UFT"]),
    "Universidade Estadual de Feira de Santana": ("Feira de Santana", "BR", ["UEFS"]),
    "Centro Universitário do Triângulo": ("Uberlândia", "BR", ["UNITRI"]),
    "Centro Universitário Serra dos Órgãos": ("Teresópolis", "BR", ["UNIFESO"]),
    "Universidade Federal do Piauí": ("Teresina", "BR", ["UFPI"]),
    "Universidade Federal do Rio Grande": ("Rio Grande", "BR", ["FURG"]),
    "Universidade Federal da Bahia": ("Salvador", "BR", ["UFBA"]),
    "Universidade Federal do Vale do São Francisco": ("Juazeiro", "BR", ["UNIVASF"]),
    "Centro Universitário IESB": ("Brasília", "BR", ["IESB"]),
    "CEFET-MG Timóteo": ("Timóteo", "BR", ["CEFET-MG"]),
    "Faculdade de Balsas": ("Balsas", "BR"),
    "Faculdade de Imperatriz": ("Imperatriz", "BR", ["FACIMP"]),
    "Escola Superior de Marketing": ("Olinda", "BR", ["AESO"]),
    "Universidad Austral de Chile": ("Valdivia", "CL", ["UACH", "Valdivia (UACH)", "Valdivia (Universidad Austral de Chile)"]),
    "Universidad Católica del Norte": ("Coquimbo", "CL", ["UCN", "Coquimbo / La Serena (UCN)", "Coquimbo (Universidad Católica del Norte)"]),
    "Universidad de Talca": ("Curicó", "CL", ["UTalca", "Curicó (UTalca)", "Universidad de Talca (Curicó)"]),
    "Universidad Católica del Maule": ("Talca", "CL", ["Talca (UCM)", "Talca (Universidad Católica del Maule)"]),
    "Universidad de Concepción": ("Concepción", "CL", ["UdeC", "Concepción (UdeC)", "Concepción (Universidad de Concepción)"]),
    "Universidad Técnica Federico Santa María": ("Valparaíso", "CL", ["UTFSM"]),
    "Universidad Técnica Federico Santa María (Santiago)": ("Santiago", "CL", ["Santiago (UTFSM)"]),
    "Universidad Católica de Temuco": ("Temuco", "CL", ["UCT", "Temuco (UCT)"]),
    # Africa & Arab additions
    "Arab Academy for Science, Technology and Maritime Transport - Abu Qir": ("Alexandria", "EG", ["AAST Abu Keer", "AAST Alexandria", "AAST Abu Qir"]),
    "Al-Balqa Applied University": ("Al-Salt", "JO", ["Balqa'", "BAU"]),
    "Tishreen University": ("Latakia", "SY", ["Tishreen"]),
    "Instituto Superior de Tecnologias de Informação e Comunicação": ("Luanda", "AO", ["ISUTIC"]),
    # Asia additions
    "VNU University of Engineering and Technology": ("Hanoi", "VN", ["UET VNU", "University of Engineering and Technology VNU", "VNU-UET"]),
    "Monash University": ("Melbourne", "AU", "VIC", ["Monash"]),
    "Charles Darwin University": ("Darwin", "AU", "NT"),
    "ABV-IIITM Gwalior": ("Gwalior", "IN", ["Gwalio India", "IIITM Gwalior", "Atal Bihari Vajpayee Indian Institute of Information Technology and Management"]),
    "Sejong University": ("Seoul", "KR"),
    "Universidad de Costa Rica Sede del Pacífico": ("Puntarenas", "CR", ["Universidad de Costa Rica Pacífico", "UCR Pacífico"]),
    "Universidad Rafael Landívar": ("Guatemala City", "GT", ["URL"]),
    "Universidad del Istmo": ("Guatemala City", "GT", ["Universidad del Itsmo de Guatemala", "Universidad del Itsmo GT"]),
    "Instituto Tecnológico Superior del Oriente del Estado de Hidalgo": ("Apan", "MX", ["ITESA"]),
    "Instituto Tecnológico Superior del Occidente del Estado de Hidalgo": ("Mixquiahuala de Juárez", "MX", ["Instituto Tecnologico Superior del Occidente del Estado de Hidalgo", "ITSOEH"]),
    "Universidad Tecnológica de la Mixteca": ("Huajuapan de León", "MX", ["Tecnologica de la Mixteca", "Universidad Tecnologica de la Mixteca", "UTM"]),
    "Instituto Tecnológico del Istmo": ("Juchitán de Zaragoza", "MX"),
    "Instituto Tecnológico de Tehuacán": ("Tehuacán", "MX", ["Instituto Tecnológico de Tehaucan"]),
    "Instituto Tecnológico Superior de Teziutlán": ("Teziutlán", "MX", ["Instituto Tecnológico Superior de Tezuitlán", "Instituto Tecnologico Superior de Teziutlan"]),
    "Instituto Tecnológico Superior de Comalcalco": ("Comalcalco", "MX", ["Instituto Tecnológico Superior de Comalcaco"]),
    "Universidad del Caribe": ("Cancún", "MX", ["Unicaribe"]),
    "Instituto Tecnológico Superior Zacatecas Sur": ("Tlaltenango de Sánchez Román", "MX"),
    "Instituto Tecnológico Superior Zacatecas Norte": ("Río Grande", "MX"),
    "Instituto Tecnológico Superior de Huetamo": ("Huetamo de Núñez", "MX"),
    "Instituto Tecnológico Superior de Tacámbaro": ("Tacámbaro de Codallos", "MX"),
    "Instituto Tecnológico de Zitácuaro": ("Heróica Zitácuaro", "MX", ["Instituto Tecnologico de Zitacuaro"]),
    "Instituto Tecnológico Superior de Centla": ("Frontera", "MX"),
    "Instituto Tecnológico y de Estudios Superiores de Zamora": ("Zamora", "MX", ["ITESZ"]),
    "Instituto Tecnológico Superior Juan Rodríguez Clara": ("Juan Rodríguez Clara", "MX", ["Instituto Tecnológico Superior Juan Rodriguez Clara"]),
    "Instituto Tecnológico Superior Nuevo Casas Grandes": ("Nuevo Casas Grandes", "MX"),
    "Instituto Tecnológico Superior San Martín Texmelucan": ("San Martín Texmelucan de Labastida", "MX"),
    "Universidad Autónoma de Coahuila": ("Saltillo", "MX", ["Universidad Autonoma de Coahuila", "Autonoma de Coahuila", "UAdeC"]),
    "Universidad Autónoma de Tlaxcala": ("Tlaxcala", "MX", ["Universidad Autonoma de Tlaxcala", "Autonoma de Tlaxcala", "UATx"]),
    "Universidad Autónoma de Aguascalientes": ("Aguascalientes", "MX", ["Universidad Autonoma de Aguascalientes", "Autonoma de Aguascalientes", "UAA"]),
    "Universidad Autónoma de Chihuahua": ("Chihuahua", "MX", ["Universidad Autonoma de Chihuahua", "Autonoma de Chihuahua", "UACH Chihuahua"]),
    "Universidad Autónoma de Zacatecas": ("Zacatecas", "MX", ["Universidad Autonoma de Zacatecas", "Club de Programación Competitiva UAZ", "UAZ"]),
    "Universidad Autónoma de Nuevo León": ("San Nicolás de los Garza", "MX", ["UANL", "Facultad de Ciencias Físico Matemáticas - UANL"]),
    "UNAM Facultad de Ciencias": ("Mexico City", "MX", ["Facultad de Ciencias UNAM", "UNAM Facultad de Ciencias - Club de Programación Competitiva"]),
    "UNAM Facultad de Ingeniería": ("Mexico City", "MX", ["Facultad de Ingeniería UNAM", "UNAM Facultad de Ingeniería - Club de Programación Competitiva"]),
    "Centro de Nanociencias y Nanotecnología UNAM": ("Ensenada", "MX", ["Centro de Nanociencias y Nanotecnologia UNAM"]),
    "Universidad Panamericana Campus Ciudad de México": ("Mexico City", "MX"),
    "Universidad del Valle de México Campus Guadalajara Sur": ("Guadalajara", "MX"),
    "Universidad Marista de Guadalajara": ("Guadalajara", "MX"),
    "CETYS Universidad": ("Mexicali", "MX", ["CETYS"]),
    "Instituto Tecnológico Superior de El Mante": ("Ciudad Mante", "MX", ["Sistemas Computacionales ITS Mante", "Instituto Tecnologico Superior de El Mante", "ITS Mante"]),
    "Universidad Politécnica de Durango": ("Victoria de Durango", "MX", ["Politecnica de Durango", "Universidad Politecnica de Durango"]),
    "Universidad Tecnológica de Aguascalientes": ("Aguascalientes", "MX", ["UTA"]),
    "Instituto Tecnológico de Aguascalientes": ("Aguascalientes", "MX", ["ITA"]),
    "Instituto Tecnológico Superior de San Pedro de las Colonias": ("San Pedro", "MX", ["Tecnologico Superior de San Pedro de las Colonias", "Instituto Tecnologico Superior de San Pedro de las Colonias"]),
    "Instituto Tecnológico de Chihuahua II": ("Chihuahua", "MX"),
    "Instituto Tecnológico de Oaxaca": ("Oaxaca", "MX", ["Instituto Tecnologico de Oaxaca", "ITO"]),
    "Universidad de Guanajuato": ("Guanajuato", "MX", ["UG"]),
    "Universidad de Colima": ("Colima", "MX", ["UCOL"]),
    "Instituto Tecnológico de Veracruz": ("Veracruz", "MX", ["Instituto Tecnologico de Veracruz", "Tecnologico de Veracruz", "Comunidad Estudiantil de Programación Competitiva de Instituto Tecnológico de Veracruz", "ITV"]),
    "Instituto Tecnológico de Querétaro": ("Santiago de Querétaro", "MX", ["ITQ"]),
    "Brigham Young University–Hawaii": ("Laie", "US", "HI", ["BYU-Hawaii", "BYU Hawaii", "BYUH"]),
    "Marymount University": ("Arlington", "US", "VA"),
    "Principia College": ("Elsah", "US", "IL"),
    "Milwaukee School of Engineering": ("Milwaukee", "US", "WI", ["Milwaukee School of Engineering, WI", "MSOE"]),
    "Gustavus Adolphus College": ("Saint Peter", "US", "MN"),
    "Kean University": ("Union", "US", "NJ"),
    "Texas A&M University": ("College Station", "US", "TX", ["Texas A & M University", "Texas A&M", "TAMU"]),
    "University of Michigan": ("Ann Arbor", "US", "MI", ["Michigan Site"]),
    "University of Winnipeg": ("Winnipeg", "CA", "MB"),
    "Brandon University": ("Brandon", "CA", "MB", ["Brandon University - MICRO"]),
    "Jomo Kenyatta University of Agriculture and Technology": ("Nairobi", "KE", ["JKUAT"]),
    "Fiji National University": ("Suva", "FJ", ["FNU"]),
    "Western Pacific University": ("Ialibu", "PG"),
    "Admiral Makarov National University of Shipbuilding": ("Mykolaiv", "UA", ["NUOS"]),
    "Central Ukrainian National Technical University": ("Kropyvnytskyi", "UA", ["The Kirovohrad Volodymyr Vynnychenko State Pedagogical University", "Kirovohrad National Technical University"]),
    "Khmelnytskyi National University": ("Khmelnytskyi", "UA", ["Khmelnitsky National University"]),
    "Vinnytsia Mykhailo Kotsiubynskyi State Pedagogical University": ("Vinnytsia", "UA"),
    "Taras Shevchenko National University of Kyiv": ("Kyiv", "UA", ["KNU", "Kyiv National University", "Taras Shevchenko Kyiv National University"]),
    "Hanoi National University of Education": ("Hanoi", "VN", ["HNUE"]),
    "Hanoi University of Science and Technology": ("Hanoi", "VN", ["HUST"]),
    "Posts and Telecommunications Institute of Technology": ("Hanoi", "VN", ["PTIT"]),
    "University of Information Technology": ("Ho Chi Minh City", "VN", ["UIT", "VNU-HCM University of Information Technology"]),
    "Ho Chi Minh City University of Science": ("Ho Chi Minh City", "VN", ["Ho Chi Minh University of Science", "HCMUS"]),
    "Yarmouk University": ("Irbid", "JO"),
    "The Hashemite University": ("Zarqa", "JO", ["Hashemite University"]),
    "Mutah University": ("Al-Karak", "JO"),
    "Al-Zaytoonah University of Jordan": ("Amman", "JO"),
    "Applied Science Private University": ("Amman", "JO", ["ASU"]),
    "Mohammed VI Polytechnic University": ("Ben Guerir", "MA", ["UM6P"]),
    "Adam Mickiewicz University": ("Poznań", "PL", ["AMU", "Amam Mickiewicz University"]),
    "UCLan Cyprus": ("Larnaca", "CY", ["UCLAN CYPRUS", "University of Central Lancashire Cyprus"]),
    "Universidad de Oriente (Cuba)": ("Santiago de Cuba", "CU", ["Universidad de Oriente (UO)", "UO"]),
    "Universidad de las Ciencias Informáticas": ("Havana", "CU", ["UCI", "Universidad de las Ciencias Informaticas"]),
    "Universidad Central Marta Abreu de Las Villas": ("Santa Clara", "CU", ["UCLV"]),
    "University of the Virgin Islands": ("Charlotte Amalie", "VI", ["UVI", "UVI-STX and UVI-STT"]),
    "University of the West Indies, St. Augustine": ("Saint Augustine", "TT", ["UWI-TTO", "UWI St. Augustine"]),
    "Universidad Privada del Valle": ("Cochabamba", "BO", ["UNIVALLE"]),
    "Universidad Autónoma del Beni José Ballivián": ("Trinidad", "BO", ['Universidad Autónoma del Beni "José Ballivián"', "UAB Trinidad"]),
    "Universidad Tecnológica Boliviana": ("La Paz", "BO", ["Universidad Tecnologica Boliviana", "UTB"]),
    "Universidad Técnica de Oruro": ("Oruro", "BO", ["UTO", "Universidad Tecnica de Oruro"]),
    "Vilnius Gediminas Technical University": ("Vilnius", "LT", ["VILNIUS TECH", "Vilnius Tech", "VGTU"]),
    "University of Tasmania": ("Hobart", "AU", "TAS", ["UT", "UTAS"]),
    "University of Technology Sydney": ("Sydney", "AU", "NSW", ["UTS"]),
    "Arab Open University Bahrain": ("Manama", "BH", ["AOU Bahrain"]),
    "University of Groningen": ("Groningen", "NL", ["RUG", "RUG Prelim for BAPC21"]),
    "Universidad Autónoma de Querétaro": ("Santiago de Querétaro", "MX", ["UAQ", "UAQ Facultad de Informatica", "Universidad Autonoma de Queretaro, Fac. Informatica", "Universidad Autonoma de Queretaro"]),
    "Tecnológico de Monterrey Campus Querétaro": ("Santiago de Querétaro", "MX", ["ITESM Campus Querétaro", "ITESM Campus Queretaro", "ITESM C. Queretaro", "ITESM Queretaro", "ITESM Qro"]),
    "Tecnológico de Monterrey Campus Central de Veracruz": ("Córdoba", "MX", ["ITESM Campus Central de Veracruz", "ITESM C Central Veracruz"]),
    "Instituto Tecnológico de Durango": ("Victoria de Durango", "MX", ["IT Durango", "Instituto Tecnologico de Durango"]),
    "Universidade do Estado da Bahia": ("Salvador", "BR", ["UNEB"]),
    "Instituto Federal da Bahia": ("Salvador", "BR", ["IFBA"]),
    "SENAI CIMATEC": ("Salvador", "BR", ["CIMATEC"]),
    "Universidade Católica do Salvador": ("Salvador", "BR", ["UCSal", "UCSAL"]),
    "Centro Universitário da Bahia": ("Salvador", "BR", ["FIB - Centro Universitário da Bahia", "ESTACIO-FIB", "FIB"]),
    "CEFET-MT": ("Cuiabá", "BR", ["Instituto Federal de Mato Grosso", "IFMT"]),
    "Sun Yat-sen University": ("Guangzhou", "CN", ["Zhongshan University", "SYSU"]),
    "Xihua University": ("Chengdu", "CN"),
    "Hangzhou Dianzi University": ("Hangzhou", "CN", ["HDU"]),
    "Beijing Normal University": ("Beijing", "CN", ["BNU"]),
    "Fujian Normal University": ("Fuzhou", "CN"),
    "National Chiao Tung University": ("Hsinchu", "TW", ["NCTU", "National Chiao Tung University Campus"]),
    "National Yang Ming Chiao Tung University": ("Hsinchu", "TW", ["NYCU"]),
    "Aston University": ("Birmingham", "GB"),
    "University of Warwick": ("Coventry", "GB", ["University of Warwick (Warwick only)"]),
    "Hamilton College": ("Clinton", "US", "NY"),
    "University of Delaware": ("Newark", "US", "DE"),
    "University of Oregon": ("Eugene", "US", "OR"),
    "University of Washington": ("Seattle", "US", "WA", ["UW"]),
    "University of Missouri": ("Columbia", "US", "MO", ["Mizzou"]),
    "Tecnológico de Monterrey Campus Santa Fe": ("Mexico City", "MX", ["ITESM Campus Santa Fe", "ITESM Santa Fe", "Tec de Monterrey Campus Santa Fe"]),
    "Tecnológico de Monterrey Campus Ciudad de México": ("Mexico City", "MX", ["ITESM Campus Ciudad de Mexico", "ITESM Ciudad de Mexico", "Tecnológico de Monterrey Campus Ciudad", "Tec de Monterrey Campus Ciudad de México", "ITESM CCM"]),
    "Tecnológico de Monterrey Campus Estado de México": ("Atizapán de Zaragoza", "MX", ["ITESM Campus Estado de Mexico", "ITESM Estado de Mexico", "Tecnológico de Monterrey Campus Estado", "Tec de Monterrey Campus Estado de México", "ITESM CEM"]),
    "Instituto Tecnológico de Nuevo León": ("Guadalupe", "MX", ["Instituto Tecnologico de Nuevo Leon", "Tecnologico de Nuevo Leon", "ITNL"]),
    "Universidad Iberoamericana Torreón": ("Torreón", "MX", ["Universidad Iberoamericana Plantel Laguna", "Ibero Torreón"]),
    "Instituto Tecnológico Superior de la Región Sierra": ("Teapa", "MX", ["Instituti Tecnológico Superior Región Sierra", "Instituto Tecnológico Superior Región Sierra"]),
    "Instituto Tecnológico Superior de la Sierra Norte de Puebla": ("Zacatlán", "MX", ["Instituto Tecnologico Superior de la Sierra del Norte de Puebla"]),
    "Instituto Tecnológico de Ciudad Jiménez": ("Ciudad Jiménez", "MX", ["Tecnológico de Cd. Jiménez", "Instituto Tecnológico de Cd. Jiménez"]),
    "Instituto Tecnológico de Lázaro Cárdenas": ("Ciudad Lázaro Cárdenas", "MX", ["Instituto Tecnologico de Lazaro Cardenas"]),
    "Universidad Iberoamericana León": ("León de los Aldama", "MX", ["Universidad Iberoamericana Campus Leon"]),
}

# city-name aliases the gazetteer lacks (spelling seen -> gazetteer name), country-scoped
CITY_FIXES = {
    ("RU", "krasonyarsk"): "Krasnoyarsk",
    ("RU", "ekaterinburg"): "Yekaterinburg",
    ("RU", "st petersburg"): "Saint Petersburg",
    ("RU", "st. petersburg"): "Saint Petersburg",
    ("RU", "saint-petersburg"): "Saint Petersburg",
    ("RU", "spb"): "Saint Petersburg",
    ("IN", "amritapuri"): None,       # a village: node made from text
    ("MA", "marrakech"): "Marrakesh",
    ("ZA", "grahamstown"): "Grahamstown",
    ("UA", "kiev"): "Kyiv",
    ("UA", "kharkov"): "Kharkiv",
    ("UA", "lvov"): "Lviv",
    ("KZ", "alma-ata"): "Almaty",
    ("JP", "aizu-wakamatsu"): "Aizuwakamatsu",
    ("JP", "aizu"): "Aizuwakamatsu",
    ("MY", "tronoh"): None,
    ("LK", "peradeniya"): None,
    ("CN", "hongkong"): "Hong Kong",
    ("MX", "ciudad de mexico"): "Mexico City",
    ("MX", "ciudad mexico"): "Mexico City",
    ("MX", "mexico d.f."): "Mexico City",
    ("MX", "mexico df"): "Mexico City",
    ("MX", "cdmx"): "Mexico City",
    ("GT", "guatemala"): "Guatemala City",
    ("PA", "panama"): "Panama City",
    ("KW", "kuwait"): "Kuwait City",
    ("BR", "brasilia"): "Brasília",
    ("BR", "sao paulo"): "São Paulo",
    ("VN", "saigon"): "Ho Chi Minh City",
    ("VN", "hcmc"): "Ho Chi Minh City",
    ("MM", "rangoon"): "Yangon",
    ("TW", "taipei"): "Taipei",
    ("HK", "hong kong"): "Hong Kong",
    ("MO", "macau"): "Macau",
    ("SG", "singapore"): "Singapore",
    ("PS", "west bank"): None,
    ("PS", "gaza strip"): "Gaza",
    ("EG", "sharm elshekh"): "Sharm el-Sheikh",
    ("EG", "sharm el-sheikh"): "Sharm el-Sheikh",
    ("EG", "sharm el sheikh"): "Sharm el-Sheikh",
    ("SA", "riyadah"): "Riyadh",
    ("CA", "charletown"): "Charlottetown",
    ("MX", "tlaquepaqur"): "Tlaquepaque",
    ("TW", "chia-yi county"): "Chiayi City",
    ("TW", "chiayi county"): "Chiayi City",
    ("TW", "chiayi"): "Chiayi City",
    ("TW", "chia-yi"): "Chiayi City",
    ("US", "newburg"): "Newberg",
    ("CN", "shenyang"): "Shenyang",
}

# single words that are places at country level in the CMS text (lowercase -> iso)
WORD_COUNTRY = {"west bank": "PS", "gaza strip": "PS", "crimea": "UA", "kerala": "IN", "hubei": "CN",
                "guangdong": "CN", "perak": "MY", "jalisco": "MX", "puerto rico": "PR", "lebanon": "LB",
                "syria": "SY", "chile": "CL", "india": "IN", "nigeria (west africa)": "NG", "dpr korea": "KP", "dprk": "KP",
                "democratic people's republic of korea": "KP", "inner mongolia": "CN", "cuban site": "CU",
                "cuban site (guests)": "CU", "cuban": "CU", "us virgin islands": "VI", "us virgin island": "VI"}


# --------------------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------------------
def site_entry_key(e: dict) -> tuple:
    return (e.get("type", ""), e.get("location", ""), e.get("name", ""), e.get("date", ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="resolve and report, write nothing")
    ap.add_argument("--review", default=str(ROOT / "data" / f"locations-review-{TODAY}.md"))
    args = ap.parse_args()

    gaz = Gazetteer()
    existing = yaml.safe_load(LOC_PATH.read_text()) if LOC_PATH.exists() else None
    tree = Tree(gaz, existing)
    known = load_known()
    res = Resolver(gaz, tree, known)
    # pre-create the gazetteer-less names
    for (cc, k), fix in CITY_FIXES.items():
        if fix:
            gaz.index[norm(k)] = gaz.lookup(fix, cc) + [c for c in gaz.index.get(norm(k), []) if c["countrycode"] != cc]
    for k, v in WORD_COUNTRY.items():
        if isinstance(v, str):
            gaz.country_by_name[norm_full(k)] = v

    cms = json.load((ROOT / "data" / "cms-sites.json").open())["contests"]
    series = catalogue.load_series()

    stats = Counter()
    unresolved = defaultdict(list)
    israel = []
    contest_sites: dict[str, list[dict]] = {}

    for sid, doc in series.items():
        region = doc["series"].get("region")
        # pre-CMS contests borrow the series' geographic area (its states disambiguate US towns)
        series_area = ""
        for c in doc["contests"]:
            for n in c.get("cms_ids") or []:
                a = clean_text((cms.get(str(n)) or {}).get("geographicArea") or "")
                if a:
                    series_area = series_area or a
        for c in doc["contests"]:
            cid = c["id"]
            entries: list[dict] = []
            cms_sites = []
            area_of = {}
            for n in c.get("cms_ids") or []:
                rec = cms.get(str(n))
                if rec:
                    cms_sites.extend(rec.get("sites") or [])
                    for s_ in rec.get("sites") or []:
                        area_of[s_["id"]] = clean_text(rec.get("geographicArea") or "")
            if cms_sites:
                stats["contests_with_cms_sites"] += 1
                for s in cms_sites:
                    stats["cms_sites"] += 1
                    loc_text = clean_text(s.get("location") or "")
                    name = clean_text(s.get("name") or "")
                    if s["type"] == "ADMINISTRATIVE" and (norm(loc_text) in ADMIN_WORDS or not loc_text and norm(name) in ADMIN_WORDS):
                        entries.append({"type": "administrative"})
                        stats["cms_sites_administrative"] += 1
                        continue
                    ctry = (s.get("country") or {}).get("a2") if isinstance(s.get("country"), dict) else None
                    if ctry:
                        ctry = ctry.upper()
                    ctx = f"{cid} cms site {s['id']}"
                    r = res.resolve_text(loc_text, region, ctx, country_hint=ctry, site_name=name,
                                         state_hint=s.get("state") or None, city_hint=s.get("city") or None,
                                         area=area_of.get(s["id"]))
                    if r["status"] == "administrative":
                        e = {"type": "administrative"}
                        if r.get("name"):
                            e["name"] = r["name"]
                        entries.append(e)
                        stats["cms_sites_administrative"] += 1
                        continue
                    if s["delivery"] == "ONLINE":
                        r["type"] = "online"
                    if s["type"] == "ADMINISTRATIVE":
                        r["type"] = "administrative"
                    e = {}
                    if r.get("location"):
                        e["location"] = r["location"]
                        stats["cms_sites_located"] += 1
                        stats[f"cms_level_{r['level']}"] += 1
                        if tree.country_of(r["location"]) == "IL":
                            israel.append(f"{ctx}: {name!r} / {loc_text!r} -> `{r['location']}`")
                    if r.get("name"):
                        e["name"] = r["name"]
                    if s.get("date") and s["date"] != c.get("date") and s["date"][:4] != "1970":
                        e["date"] = s["date"]
                    if r.get("type"):
                        e["type"] = r["type"]
                    if not e.get("location") and e.get("type") != "online":
                        stats["cms_sites_unresolved"] += 1
                        unresolved[sid].append(f"{cid} (cms site {s['id']}): name={name!r} location={loc_text!r}"
                                               + (f" city={s.get('city')!r}" if s.get("city") else "")
                                               + (f" state={s.get('state')!r}" if s.get("state") else "")
                                               + (f" area={clean_text(cms[str(c['cms_ids'][0])].get('geographicArea') or '')[:60]!r}" if c.get("cms_ids") else ""))
                    elif not e.get("location"):
                        stats["cms_sites_online_unlocated"] += 1
                    if e.get("location") or e.get("name") or e.get("type"):
                        entries.append(e)
            elif c.get("location"):
                stats["contests_free_text"] += 1
                for part in [p.strip() for p in c["location"].split(";") if p.strip()]:
                    stats["free_text_parts"] += 1
                    if norm(part) in ADMIN_WORDS:
                        entries.append({"type": "administrative"})
                        continue
                    if part.startswith("(") and part.endswith(")"):
                        unresolved[sid].append(f"{cid}: note-like location {part!r}")
                        stats["free_text_unresolved"] += 1
                        continue
                    r = res.resolve_text(part, region, f"{cid} location text", area=series_area or None)
                    e = {}
                    if r.get("location"):
                        e["location"] = r["location"]
                        stats["free_text_located"] += 1
                        if tree.country_of(r["location"]) == "IL":
                            israel.append(f"{cid}: {part!r} -> `{r['location']}`")
                    if r.get("name") and r.get("level") != "institution":
                        e["name"] = r["name"]
                    if r.get("type"):
                        e["type"] = r["type"]
                    if not e.get("location") and e.get("type") != "online":
                        stats["free_text_unresolved"] += 1
                        unresolved[sid].append(f"{cid}: location text {part!r}")
                    if e:
                        entries.append(e)
            # dedupe (ignoring the date; the dated copy wins), keep order
            by_key: dict[tuple, dict] = {}
            uniq = []
            for e in entries:
                k = (e.get("type", ""), e.get("location", ""), e.get("name", ""))
                if k in by_key:
                    if "date" in e and "date" not in by_key[k]:
                        by_key[k]["date"] = e["date"]
                    continue
                by_key[k] = e
                uniq.append(e)
            if uniq:
                contest_sites[cid] = uniq
                if any("location" in e for e in uniq):
                    stats["contests_with_located_site"] += 1
            stats["contests"] += 1

    # ---- possible duplicate institutions: same city, similar token sets ----
    dups = []
    by_city = defaultdict(list)
    for n in tree.nodes.values():
        if n["type"] == "institution":
            by_city[n["parent"]].append(n)
    for city, insts in sorted(by_city.items()):
        for i in range(len(insts)):
            for j in range(i + 1, len(insts)):
                a, b = insts[i], insts[j]
                ta = set(norm(a["name"]).split()) - SHORT_DROP
                tb = set(norm(b["name"]).split()) - SHORT_DROP
                if not ta or not tb:
                    continue
                jac = len(ta & tb) / len(ta | tb)
                if jac >= 0.5 or ta <= tb or tb <= ta:
                    dups.append(f"`{a['id']}` ({a['name']}) ~ `{b['id']}` ({b['name']})")

    # ---- counts ----
    type_counts = Counter(n["type"] for n in tree.nodes.values())
    n_review = sum(len(v) for v in unresolved.values()) + len(res.ambiguous) + len(dups) + len(israel) \
        + sum(len(v) for v in res.review.values()) + len(res.inferred)

    # ---- review file ----
    lines = [f"# Locations migration — review items ({TODAY})", "",
             "Generated by `tools/migrate_locations.py`. Everything here needs a human; the tree in",
             "`locations.yaml` and the `sites:` lists in `series/*.yaml` are usable as they stand, but the",
             "items below are either unresolved (no node emitted), a judgment call the tool made, or a",
             "possible merge it refused to make on its own.", "",
             "## Counts", "",
             f"- contests: {stats['contests']}; with CMS sites: {stats['contests_with_cms_sites']}; "
             f"with free-text location only: {stats['contests_free_text']}",
             f"- contests with ≥1 located site: {stats['contests_with_located_site']}",
             f"- CMS sites: {stats['cms_sites']}; administrative (no location by design): {stats['cms_sites_administrative']}; "
             f"located: {stats['cms_sites_located']} (institution {stats['cms_level_institution']}, city {stats['cms_level_city']}, "
             f"region {stats['cms_level_region']}, country {stats['cms_level_country']}); "
             f"online without a place: {stats['cms_sites_online_unlocated']}; unresolved: {stats['cms_sites_unresolved']}",
             f"- free-text parts: {stats['free_text_parts']}; located: {stats['free_text_located']}; unresolved: {stats['free_text_unresolved']}",
             f"- nodes: {sum(type_counts.values())} (" + ", ".join(f"{t} {type_counts[t]}" for t in ("country", "region", "city", "institution")) + ")",
             f"- review items: {n_review}", ""]
    lines += ["## Unresolved sites / strings (by series)", "",
              "No node was emitted; the site entry keeps the CMS label under `name`, the free-text `location` on the contest is untouched.", ""]
    for sid in sorted(unresolved):
        lines.append(f"### {sid}")
        lines.append("")
        lines += [f"- {x}" for x in unresolved[sid]]
        lines.append("")
    lines += ["## Ambiguous city picks", "",
              "The tool picked the most populous candidate within the series' region; the alternatives are listed.", ""]
    for key, (name, top, others, ctx) in sorted(res.ambiguous.items(), key=lambda kv: kv[1][0]):
        alt = "; ".join(f"{o['name']}, {o['countrycode']}{'-' + (gaz.admin_code(o) or '') if gaz.admin_code(o) else ''} ({o['population']:,})" for o in others)
        lines.append(f"- {name!r} -> {top['name']}, {top['countrycode']}"
                     f"{'-' + gaz.admin_code(top) if gaz.admin_code(top) else ''} ({top['population']:,}); alternatives: {alt} — first seen at {ctx}")
    lines.append("")
    lines += ["## Cities inferred from institution names", "",
              "The city was read off the institution's own name (\"University of X\", \"X University\", \"Campus X\"...). "
              "Usually right; wrong when the name is a person or a region (listed so a human can scan).", ""]
    for iid, (iname, cname, ctx) in sorted(res.inferred.items()):
        lines.append(f"- `{iid}`: {iname!r} -> {cname} (first seen at {ctx})")
    lines.append("")
    for section, items in sorted(res.review.items()):
        lines += [f"## {section}", ""] + [f"- {x}" for x in sorted(set(items))] + [""]
    lines += ["## Possible duplicate institutions (same city, overlapping names)", "",
              "Not merged automatically; merge by moving one name into the other's `aliases` and re-pointing sites.", ""]
    lines += [f"- {d}" for d in dups] + [""]
    lines += ["## Sites resolved to Israel", "",
              "ICPC placed Israel in SWERC (Europe) historically; confirm the region assignment of these series.", ""]
    lines += [f"- {x}" for x in israel] + [""]

    print(json.dumps(stats, indent=1, sort_keys=True))
    print("nodes:", dict(type_counts), "new:", len(tree.added))
    print("review items:", n_review)

    if args.dry_run:
        Path(args.review).write_text("\n".join(lines))
        print(f"dry run: only the review file written ({args.review})")
        return 0

    LOC_PATH.write_text(
        "# Location tree: country > region > city > institution (DEFINITIONS.md, Locations).\n"
        "# Maintained in-repo; built by tools/migrate_locations.py, edited by hand afterwards.\n"
        + yaml.dump(tree.dump(), Dumper=catalogue.Dumper, sort_keys=False, allow_unicode=True, width=100))
    changed = 0
    for sid, doc in series.items():
        touched = False
        new_contests = []
        for c in doc["contests"]:
            sites = contest_sites.get(c["id"])
            if sites is None:
                if "sites" in c:
                    del c["sites"]
                    touched = True
                new_contests.append(c)
                continue
            if c.get("sites") != sites:
                touched = True
            # place `sites` right after `venue`/`location`/`date`/`name`
            anchor = last_anchor(c)
            out = {}
            for k, v in c.items():
                if k == "sites":
                    continue
                out[k] = v
                if k == anchor:
                    out["sites"] = sites
            new_contests.append(out)
        if touched:
            doc["contests"] = new_contests
            catalogue.dump_series(sid, doc, TOOL)
            changed += 1
    Path(args.review).write_text("\n".join(lines))
    print(f"wrote locations.yaml ({len(tree.nodes)} nodes), {changed} series files, {args.review}")
    return 0


def last_anchor(c: dict) -> str:
    for k in ("venue", "location", "date", "name"):
        if k in c:
            return k
    return "id"


if __name__ == "__main__":
    sys.exit(main())
